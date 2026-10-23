import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("../tools").resolve()))
from court import RIM  # noqa: E402

P = json.load(open("work/e676w/players.json"))
for f in [int(x) for x in sys.argv[1:]]:
    row = [f]
    for k in P:
        u = P[k]["uv"][f]
        row.append(f"{k} {u}" + (f" rim {np.linalg.norm(np.array(u) - RIM):.1f}" if u else ""))
    if "BR" in P and "WB" in P and P["BR"]["uv"][f] and P["WB"]["uv"][f]:
        row.append(f"BR-WB {np.linalg.norm(np.array(P['BR']['uv'][f]) - np.array(P['WB']['uv'][f])):.1f}")
    print(*row, sep=" | ")
