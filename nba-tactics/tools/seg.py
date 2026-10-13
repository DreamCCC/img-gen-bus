#!/usr/bin/env python3
"""给指定跟踪 ID 的球员抠人形蒙版（YOLO-seg），按与 tracks.json 框的 IoU 配对。

输出 <out>/masks/NNNN.npz：每个 key 一个 (x1, y1, 裁剪后的 uint8 蒙版)。
用法: python seg.py raw/e464_three.mp4 work/e464 --ids 5,301,3,1,13,4 --start 0 --end 200
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--ids", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10**9)
    ap.add_argument("--model", default="yolo11x-seg.pt")
    a = ap.parse_args()

    out = Path(a.out)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    tracks = json.load(open(out / "tracks.json"))["frames"]
    ids = {int(x) for x in a.ids.split(",")}
    model = YOLO(a.model)
    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.start)
    i = a.start
    while i <= min(a.end, len(tracks) - 1):
        ok, frame = cap.read()
        if not ok:
            break
        want = [d for d in tracks[i] if d["id"] in ids]
        if want:
            res = model.predict(frame, classes=[0], conf=0.2, imgsz=1280, retina_masks=True,
                                verbose=False, device="mps")[0]
            boxes = res.boxes.xyxy.cpu().numpy() if res.masks is not None else []
            saved = {}
            for d in want:
                best, bi = 0.3, -1
                for k, b in enumerate(boxes):
                    s = iou(d["box"], b)
                    if s > best:
                        best, bi = s, k
                if bi < 0:
                    continue
                m = res.masks.data[bi].cpu().numpy() > 0.5
                ys, xs = np.nonzero(m)
                if len(xs) == 0:
                    continue
                x1, y1, x2, y2 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
                saved[str(d["id"])] = np.array([x1, y1])
                saved[f"m{d['id']}"] = m[y1:y2, x1:x2].astype(np.uint8)
            np.savez_compressed(out / "masks" / f"{i:04d}.npz", **saved)
        i += 1
    print(f"masks {a.start}-{i - 1} -> {out / 'masks'}")


if __name__ == "__main__":
    main()
