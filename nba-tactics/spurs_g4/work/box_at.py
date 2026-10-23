"""Print tracked box + hq mask extent for players at a frame. usage: python box_at.py work_dir frame KEY [KEY..]"""
import json
import sys
from pathlib import Path

import numpy as np

work, f, keys = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3:]
P = json.loads((work / "players.json").read_text(encoding="utf-8"))
for k in keys:
    d = P[k] if isinstance(P, dict) and k in P else next(p for p in P["players"] if p["key"] == k)
    box = d["box"][f] if f < len(d["box"]) else None
    hq = work / "masks_hq" / f"{f:04d}_{k}.npz"
    ext = None
    if hq.exists():
        e = np.load(hq)
        (x1, y1), m = e["xy"], e["m"] > 0
        ys, xs = np.nonzero(m)
        ext = [int(x1 + xs.min()), int(y1 + ys.min()), int(x1 + xs.max()), int(y1 + ys.max())]
    print(k, "box", None if box is None else [round(v) for v in box], "hq-mask", ext)
