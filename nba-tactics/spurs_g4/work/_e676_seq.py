"""usage: _e676_seq.py f0 f1 step x1 y1 x2 y2 out.jpg [scale] [cols]"""
import sys
import cv2
import numpy as np

f0, f1, step, x1, y1, x2, y2 = (int(v) for v in sys.argv[1:8])
out = sys.argv[8]
sc = float(sys.argv[9]) if len(sys.argv) > 9 else 0.5
cols = int(sys.argv[10]) if len(sys.argv) > 10 else 5
tiles = []
for f in range(f0, f1 + 1, step):
    im = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")[y1:y2, x1:x2].copy()
    for x in range((x1 // 100 + 1) * 100, x2, 100):
        cv2.line(im, (x - x1, 0), (x - x1, y2 - y1), (0, 200, 200), 1)
        cv2.putText(im, str(x), (x - x1 + 2, 16), 0, 0.6, (0, 255, 255), 2)
    for y in range((y1 // 100 + 1) * 100, y2, 100):
        cv2.line(im, (0, y - y1), (x2 - x1, y - y1), (0, 200, 200), 1)
        cv2.putText(im, str(y), (2, y - y1 - 3), 0, 0.6, (0, 255, 255), 2)
    im = cv2.resize(im, None, fx=sc, fy=sc)
    cv2.putText(im, f"f{f}", (6, im.shape[0] - 8), 0, 0.8, (0, 0, 255), 2)
    tiles.append(im)
rows = [np.hstack(tiles[k:k + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[k:k + cols]))) for k in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
