"""Tile crops of several frames with a pixel grid for reading foot positions.

usage: python kfsheet.py fr_dir out.jpg f0,f1,... x0,y0,x1,y1 [cols] [step]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

fr, out, fs, box = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 3
step = int(sys.argv[6]) if len(sys.argv) > 6 else 50
x0, y0, x1, y1 = map(int, box.split(","))
tiles = []
for f in map(int, fs.split(",")):
    im = cv2.imread(str(Path(fr) / f"{f:04d}.jpg"))[y0:y1, x0:x1].copy()
    for x in range((x0 // step + 1) * step, x1, step):
        cv2.line(im, (x - x0, 0), (x - x0, y1 - y0), (0, 255, 255) if x % 100 == 0 else (0, 160, 160), 1)
        if x % 100 == 0:
            cv2.putText(im, str(x), (x - x0 + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    for y in range((y0 // step + 1) * step, y1, step):
        cv2.line(im, (0, y - y0), (x1 - x0, y - y0), (255, 0, 255) if y % 100 == 0 else (160, 0, 160), 1)
        if y % 100 == 0:
            cv2.putText(im, str(y), (2, y - y0 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1)
    cv2.rectangle(im, (0, y1 - y0 - 30), (90, y1 - y0), (0, 0, 0), -1)
    cv2.putText(im, f"f{f}", (6, y1 - y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(im)
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
