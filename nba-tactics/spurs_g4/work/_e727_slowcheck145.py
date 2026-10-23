import cv2
import numpy as np

base = "work/e727w/fr/"


def g(p):
    return cv2.resize(cv2.imread(p, 0), (480, 270)).astype(np.float32)


for f in (150, 160, 176, 186, 200, 204):
    o = g(f"{base}orig/{f:04d}.jpg")
    res = []
    for i in range(4 * (f - 146) - 4, 4 * (f - 146) + 5):
        if 0 <= i <= 336:
            res.append((round(float(np.abs(g(f"{base}slow145/{i:04d}.jpg") - o).mean()), 2), i - 4 * (f - 146)))
    print(f, sorted(res)[:2])
