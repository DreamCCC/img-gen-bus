"""Contact sheet: sheet.py <video> <out.jpg> <t0> <t1> <step> [cols] [width] [crop x1,y1,x2,y2]
Times in seconds (absolute video time); each tile labelled with time and frame number."""
import sys
import cv2
import numpy as np

vid, out, t0, t1, step = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 4
w = int(sys.argv[7]) if len(sys.argv) > 7 else 480
crop = [int(v) for v in sys.argv[8].split(",")] if len(sys.argv) > 8 else None
cap = cv2.VideoCapture(vid)
fps = cap.get(cv2.CAP_PROP_FPS)
tiles = []
t = t0
while t <= t1 + 1e-6:
    f = int(round(t * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f)
    ok, im = cap.read()
    if not ok:
        break
    if crop:
        im = im[crop[1]:crop[3], crop[0]:crop[2]]
    h = int(im.shape[0] * w / im.shape[1])
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f"{t:.2f}s f{f}", (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
    cv2.putText(im, f"{t:.2f}s f{f}", (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    tiles.append(im)
    t += step
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(out, len(tiles), fps)
