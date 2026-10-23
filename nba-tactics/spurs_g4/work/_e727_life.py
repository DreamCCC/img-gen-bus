"""Lifetime + sampled foot uv of given track ids: python work/_e727_life.py 1,519,340"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from court import Cam  # noqa: E402

W = Path("work/e727w")
tr = json.load(open(W / "tracks.json"))["frames"]
cam = Cam(W / "cam.json")
for i in [int(x) for x in sys.argv[1].split(",")]:
    fs = [(f, d["box"]) for f, ds in enumerate(tr) for d in ds if d["id"] == i]
    if not fs:
        print(i, "none")
        continue
    print(f"id {i}: {fs[0][0]}-{fs[-1][0]} n={len(fs)}")
    for f, b in fs:
        if f % 6 == 0 or f == fs[0][0] or f == fs[-1][0]:
            u, v = cam.to_court(f, [((b[0] + b[2]) / 2, b[3])])[0]
            print(f"   f{f} foot {int((b[0] + b[2]) / 2)},{int(b[3])} uv {u:.1f},{v:.1f}")
