"""Hard-cut montage with a short white flash at each cut; audio = the clips' own source windows at a fixed gain.

usage (from spurs_g4/): python film/out/s04/_tools/montage.py s04_montage.json
spec: {"out": ..., "fps": 30, "audio_db": -14, "flash": {"peak": 0.7, "n": 2},
       "clips": [{"video": mp4 or image sequence ("dir/%04d.jpg"), "vstart": first frame (default 0), "frames": n,
                  "wav": source wav, "from": source frame of the window start}, ...]}
Audio is the source window [from, from+frames) at constant audio_db (no normalisation, no ducking),
with 10 ms de-click fades at each cut.
"""
import json
import subprocess
import sys
from pathlib import Path

spec = json.load(open(sys.argv[1], encoding="utf-8"))
fps = spec.get("fps", 30)
db = spec.get("audio_db", -14)
fl = spec.get("flash", {"peak": 0.7, "n": 2})


def flash(frame: int, peak: float, n: int) -> str:
    out = []
    for i in range(n):
        a = peak * (1 - i / n) ** 2
        t0, t1 = (frame + i - 0.5) / fps, (frame + i + 0.5) / fps
        out.append(f"drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=white@{a:.3f}:enable='between(t,{t0:.4f},{t1:.4f})'")
    return ",".join(out)


args, fc, cat, cuts, at = ["ffmpeg", "-v", "error", "-y"], [], "", [], 0
for k, c in enumerate(spec["clips"]):
    s, n = c.get("vstart", 0), c["frames"]
    if "%" in c["video"]:
        args += ["-framerate", str(fps), "-start_number", str(s)]
        s = 0
    args += ["-i", c["video"], "-i", c["wav"]]
    a0, d = c["from"] / fps, n / fps
    fc.append(f"[{2 * k}:v]trim=start_frame={s}:end_frame={s + n},setpts=PTS-STARTPTS,format=yuv420p[v{k}]")
    fc.append(f"[{2 * k + 1}:a]atrim=start={a0:.5f}:end={a0 + d:.5f},asetpts=PTS-STARTPTS,"
              f"aformat=sample_rates=48000:channel_layouts=stereo,volume={db}dB,"
              f"afade=t=in:d=0.01,afade=t=out:st={d - 0.01:.5f}:d=0.01[a{k}]")
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
