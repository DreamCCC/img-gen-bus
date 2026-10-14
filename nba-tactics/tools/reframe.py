#!/usr/bin/env python3
"""横屏比赛片段 → 竖屏 1080×1920：逐帧检测篮球和场上球员，离线平滑出跟拍路径，裁成 1080×1280 窗口套进竖屏模板。

检测结果缓存在 <out>.det.json，调参重渲不用重跑 YOLO。--debug 额外输出横屏调试画面（裁切框、球、球员）。
用法: python reframe.py in.mp4 out.mp4 --title "布伦森抛投反超" --sub "总决赛 G4 · 第四节 1:22" [--debug]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from court import device
from track import floor_mask

OW, OH = 1080, 1920
WIN_Y, WIN_H = 300, 1280
BUG = (436, 930, 1464, 1010)
FONT = Path(__file__).resolve().parent.parent / "spurs_g4/film/assets/fonts/NotoSansSC.ttf"
MODEL = Path(__file__).resolve().parent.parent / "kyrie_macau/yolo11x.pt"


def detect(src: str, cache: Path) -> dict:
    if cache.exists():
        return json.loads(cache.read_text())
    from ultralytics import YOLO
    model, dev = YOLO(str(MODEL)), device()
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames, cuts, prev = [], [], None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        hsv = cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2HSV)
        h = cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256]), None).flatten()
        if prev is not None and cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA) > 0.45:
            cuts.append(len(frames))
        prev = h
        top = court_top(f)
        r = model.predict(f, imgsz=1920, classes=[0, 32], conf=0.05, device=dev, verbose=False)[0]
        balls, people = [], []
        for (x1, y1, x2, y2), c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            if int(k) == 32:
                balls.append([round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1), round(c, 3)])
            elif c >= 0.25:
                fx, fy = int((x1 + x2) / 2), int(y2)
                on = fy > top[min(fx, len(top) - 1)] + 12 and y2 - y1 > 80
                people.append([round(x1), round(y1), round(x2), round(y2), round(c, 3), bool(on)])
        frames.append({"ball": balls, "people": people, "bug": bug_score(f)})
    det = {"fps": fps, "w": int(cap.get(3)), "h": int(cap.get(4)), "cuts": cuts, "frames": frames}
    cache.write_text(json.dumps(det))
    return det


def court_top(f: np.ndarray) -> np.ndarray:
    """每一列地板（木地板 + 油漆区）的上沿 y；看台上的人脚在这条线以上。"""
    m = cv2.morphologyEx(floor_mask(f), cv2.MORPH_OPEN, np.ones((31, 31), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    has = m.any(0)
    top = np.where(has, m.argmax(0), f.shape[0])
    k = 41
    return np.array([np.median(top[max(0, i - k):i + k]) for i in range(len(top))])


def bug_score(f: np.ndarray) -> float:
    x1, y1, x2, y2 = BUG
    g = cv2.cvtColor(f[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    return round(float((g < 45).mean()), 3)


def consistent(det: dict) -> list:
    """低置信度的球只有在前后 3 帧内附近也有检测时才保留，去掉看台和衣服上的误检。"""
    fr, n = det["frames"], len(det["frames"])
    keep = []
    for i in range(n):
        ks = []
        for x, y, c in fr[i]["ball"]:
            if c >= 0.35:
                ks.append((x, y, c))
                continue
            if c < 0.08:
                continue
            near = sum(1 for j in range(max(0, i - 3), min(n, i + 4)) if j != i
                       for x2, y2, _ in fr[j]["ball"] if np.hypot(x - x2, y - y2) < 35 * abs(i - j) + 20)
            if near >= 2:
                ks.append((x, y, c))
        keep.append(ks)
    return keep


def pick_balls(det: dict) -> list:
    """每帧选一个球：置信度够高、离上一帧的球不太远；镜头切换后重置。"""
    out, last, gap = [], None, 99
    cuts = set(det["cuts"])
    cand = consistent(det)
    for i in range(len(cand)):
        if i in cuts:
            last, gap = None, 99
        best, score = None, -1e9
        for x, y, c in cand[i]:
            d = 0 if last is None else np.hypot(x - last[0], y - last[1])
            if last is not None and d > 90 + 40 * gap and c < 0.6:
                continue
            s = c - d / 600
            if s > score:
                best, score = (x, y, c), s
        out.append(best)
        if best:
            last, gap = best, 1
        else:
            gap += 1
    return fill_gaps(out, det["cuts"], int(det["fps"] * 0.6))


def fill_gaps(balls: list, cuts: list, maxgap: int) -> list:
    """同一镜头内不超过 maxgap 帧的空缺按直线插值（置信度记 0），给跟拍路径一个连续的目标。"""
    out = list(balls)
    idx = [i for i, b in enumerate(balls) if b]
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= maxgap and not any(a < c <= b for c in cuts):
            for i in range(a + 1, b):
                u = (i - a) / (b - a)
                out[i] = (balls[a][0] * (1 - u) + balls[b][0] * u, balls[a][1] * (1 - u) + balls[b][1] * u, 0.0)
    return out


def wsmooth(x: np.ndarray, w: np.ndarray, sigma: float) -> np.ndarray:
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    xp = np.pad(x * w, r, mode="edge")
    wp = np.pad(w, r, mode="edge")
    return np.convolve(xp, k, "valid") / np.maximum(np.convolve(wp, k, "valid"), 1e-6)


def camera_path(det: dict, balls: list, cw: float) -> np.ndarray:
    """跟球为主、球员重心为辅；按镜头分段做零相位加权平滑，再保证球始终落在窗口中间 64% 内。"""
    W, n, fps = det["w"], len(det["frames"]), det["fps"]
    tx, tw = np.full(n, W / 2), np.full(n, 1e-3)
    lo, hi = np.full(n, cw / 2), np.full(n, W - cw / 2)
    for i, fr in enumerate(det["frames"]):
        on = [p for p in fr["people"] if p[5] and p[3] - p[1] > 70]
        pc = float(np.median([(p[0] + p[2]) / 2 for p in on])) if on else None
        b = balls[i]
        if b:
            real = b[2] > 0
            tx[i], tw[i] = (0.75 * b[0] + 0.25 * pc) if pc else b[0], 1.0 if real else 0.6
            m = 0.32 if real else 0.38
            lo[i], hi[i] = max(lo[i], b[0] - m * cw), min(hi[i], b[0] + m * cw)
        elif pc is not None:
            tx[i], tw[i] = pc, 0.15
    bounds = [0] + det["cuts"] + [n]
    path = np.empty(n)
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b <= a:
            continue
        s = slice(a, b)
        p = wsmooth(tx[s], tw[s], 0.45 * fps)
        for _ in range(3):
            p = np.clip(p, lo[s], np.maximum(lo[s], hi[s]))
            p = wsmooth(p, np.ones(b - a), 0.15 * fps)
        path[s] = np.clip(p, cw / 2, W - cw / 2)
    return path


def bug_visible(det: dict) -> np.ndarray:
    s = np.array([fr["bug"] for fr in det["frames"]])
    ref = np.median(s[s > 0.15]) if (s > 0.15).any() else 1.0
    v = (s > 0.6 * ref).astype(float)
    k = int(det["fps"] * 0.25)
    v = np.convolve(np.pad(v, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    return np.clip((v - 0.3) / 0.4, 0, 1)


def template(title: str, sub: str) -> np.ndarray:
    y = np.linspace(0, 1, OH)[:, None]
    top, bot = np.array([18, 22, 38]), np.array([6, 8, 14])
    bg = (top * (1 - y) + bot * y)[:, None, :].repeat(OW, 1).astype(np.uint8)
    im = Image.fromarray(bg)
    d = ImageDraw.Draw(im)
    acc = (230, 62, 50)
    cx, base = OW // 2, OH + 260
    for r in (620, 360):
        d.ellipse((cx - r, base - r - 380, cx + r, base + r - 380), outline=(60, 70, 96), width=3)
    d.rectangle((cx - 240, OH - 330, cx + 240, OH), outline=(52, 60, 84), width=3)
    ft = ImageFont.truetype(str(FONT), 76)
    fs = ImageFont.truetype(str(FONT), 40)
    d.rectangle((80, 128, 92, 214), fill=acc)
    d.text((118, 120), title, font=ft, fill=(255, 255, 255))
    d.text((84, WIN_Y + WIN_H + 52), sub, font=fs, fill=(176, 184, 204))
    return np.array(im)[:, :, ::-1].copy()


def render(src: str, out: str, det: dict, path: np.ndarray, bugv: np.ndarray, tpl: np.ndarray, debug: bool, balls: list):
    H = det["h"]
    cw = H * OW / WIN_H
    sc = WIN_H / H
    bx1, by1, bx2, by2 = BUG
    bw = OW - 40
    bh = round((by2 - by1) * bw / (bx2 - bx1))
    band = (round((by1 - 14) * sc), round((by2 + 14) * sc))
    by = WIN_Y + (band[0] + band[1]) // 2 - bh // 2
    cap = cv2.VideoCapture(src)
    enc = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
           "-r", str(det["fps"]), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
           "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    pe = subprocess.Popen(enc, stdin=subprocess.PIPE)
    dbg = None
    if debug:
        dbg = cv2.VideoWriter(str(Path(out).with_suffix(".debug.mp4")), cv2.VideoWriter_fourcc(*"mp4v"), det["fps"], (960, 540))
    for i in range(len(path)):
        ok, f = cap.read()
        if not ok:
            break
        x0 = int(round(path[i] - cw / 2))
        win = cv2.resize(f[:, x0:x0 + int(round(cw))], (OW, WIN_H), interpolation=cv2.INTER_LANCZOS4)
        canvas = tpl.copy()
        canvas[WIN_Y:WIN_Y + WIN_H] = win
        a = bugv[i]
        if a > 0:
            seg = canvas[WIN_Y + band[0]:WIN_Y + band[1]].astype(np.float32)
            canvas[WIN_Y + band[0]:WIN_Y + band[1]] = (seg * (1 - 0.82 * a)).astype(np.uint8)
            bug = cv2.resize(f[by1:by2, bx1:bx2], (bw, bh), interpolation=cv2.INTER_AREA)
            roi = canvas[by:by + bh, 20:20 + bw].astype(np.float32)
            canvas[by:by + bh, 20:20 + bw] = (roi * (1 - a) + bug * a).astype(np.uint8)
        pe.stdin.write(canvas.tobytes())
        if dbg is not None:
            g = f.copy()
            for p in det["frames"][i]["people"]:
                cv2.rectangle(g, (p[0], p[1]), (p[2], p[3]), (0, 200, 0) if p[5] else (90, 90, 90), 2)
            if balls[i]:
                cv2.circle(g, (int(balls[i][0]), int(balls[i][1])), 16, (0, 140, 255), 4)
            cv2.rectangle(g, (x0, 0), (x0 + int(cw), H - 1), (255, 255, 255), 6)
            dbg.write(cv2.resize(g, (960, 540)))
    pe.stdin.close()
    pe.wait()
    if dbg is not None:
        dbg.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--title", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    det = detect(a.src, Path(a.out).with_suffix(".det.json"))
    cw = det["h"] * OW / WIN_H
    balls = pick_balls(det)
    path = camera_path(det, balls, cw)
    seen = sum(1 for b in balls if b and b[2] > 0)
    filled = sum(1 for b in balls if b and b[2] == 0)
    print(f"{len(balls)} frames, ball detected {seen} ({seen / len(balls):.0%}), interpolated {filled}, cuts {det['cuts']}")
    render(a.src, a.out, det, path, bug_visible(det), template(a.title, a.sub), a.debug, balls)
    print("->", a.out)


if __name__ == "__main__":
    main()
