"""去掉万相输出里的重复帧并用运动补偿插帧补回 30fps，时间轴不变（口型仍对齐）。

python smooth.py F2 N2 ...  → wan/smooth/<id>.mp4
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent


def dup_frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=320:180", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    out = []
    for i, x in enumerate(d):
        local = np.median(d[max(0, i - 7):i + 8])
        if x < max(0.25, 0.3 * local):
            out.append(i + 1)
    return out


def run(name):
    src, dst = HERE / f"{name}.mp4", HERE / "smooth" / f"{name}.mp4"
    drop = dup_frames(src)
    keep = "select='" + ("not(" + "+".join(f"eq(n\\,{k})" for k in drop) + ")" if drop else "1") + "'"
    vf = f"{keep},minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14",
                    "-preset", "medium", "-pix_fmt", "yuv420p", str(dst)], check=True)
    return name, len(drop)


if __name__ == "__main__":
    (HERE / "smooth").mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for name, n in ex.map(run, sys.argv[1:]):
            print(name, "dropped", n)
