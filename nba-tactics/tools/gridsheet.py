#!/usr/bin/env python3
"""抽指定帧拼成带像素网格的联系表，用来人工读球/篮筐坐标。

用法: python gridsheet.py raw/e464_three.mp4 out.jpg 64,66,68,70 [--crop x1,y1,x2,y2] [--cols 3]
"""
from __future__ import annotations

import argparse

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("frames")
    ap.add_argument("--crop", default="0,0,1920,1080")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--tile", type=int, default=640)
    ap.add_argument("--step", type=int, default=50)
    a = ap.parse_args()
    want = [int(x) for x in a.frames.split(",")]
    x1, y1, x2, y2 = (int(v) for v in a.crop.split(","))
    cap = cv2.VideoCapture(a.video)
    got = {}
    i = 0
    while i <= max(want):
        ok, f = cap.read()
        if not ok:
            break
        if i in want:
            c = f[y1:y2, x1:x2].copy()
            for gx in range((x1 // a.step + 1) * a.step, x2, a.step):
                big = gx % (a.step * 2) == 0
                cv2.line(c, (gx - x1, 0), (gx - x1, y2 - y1), (0, 255, 255) if big else (0, 160, 160), 1)
                if big:
                    cv2.putText(c, str(gx), (gx - x1 + 2, 14), 0, 0.45, (0, 255, 255), 1)
            for gy in range((y1 // a.step + 1) * a.step, y2, a.step):
                big = gy % (a.step * 2) == 0
                cv2.line(c, (0, gy - y1), (x2 - x1, gy - y1), (255, 0, 255) if big else (160, 0, 160), 1)
                if big:
                    cv2.putText(c, str(gy), (2, gy - y1 - 2), 0, 0.45, (255, 0, 255), 1)
            s = a.tile / (x2 - x1)
            c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            cv2.putText(c, f"f{i}", (8, c.shape[0] - 10), 0, 0.9, (0, 0, 0), 4)
            cv2.putText(c, f"f{i}", (8, c.shape[0] - 10), 0, 0.9, (255, 255, 255), 2)
            got[i] = c
        i += 1
    tiles = [got[k] for k in want if k in got]
    th, tw = tiles[0].shape[:2]
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = np.zeros((rows * th, a.cols * tw, 3), np.uint8)
    for k, t in enumerate(tiles):
        r, cc = divmod(k, a.cols)
        sheet[r * th:(r + 1) * th, cc * tw:(cc + 1) * tw] = t
    cv2.imwrite(a.out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == "__main__":
    main()
