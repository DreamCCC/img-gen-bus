#!/usr/bin/env python3
"""球员检测 + 跟踪：YOLO（person）+ BoT-SORT，按木地板/油漆区颜色过滤看台观众。

输出:
  <out>/tracks.json   {"fps", "w", "h", "frames": [[{"id","box":[x1,y1,x2,y2],"conf","team"}...], ...]}
  <out>/ids/NNNN.jpg  每 N 帧一张带编号的预览图（用来人工认球员）

用法: python track.py raw/e453_pullup.mp4 work/e453 --end 11.8 --every 15
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from court import device


def floor_mask(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    wood = cv2.inRange(hsv, (5, 25, 110), (30, 140, 255))
    paint = cv2.inRange(hsv, (100, 120, 60), (125, 255, 230))
    m = cv2.morphologyEx(wood | paint, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    return m


def on_floor(mask: np.ndarray, box) -> bool:
    x1, y1, x2, y2 = (int(v) for v in box)
    h, w = mask.shape
    cx = (x1 + x2) // 2
    ys = slice(min(h - 1, y2), min(h, y2 + 12))
    xs = slice(max(0, cx - 15), min(w, cx + 15))
    patch = mask[ys, xs]
    return patch.size > 0 and patch.mean() > 100


def jersey_team(frame: np.ndarray, box) -> str:
    """火箭红衣 / 独行侠蓝衣，按躯干中段的色相粗分。"""
    x1, y1, x2, y2 = (int(v) for v in box)
    bh, bw = y2 - y1, x2 - x1
    roi = frame[y1 + int(bh * 0.22): y1 + int(bh * 0.5), x1 + int(bw * 0.25): x2 - int(bw * 0.25)]
    if roi.size == 0:
        return "?"
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sat = hsv[..., 1] > 90
    red = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & sat).mean()
    blue = (((hsv[..., 0] > 95) & (hsv[..., 0] < 130)) & sat).mean()
    if red > 0.18 and red > blue:
        return "HOU"
    if blue > 0.18:
        return "DAL"
    return "?"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--end", type=float, default=1e9, help="只处理到第几秒（跳过片尾近景回放）")
    ap.add_argument("--every", type=int, default=15)
    ap.add_argument("--model", default="yolo11x.pt")
    ap.add_argument("--imgsz", type=int, default=1280)
    a = ap.parse_args()

    out = Path(a.out)
    (out / "ids").mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    model = YOLO(a.model)
    frames: list[list[dict]] = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok or i / fps > a.end:
            break
        res = model.track(frame, persist=True, classes=[0], conf=0.25, imgsz=a.imgsz,
                          tracker="botsort.yaml", verbose=False, device=device())[0]
        mask = floor_mask(frame)
        dets = []
        if res.boxes.id is not None:
            for box, tid, conf in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.id.cpu().numpy(),
                                      res.boxes.conf.cpu().numpy()):
                if (box[3] - box[1]) < 60 or not on_floor(mask, box):
                    continue
                dets.append({"id": int(tid), "box": [round(float(v), 1) for v in box],
                             "conf": round(float(conf), 3), "team": jersey_team(frame, box)})
        frames.append(dets)
        if i % a.every == 0:
            vis = frame.copy()
            for d in dets:
                x1, y1, x2, y2 = (int(v) for v in d["box"])
                col = {"HOU": (40, 40, 230), "DAL": (230, 140, 30)}.get(d["team"], (200, 200, 200))
                cv2.rectangle(vis, (x1, y1), (x2, y2), col, 2)
                cv2.putText(vis, str(d["id"]), (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
                cv2.putText(vis, str(d["id"]), (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(vis, f"f{i} t={i / fps:.2f}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 3)
            cv2.imwrite(str(out / "ids" / f"{i:04d}.jpg"), cv2.resize(vis, (1280, 720)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        i += 1
    json.dump({"fps": fps, "w": w, "h": h, "frames": frames}, open(out / "tracks.json", "w"))
    print(f"{i} frames, ids={len({d['id'] for f in frames for d in f})} -> {out}")


if __name__ == "__main__":
    main()
