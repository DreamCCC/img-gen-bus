"""Tile gridded zoom crops around guessed points: corners.py frame.jpg out.jpg "x,y;x,y;..." [half=70] [zoom=3]"""
import sys

import cv2
import numpy as np

img = cv2.imread(sys.argv[1])
pts = [[int(v) for v in p.split(",")] for p in sys.argv[3].split(";")]
half = int(sys.argv[4]) if len(sys.argv) > 4 else 70
z = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
tiles = []
for k, (cx, cy) in enumerate(pts):
    x0, y0 = max(0, cx - half), max(0, cy - half)
    x1, y1 = min(img.shape[1], cx + half), min(img.shape[0], cy + half)
    c = cv2.resize(img[y0:y1, x0:x1], None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    for gx in range((x0 // 5 + 1) * 5, x1, 5):
        px = int((gx - x0) * z)
        major = gx % 25 == 0
        cv2.line(c, (px, 0), (px, c.shape[0]), (0, 255, 255) if major else (0, 90, 90), 1)
        if major:
            cv2.putText(c, str(gx), (px + 2, 12), 0, 0.4, (0, 255, 255), 1)
    for gy in range((y0 // 5 + 1) * 5, y1, 5):
        py = int((gy - y0) * z)
        major = gy % 25 == 0
        cv2.line(c, (0, py), (c.shape[1], py), (255, 0, 255) if major else (90, 0, 90), 1)
        if major:
            cv2.putText(c, str(gy), (2, py - 2), 0, 0.4, (255, 0, 255), 1)
    cv2.putText(c, f"P{k}", (c.shape[1] - 40, c.shape[0] - 10), 0, 0.7, (255, 255, 255), 2)
    full = np.zeros((2 * half * int(z), 2 * half * int(z), 3), np.uint8)
    full[:c.shape[0], :c.shape[1]] = c
    tiles.append(full)
while len(tiles) % 2:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
cv2.imwrite(sys.argv[2], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
