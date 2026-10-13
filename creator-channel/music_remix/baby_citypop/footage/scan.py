"""素材浏览：检测镜头切换，每个镜头取一张缩略图（标时间码），拼成接触表 sheets/<name>_<页>.jpg。

python scan.py [名字 ...]       默认扫 raw/ 下全部 mp4；已扫过的跳过（scenes/<name>.json）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
RAW, SC, SH = HERE / "raw", HERE / "scenes", HERE / "sheets"
SC.mkdir(exist_ok=True)
SH.mkdir(exist_ok=True)
FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
TW, TH, COLS, ROWS = 384, 216, 6, 6


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def cuts(p, thr=0.32):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-an", "-vf", f"scale=256:-2,select='gt(scene,{thr})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def thumb(p, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1",
                        "-vf", f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if len(r.stdout) < TW * TH * 3:
        return Image.new("RGB", (TW, TH))
    return Image.frombytes("RGB", (TW, TH), r.stdout[:TW * TH * 3])


def scan(p):
    name = p.stem
    out = SC / f"{name}.json"
    if out.exists():
        return
    dur = duration(p)
    cs = [0.0] + cuts(p)
    scenes = [(a, b) for a, b in zip(cs, cs[1:] + [dur]) if b - a >= 0.6]
    out.write_text(json.dumps(dict(name=name, duration=dur, scenes=scenes)))
    per = COLS * ROWS
    for page in range(0, len(scenes), per):
        sheet = Image.new("RGB", (COLS * TW, ROWS * (TH + 28)), (16, 16, 20))
        d = ImageDraw.Draw(sheet)
        for k, (a, b) in enumerate(scenes[page:page + per]):
            x, y = (k % COLS) * TW, (k // COLS) * (TH + 28)
            sheet.paste(thumb(p, a + min(0.5, (b - a) / 2)), (x, y + 28))
            d.text((x + 6, y + 3), f"#{page + k} {a:.1f}s ({b - a:.1f})", font=FONT, fill=(255, 255, 120))
        sheet.save(SH / f"{name}_{page // per:02d}.jpg", quality=80)
    print(name, len(scenes), "scenes", flush=True)


want = sys.argv[1:]
for p in sorted(RAW.glob("*.mp4")):
    if (want and p.stem not in want) or re.search(r"\.f\d+$", p.stem):
        continue
    scan(p)
