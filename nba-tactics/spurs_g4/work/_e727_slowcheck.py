import cv2
import numpy as np

import sys

base = "work/e727w/fr/"
SLOW, F0, LAST = (sys.argv[1], int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else ("slow", 160, 276)


def g(p):
    return cv2.resize(cv2.imread(p, 0), (480, 270)).astype(np.float32)


for f in (150, 160, 172, 186, 201, 204, 220):
    k = f - F0
    o = g(f"{base}orig/{f:04d}.jpg")
    best = []
    for d in range(-7, 4):
        i = 4 * k + d
        if i < 0 or i > LAST:
            continue
        s = g(f"{base}{SLOW}/{i:04d}.jpg")
        best.append((round(float(np.abs(s - o).mean()), 2), d))
    print(f, sorted(best)[:3])
