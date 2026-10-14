"""竖版比赛镜头的 4:5 跟拍路径：对 scenes/clips/<name>/ 的抽帧跑 YOLO（球 + 人），按 nba-tactics/tools/reframe.py 的办法平滑出裁切中心，
写 scenes/track_vt.json：{clip: {"cx": [每帧裁切中心，素材像素], "bug": [每帧转播计分牌可见度 0–1]}}。

隔一帧检测一次，路径再插值回每帧；检测结果缓存在 work/vt_det/<clip>.json，调参不用重跑 YOLO。
要跟拍的镜头清单由 tools/timeline_vt.py 写在 work/vt_track_list.json（cx 写死的镜头不在里面）。
用法：nba-tactics/.venv/bin/python tools/track_vt.py [clip ...]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parents[1] / "tools"))
import reframe  # noqa: E402
from court import device  # noqa: E402

CLIPS = ROOT / "scenes/clips"
CACHE = ROOT / "work/vt_det"
OUT = ROOT / "scenes/track_vt.json"
CROP_W = 1080 * 1080 / 1350
STEP = 2


def detect(name, model, dev):
    cache = CACHE / f"{name}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    files = sorted((CLIPS / name).glob("*.jpg"))
    frames, cuts, prev = [], [], None
    for k, fp in enumerate(files[::STEP]):
        f = cv2.imread(str(fp))
        hsv = cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2HSV)
        h = cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256]), None).flatten()
        if prev is not None and cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA) > 0.45:
            cuts.append(k)
        prev = h
        top = reframe.court_top(f)
        r = model.predict(f, imgsz=1920, classes=[0, 32], conf=0.05, device=dev, verbose=False)[0]
        balls, people = [], []
        for (x1, y1, x2, y2), c, cl in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            if int(cl) == 32:
                balls.append([round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1), round(c, 3)])
            elif c >= 0.25:
                fx, fy = int((x1 + x2) / 2), int(y2)
                on = fy > top[min(fx, len(top) - 1)] + 12 and y2 - y1 > 80
                people.append([round(x1), round(y1), round(x2), round(y2), round(c, 3), bool(on)])
        frames.append({"ball": balls, "people": people, "bug": reframe.bug_score(f)})
    det = {"fps": 30 / STEP, "w": 1920, "h": 1080, "n": len(files), "cuts": cuts, "frames": frames}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(det))
    return det


def track(det):
    balls = reframe.pick_balls(det)
    path = reframe.camera_path(det, balls, CROP_W)
    bug = reframe.bug_visible(det)
    n = det["n"]
    xs = np.arange(len(path)) * STEP
    full = np.arange(n)
    cx = np.interp(full, xs, path)
    bv = np.interp(full, xs, bug)
    for c in det["cuts"]:
        a, b = (c - 1) * STEP, c * STEP
        cx[a + 1:b] = path[c]
        bv[a + 1:b] = bug[c]
    seen = sum(1 for b in balls if b and b[2] > 0)
    return cx, bv, seen / max(1, len(balls))


def main():
    from ultralytics import YOLO
    names = sys.argv[1:] or json.loads((ROOT / "work/vt_track_list.json").read_text())
    model, dev = YOLO(str(reframe.MODEL)), device()
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name in names:
        det = detect(name, model, dev)
        cx, bv, rate = track(det)
        out[name] = {"cx": [round(float(x), 1) for x in cx], "bug": [round(float(x), 2) for x in bv]}
        print(f"{name:16s} {det['n']:4d} 帧  球 {rate:4.0%}  镜头切换 {det['cuts']}  cx {cx.min():.0f}–{cx.max():.0f}  bug {bv.mean():.2f}", flush=True)
        OUT.write_text(json.dumps(out))
    print("->", OUT)


if __name__ == "__main__":
    main()
