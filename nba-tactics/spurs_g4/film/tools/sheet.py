"""视频缩略图拼板，每格标注时间码，用于挑镜头。
用法：python tools/sheet.py video.mp4 out.jpg [每隔秒数=2] [列数=8] [起点=0] [终点=结尾]
"""
import sys

import cv2
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 8
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
t0 = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
t1 = float(sys.argv[6]) if len(sys.argv) > 6 else dur
W0, H0 = int(cap.get(3)), int(cap.get(4))
tw = 240
th = int(tw * H0 / W0)
tiles = []
t = t0
while t < t1:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    if not ok:
        break
    f = cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA)
    cv2.rectangle(f, (0, 0), (62, 18), (0, 0, 0), -1)
    cv2.putText(f, f"{t:6.1f}", (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    tiles.append(f)
    t += step
while len(tiles) % cols:
    tiles.append(np.zeros((th, tw, 3), np.uint8))
rows = [np.hstack(tiles[i : i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(dst, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(dst, f"{W0}x{H0} {fps:.2f}fps {dur:.1f}s tiles={len(tiles)}")
