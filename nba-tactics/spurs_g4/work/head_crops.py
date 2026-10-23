"""Crop around a player's head at given frames of an AR mp4 and tile them.
usage: python head_crops.py video.mp4 out.jpg f1:x:y f2:x:y ...   (x,y = crop centre in 1920x1080 px)"""
import subprocess
import sys

import cv2
import numpy as np

src, out, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
tiles = []
for sp in specs:
    f, x, y = map(int, sp.split(":"))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"select=eq(n\\,{f})", "-fps_mode", "passthrough",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    img = np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3)
    x0, y0 = max(0, min(1920 - 420, x - 210)), max(0, min(1080 - 420, y - 210))
    t = img[y0:y0 + 420, x0:x0 + 420].copy()
    cv2.putText(t, f"f{f}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    tiles.append(t)
cv2.imwrite(out, np.hstack(tiles))
