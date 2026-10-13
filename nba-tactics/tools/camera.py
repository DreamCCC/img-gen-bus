#!/usr/bin/env python3
"""逐帧估计转播镜头运动（相邻帧单应），链式累积到参考帧，再乘上参考帧的场地标定，得到每帧 像素→球场(英尺) 的映射。

球场坐标: u = 距底线英尺（向中场为正），v = 横向英尺（0 为篮筐中轴，靠近机位为正）。

输出 <out>/cam.json: {"ref": 124, "court": [[3x3] 每帧: 像素→球场]}
用法: python camera.py raw/e464_three.mp4 work/e464 --ref 124 --G work/calib/G124.npy --end 8.8
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def static_mask(shape, boxes) -> np.ndarray:
    h, w = shape[:2]
    m = np.full((h, w), 255, np.uint8)
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(m, (int(x1) - 10, int(y1) - 10), (int(x2) + 10, int(y2) + 10), 0, -1)
    m[int(h * 0.88):, int(w * 0.6):] = 0   # 记分牌
    m[:int(h * 0.12), :int(w * 0.12)] = 0  # 角标
    return m


def pair_h(orb, matcher, a, b, ma, mb):
    ka, da = orb.detectAndCompute(a, ma)
    kb, db = orb.detectAndCompute(b, mb)
    if da is None or db is None or len(ka) < 30 or len(kb) < 30:
        return np.eye(3)
    ms = matcher.knnMatch(da, db, k=2)
    good = [m for m, n in (p for p in ms if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 25:
        return np.eye(3)
    pa = np.float32([ka[m.queryIdx].pt for m in good])
    pb = np.float32([kb[m.trainIdx].pt for m in good])
    H, _ = cv2.findHomography(pa, pb, cv2.RANSAC, 2.5)
    return H if H is not None else np.eye(3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--ref", type=int, required=True)
    ap.add_argument("--G", required=True, help="参考帧 像素→球场 的 3x3 .npy")
    ap.add_argument("--end", type=float, default=1e9)
    a = ap.parse_args()

    out = Path(a.out)
    tracks = json.load(open(out / "tracks.json"))["frames"]
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    orb = cv2.ORB_create(4000, fastThreshold=12)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

    grays, masks = [], []
    i = 0
    while True:
        ok, f = cap.read()
        if not ok or i / fps > a.end or i >= len(tracks):
            break
        g = cv2.cvtColor(cv2.resize(f, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
        boxes = [[v * 0.5 for v in d["box"]] for d in tracks[i]]
        grays.append(g)
        masks.append(static_mask(g.shape, boxes))
        i += 1
    n = len(grays)
    S = np.diag([0.5, 0.5, 1.0])
    step = [np.eye(3)] * n  # step[i]: 帧 i → 帧 i+1（全分辨率）
    for k in range(n - 1):
        Hh = pair_h(orb, matcher, grays[k], grays[k + 1], masks[k], masks[k + 1])
        step[k] = np.linalg.inv(S) @ Hh @ S

    to_ref = [np.eye(3) for _ in range(n)]
    for k in range(a.ref - 1, -1, -1):
        to_ref[k] = to_ref[k + 1] @ step[k]
    for k in range(a.ref + 1, n):
        to_ref[k] = to_ref[k - 1] @ np.linalg.inv(step[k - 1])

    G = np.load(a.G)
    court = [(G @ H / (G @ H)[2, 2]).tolist() for H in to_ref]
    json.dump({"ref": a.ref, "fps": fps, "court": court}, open(out / "cam.json", "w"))
    print(f"{n} frames -> {out / 'cam.json'}")


if __name__ == "__main__":
    main()
