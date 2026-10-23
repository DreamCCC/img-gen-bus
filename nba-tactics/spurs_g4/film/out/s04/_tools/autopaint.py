"""Find the blue paint quad on a frame: autopaint.py frame.jpg seed_x,seed_y out.jpg [open_px]
Prints calib.py pairs (baseline on the right of frame, far side up): "x,y=0,8;x,y=0,-8;x,y=19,8;x,y=19,-8"."""
import sys

import cv2
import numpy as np

img = cv2.imread(sys.argv[1])
seeds = [[int(v) for v in p.split(",")] for p in sys.argv[2].split(";")]
k = int(sys.argv[4]) if len(sys.argv) > 4 else 9
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
m = cv2.inRange(hsv, (98, 110, 50), (128, 255, 255))
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
blob = np.zeros(m.shape, np.uint8)
for sx, sy in seeds:
    c = lab[sy, sx]
    if c == 0:
        raise SystemExit(f"seed {sx},{sy} not on paint")
    blob |= (lab == c).astype(np.uint8)
cnt, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
hull = cv2.convexHull(np.vstack(cnt))
eps = 2.0
quad = cv2.approxPolyDP(hull, eps, True)
while len(quad) > 4:
    eps *= 1.15
    quad = cv2.approxPolyDP(hull, eps, True)
q = quad.reshape(-1, 2).astype(float)
if len(q) != 4:
    raise SystemExit(f"got {len(q)} vertices")
q = q[np.argsort(q[:, 0])]
ft = q[:2][np.argsort(q[:2, 1])]
bl = q[2:][np.argsort(q[2:, 1])]
pairs = f"{bl[1][0]:.0f},{bl[1][1]:.0f}=0,8;{bl[0][0]:.0f},{bl[0][1]:.0f}=0,-8;{ft[1][0]:.0f},{ft[1][1]:.0f}=19,8;{ft[0][0]:.0f},{ft[0][1]:.0f}=19,-8"
print(pairs)
vis = img.copy()
vis[blob > 0] = (vis[blob > 0] * 0.5 + np.array([0, 255, 0]) * 0.5).astype(np.uint8)
cv2.polylines(vis, [quad.reshape(-1, 1, 2)], True, (0, 0, 255), 2)
cv2.imwrite(sys.argv[3], cv2.resize(vis, (960, 540)))
