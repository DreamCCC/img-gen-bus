#!/usr/bin/env python3
"""每个跟踪编号截 3 帧原图拼成一张认人表，配合 eNNN_players.json 用。

用法: python idsheet.py raw/xxx.mp4 work/eNNN [--min 15] [--from 0] [--to 99999] [--miny 420]
输出 work/eNNN/idsheet.jpg，每行一个编号：编号、存活帧段、三张裁切（起、中、末）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("work")
    ap.add_argument("--min", type=int, default=15, help="至少存活多少帧")
    ap.add_argument("--from", dest="f0", type=int, default=0)
    ap.add_argument("--to", dest="f1", type=int, default=10**9)
    ap.add_argument("--miny", type=float, default=420, help="框底低于这条线才算场上（过滤看台）")
    a = ap.parse_args()

    frames = json.load(open(Path(a.work) / "tracks.json"))["frames"]
    life: dict[int, list[tuple[int, list[float]]]] = {}
    for f, dets in enumerate(frames):
        if not a.f0 <= f <= a.f1:
            continue
        for d in dets:
            if d["box"][3] >= a.miny:
                life.setdefault(d["id"], []).append((f, d["box"]))
    ids = sorted((i for i, v in life.items() if len(v) >= a.min), key=lambda i: life[i][0][0])

    want = {}
    for i in ids:
        v = life[i]
        for k in (0, len(v) // 2, len(v) - 1):
            want.setdefault(v[k][0], []).append((i, k, v[k][1]))
    cap = cv2.VideoCapture(a.video)
    crops: dict[tuple[int, int], np.ndarray] = {}
    f = 0
    while f <= max(want, default=-1):
        ok, img = cap.read()
        if not ok:
            break
        for i, k, b in want.get(f, []):
            x1, y1, x2, y2 = map(int, b)
            pad = int((y2 - y1) * 0.15)
            c = img[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad]
            h = 200
            crops[(i, k)] = cv2.resize(c, (max(1, int(c.shape[1] * h / max(1, c.shape[0]))), h))
        f += 1

    rows = []
    for i in ids:
        v = life[i]
        cells = [crops[(i, k)] for k in (0, len(v) // 2, len(v) - 1) if (i, k) in crops]
        label = np.zeros((200, 220, 3), np.uint8)
        cv2.putText(label, f"#{i}", (8, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 3)
        cv2.putText(label, f"{v[0][0]}-{v[-1][0]}", (8, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(label, f"n={len(v)}", (8, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)
        row = np.hstack([label] + cells)
        rows.append(row)
    W = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.zeros((200, W - r.shape[1], 3), np.uint8)]) for r in rows]
    out = Path(a.work) / "idsheet.jpg"
    per = 12
    for p in range(0, len(rows), per):
        cv2.imwrite(str(out.with_name(f"idsheet_{p // per}.jpg")), np.vstack(rows[p:p + per]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(len(ids), "ids ->", out.parent / "idsheet_*.jpg")


if __name__ == "__main__":
    main()
