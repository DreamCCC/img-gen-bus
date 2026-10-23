"""Zoomed crop with full-res pixel grid: zoomgrid.py frame.jpg out.jpg x0,y0,x1,y1 [zoom] [step]."""
import sys

import cv2

img = cv2.imread(sys.argv[1])
x0, y0, x1, y1 = [int(t) for t in sys.argv[3].split(",")]
z = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
step = int(sys.argv[5]) if len(sys.argv) > 5 else 10
c = cv2.resize(img[y0:y1, x0:x1], None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
for gx in range((x0 // step + 1) * step, x1, step):
    px, major = int((gx - x0) * z), gx % (step * 5) == 0
    cv2.line(c, (px, 0), (px, c.shape[0]), (0, 255, 255) if major else (0, 110, 110), 1)
    if major:
        cv2.putText(c, str(gx), (px + 2, 14), 0, 0.45, (0, 255, 255), 1)
for gy in range((y0 // step + 1) * step, y1, step):
    py, major = int((gy - y0) * z), gy % (step * 5) == 0
    cv2.line(c, (0, py), (c.shape[1], py), (255, 0, 255) if major else (110, 0, 110), 1)
    if major:
        cv2.putText(c, str(gy), (2, py - 2), 0, 0.45, (255, 0, 255), 1)
cv2.imwrite(sys.argv[2], c, [cv2.IMWRITE_JPEG_QUALITY, 92])
