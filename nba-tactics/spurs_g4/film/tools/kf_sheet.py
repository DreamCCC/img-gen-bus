"""人工打跟拍关键帧用的看图工具：镜头内按 --step 秒抽帧，横屏原画面叠横向刻度（每 160 素材像素一条线、标坐标），
可选画出当前裁切框（--box，按 film_vt.json 现有的 cx/cxk/track 算）。每张图 2 列 × 3 行。
--raw 直接读原视频，--t0/--t1 可以超出镜头范围（负数 = 镜头开始之前），用来找出手、进球那一帧；时间仍按镜头内秒数标。
--big 一列大图看清球，--y0/--y1 只取画面这几行（去掉看台和比分条，图更清楚）。
用法：nba-tactics/.venv/bin/python tools/kf_sheet.py v_s2_down [--step 0.5] [--box] [--raw --t0 -1 --t1 2 --big] [--out out/vt/kf]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from qa_track_vt import crop_box  # noqa: E402

FPS, TW, TH, COLS, ROWS = 30, 960, 540, 2, 3


def ruler(f, y0=0, y1=1080):
    g = f.copy()
    for x in range(160, 1920, 160):
        cv2.line(g, (x, 0), (x, 1079), (0, 255, 255), 2)
        for y in (y0 + 60, y1 - 40):
            cv2.putText(g, str(x), (x - 52, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 9)
            cv2.putText(g, str(x), (x - 52, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 3)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--box", action="store_true")
    ap.add_argument("--t0", type=float, default=0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--out", default=str(ROOT / "out/vt/kf"))
    ap.add_argument("--big", action="store_true", help="一列大图，看清球和出手动作")
    ap.add_argument("--raw", action="store_true", help="读原视频，可看镜头前后")
    ap.add_argument("--y0", type=int, default=0)
    ap.add_argument("--y1", type=int, default=1080)
    ap.add_argument("--x0", type=int, default=0)
    ap.add_argument("--x1", type=int, default=1920)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=2)
    a = ap.parse_args()
    global TW, TH, COLS, ROWS
    film = json.loads((ROOT / "scenes/film_vt.json").read_text())
    track = json.loads((ROOT / "scenes/track_vt.json").read_text())
    sh = next(s for s in film["shots"] if s.get("clip") == a.clip)
    dur = sh["b"] - sh["a"]
    w, h = a.x1 - a.x0, a.y1 - a.y0
    if a.big:
        TW, TH = 1920 // 2 if w <= 960 else 1920, None
        TH = TW * h // w
        COLS = 1920 // TW
        ROWS = max(1, 2400 // TH)
    else:
        TH = TW * h // w
        ROWS, COLS = a.rows, a.cols
    if a.raw:
        spec = next(c for c in json.loads((ROOT / "clips_vt.json").read_text()) if c["name"] == a.clip)
        rate = (spec["t1"] - spec["t0"]) / spec["dur"]

        def frame(lt):
            # OpenCV 在 AV1 / VP9 素材里按时间跳转会落到别的画面，只能用 ffmpeg 定位
            t = max(0.0, spec["t0"] + lt * rate)
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(ROOT / spec["src"]), "-frames:v", "1",
                                  "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
            if len(raw) < 1920 * 1080 * 3:
                return np.zeros((1080, 1920, 3), np.uint8)
            return np.frombuffer(raw[:1920 * 1080 * 3], np.uint8).reshape(1080, 1920, 3).copy()
    else:
        files = sorted((ROOT / "scenes/clips" / a.clip).glob("*.jpg"))

        def frame(lt):
            return cv2.imread(str(files[min(max(int(lt * FPS), 0), len(files) - 1)]))
    tiles = []
    t1 = a.t1 if a.t1 is not None else dur
    for lt in np.arange(a.t0, (t1 if a.raw else min(dur, t1)) + 1e-6, a.step):
        g = ruler(frame(lt), a.y0, a.y1)
        if a.box and 0 <= lt <= dur:
            sx, sy, sw, shh, _ = crop_box(sh, lt, track.get(a.clip))
            cv2.rectangle(g, (int(sx), int(sy)), (int(sx + sw), int(sy + shh) - 1), (255, 255, 255), 10)
        g = g[a.y0:a.y1, a.x0:a.x1]
        t = cv2.resize(g, (TW, TH), interpolation=cv2.INTER_AREA)
        cv2.rectangle(t, (0, 0), (250, 56), (0, 0, 0), -1)
        cv2.putText(t, f"{lt:.2f}s", (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255) if 0 <= lt <= dur else (0, 0, 255), 3)
        tiles.append(t)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    per = COLS * ROWS
    tag = f"_{a.t0:g}" if a.t0 else ""
    for p in range(0, len(tiles), per):
        page = tiles[p:p + per]
        while len(page) < per:
            page.append(np.zeros((TH, TW, 3), np.uint8))
        img = np.vstack([np.hstack(page[r * COLS:(r + 1) * COLS]) for r in range(ROWS)])
        path = out / f"{a.clip}{tag}_{p // per}.jpg"
        cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 82])
        print(path)


if __name__ == "__main__":
    main()
