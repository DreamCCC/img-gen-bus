"""成片/片段体检：按秒报告码率、重复帧比例、画面冻结、黑场，并核对帧数与时长。

python video_qa.py in.mp4 [--from 秒] [--to 秒] [--region x,y,w,h] [--all] [--max-mbps 50]
  --region    只看画面的一块（比例 0–1），例如九宫格正中一格：0.333,0.333,0.333,0.333
  --all       每秒都打印；默认只打印有问题的秒
  --max-mbps  码率阈值；检查高码率中间文件时设 0 关掉这项
判定（每秒）：码率超过阈值；重复帧 > 15%（与前一帧几乎相同，且明显低于附近帧的变化量）；
整秒冻结（所有帧都几乎不变）；黑场（平均亮度 < 0.03）。
"""
import argparse
import json
import subprocess
from collections import Counter

import numpy as np

W, H = 320, 180


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-count_packets", "-show_entries",
                          "stream=r_frame_rate,nb_read_packets:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    num, den = j["streams"][0]["r_frame_rate"].split("/")
    return float(j["format"]["duration"]), float(num) / float(den), int(j["streams"][0]["nb_read_packets"])


def bitrate_per_sec(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "packet=pts_time,size",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
    b = Counter()
    for line in out.splitlines():
        t, s = line.split(",")[:2]
        if t not in ("", "N/A"):
            b[int(float(t))] += int(s)
    return {k: v * 8 / 1e6 for k, v in b.items()}


def frames(path, t0, t1, region):
    vf = f"scale={W}:{H}"
    if region:
        x, y, w, h = region
        vf = f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}," + vf
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-i", path, "-t", str(t1 - t0), "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--region")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-mbps", type=float, default=50)
    a = ap.parse_args()

    dur, fps, n = probe(a.path)
    print(f"时长 {dur:.3f}s  帧率 {fps:.3f}  帧数 {n}（应为 {round(dur * fps)}）")
    br = bitrate_per_sec(a.path)
    print(f"码率 平均 {np.mean(list(br.values())):.1f} Mbps  峰值 {max(br.values()):.1f} Mbps（第 {max(br, key=br.get)} 秒）")

    t1 = a.t1 if a.t1 is not None else dur
    region = [float(v) for v in a.region.split(",")] if a.region else None
    f = frames(a.path, a.t0, t1, region)
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    dup = np.array([x < max(0.25, 0.3 * np.median(d[max(0, i - 7):i + 8])) for i, x in enumerate(d)])
    luma = f.mean((1, 2)) / 255
    per = int(round(fps))
    print("秒      码率  重复帧  冻结  黑场")
    bad = 0
    for s in range(0, len(d), per):
        sec = int(a.t0) + s // per
        r_dup, frozen, black = dup[s:s + per].mean(), bool((d[s:s + per] < 0.25).all()), luma[s:s + per].mean() < 0.03
        mb = br.get(sec, 0)
        flag = (a.max_mbps > 0 and mb > a.max_mbps) or r_dup > 0.15 or frozen or black
        bad += flag
        if flag or a.all:
            print(f"{sec:5d} {mb:7.1f} {r_dup:6.0%} {'是' if frozen else '':>4} {'是' if black else '':>4}{'  ←' if flag else ''}")
    print("没有发现问题" if not bad else f"{bad} 秒有问题")


if __name__ == "__main__":
    main()
