import json

import numpy as np

P = json.load(open("work/e727w/players.json"))
RIM = np.array([5.25, 0.0])
for f in (110, 114, 118, 120, 124):
    u = {k: (np.array(v["uv"][f]) if v["uv"][f] else None) for k, v in P.items()}
    og = u["OG"]
    d = {k: round(float(np.linalg.norm(u[k] - og)), 1) for k in ("WB", "FX", "CA", "HP", "VS") if u[k] is not None}
    b = {k: round(float(np.linalg.norm(u[k] - u["BR"])), 1) for k in ("WB", "FX") if u[k] is not None}
    print(f, "OG", og, "rim", round(float(np.linalg.norm(og - RIM)), 1), "OG-def", d, "BR-def", b,
          "BR rim", round(float(np.linalg.norm(u["BR"] - RIM)), 1))
