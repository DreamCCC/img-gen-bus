"""near.py <tracks.json> <frames a:b:step> <x,y> [radius]: track boxes whose foot point is near (x,y) in original pixels."""
import json
import sys

d = json.load(open(sys.argv[1]))
a, b, st = (int(v) for v in sys.argv[2].split(":"))
x, y = (float(v) for v in sys.argv[3].split(","))
R = float(sys.argv[4]) if len(sys.argv) > 4 else 150
for f in range(a, min(b, len(d["frames"]) - 1) + 1, st):
    out = []
    for o in d["frames"][f]:
        x1, y1, x2, y2 = o["box"]
        fx, fy = (x1 + x2) / 2, y2
        dist = ((fx - x) ** 2 + (fy - y) ** 2) ** 0.5
        if dist < R:
            out.append(f"id{o['id']}@({fx:.0f},{fy:.0f}) h{y2 - y1:.0f} c{o['conf']:.2f}")
    print(f, " | ".join(out))
