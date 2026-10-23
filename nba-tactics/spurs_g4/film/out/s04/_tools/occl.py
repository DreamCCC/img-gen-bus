"""Add a union-of-all-people occluder (YOLO-seg) to work/masks/NNNN.npz as key "8998", so floor rings go behind
every player, not only the tracked shooter. Existing keys in the npz are kept.

usage: occl.py work f0 f1 [--conf 0.25]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("f0", type=int)
ap.add_argument("f1", type=int)
ap.add_argument("--conf", type=float, default=0.25)
ap.add_argument("--model", default=str(Path(__file__).resolve().parents[4] / "work" / "yolo11x-seg.pt"))
a = ap.parse_args()

work = Path(a.work)
model = YOLO(a.model)
for f in range(a.f0, a.f1 + 1):
    im = cv2.imread(str(work / "fr" / "orig" / f"{f:04d}.jpg"))
    r = model.predict(im, classes=[0], conf=a.conf, imgsz=1280, retina_masks=True, verbose=False, device="cuda")[0]
    p = work / "masks" / f"{f:04d}.npz"
    z = dict(np.load(p)) if p.exists() else {}
    z.pop("8998", None), z.pop("m8998", None)
    if r.masks is not None and len(r.masks):
        m = (r.masks.data.cpu().numpy() > 0.5).any(0).astype(np.uint8)
        if m.shape != im.shape[:2]:
            m = cv2.resize(m, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8))
        ys, xs = np.nonzero(m)
        x1, y1, x2, y2 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        z["8998"] = np.array([x1, y1])
        z["m8998"] = m[y1:y2, x1:x2]
    np.savez_compressed(p, **z)
print(f"occluder 8998 f{a.f0}-{a.f1}")
