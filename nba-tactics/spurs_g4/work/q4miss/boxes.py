"""boxes.py <work_dir> <out.jpg> <frames,comma> [crop x1,y1,x2,y2] [width]: draw all track boxes+ids on frames from fr/orig, tiled 3 per row."""
import json
import sys

import cv2
import numpy as np

wd, out = sys.argv[1], sys.argv[2]
frames = [int(v) for v in sys.argv[3].split(",")]
crop = [int(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
w = int(sys.argv[5]) if len(sys.argv) > 5 else 640
d = json.load(open(f"{wd}/tracks.json"))
tiles = []
for f in frames:
    im = cv2.imread(f"{wd}/fr/orig/{f:04d}.jpg")
    for o in d["frames"][f]:
        x1, y1, x2, y2 = map(int, o["box"])
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(im, str(o["id"]), (x1, y1 - 4), 0, 0.9, (0, 0, 0), 4)
        cv2.putText(im, str(o["id"]), (x1, y1 - 4), 0, 0.9, (0, 255, 255), 2)
    if crop:
        im = im[crop[1]:crop[3], crop[0]:crop[2]]
    im = cv2.resize(im, (w, int(im.shape[0] * w / im.shape[1])))
    cv2.putText(im, f"f{f}", (6, 30), 0, 1, (0, 0, 255), 3)
    tiles.append(im)
while len(tiles) % 3:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))
