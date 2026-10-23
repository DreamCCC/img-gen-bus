"""Post-process work/players.json after traj.py so tags sit still, and add a crowd occluder to the masks.

usage: steady.py work f0 f1 [--sigma 2.0] [--crowd-y 840]
- uv: extra Gaussian smoothing (sigma frames) over valid frames.
- box: rebuilt from the smoothed foot point and a constant standing height/width (25th-percentile box height
  of the raw track outside its air frames), so the tag anchor (box top) does not follow raised arms or box flicker.
- masks/NNNN.npz: key "8999"/"m8999" = non-floor pixels below crowd-y (front-row heads, score bug) so floor
  rings are hidden behind them instead of painted on top.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4].parent / "tools"))
from court import Cam  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("f0", type=int)
ap.add_argument("f1", type=int)
ap.add_argument("--sigma", type=float, default=2.0)
ap.add_argument("--crowd-y", type=int, default=840)
a = ap.parse_args()
work = Path(a.work)
cam = Cam(work / "cam.json")
P = json.load(open(work / "players.json"))
for k, d in P.items():
    uv = d["uv"]
    ok = np.array([q is not None for q in uv])
    arr = np.array([q if q is not None else [0, 0] for q in uv], float)
    sm = arr.copy()
    idx = np.nonzero(ok)[0]
    r = int(3 * a.sigma)
    for i in idx:
        js = idx[(idx >= i - r) & (idx <= i + r)]
        w = np.exp(-0.5 * ((js - i) / a.sigma) ** 2)
        sm[i] = (arr[js] * w[:, None]).sum(0) / w.sum()
    raw = [b for b in d["box"] if b is not None]
    hs = np.array([b[3] - b[1] for b in raw])
    ws = np.array([b[2] - b[0] for b in raw])
    H, W = float(np.percentile(hs, 25)), float(np.median(ws))
    box = [None] * len(uv)
    for i in idx:
        fx, fy = cam.to_img(i, [sm[i]])[0]
        box[i] = [round(fx - W / 2, 1), round(fy - H, 1), round(fx + W / 2, 1), round(fy, 1)]
    d["uv"] = [[round(float(u), 3), round(float(v), 3)] if ok[i] else None for i, (u, v) in enumerate(sm)]
    d["box"] = box
    print(f"{k}: H={H:.0f} W={W:.0f} valid {ok.sum()} frames")
json.dump(P, open(work / "players.json", "w"), ensure_ascii=False)

for f in range(a.f0, a.f1 + 1):
    im = cv2.imread(str(work / "fr" / "orig" / f"{f:04d}.jpg"))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    wood = cv2.inRange(hsv, (0, 20, 140), (30, 150, 255)) | cv2.inRange(hsv, (165, 20, 140), (180, 150, 255))
    paint = cv2.inRange(hsv, (98, 110, 50), (128, 255, 255))
    floor = cv2.morphologyEx(wood | paint, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    occ = (floor == 0).astype(np.uint8)
    occ[:a.crowd_y] = 0
    occ = cv2.morphologyEx(occ, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    occ = cv2.morphologyEx(occ, cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
    occ[:a.crowd_y] = 0
    p = work / "masks" / f"{f:04d}.npz"
    z = dict(np.load(p)) if p.exists() else {}
    z["8999"] = np.array([0, a.crowd_y])
    z["m8999"] = occ[a.crowd_y:]
    np.savez_compressed(p, **z)
print(f"crowd occluder f{a.f0}-{a.f1}")
