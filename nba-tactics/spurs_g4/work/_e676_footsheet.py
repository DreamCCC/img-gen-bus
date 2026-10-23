"""usage: _e676_footsheet.py tid out.jpg f1 f2 ...: 300x330 crops around the SAM box, 25px grid in full-frame coords"""
import json
import sys

import cv2
import numpy as np

sam = json.load(open(f"work/e676w/sam_{sys.argv[1]}.json"))
tiles = []
for f in [int(v) for v in sys.argv[3:]]:
    im = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")
    b = sam[str(f)]
    cx = (b[0] + b[2]) // 2
    x1, y1 = cx - 150, b[1] - 30
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = x1 + 300, min(1080, y1 + 330)
    t = im[y1:y2, x1:x2].copy()
    for x in range((x1 // 25 + 1) * 25, x2, 25):
        c = (0, 255, 255) if x % 100 == 0 else (0, 120, 120)
        cv2.line(t, (x - x1, 0), (x - x1, y2 - y1), c, 1)
        if x % 100 == 0:
            cv2.putText(t, str(x), (x - x1 + 2, 12), 0, 0.4, (0, 255, 255), 1)
    for y in range((y1 // 25 + 1) * 25, y2, 25):
        c = (0, 255, 255) if y % 100 == 0 else (0, 120, 120)
        cv2.line(t, (0, y - y1), (x2 - x1, y - y1), c, 1)
        cv2.putText(t, str(y), (2, y - y1 - 2), 0, 0.35, (0, 255, 255), 1)
    cv2.putText(t, f"f{f}", (200, y2 - y1 - 8), 0, 0.7, (0, 0, 255), 2)
    t = cv2.copyMakeBorder(t, 0, 330 - t.shape[0], 0, 0, cv2.BORDER_CONSTANT)
    tiles.append(t)
cols = 5
rows = [np.hstack(tiles[k:k + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[k:k + cols]))) for k in range(0, len(tiles), cols)]
cv2.imwrite(sys.argv[2], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
