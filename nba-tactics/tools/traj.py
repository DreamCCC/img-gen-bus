#!/usr/bin/env python3
"""把跟踪 ID 合并成每名球员一条球场轨迹（英尺），补短缺口、平滑。

输入: <work>/tracks.json, <work>/cam.json, 球员配置（见 kd_macau/e464_players.json）
输出: <work>/players.json  {key: {name, num, team, uv[N], box[N], tid[N]}}，缺失为 null
用法: python traj.py kd_macau/work/e464 kd_macau/e464_players.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from court import Cam  # noqa: E402

MAX_GAP = 45


def smooth(a: np.ndarray, ok: np.ndarray, k: int = 7) -> np.ndarray:
    out = a.copy()
    h = k // 2
    for i in np.nonzero(ok)[0]:
        lo, hi = max(0, i - h), min(len(a), i + h + 1)
        w = ok[lo:hi]
        med = np.median(a[lo:hi][w], axis=0)
        out[i] = med
    res = out.copy()
    for i in np.nonzero(ok)[0]:
        lo, hi = max(0, i - 2), min(len(a), i + 3)
        w = ok[lo:hi]
        res[i] = out[lo:hi][w].mean(axis=0)
    return res


def main() -> None:
    work = Path(sys.argv[1])
    cfg = json.load(open(sys.argv[2]))["players"]
    tracks = json.load(open(work / "tracks.json"))["frames"]
    cam = Cam(work / "cam.json")
    n = min(len(tracks), cam.n)
    out = {}
    for p in cfg:
        uv = np.full((n, 2), np.nan)
        box: list = [None] * n
        tid: list = [None] * n
        for f in range(n):
            for i, a, b in p["ids"]:
                if not a <= f <= b:
                    continue
                d = next((d for d in tracks[f] if d["id"] == i), None)
                if d is None:
                    continue
                x1, y1, x2, y2 = d["box"]
                uv[f] = cam.to_court(f, [(x1 + x2) / 2, y2])[0]
                box[f], tid[f] = d["box"], i
                break
        for f, x, y in p.get("manual", []):
            uv[f] = cam.to_court(f, [x, y])[0]
        for a, b in p.get("air", []):
            uv[a + 1:b] = np.nan
        ok = ~np.isnan(uv[:, 0])
        uv = smooth(np.nan_to_num(uv), ok)
        idx = np.nonzero(ok)[0]
        for a, b in zip(idx[:-1], idx[1:]):
            if 1 < b - a <= MAX_GAP:
                t = (np.arange(a + 1, b) - a) / (b - a)
                uv[a + 1:b] = uv[a] * (1 - t[:, None]) + uv[b] * t[:, None]
                ok[a + 1:b] = True
        out[p["key"]] = {"name": p["name"], "num": p["num"], "team": p["team"],
                         "uv": [[round(float(u), 2), round(float(v), 2)] if ok[f] else None for f, (u, v) in enumerate(uv)],
                         "box": box, "tid": tid}
        print(f"{p['key']:3s} {p['name']:6s} 有效 {ok.sum()}/{n} 帧  首 {idx.min() if len(idx) else '-'} 末 {idx.max() if len(idx) else '-'}")
    json.dump(out, open(work / "players.json", "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
