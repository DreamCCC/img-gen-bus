"""Tile raw frames with frame numbers: _retime_tiles.py <frames dir> <a> <b> <step> <out.jpg> [cols] [x1,y1,x2,y2 crop]"""
import sys
from pathlib import Path

import cv2
import numpy as np

d, a, b, st, out = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 5
crop = [int(v) for v in sys.argv[7].split(",")] if len(sys.argv) > 7 else None
tiles = []
for f in range(a, b + 1, st):
    im = cv2.imread(str(d / f"{f:04d}.jpg"))
    if im is None:
        continue
    if crop:
        x1, y1, x2, y2 = crop
        im = im[y1:y2, x1:x2]
    h, w = im.shape[:2]
    tw = 384 if not crop else min(640, w)
    t = cv2.resize(im, (tw, round(h * tw / w)), interpolation=cv2.INTER_AREA)
    cv2.putText(t, str(f), (6, 28), 0, 0.9, (0, 0, 0), 4)
    cv2.putText(t, str(f), (6, 28), 0, 0.9, (0, 255, 255), 2)
    tiles.append(t)
blank = np.zeros_like(tiles[0])
rows = [np.hstack(tiles[k:k + cols] + [blank] * (cols - len(tiles[k:k + cols]))) for k in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(tiles))
