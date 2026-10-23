import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("../tools").resolve()))
from court import RIM, Cam  # noqa: E402

cam = Cam(Path("work/e676w/cam.json"))
print("cam frames", cam.n)
for f in (150, 204, 247, 276):
    print(f, "rim floor", cam.to_img(f, [RIM]).round(0).tolist())
for nm, (u, v) in {"BR": (23.8, -20.2), "WB": (26.0, -15.3)}.items():
    for s in (1, -1):
        print(nm, "v sign", s, cam.to_img(204, [(u, s * v)]).round(0).tolist())
for xy in [(830, 850), (915, 790), (630, 940), (770, 880), (1000, 724), (892, 768)]:
    print(xy, "->", cam.to_court(204, [xy]).round(1).tolist())
