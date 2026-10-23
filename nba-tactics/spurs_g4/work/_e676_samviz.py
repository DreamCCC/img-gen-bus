"""usage: _e676_samviz.py out.jpg f1 f2 ... : crops 600-1150 x 450-950 with WB(9001, yellow) / BR(9011, orange) boxes"""
import json
import sys

import cv2
import numpy as np

a = json.load(open("work/e676w/sam_9001.json"))
b = json.load(open("work/e676w/sam_9011.json"))
x1, y1, x2, y2 = 600, 430, 1150, 960
tiles = []
for f in [int(v) for v in sys.argv[2:]]:
    im = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")
    for d, c in ((a, (0, 255, 255)), (b, (0, 128, 255))):
        if str(f) in d:
            bx = d[str(f)]
            cv2.rectangle(im, (bx[0], bx[1]), (bx[2], bx[3]), c, 2)
    t = im[y1:y2, x1:x2]
    for x in range(700, x2, 100):
        cv2.putText(t, str(x), (x - x1, 14), 0, 0.5, (255, 255, 255), 1)
    for y in range(500, y2, 100):
        cv2.putText(t, str(y), (2, y - y1), 0, 0.5, (255, 255, 255), 1)
    cv2.putText(t, f"f{f}", (6, y2 - y1 - 8), 0, 0.9, (0, 0, 255), 2)
    tiles.append(t)
cols = 3
rows = [np.hstack(tiles[k:k + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[k:k + cols]))) for k in range(0, len(tiles), cols)]
cv2.imwrite(sys.argv[1], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
