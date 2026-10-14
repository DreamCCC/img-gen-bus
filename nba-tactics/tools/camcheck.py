#!/usr/bin/env python3
"""镜头补偿核对：按 cam.json 把全场线投回指定帧，拼联系表。线贴住地板说明这一帧的 像素→球场 可信。

用法: python camcheck.py raw/e715.mp4 work/e715 out.jpg 0,60,120,190,260 [--cols 3]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from court import Cam  # noqa: E402
from render_play import court_lines  # noqa: E402


def full_court():
    half = court_lines()
    L = half + [[(94 - u, v) for u, v in ln] for ln in half]
    L.append([(47, -25), (47, 25)])
    a = np.linspace(0, 2 * np.pi, 60)
    L.append(list(zip(47 + 6 * np.cos(a), 6 * np.sin(a))))
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("frames")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--tile", type=int, default=640)
    a = ap.parse_args()
    cam = Cam(Path(a.work) / "cam.json")
    want = sorted(int(x) for x in a.frames.split(","))
    lines = [np.float64(ln) for ln in full_court()]
    cap = cv2.VideoCapture(a.video)
    tiles, i = [], 0
    while i <= want[-1]:
        ok, f = cap.read()
        if not ok:
            break
        if i in want:
            h, w = f.shape[:2]
            for ln in lines:
                q = cam.to_img(i, ln)
                q = q[(np.abs(q[:, 0]) < 4 * w) & (np.abs(q[:, 1]) < 4 * h)]
                if len(q) > 1:
                    cv2.polylines(f, [q.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
            s = a.tile / w
            t = cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            cv2.putText(t, f"f{i}", (8, t.shape[0] - 10), 0, 0.9, (0, 0, 0), 4)
            cv2.putText(t, f"f{i}", (8, t.shape[0] - 10), 0, 0.9, (255, 255, 255), 2)
            tiles.append(t)
        i += 1
    th, tw = tiles[0].shape[:2]
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = np.zeros((rows * th, a.cols * tw, 3), np.uint8)
    for k, t in enumerate(tiles):
        r, c = divmod(k, a.cols)
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t
    cv2.imwrite(a.out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    main()
