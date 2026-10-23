"""Contact sheet of a cut: one frame per clip at a chosen fraction (or explicit times), labelled.

usage: qa_sheet.py film.mp4 film.json out.jpg [frac | t1,t2,...]
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

video, man, out = sys.argv[1:4]
arg = sys.argv[4] if len(sys.argv) > 4 else "0.6"
cuts = json.loads(Path(man).read_text(encoding="utf-8"))["cuts"]
if "," in arg:
    shots = [(f"{float(t):.2f}", float(t)) for t in arg.split(",")]
else:
    shots = [(c["id"], c["t0"] + c["dur"] * float(arg)) for c in cuts]
W, H, COLS = 640, 360, 4
rows = (len(shots) + COLS - 1) // COLS
sheet = Image.new("RGB", (W * COLS, H * rows))
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
for k, (name, t) in enumerate(shots):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                          f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    im = Image.frombytes("RGB", (W, H), raw)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 170, 30], fill=(0, 0, 0))
    d.text((6, 3), f"{name} {t:.1f}s", fill=(255, 220, 0), font=font)
    sheet.paste(im, ((k % COLS) * W, (k // COLS) * H))
sheet.save(out, quality=88)
print(out, len(shots))
