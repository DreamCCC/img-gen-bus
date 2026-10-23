"""Draw track IDs + court uv on chosen frames: python work/_e727_ids.py 118,150,... [x0,y0,x1,y1]"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from court import Cam, RIM  # noqa: E402

W = Path("work/e727w")
tr = json.load(open(W / "tracks.json"))["frames"]
cam = Cam(W / "cam.json")
fs = [int(x) for x in sys.argv[1].split(",")]
crop = [int(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
for f in fs:
    img = cv2.imread(str(W / f"fr/orig/{f:04d}.jpg"))
    print(f"--- f{f}")
    for d in tr[f]:
        x1, y1, x2, y2 = d["box"]
        if y2 < 380:
            continue
        u, v = cam.to_court(f, [((x1 + x2) / 2, y2)])[0]
        rd = np.hypot(u - RIM[0], v - RIM[1])
        print(f"  id {d['id']:4d} foot {int((x1 + x2) / 2):4d},{int(y2):4d}  uv {u:6.1f},{v:6.1f}  rim {rd:5.1f}")
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
        cv2.putText(img, f"{d['id']}", (int(x1), int(y1) - 6), 0, 0.9, (0, 0, 0), 5)
        cv2.putText(img, f"{d['id']}", (int(x1), int(y1) - 6), 0, 0.9, (0, 255, 255), 2)
        cv2.putText(img, f"{u:.0f},{v:.0f}", (int(x1), int(y2) + 20), 0, 0.6, (255, 255, 255), 2)
    cv2.putText(img, f"f{f}", (20, 50), 0, 1.4, (0, 255, 255), 3)
    if crop:
        img = img[crop[1]:crop[3], crop[0]:crop[2]]
    cv2.imwrite(str(W / f"_ids_{f:04d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
