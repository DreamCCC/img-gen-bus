"""Assemble the 2-min EN horizontal cut from a timeline JSON.

usage (from film/):  python tools/assemble.py timeline_simple.json
Each item is one finished clip (fxclip footage, render.mjs code scene, sampleA, prepared soundbites):
  {"id", "src", "type": "foot"|"code",
   "trim": [t0, t1]?            cut a range out of a long source (soundbites, broadcast call); re-encoded in prep
   "vertical": true?            1080x1920 source -> centred over a blurred fill
   "keep_h": px?                vertical only: keep the top px rows (drops burned-in source captions)
   "pad": s?                    hold the last frame
   "audio": "clip"|null|{"src", "from", "db"}   clip's own sound, silence, or an external bed
   "audio_db": dB?              gain on the clip's own sound
   "vo": [[id, offset], ...]?   code scenes default to vo_line/vo_offset from scenes/<id>_*.json
   "vo_split": {"id", "marks": [t, ...]}?   one VO file cut at its pauses, each word placed at a mark
   "vo_baked": "manifest.json"? clip audio already carries VO (sampleA); manifest gives captions
   "spec": "shots/x.json"?      fxclip spec: its flashes get a synthetic hit
   "subs": [{"at": [t0, t1], "text", "who"?}]?   captions relative to the clip
   "hud": [{"at", "x", "y", "text", "size"?, "color"?, "an"?, "fad"?} | {"at", "box": [x0, y0, x1, y1]}]?
                                 broadcast-style text / panels burned with the captions (counters = consecutive entries)
  }
Picture: concat of all clips, a short white flash on every footage <-> code cut, captions burned in.
Sound: clip sound + VO + code-scene sfx + hits, fixed gain to -16 LUFS then a true-peak-ish limiter (no ducking).
"""
import glob
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subs  # noqa: E402
from sample_a import GAIN, flash, lufs, sfx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FPS, SR, TARGET = 30, 48000, -16.0
VO = ROOT / "audio/vo_en"


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


def probe_frames(p: Path) -> int:
    out = run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
               "stream=nb_read_packets", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return int(out.strip())


def read_audio(p: Path, start: float = 0.0, dur: float | None = None) -> np.ndarray:
    args = ["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", p]
    if dur is not None:
        args += ["-t", f"{dur:.4f}"]
    r = subprocess.run([str(a) for a in args + ["-vn", "-ac", "1", "-ar", SR, "-f", "f32le", "-"]],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def prep(it: dict, cache: Path) -> Path:
    """Soundbite / broadcast items: cut and conform to 1920x1080 once."""
    src = ROOT / it["src"]
    if "trim" not in it and not it.get("vertical"):
        return src
    t0, t1 = it.get("trim", [0, None])
    out = cache / f"{it['id']}_{t0}_{t1}{'_v' + str(it.get('keep_h', 1920)) if it.get('vertical') else ''}.mp4"
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        return out
    pre = ["-ss", f"{t0:.3f}"] + (["-t", f"{t1 - t0:.3f}"] if t1 else [])
    if it.get("vertical"):
        keep = it.get("keep_h", 1920)
        vf = (f"[0:v]crop=iw:{keep}:0:0,split[a][b];"
              "[a]scale=1920:-2,crop=1920:1080,boxblur=40:2,eq=brightness=-0.18:saturation=0.7[bg];"
              "[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,format=yuv420p[v]")
    else:
        vf = "[0:v]scale=1920:1080,format=yuv420p[v]"
    run(["ffmpeg", "-y", "-loglevel", "error", *pre, "-i", src, "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
         "-r", FPS, "-c:v", "libx264", "-preset", "medium", "-crf", 14, "-c:a", "aac", "-b:a", "320k", "-ar", SR, out])
    return out


HUD_COL = {"white": "&H00F6F4F2&", "gold": "&H0045C8FF&", "green": "&H007BD62B&", "red": "&H003B3BFF&",
           "orange": "&H002684F5&", "silver": "&H00D4CEC4&"}


def hud_events(t0: float, hud: list) -> list[str]:
    ev = []
    for h in hud:
        a, b = subs.ts(t0 + h["at"][0]), subs.ts(t0 + h["at"][1])
        fad = "\\fad({},{})".format(*h.get("fad", [0, 0]))
        if "box" in h:
            x0, y0, x1, y1 = h["box"]
            ev.append(f"Dialogue: 2,{a},{b},Box,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c&H0028140A&\\1a&H22&\\p1}}"
                      f"m {x0} {y0} l {x1} {y0} {x1} {y1} {x0} {y1}{{\\p0}}")
            ev.append(f"Dialogue: 2,{a},{b},Box,,0,0,0,,{{\\an7\\pos(0,0){fad}\\1c&H002E10C8&\\p1}}"
                      f"m {x0} {y0} l {x0 + 7} {y0} {x0 + 7} {y1} {x0} {y1}{{\\p0}}")
        else:
            ev.append(f"Dialogue: 3,{a},{b},Cap,,0,0,0,,{{\\an{h.get('an', 7)}\\pos({h['x']},{h['y']}){fad}"
                      f"\\fnBarlow Condensed ExtraBold\\fs{h.get('size', 40)}\\c{HUD_COL[h.get('color', 'white')]}"
                      f"\\fsp1}}{h['text']}")
    return ev


def scene_json(cid: str) -> dict | None:
    hits = glob.glob(str(ROOT / f"scenes/{cid}_*.json"))
    return json.loads(Path(hits[0]).read_text(encoding="utf-8")) if hits else None


def onsets(y: np.ndarray, thr_db: float = -32) -> np.ndarray:
    hop = SR // 200
    env = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, "same"))
    return env > 10 ** (thr_db / 20) * np.abs(y).max()


