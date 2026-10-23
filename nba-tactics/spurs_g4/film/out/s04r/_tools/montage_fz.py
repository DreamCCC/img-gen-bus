"""Hard-cut montage with a short white flash at each cut; audio = per-segment source windows (clips may contain freezes).

usage (from spurs_g4/): python film/out/s04r/_tools/montage_fz.py s04r_montage.json
spec: {"out": ..., "fps": 30, "flash": {"peak": 0.7, "n": 2},
       "clips": [{"video": mp4, "frames": n, "wav": source wav,
                  "audio": [[src_from, n_frames, gain_db], ...]}, ...]}
Same picture/flash treatment as film/out/s04/_tools/montage.py. Each clip's audio is the concatenation of its
"audio" pieces (they must add up to "frames"): the play segments take the source window that matches the picture,
a freeze takes a stand-in window (arena ambience) so the swish stays in sync after the freeze. Constant gains,
no normalisation; 10 ms de-click fades on every piece.
"""
import json
import subprocess
import sys
from pathlib import Path

spec = json.load(open(sys.argv[1], encoding="utf-8"))
fps = spec.get("fps", 30)
fl = spec.get("flash", {"peak": 0.7, "n": 2})


def flash(frame: int, peak: float, n: int) -> str:
    out = []
    for i in range(n):
        a = peak * (1 - i / n) ** 2
        t0, t1 = (frame + i - 0.5) / fps, (frame + i + 0.5) / fps
        out.append(f"drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=white@{a:.3f}:enable='between(t,{t0:.4f},{t1:.4f})'")
    return ",".join(out)


args, fc, cat, cuts, at, inp = ["ffmpeg", "-v", "error", "-y"], [], "", [], 0, 0
for k, c in enumerate(spec["clips"]):
    n = c["frames"]
    if sum(p[1] for p in c["audio"]) != n:
        raise SystemExit(f"clip {k}: audio pieces {sum(p[1] for p in c['audio'])} frames != video {n}")
    args += ["-i", c["video"]]
    vi = inp
    inp += 1
    fc.append(f"[{vi}:v]trim=start_frame=0:end_frame={n},setpts=PTS-STARTPTS,format=yuv420p[v{k}]")
    pieces = ""
    for j, (f0, m, db) in enumerate(c["audio"]):
        args += ["-i", c["wav"]]
        a0, d = f0 / fps, m / fps
        fc.append(f"[{inp}:a]atrim=start={a0:.5f}:end={a0 + d:.5f},asetpts=PTS-STARTPTS,"
                  f"aformat=sample_rates=48000:channel_layouts=stereo,volume={db}dB,"
                  f"afade=t=in:d=0.01,afade=t=out:st={d - 0.01:.5f}:d=0.01[a{k}_{j}]")
        pieces += f"[a{k}_{j}]"
        inp += 1
    fc.append(f"{pieces}concat=n={len(c['audio'])}:v=0:a=1[a{k}]")
    cat += f"[v{k}][a{k}]"
    if k:
        cuts.append(at)
    at += n
fc.append(f"{cat}concat=n={len(spec['clips'])}:v=1:a=1[vc][ac]")
fc.append("[vc]" + (",".join(flash(f, fl["peak"], fl["n"]) for f in cuts) if cuts and fl["n"] else "null") + "[v]")
out = Path(spec["out"])
out.parent.mkdir(parents=True, exist_ok=True)
args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[ac]", "-r", str(fps),
         "-c:v", "libx264", "-crf", str(spec.get("crf", 12)), "-preset", "slow", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", str(out)]
subprocess.run(args, check=True)
print(f"{out}: {at} frames = {at / fps:.3f} s, cuts at frames {cuts}")
