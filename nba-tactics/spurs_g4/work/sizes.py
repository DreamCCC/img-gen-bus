import os
from collections import defaultdict

# Directories holding many image files are frame caches (regenerable from raw video).
agg = defaultdict(lambda: [0, 0])
for root in ["work", "film"]:
    for r, _, fs in os.walk(root):
        imgs = [f for f in fs if f.lower().endswith((".jpg", ".png"))]
        if len(imgs) > 40:
            agg[r][0] += len(imgs)
            agg[r][1] += sum(os.path.getsize(os.path.join(r, f)) for f in imgs)
tot = 0
for r, (n, s) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    tot += s
    if s > 5e7:
        print(f"{r:60s} {n:6d} {s / 1e9:.2f} GB")
print("frame-cache total", f"{tot / 1e9:.2f} GB")
