"""Contact sheet: sheet.py video out.jpg [step] [start] [end] [cols] [w] [crop x0,y0,x1,y1]"""
import sys
import cv2
import numpy as np

vid, out = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 15
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
end = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 6
w = int(sys.argv[7]) if len(sys.argv) > 7 else 320
crop = [int(v) for v in sys.argv[8].split(',')] if len(sys.argv) > 8 else None

cap = cv2.VideoCapture(vid)
tiles = []
i = 0
while True:
    ok, f = cap.read()
    if not ok or i > end:
        break
    if i >= start and (i - start) % step == 0:
        if crop:
            f = f[crop[1]:crop[3], crop[0]:crop[2]]
        h = int(f.shape[0] * w / f.shape[1])
        t = cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA)
        cv2.putText(t, str(i), (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(t, str(i), (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        tiles.append(t)
    i += 1
rows = []
for r in range(0, len(tiles), cols):
    row = tiles[r:r + cols]
    while len(row) < cols:
        row.append(np.zeros_like(tiles[0]))
    rows.append(np.hstack(row))
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(tiles), 'frames of', i)
