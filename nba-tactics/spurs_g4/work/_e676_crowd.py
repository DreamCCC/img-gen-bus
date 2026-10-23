"""Front-row spectators at frame f as one occluder: work/e676w/masks_extra/NNNN_crowd.npz (render_play's
Masks.everyone() reads every masks_extra/NNNN_*.npz, so floor rings get hidden behind these people).
usage: _e676_crowd.py f [ymin]   (people whose box top is below ymin, minus the tracked players' boxes)"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

f = int(sys.argv[1])
ymin = int(sys.argv[2]) if len(sys.argv) > 2 else 740
P = json.load(open("work/e676w/players.json"))
pb = [P[k]["box"][f] for k in P if P[k]["box"][f] is not None]


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


img = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")
res = YOLO("work/yolo11x-seg.pt").predict(img, classes=[0], conf=0.15, imgsz=1280, retina_masks=True, verbose=False)[0]
m = np.zeros(img.shape[:2], np.uint8)
n = 0
for b, mm in zip(res.boxes.xyxy.cpu().numpy(), res.masks.data.cpu().numpy()):
    if b[1] < ymin or any(iou(b, q) > 0.3 for q in pb):
        continue
    m |= (mm > 0.5).astype(np.uint8)
    n += 1
ys, xs = np.nonzero(m)
out = Path("work/e676w/masks_extra")
out.mkdir(exist_ok=True)
np.savez_compressed(out / f"{f:04d}_crowd.npz", xy=np.array([xs.min(), ys.min()]),
                    m=m[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
vis = img.copy()
vis[m > 0] = (vis[m > 0] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
cv2.imwrite(f"work/_e676_crowd_{f:04d}.jpg", cv2.resize(vis, (960, 540)))
print(n, "people ->", out / f"{f:04d}_crowd.npz")
