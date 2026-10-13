"""usage: python tools/montage.py out.png cols width img1 img2 ..."""
import sys
import cv2
import numpy as np

out, cols, w = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ims = [cv2.imread(p) for p in sys.argv[4:]]
ims = [cv2.resize(im, (w, round(im.shape[0] * w / im.shape[1]))) for im in ims]
h = max(im.shape[0] for im in ims)
rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
grid = np.zeros((h * len(rows), w * cols, 3), np.uint8)
for r, row in enumerate(rows):
    for c, im in enumerate(row):
        grid[r * h:r * h + im.shape[0], c * w:(c + 1) * w] = im
cv2.imwrite(out, grid)
