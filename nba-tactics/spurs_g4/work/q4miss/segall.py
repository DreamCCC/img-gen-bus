"""segall.py <work_dir> <f0> <f1>: YOLO-seg every person on fr/orig frames f0..f1, save <work>/masks/NNNN.npz
in the renderer's format ({"<id>": [x1, y1], "m<id>": uint8 crop}) so floor layers are occluded by all bodies."""
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

wd, f0, f1 = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
model = YOLO(str(Path(__file__).resolve().parents[1] / "yolo11x-seg.pt"))
(wd / "masks").mkdir(exist_ok=True)
for f in range(f0, f1 + 1):
    p = wd / "fr" / "orig" / f"{f:04d}.jpg"
    if not p.exists():
        break
    im = cv2.imread(str(p))
    H, W = im.shape[:2]
    r = model.predict(im, classes=[0], conf=0.3, imgsz=1280, verbose=False)[0]
    out = {}
    if r.masks is not None:
        for i, poly in enumerate(r.masks.xy):
            if len(poly) < 3:
                continue
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [poly.astype(np.int32)], 1)
            ys, xs = np.nonzero(m)
            if len(xs) < 200:
                continue
            x1, y1 = xs.min(), ys.min()
            key = str(9000 + i)
            out[key] = np.array([x1, y1])
            out["m" + key] = m[y1:ys.max() + 1, x1:xs.max() + 1]
    np.savez_compressed(wd / "masks" / f"{f:04d}.npz", **out)
print("masks", f0, f1, "->", wd / "masks")
