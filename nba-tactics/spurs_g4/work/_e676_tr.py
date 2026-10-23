import json, sys
from collections import defaultdict
import cv2

tr = json.load(open("work/e676w/tracks.json"))
fr = tr["frames"]
print("keys", list(tr.keys()), "nframes", len(fr), "sample", fr[150][:2] if fr[150] else None)
span = defaultdict(list)
for f, ds in enumerate(fr):
    for d in ds:
        span[d["id"]].append(f)
rows = []
for i, fs in span.items():
    if max(fs) < 140 or min(fs) > 280:
        continue
    rows.append((i, min(fs), max(fs), len(fs)))
for r in sorted(rows, key=lambda r: r[1]):
    print(r)

# draw boxes on chosen frames
for f in [int(x) for x in sys.argv[1:]]:
    im = cv2.imread(f"work/e676w/fr/orig/{f:04d}.jpg")
    for d in fr[f]:
        x1, y1, x2, y2 = map(int, d["box"])
        if y2 < 300:
            continue
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(im, str(d["id"]), (x1, y1 - 6), 0, 1.0, (0, 0, 255), 3)
    cv2.putText(im, f"f{f}", (20, 50), 0, 1.5, (0, 255, 0), 3)
    cv2.imwrite(f"work/_e676_ids_{f:04d}.jpg", cv2.resize(im, (1280, 720)))
