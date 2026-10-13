#!/usr/bin/env python3
"""参考帧场地标定：像素点 ↔ 球场点（英尺）求单应 G（像素→球场），并把半场线投回画面供核对。

球场坐标同 court.py: u = 距底线英尺，v = 横向英尺（0 为篮筐中轴，靠近机位为正）。
常用点: 禁区底线两角 (0,±8)、罚球线两端 (19,±8)、罚球圈顶 (25,0)、底角三分 (0,±22)。

输出: <G.npy> 和同名 _proj.jpg（绿线应贴住地板实线）
用法: python calib.py raw/e453_pullup.mp4 184 "390,695=0,8;643,496=0,-8;1155,794=19,8;1340,565=19,-8" work/calib/G453_184.npy
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from render_play import court_lines  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("frame", type=int)
    ap.add_argument("pairs", help='"x,y=u,v;..."，至少 4 组')
    ap.add_argument("out")
    a = ap.parse_args()

    px, uv = [], []
    for p in a.pairs.split(";"):
        l, r = p.split("=")
        px.append([float(v) for v in l.split(",")])
        uv.append([float(v) for v in r.split(",")])
    px, uv = np.float32(px), np.float32(uv)
    G, _ = cv2.findHomography(px, uv, 0)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, G)

    back = cv2.perspectiveTransform(uv[None], np.linalg.inv(G))[0]
    for (x, y), (bx, by), (u, v) in zip(px, back, uv):
        print(f"  ({u:5.1f},{v:5.1f})  点 {x:.0f},{y:.0f}  回投误差 {np.hypot(bx - x, by - y):.1f}px")

    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.frame)
    ok, img = cap.read()
    if not ok:
        raise SystemExit(f"读不到第 {a.frame} 帧")
    Hi = np.linalg.inv(G)
    for ln in court_lines():
        q = cv2.perspectiveTransform(np.float32(ln)[None], Hi)[0]
        cv2.polylines(img, [q.astype(np.int32)], False, (0, 255, 0), 2, cv2.LINE_AA)
    for x, y in px:
        cv2.circle(img, (int(x), int(y)), 7, (0, 0, 255), 2)
    proj = out.with_name(out.stem + "_proj.jpg")
    cv2.imwrite(str(proj), img)
    print(f"G -> {out}\n核对图 -> {proj}")


if __name__ == "__main__":
    main()
