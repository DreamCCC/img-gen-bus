"""去掉 AI 视频（万相等）里的重复帧，用运动补偿插帧补回原帧率；时间轴不变，对口型镜头仍然对齐。

python smooth_dups.py in.mp4 out.mp4 [--fps 30]
先用 video_qa.py 确认有重复帧（每秒 > 15%）再用。只处理画面，不带音频。
ffmpeg 自带的 mpdecimate 认不出这种重新编码过的"近似重复"帧，所以这里自己逐帧比较后用 select 删掉。
"""
import argparse
import subprocess

import numpy as np


def dup_frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=320:180", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    return [i + 1 for i, x in enumerate(d) if x < max(0.25, 0.3 * np.median(d[max(0, i - 7):i + 8]))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    drop = dup_frames(a.src)
    keep = "select='not(" + "+".join(f"eq(n\\,{k})" for k in drop) + ")'," if drop else ""
    vf = f"{keep}minterpolate=fps={a.fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14",
                    "-preset", "medium", "-pix_fmt", "yuv420p", a.dst], check=True)
    print(f"{a.src}: 删掉 {len(drop)} 个重复帧 → {a.dst}")


if __name__ == "__main__":
    main()
