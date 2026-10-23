import json, shutil
from pathlib import Path
import cv2
import numpy as np

for ev, a, b in (("613", 70, 125), ("554", 40, 96)):
    d = Path(f"work/q4miss/e{ev}/fr/orig")
    prev, out = None, []
    for f in range(a, b):
        g = cv2.resize(cv2.imread(str(d / f"{f:04d}.jpg"), 0), (240, 135)).astype(np.float32)
        if prev is not None:
            out.append((f, round(float(np.abs(g - prev).mean()), 1)))
        prev = g
    print(ev, sorted(out, key=lambda x: -x[1])[:5])
    cam = json.load(open(f"work/q4miss/e{ev}/cam.json"))
    print(ev, "cam ref", str(cam["ref"])[:200])
    w = Path(f"work/q4miss/e{ev}")
    print(ev, "masks MB", round(sum(p.stat().st_size for p in (w / "masks").glob("*")) / 1e6, 1),
          [p.name for p in w.iterdir()])