def split_vo(vid: str, marks: list[float]) -> list[tuple[float, np.ndarray]]:
    """Cut a VO file at its pauses; return (offset of piece onset, piece) so each word's onset lands on a mark."""
    y, _ = sf.read(VO / f"{vid}.wav")
    y = y.mean(1) if y.ndim > 1 else y
    on = onsets(y)
    edges = np.flatnonzero(np.diff(on.astype(int)))
    starts = [i + 1 for i in edges if not on[i]] if not on[0] else [0] + [i + 1 for i in edges if not on[i]]
    starts = [s for k, s in enumerate(starts) if k == 0 or s - starts[k - 1] > 0.12 * SR]
    if len(starts) < len(marks):
        raise SystemExit(f"{vid}: found {len(starts)} words, need {len(marks)}")
    starts = starts[:len(marks)]
    pieces = []
    for k, s in enumerate(starts):
        a = max(0, s - int(0.03 * SR))
        b = starts[k + 1] - int(0.03 * SR) if k + 1 < len(starts) else len(y)
        piece = y[a:b].copy()
        fade = min(len(piece), int(0.01 * SR))
        piece[-fade:] *= np.linspace(1, 0, fade)
        pieces.append((marks[k] - (s - a) / SR, piece))
    return pieces


def main() -> None:
    tl_path = ROOT / sys.argv[1]
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    out = ROOT / tl["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "work/assemble"
    cache.mkdir(parents=True, exist_ok=True)

    items, t = [], 0.0
    for it in tl["items"]:
        if not (ROOT / it["src"]).exists() and "fallback" in it:
            print(f"  {it['id']}: {it['src']} missing, using {it['fallback']}")
            it = {**it, "src": it["fallback"]}
        src = prep(it, cache)
        n = probe_frames(src)
        pad = round(it.get("pad", 0) * FPS)
        items.append({**it, "path": src, "frames": n, "pad_f": pad, "t0": t, "dur": (n + pad) / FPS})
        t += (n + pad) / FPS
    total = t
    print(f"{len(items)} clips, {total:.2f}s")

    # sound
    mix = np.zeros(int((total + 1) * SR))

    def add(at: float, y: np.ndarray, db: float = 0.0) -> None:
        a = int(round(at * SR))
        if a < 0:
            y, a = y[-a:], 0
        y = y[: len(mix) - a]
        mix[a:a + len(y)] += y * 10 ** (db / 20)

    vo_at, cap_defs, vo_spans = {}, [], []
    all_defs = json.loads((ROOT / "subs_en.json").read_text(encoding="utf-8"))
    for it in items:
        t0, dur = it["t0"], it["dur"]
        a = it.get("audio", "clip" if it["type"] == "foot" else None)
        if a == "clip":
            add(t0, read_audio(it["path"], 0, it["frames"] / FPS), it.get("audio_db", 0))
        elif isinstance(a, dict):
            y = read_audio(ROOT / a["src"], a["from"], dur)
            fo = int(a.get("fade_out", 0) * SR)
            if fo:
                y[-fo:] *= np.linspace(1, 0, fo) ** 2
            add(t0, y, a.get("db", 0))
        vos = it.get("vo")
        if vos is None and it["type"] == "code":
            sj = scene_json(it["id"])
            if sj and sj.get("vo_offset") is not None and it.get("vo_line", sj.get("vo_line")):
                vos = [[it.get("vo_line", sj.get("vo_line")), sj["vo_offset"]]]
        for vid, off in vos or []:
            y, _ = sf.read(VO / f"{vid}.wav")
            y = y.mean(1) if y.ndim > 1 else y
            add(t0 + off, y)
            vo_at[vid] = t0 + off
            vo_spans.append((t0 + off, t0 + off + len(y) / SR, vid))
        if "vo_split" in it:
            for off, piece in split_vo(it["vo_split"]["id"], it["vo_split"]["marks"]):
                add(t0 + off, piece)
                vo_spans.append((t0 + off, t0 + off + len(piece) / SR, it["vo_split"]["id"]))
        if "vo_baked" in it:
            man = json.loads((ROOT / it["vo_baked"]).read_text(encoding="utf-8"))
            for v in man["vo"]:
                vo_at[v["id"]] = t0 + v["t"]
                vo_spans.append((t0 + v["t"], t0 + v["end"], v["id"]))
        if it["type"] == "code":
            sj = scene_json(it["id"]) or {}
            for st, kind in sj.get("sfx", []):
                add(t0 + st, sfx(kind), GAIN[kind])
        if "spec" in it:
            for ft, strength, _ in json.loads((ROOT / it["spec"]).read_text(encoding="utf-8")).get("flash", []):
                if strength >= 0.6:
                    add(t0 + ft, sfx("hit"), -9)
        for s in it.get("subs", []):
            cap_defs.append({**s, "at": [t0 + s["at"][0], t0 + s["at"][1]]})

    vo_spans.sort()
    for (a0, a1, va), (b0, b1, vb) in zip(vo_spans, vo_spans[1:]):
        if b0 - a1 < 0.3:
            print(f"  VO tight: {va} ends {a1:.2f}, {vb} starts {b0:.2f} (gap {b0 - a1:+.2f}s)")

    mix = mix[: int(total * SR)]
    mix_path = out.with_name(out.stem + "_mix.wav")
    sf.write(mix_path, np.c_[mix, mix].astype(np.float32), SR, subtype="FLOAT")
    gain = TARGET - lufs(mix_path) + 0.3

    # captions
    used = [d for d in all_defs if d["vo"] in vo_at]
    ass = out.with_suffix(".ass")
    subs.build(used + cap_defs, vo_at, subs.load_words(VO), ass)
    hud = [e for it in items for e in hud_events(it["t0"], it.get("hud", []))]
    if hud:
        ass.write_text(ass.read_text(encoding="utf-8") + "\n".join(hud) + "\n", encoding="utf-8")

    # picture
    fc, labels = [], []
    for k, it in enumerate(items):
        chain = f"[{k}:v]setpts=PTS-STARTPTS,fps={FPS},format=yuv420p"
        if it["pad_f"]:
            chain += f",tpad=stop_mode=clone:stop={it['pad_f']}"
        fc.append(chain + f"[v{k}]")
        labels.append(f"[v{k}]")
    flashes = []
    for prev, nxt in zip(items, items[1:]):
        if prev["type"] != nxt["type"]:
            flashes.append(flash(round(nxt["t0"] * FPS), FPS, 0.7, 4))
    rel_ass = ass.relative_to(ROOT).as_posix()
    fc.append("".join(labels) + f"concat=n={len(items)}:v=1:a=0," + "".join(f + "," for f in flashes) +
              f"subtitles={rel_ass}:fontsdir=assets/fonts[v]")
    fc.append(f"[{len(items)}:a]volume={gain:.2f}dB,aresample=192000,"
              "alimiter=limit=0.75:attack=2:release=60:level=false,aresample=48000[a]")
    script = cache / (out.stem + "_fc.txt")
    script.write_text(";\n".join(fc), encoding="utf-8")
    ins = []
    for it in items:
        ins += ["-i", it["path"]]
    run(["ffmpeg", "-y", "-loglevel", "error", "-stats_period", "5", *ins, "-i", mix_path,
         "-/filter_complex", script, "-map", "[v]", "-map", "[a]", "-r", FPS,
         "-c:v", "libx264", "-preset", "medium", "-crf", 16, "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], cwd=ROOT)

    cuts = [{"id": it["id"], "t0": round(it["t0"], 3), "dur": round(it["dur"], 3)} for it in items]
    out.with_suffix(".json").write_text(json.dumps({"duration": total, "cuts": cuts, "vo_at": vo_at,
                                                    "gain_db": gain}, indent=1), encoding="utf-8")
    print(f"-> {out}  {total:.2f}s  gain {gain:+.1f} dB  {lufs(out):.1f} LUFS")


if __name__ == "__main__":
    main()
