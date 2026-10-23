import re
import subprocess
import sys

for spec in sys.argv[1:]:
    path, *rng = spec.split("@")
    pre = ["-ss", rng[0].split("-")[0], "-to", rng[0].split("-")[1]] if rng else []
    err = subprocess.run(["ffmpeg", "-nostats", *pre, "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"^\s*I:\s*(-?[\d.]+) LUFS", err, re.M)
    print(f"{spec:55s} {i[-1] if i else 'n/a':>7s} LUFS")
