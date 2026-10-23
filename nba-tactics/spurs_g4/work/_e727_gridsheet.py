"""Grid sheet of crops: python work/_e727_gridsheet.py out.jpg 164,168,... x0,y0,x1,y1 [zoom] [cols]"""
import sys

import cv2

out, fs, box = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], [int(v) for v in sys.argv[3].split(",")]
z = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 3
x0, y0, x1, y1 = box
tiles = []
for f in fs:
    img = cv2.imread(f"work/e727w/fr/orig/{f:04d}.jpg")[y0:y1, x0:x1].copy()
    img = cv2.resize(img, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    for gx in range((x0 // 50 + 1) * 50, x1, 50):
        px = int((gx - x0) * z)
        cv2.line(img, (px, 0), (px, img.shape[0]), (0, 255, 255) if gx % 100 == 0 else (0, 120, 120), 1)
        if gx % 100 == 0:
            cv2.putText(img, str(gx), (px + 2, 14), 0, 0.45, (0, 255, 255), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50):
        py = int((gy - y0) * z)
        cv2.line(img, (0, py), (img.shape[1], py), (255, 0, 255) if gy % 100 == 0 else (120, 0, 120), 1)
        if gy % 100 == 0:
            cv2.putText(img, str(gy), (2, py - 2), 0, 0.45, (255, 0, 255), 1)
    cv2.putText(img, f"f{f}", (8, img.shape[0] - 10), 0, 0.9, (0, 0, 0), 4)
    cv2.putText(img, f"f{f}", (8, img.shape[0] - 10), 0, 0.9, (255, 255, 255), 2)
    tiles.append(img)
import numpy as np  # noqa: E402

h, w = tiles[0].shape[:2]
rows = []
for k in range(0, len(tiles), cols):
    r = tiles[k:k + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[k:k + cols]))
    rows.append(np.hstack(r))
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
