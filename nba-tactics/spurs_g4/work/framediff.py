"""Mean abs difference between consecutive frames (downscaled gray); flags near-duplicates and spikes."""
import subprocess
import sys

import numpy as np

path, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200
W, H = 320, 180
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H},format=gray", "-frames:v", str(n),
                      "-f", "rawvideo", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
med = np.median(d)
print(f"{path}: {len(fr)} frames, median diff {med:.2f}")
print(" ".join(f"{v:.1f}" for v in d))
print("near-dup frames:", [i + 1 for i, v in enumerate(d) if v < 0.25 * med])
print("spikes:", [i + 1 for i, v in enumerate(d) if v > 3 * med])
