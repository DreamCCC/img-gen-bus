import json, sys
from pathlib import Path
for ev in ("613", "554"):
    w = Path(f"work/q4miss/e{ev}")
    P = json.load(open(w / "players.json"))
    for k, d in P.items():
        uv = [i for i, u in enumerate(d["uv"]) if u is not None]
        bx = [i for i, u in enumerate(d["box"]) if u is not None]
        print(ev, k, len(d["uv"]), "uv", uv[:1], uv[-1:], len(uv), "box", bx[:1], bx[-1:], len(bx))
    m = sorted(int(p.stem) for p in (w / "masks").glob("*.npz"))
    print(ev, "masks", m[:1], m[-1:], len(m))
    cam = json.load(open(w / "cam.json"))
    print(ev, "cam keys", list(cam)[:6] if isinstance(cam, dict) else type(cam))
