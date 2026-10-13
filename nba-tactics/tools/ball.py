#!/usr/bin/env python3
"""逐帧检测篮球（COCO sports ball），输出 ball.json: [[frame, x, y, r, conf] ...]。

用法: python ball.py raw/e464_three.mp4 work/e464 --end 8.8
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from ultralytics import YOLO


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--end", type=float, default=1e9)
    ap.add_argument("--model", default="yolo11x.pt")
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    model = YOLO(a.model)
    rows = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok or i / fps > a.end:
            break
        res = model.predict(frame, classes=[32], conf=0.08, imgsz=1920, verbose=False, device="mps")[0]
        for box, conf in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy()):
            x1, y1, x2, y2 = box
            rows.append([i, round(float((x1 + x2) / 2), 1), round(float((y1 + y2) / 2), 1),
                         round(float(max(x2 - x1, y2 - y1) / 2), 1), round(float(conf), 3)])
        i += 1
    Path(a.out).mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(Path(a.out) / "ball.json", "w"))
    print(f"{i} frames, {len(rows)} ball detections")


if __name__ == "__main__":
    main()
