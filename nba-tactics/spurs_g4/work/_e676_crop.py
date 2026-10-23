"""usage: _e676_crop.py f x1 y1 x2 y2 [scale]  -> work/_e676_crop_<f>.jpg with a 50px grid labelled in full-frame pixels"""
import sys
import cv2

f, x1, y1, x2, y2 = (int(v) for v in sys.argv[1:6])
sc = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
im = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")[y1:y2, x1:x2].copy()
for x in range((x1 // 50 + 1) * 50, x2, 50):
    cv2.line(im, (x - x1, 0), (x - x1, y2 - y1), (0, 255, 255) if x % 100 == 0 else (0, 140, 140), 1)
    if x % 100 == 0:
        cv2.putText(im, str(x), (x - x1 + 2, 14), 0, 0.45, (0, 255, 255), 1)
for y in range((y1 // 50 + 1) * 50, y2, 50):
    cv2.line(im, (0, y - y1), (x2 - x1, y - y1), (0, 255, 255) if y % 100 == 0 else (0, 140, 140), 1)
    if y % 100 == 0:
        cv2.putText(im, str(y), (2, y - y1 - 3), 0, 0.45, (0, 255, 255), 1)
cv2.putText(im, f"f{f}", (8, y2 - y1 - 10), 0, 0.9, (0, 0, 255), 2)
if sc != 1.0:
    im = cv2.resize(im, None, fx=sc, fy=sc)
cv2.imwrite(f"work/_e676_crop_{f:04d}.jpg", im)
