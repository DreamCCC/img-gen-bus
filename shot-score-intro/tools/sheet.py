"""静帧联系表：python tools/sheet.py <静帧目录> <输出前缀> [列数=3] [每张格数=9] [格宽=640]

按文件名里的时间 tNN.NN 排序，每格左上角标时间。
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

src, prefix = Path(sys.argv[1]), sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
per = int(sys.argv[4]) if len(sys.argv) > 4 else 9
cw = int(sys.argv[5]) if len(sys.argv) > 5 else 640
files = sorted(src.glob("t*.png"), key=lambda p: float(re.findall(r"t([\d.]+)\.png", p.name)[0]))
font = ImageFont.load_default(size=28)
for s in range(0, len(files), per):
    batch = files[s : s + per]
    ims = [Image.open(f).convert("RGB") for f in batch]
    ch = round(cw * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), "black")
    for i, (im, f) in enumerate(zip(ims, batch)):
        x, y = i % cols * cw, i // cols * ch
        sheet.paste(im.resize((cw, ch)), (x, y))
        d = ImageDraw.Draw(sheet)
        d.rectangle([x, y, x + 120, y + 36], fill="black")
        d.text((x + 6, y + 2), f.stem[1:] + "s", fill="yellow", font=font)
    out = f"{prefix}_{s // per + 1}.jpg"
    sheet.save(out, quality=88)
    print(out)
