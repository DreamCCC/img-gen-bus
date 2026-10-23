"""Tile frames from several videos. usage: python frames_grid.py out.jpg cols width video:frame ..."""
import subprocess
import sys

import cv2
import numpy as np

out, cols, wd, specs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
tiles = []
for sp in specs:
    v, f = sp.rsplit(":", 1)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select=eq(n\\,{f}),scale={wd}:-2", "-fps_mode",
                          "passthrough", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    h = len(raw) // (wd * 3)
    t = np.frombuffer(raw, np.uint8).reshape(h, wd, 3).copy()
    cv2.putText(t, f"{v.split('/')[-1]} f{f}", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    tiles.append(t)
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows))
