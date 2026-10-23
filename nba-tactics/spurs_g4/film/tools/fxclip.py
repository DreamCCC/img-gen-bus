"""Fast footage FX: speed ramps, freeze-frame telestrator, punch-in zoom, flash, shake, ASS callouts.

usage (cwd = film/):  python tools/fxclip.py shots/s08.json [--stills t1,t2,...]

spec (paths relative to film/):
{
 "src": "raw/2606111127202702.mp4", "out": "out/s08/s08.mp4", "audio_db": -14,
 "segs": [
   {"kind": "play", "from": 120, "to": 204, "speed": 1},
   {"kind": "freeze", "at": 204, "dur": 1.2, "spot": [[820, 700, 170, 260]], "badge": "FREEZE"},
   {"kind": "play", "from": 204, "to": 250, "speed": 0.25, "badge": "SLOW-MO x0.25"}
 ],
 "zoom":  [[t, z, cx, cy], ...]     keyframes in output seconds, source px focus; smoothstep between keys
 "flash": [[t, strength, frames]],  "shake": [[t, dur, amp_px]],
 "callouts": [{"t": [t0, t1], "kind": "tag|stat|big|badge|ring|line|label", ...}]
}
Frame numbers are source frames (30 fps). speed < 1 uses minterpolate (cached under work/fxcache/).
freeze: background desaturates and darkens, `spot` ellipses [cx, cy, rx, ry] (source px) stay in colour.
Callout coordinates are OUTPUT px unless "src": true (then source px mapped through the zoom at t0).
  tag   {x, y, text, sub?, color?, to?: [px, py]}       name plate, bottom-centre at (x, y), optional leader line
  stat  {x, y, label, value, color?}                    small caps label over a big number
  big   {text, sub?, color?, y?}                        centred slam
  badge {text}                                          top-left badge (red slash)
  ring  {x, y, rx, ry, color?}                          floor ellipse (use on freezes)
  line  {a: [x, y], b: [x, y], text?, color?}           dashed measuring line with optional label at the middle
  label {x, y, text, color?, size?}                     plain bold text
Colours: red blue nyk orange silver green white gold.
Audio: original sound only on speed-1 segments at audio_db (a play segment may set its own "audio_db"; no ducking),
silence elsewhere.
Writes <out>.json manifest: segment output times, so the master mix can place sfx.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
FPS, W, H = 30, 1920, 1080
COL = {"red": (200, 16, 46), "blue": (29, 66, 138), "nyk": (0, 107, 182), "orange": (245, 132, 38),
       "silver": (196, 206, 212), "green": (43, 214, 123), "white": (246, 244, 242), "gold": (255, 200, 69),
       "navy": (10, 20, 40), "neg": (255, 59, 59)}


def ass_c(name: str) -> str:
    r, g, b = COL.get(name, COL["white"])
    return f"&H{b:02X}{g:02X}{r:02X}&"


def ts(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def smooth(a: float) -> float:
    a = min(1.0, max(0.0, a))
    return a * a * (3 - 2 * a)


class Src:
    def __init__(self, video: Path, cache: Path):
        self.video, self.cache = video, cache
        self.orig = cache / "orig"
        if not (self.orig / "0000.jpg").exists():
            self.orig.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-q:v", "2", "-start_number", "0",
                            str(self.orig / "%04d.jpg")], check=True)
        self.n = len(list(self.orig.glob("*.jpg")))

    def slow_dir(self, f0: int, f1: int, mul: int) -> Path:
        d = self.cache / f"slow_{f0}_{f1}_x{mul}"
        if not (d / "0000.jpg").exists():
            d.mkdir(parents=True, exist_ok=True)
            vf = (f"trim=start_frame={f0}:end_frame={f1 + 1},setpts=PTS-STARTPTS,"
                  f"minterpolate=fps={FPS * mul}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(self.video), "-vf", vf, "-q:v", "2",
                            "-start_number", "0", str(d / "%04d.jpg")], check=True)
        return d

    def frame(self, ref) -> np.ndarray:
        if ref[0] == "o":
            return cv2.imread(str(self.orig / f"{min(ref[1], self.n - 1):04d}.jpg"))
        p = ref[1] / f"{ref[2]:04d}.jpg"
        if not p.exists():
            files = sorted(ref[1].glob("*.jpg"))
            p = files[-1]
        return cv2.imread(str(p))


def timeline(spec, src: Src):
    """-> list of (frame_ref, seg_index, local_t) per output frame, and segment table."""
    frames, table, t = [], [], 0.0
    for i, s in enumerate(spec["segs"]):
        start = len(frames)
        if s["kind"] == "play":
            sp = s.get("speed", 1)
            if sp >= 1:
                for f in range(s["from"], s["to"]):
                    frames.append((("o", f), i))
            else:
                mul = max(1, round(1 / sp))
                d = src.slow_dir(s["from"], s["to"], mul)
                for k in range((s["to"] - s["from"]) * mul):
                    frames.append((("s", d, k), i))
        elif s["kind"] == "freeze":
            for _ in range(round(s["dur"] * FPS)):
                frames.append((("o", s["at"]), i))
        n = len(frames) - start
        table.append({**{k: v for k, v in s.items() if k not in ("spot",)}, "t0": round(start / FPS, 3),
                      "t1": round((start + n) / FPS, 3)})
    return frames, table


def zoom_at(keys, t):
    if not keys:
        return 1.0, W / 2, H / 2
    if t <= keys[0][0]:
        return tuple(keys[0][1:])
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            k = smooth((t - a[0]) / max(1e-6, b[0] - a[0]))
            return tuple(a[j] + (b[j] - a[j]) * k for j in (1, 2, 3))
    return tuple(keys[-1][1:])


def crop_box(z, cx, cy):
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    return x0, y0, w, h


def to_out(keys, t, x, y):
    z, cx, cy = zoom_at(keys, t)
    x0, y0, w, h = crop_box(z, cx, cy)
    return (x - x0) * W / w, (y - y0) * H / h


def grade_freeze(img, spots, k):
    if k <= 0:
        return img
    gray = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    dim = (img * (1 - 0.55 * k) + gray * 0.55 * k) * (1 - 0.30 * k)
    if spots:
        m = np.zeros(img.shape[:2], np.float32)
        for cx, cy, rx, ry in spots:
            cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 18)[..., None]
        dim = img * m + dim * (1 - m)
    return np.clip(dim, 0, 255).astype(np.uint8)


def callouts_ass(spec, out_ass: Path):
    keys = spec.get("zoom", [])
    ev = []
    F = "Barlow Condensed ExtraBold"
    for c in spec.get("callouts", []):
        t0, t1 = c["t"]
        fad = r"\fad(160,200)"
        col = c.get("color", "red")

        def P(x, y):
            return to_out(keys, t0, x, y) if c.get("src") else (x, y)

        k = c["kind"]
        if k == "badge":
            ev.append(f"Dialogue: 5,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c('navy')}\\1a&H30&\\p1}}"
                      f"m 96 40 l 470 40 455 92 81 92{{\\p0}}")
            ev.append(f"Dialogue: 6,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c('red')}\\p1}}"
                      f"m 96 40 l 108 40 93 92 81 92{{\\p0}}")
            ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an4\\pos(122,66){fad}\\fn{F}\\fs40\\fsp1\\1c{ass_c('white')}}}{c['text']}")
        elif k == "tag":
            x, y = P(c["x"], c["y"])
            txt, sub = c["text"], c.get("sub", "")
            wpx = max(len(txt) * 23 + 60, len(sub) * 13 + 60)
            x0, x1, y0, y1 = x - wpx / 2, x + wpx / 2, y - 62, y
            pop = r"\t(0,140,\fscx104\fscy104)\t(140,240,\fscx100\fscy100)"
            if c.get("to"):
                px, py = P(*c["to"])
                ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c(col)}\\p1}}"
                          f"m {x - 2:.0f} {y1:.0f} l {x + 2:.0f} {y1:.0f} {px + 2:.0f} {py:.0f} {px - 2:.0f} {py:.0f}{{\\p0}}")
            ev.append(f"Dialogue: 5,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c('navy')}\\1a&H20&\\p1}}"
                      f"m {x0:.0f} {y0:.0f} l {x1:.0f} {y0:.0f} {x1:.0f} {y1:.0f} {x0:.0f} {y1:.0f}{{\\p0}}")
            ev.append(f"Dialogue: 6,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c(col)}\\p1}}"
                      f"m {x0:.0f} {y0:.0f} l {x0 + 8:.0f} {y0:.0f} {x0 + 8:.0f} {y1:.0f} {x0:.0f} {y1:.0f}{{\\p0}}")
            ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an5\\pos({x + 4:.0f},{y0 + (22 if sub else 31):.0f}){fad}{pop}"
                      f"\\fn{F}\\fs40\\fsp1\\1c{ass_c('white')}}}{txt}")
            if sub:
                ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an5\\pos({x + 4:.0f},{y0 + 48:.0f}){fad}"
                          f"\\fnInter SemiBold\\fs20\\fsp2\\1c{ass_c('silver')}}}{sub}")
        elif k == "stat":
            x, y = P(c["x"], c["y"])
            ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an1\\pos({x:.0f},{y - 92:.0f}){fad}"
                      f"\\fnInter SemiBold\\fs24\\fsp3\\1c{ass_c('silver')}\\bord0\\shad3\\4a&H60&}}{c['label']}")
            ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an1\\pos({x:.0f},{y:.0f}){fad}"
                      r"\t(0,120,\fscx112\fscy112)\t(120,260,\fscx100\fscy100)"
                      f"\\fn{F}\\i1\\fs104\\1c{ass_c(col)}\\bord0\\shad4\\4a&H50&}}{c['value']}")
        elif k == "big":
            y = c.get("y", 470)
            ev.append(f"Dialogue: 8,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an5\\pos(960,{y}){fad}"
                      r"\fscx150\fscy150\blur6\t(0,180,\fscx96\fscy96\blur0)\t(180,300,\fscx100\fscy100)"
                      f"\\fn{F}\\i1\\fs210\\1c{ass_c(c.get('color', 'white'))}\\bord0\\shad6\\4a&H40&}}{c['text']}")
            if c.get("sub"):
                ev.append(f"Dialogue: 8,{ts(t0 + 0.15)},{ts(t1)},D,,0,0,0,,{{\\an5\\pos(960,{y + 130}){fad}"
                          f"\\fnInter SemiBold\\fs34\\fsp4\\1c{ass_c('white')}\\bord0\\shad3}}{c['sub']}")
        elif k == "ring":
            x, y = P(c["x"], c["y"])
            rx, ry = c["rx"], c["ry"]

            def ell(rx_, ry_, rev=False):
                ang = np.linspace(0, 2 * math.pi, 48)
                pts = [(x + rx_ * math.cos(a), y + ry_ * math.sin(a)) for a in (ang[::-1] if rev else ang)]
                return "m " + " l ".join(f"{px:.0f} {py:.0f}" for px, py in pts)
            ring = ell(rx, ry) + " " + ell(rx - 6, ry - 3, rev=True)
            grow = r"\t(0,220,\fscx100\fscy100)"
            ev.append(f"Dialogue: 3,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\org({x:.0f},{y:.0f})\\fscx40\\fscy40{grow}"
                      f"\\1c{ass_c(col)}\\blur1.2\\p1}}{ring}{{\\p0}}")
            ev.append(f"Dialogue: 2,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\org({x:.0f},{y:.0f})\\fscx40\\fscy40{grow}"
                          f"\\1c{ass_c(col)}\\1a&HB0&\\blur10\\p1}}{ell(rx + 6, ry + 4)} {ell(rx - 10, ry - 6, rev=True)}{{\\p0}}")
        elif k == "line":
            (ax, ay), (bx, by) = P(*c["a"]), P(*c["b"])
            L = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / L, (by - ay) / L
            nx, ny = -uy * 2.5, ux * 2.5
            dashes, d = [], 0.0
            while d < L:
                e = min(L, d + 18)
                p0 = (ax + ux * d, ay + uy * d)
                p1 = (ax + ux * e, ay + uy * e)
                dashes.append(f"m {p0[0] + nx:.0f} {p0[1] + ny:.0f} l {p1[0] + nx:.0f} {p1[1] + ny:.0f} "
                              f"{p1[0] - nx:.0f} {p1[1] - ny:.0f} {p0[0] - nx:.0f} {p0[1] - ny:.0f}")
                d += 30
            ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c(col)}\\p1}}{' '.join(dashes)}{{\\p0}}")
            for px, py in ((ax, ay), (bx, by)):
                ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c{ass_c(col)}\\p1}}"
                          f"m {px - 7:.0f} {py:.0f} l {px:.0f} {py - 7:.0f} {px + 7:.0f} {py:.0f} {px:.0f} {py + 7:.0f}{{\\p0}}")
            if c.get("text"):
                mx, my = (ax + bx) / 2, (ay + by) / 2 - 18
                ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an2\\pos({mx:.0f},{my:.0f}){fad}"
                          f"\\fn{F}\\i1\\fs52\\1c{ass_c('white')}\\3c{ass_c('navy')}\\bord4\\shad0}}{c['text']}")
        elif k == "label":
            x, y = P(c["x"], c["y"])
            ev.append(f"Dialogue: 7,{ts(t0)},{ts(t1)},D,,0,0,0,,{{\\an5\\pos({x:.0f},{y:.0f}){fad}"
                      f"\\fn{F}\\i1\\fs{c.get('size', 56)}\\1c{ass_c(col)}\\3c{ass_c('navy')}\\bord3\\shad3\\4a&H60&}}{c['text']}")
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\nStyle: D,Inter SemiBold,40,&H00F2F4F6&,&H00F2F4F6&,&H00000000&,&H00000000&,0,0,0,0,"
            "100,100,0,0,1,0,0,7,0,0,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n")
    out_ass.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


def build_audio(spec, src_video: Path, table, n_out: int, out_wav: Path):
    sr = 48000
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src_video), "-vn", "-ac", "2", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2)
    mix = np.zeros((int(n_out / FPS * sr) + sr, 2), np.float32)
    g = 10 ** (spec.get("audio_db", -14) / 20)
    for s in table:
        if s["kind"] == "play" and s.get("speed", 1) >= 1:
            i0, i1 = int(s["from"] / FPS * sr), int(s["to"] / FPS * sr)
            o0 = int(s["t0"] * sr)
            seg = a[i0:i1] * (10 ** (s["audio_db"] / 20) if "audio_db" in s else g)
            n = min(len(seg), len(mix) - o0)
            ramp = min(480, n // 2)
            seg = seg[:n].copy()
            seg[:ramp] *= np.linspace(0, 1, ramp)[:, None]
            seg[n - ramp:] *= np.linspace(1, 0, ramp)[:, None]
            mix[o0:o0 + n] += seg
    sf.write(str(out_wav), mix[: int(n_out / FPS * sr)], sr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--stills", default="")
    a = ap.parse_args()
    os.chdir(ROOT)
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    video = Path(spec["src"])
    out = Path(spec["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    src = Src(video, Path("work/fxcache") / video.stem)
    frames, table = timeline(spec, src)
    n = len(frames)
    keys = spec.get("zoom", [])
    flashes, shakes = spec.get("flash", []), spec.get("shake", [])
    ass = out.with_suffix(".ass")
    callouts_ass(spec, ass)

    def render(i):
        ref, si = frames[i]
        t = i / FPS
        s = spec["segs"][si]
        img = src.frame(ref)
        if s["kind"] == "freeze":
            k = smooth((t - table[si]["t0"]) / 0.25) * smooth((table[si]["t1"] - t) / 0.12 + 0.0) if s.get("out_fade") else \
                smooth((t - table[si]["t0"]) / 0.25)
            img = grade_freeze(img, s.get("spot", []), k * s.get("grade", 1.0))
        z, cx, cy = zoom_at(keys, t)
        dx = dy = 0.0
        for t0, dur, amp in shakes:
            if t0 <= t < t0 + dur:
                e = 1 - (t - t0) / dur
                dx += amp * e * math.sin(t * 97.0)
                dy += amp * e * math.cos(t * 71.0)
        if z != 1 or dx or dy:
            x0, y0, w, h = crop_box(z, cx, cy)
            M = np.float32([[W / w, 0, -x0 * W / w + dx], [0, H / h, -y0 * H / h + dy]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        for t0, st, nf in flashes:
            j = round((t - t0) * FPS)
            if 0 <= j < nf:
                al = st * (1 - j / nf)
                img = cv2.addWeighted(img, 1 - al, np.full_like(img, 255), al, 0)
        return img

    if a.stills:
        sd = out.parent / "stills"
        sd.mkdir(exist_ok=True)
        raw = sd / "_raw"
        raw.mkdir(exist_ok=True)
        for tt in map(float, a.stills.split(",")):
            i = min(n - 1, round(tt * FPS))
            cv2.imwrite(str(raw / f"{tt:.2f}.png"), render(i))
            rel_ass = os.path.relpath(ass, raw).replace("\\", "/")
            fd = os.path.relpath(ROOT / "assets/fonts", raw).replace("\\", "/")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{tt:.2f}.png", "-vf",
                            f"setpts=PTS+{tt}/TB,subtitles={rel_ass}:fontsdir={fd}", "-frames:v", "1",
                            str(Path(os.path.relpath(sd, raw)) / f"{out.stem}_{tt:.2f}.jpg")], cwd=raw, check=True)
        print("stills ->", sd)
        return

    wav = out.with_suffix(".wav")
    build_audio(spec, video, table, n, wav)
    tmp = out.with_name(out.stem + "_nofx.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "fast",
                          "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(12) as ex:
        for k, img in enumerate(ex.map(render, range(n))):
            p.stdin.write(img.tobytes())
            if k % 150 == 0:
                print(f"  {k}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    rel_ass = os.path.relpath(ass, out.parent).replace("\\", "/")
    fd = os.path.relpath(ROOT / "assets/fonts", out.parent).replace("\\", "/")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name, "-i", wav.name, "-vf",
                    f"subtitles={rel_ass}:fontsdir={fd}", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", out.name], cwd=out.parent, check=True)
    tmp.unlink()
    man = {"src": spec["src"], "dur": round(n / FPS, 3), "segments": table}
    out.with_suffix(".json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(f"-> {out}  {n / FPS:.2f}s")


if __name__ == "__main__":
    sys.exit(main())
