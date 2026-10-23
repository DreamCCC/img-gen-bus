"""Sample A (2-min EN horizontal, storyboard v3 shots 10–12): e715 breakdown with the C5 rule scene cut into its 'rule' segment.

usage (from film/):  python tools/sample_a.py
needs: work/bd/e715_en_h.mp4 + .json from `render_play.py e715_en_h_edl.json` (run in spurs_g4/).
1. last frame of segment A -> out/sampleA/bgA.jpg (C5 background, so the cut into the graphics is continuous)
2. node render.mjs scenes/c5_endgame.html at the rule segment's exact length
3. picture: footage[0, rule) + C5 + footage[rule end, end), white flash on the PINNED freeze
4. sound: footage mix (VO + original + render_play sfx) + C5 sfx from scenes/c5_endgame.json, fixed gain to -16 LUFS
   (same scheme as deliver.sh: no loudnorm, no ducking)
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

import subs

ROOT = Path(__file__).resolve().parent.parent
BD = ROOT / "work/bd/e715_en_h"
OUT = ROOT / "out/sampleA"
SR = 48000
TARGET = -16.0
NOSUB = __import__("os").environ.get("NOSUB") == "1"


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


def sfx(kind: str) -> np.ndarray:
    rng = np.random.default_rng(len(kind))
    if kind in ("thud", "hit"):
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * np.cumsum(42 + 60 * np.exp(-t * 30)) / SR) * np.exp(-t * 7)
        click = rng.standard_normal(n) * np.exp(-t * 400) * 0.5
        y = body + click
        if kind == "hit":
            ring = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1180, 0.10), (2350, 0.06), (3900, 0.03))) * np.exp(-t * 18)
            air = np.diff(rng.standard_normal(n + 1)) * np.exp(-t * 35) * 0.25
            y = y + ring + air
        return y
    if kind == "whoosh":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        noise = rng.standard_normal(n)
        k = 40
        band = np.convolve(noise, np.ones(k) / k, "same") - np.convolve(noise, np.ones(4 * k) / (4 * k), "same")
        return band * np.sin(np.pi * t / t[-1]) ** 2 * 3.0
    if kind == "tick":
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 120) * 0.6
    raise ValueError(kind)


GAIN = {"thud": -9, "hit": -7, "whoosh": -15, "tick": -17}


def flash(frame: int, fps: int, peak: float, n: int) -> str:
    """White flash decaying over n frames from `frame`, one fixed-alpha drawbox per frame."""
    out = []
    for i in range(n):
        a = peak * (1 - i / n) ** 2
        t0, t1 = (frame + i - 0.5) / fps, (frame + i + 0.5) / fps
        out.append(f"drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=white@{a:.3f}:enable='between(t,{t0:.4f},{t1:.4f})'")
    return ",".join(out)


def lufs(path: Path) -> float:
    err = run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
              capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(re.findall(r"^\s*I:\s*(-?[\d.]+) LUFS", err, re.M)[-1])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    man = json.loads(BD.with_suffix(".json").read_text(encoding="utf-8"))
    fps = man["fps"]
    seg = {s["id"]: s for s in man["segments"]}
    r0, r1 = round(seg["rule"]["start"] * fps), round(seg["rule"]["end"] * fps)
    n_all = round(man["duration"] * fps)
    p_at = seg["P"]["start"]

    run(["ffmpeg", "-y", "-loglevel", "error", "-i", BD.with_suffix(".mp4"), "-vf", f"select=eq(n\\,{r0 - 1})",
         "-frames:v", "1", "-q:v", "2", OUT / "bgA.jpg"])
    dur = (r1 - r0) / fps
    c5 = OUT / "c5.mp4"
    run(["node", "render.mjs", "scenes/c5_endgame.html", c5], cwd=ROOT,
        env={**__import__("os").environ, "QUERY": f"dur={dur:.4f}"})

    fc = (f"[0:v]trim=start_frame=0:end_frame={r0},setpts=PTS-STARTPTS[a];"
          f"[1:v]trim=start_frame=0:end_frame={r1 - r0},setpts=PTS-STARTPTS[c];"
          f"[0:v]trim=start_frame={r1}:end_frame={n_all},setpts=PTS-STARTPTS[b];"
          f"[a][c][b]concat=n=3:v=1:a=0,format=yuv420p,"
          f"{flash(r1, fps, 0.8, 7)},{flash(round(p_at * fps), fps, 0.65, 9)}"
          + ("[v]" if NOSUB else ",subtitles=out/sampleA/sampleA.ass:fontsdir=assets/fonts[v]"))
    defs = json.loads((ROOT / "subs_en.json").read_text(encoding="utf-8"))
    vo_at = {v["id"]: v["t"] for v in man["vo"]}
    subs.build([d for d in defs if d.get("vo") in vo_at], vo_at, subs.load_words(ROOT / "audio/vo_en"), OUT / "sampleA.ass")
    master = OUT / ("sampleA_clean.mp4" if NOSUB else "sampleA_master.mp4")
    if NOSUB:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", BD.with_suffix(".mp4"), "-i", c5, "-filter_complex", fc,
             "-map", "[v]", "-r", fps, "-c:v", "libx264", "-preset", "medium", "-crf", 14, "-pix_fmt", "yuv420p", master])
        build_mix(seg, p_at)
        print(f"clean picture -> {master}, mix -> {OUT / 'sampleA_mix.wav'}")
        return
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", BD.with_suffix(".mp4"), "-i", c5, "-filter_complex", fc,
         "-map", "[v]", "-r", fps, "-c:v", "libx264", "-preset", "medium", "-crf", 14, "-pix_fmt", "yuv420p", master])
    mix = build_mix(seg, p_at)

    gain = TARGET - lufs(mix) + 0.3
    final = OUT / "sampleA.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", master, "-i", mix, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-af", f"volume={gain:.1f}dB,aresample=192000,alimiter=limit=0.75:attack=2:release=60:level=false,"
         "aresample=48000", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final])
    print(f"rule {r0}-{r1} ({dur:.2f}s), P at {p_at:.2f}s, gain {gain:+.1f} dB -> {final}, {lufs(final):.1f} LUFS")


def build_mix(seg: dict, p_at: float) -> Path:
    base = OUT / "footage_mix.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", BD.with_suffix(".mp4"), "-vn", "-ac", 1, "-ar", SR, base])
    y, _ = sf.read(base)
    beats = json.loads((ROOT / "scenes/c5_endgame.json").read_text(encoding="utf-8"))
    for t, kind in beats["sfx"]:
        s = sfx(kind) * 10 ** (GAIN[kind] / 20)
        a = int((seg["rule"]["start"] + t) * SR)
        s = s[: max(0, len(y) - a)]
        y[a:a + len(s)] += s
    s = sfx("hit") * 10 ** (-8 / 20)
    a = int(p_at * SR)
    y[a:a + len(s)] += s[: len(y) - a]
    y = y / max(1.0, np.abs(y).max() / 0.95)
    mix = OUT / "sampleA_mix.wav"
    sf.write(mix, np.c_[y, y].astype(np.float32), SR)
    return mix


if __name__ == "__main__":
    main()
