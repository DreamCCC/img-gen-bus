"""Follow one player through tracks.json by box overlap (ignores tracker ID switches).

usage: follow.py work seed_frame x,y f0 f1 out.json [--video v --sheet sheet.jpg --step 3]
Seed: the detection at seed_frame whose box contains (x,y) (smallest such box).
Writes {"frames": {f: [tid, box]}, "runs": [[tid, a, b], ...]} and prints runs/gaps.
"""
import argparse
import json

import cv2
import numpy as np


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0


ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("seed", type=int)
ap.add_argument("xy")
ap.add_argument("f0", type=int)
ap.add_argument("f1", type=int)
ap.add_argument("out")
ap.add_argument("--video")
ap.add_argument("--sheet")
ap.add_argument("--step", type=int, default=3)
ap.add_argument("--thr", type=float, default=0.35)
ap.add_argument("--cut", default="", help="frames where the followed box must be dropped, e.g. 150-153,160")
a = ap.parse_args()

T = json.load(open(f"{a.work}/tracks.json"))["frames"]
x, y = (float(v) for v in a.xy.split(","))
cand = [d for d in T[a.seed] if d["box"][0] <= x <= d["box"][2] and d["box"][1] <= y <= d["box"][3]]
if not cand:
    raise SystemExit(f"no box contains {x},{y} at f{a.seed}: " + str([(d['id'], d['box']) for d in T[a.seed]]))
seed = min(cand, key=lambda d: (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]))
cut = set()
for p in filter(None, a.cut.split(",")):
    lo, _, hi = p.partition("-")
    cut |= set(range(int(lo), int(hi or lo) + 1))
res = {a.seed: (seed["id"], seed["box"])}


def walk(rng):
    last = seed
    miss = 0
    for f in rng:
        if f < 0 or f >= len(T):
            break
        best, bs = None, 0
        for d in T[f]:
            s = iou(last["box"], d["box"]) + (0.15 if d["id"] == last["id"] else 0)
            if s > bs:
                best, bs = d, s
        if best is not None and bs >= a.thr - 0.05 * min(miss, 4) and f not in cut:
            res[f] = (best["id"], best["box"])
            last, miss = best, 0
        else:
            miss += 1


walk(range(a.seed + 1, a.f1 + 1))
walk(range(a.seed - 1, a.f0 - 1, -1))
fr = sorted(res)
runs = []
for f in fr:
    tid = res[f][0]
    if runs and runs[-1][0] == tid and runs[-1][2] == f - 1:
        runs[-1][2] = f
    else:
        runs.append([tid, f, f])
gaps = [(p + 1, q - 1) for p, q in zip(fr[:-1], fr[1:]) if q - p > 1]
print("runs", runs)
print("gaps", gaps, "missing at ends:", (a.f0, fr[0] - 1) if fr[0] > a.f0 else None, (fr[-1] + 1, a.f1) if fr[-1] < a.f1 else None)
json.dump({"frames": {str(f): [res[f][0], res[f][1]] for f in fr}, "runs": runs}, open(a.out, "w"))

if a.sheet and a.video:
    cap = cv2.VideoCapture(a.video)
    boxes = np.array([res[f][1] for f in fr])
    cx0, cy0 = boxes[:, 0].min() - 120, boxes[:, 1].min() - 120
    cx1, cy1 = boxes[:, 2].max() + 120, boxes[:, 3].max() + 80
    cx0, cy0, cx1, cy1 = int(max(0, cx0)), int(max(0, cy0)), int(min(1920, cx1)), int(min(1080, cy1))
    tiles = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.f0)
    for f in range(a.f0, a.f1 + 1):
        ok, im = cap.read()
        if not ok:
            break
        if (f - a.f0) % a.step:
            continue
        if f in res:
            tid, b = res[f]
            cv2.rectangle(im, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 255), 2)
            cv2.putText(im, str(tid), (int(b[0]), int(b[1]) - 6), 0, 0.8, (0, 255, 255), 2)
        t = im[cy0:cy1, cx0:cx1]
        sc = 300 / t.shape[1]
        t = cv2.resize(t, None, fx=sc, fy=sc)
        cv2.putText(t, f"f{f}" + ("" if f in res else " MISS"), (5, 22), 0, 0.7, (0, 0, 255) if f not in res else (0, 255, 0), 2)
        tiles.append(t)
    cols = 5
    rows = []
    for r in range(0, len(tiles), cols):
        row = tiles[r:r + cols]
        row += [np.zeros_like(tiles[0])] * (cols - len(row))
        rows.append(np.hstack(row))
    cv2.imwrite(a.sheet, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("sheet", a.sheet, (cx0, cy0, cx1, cy1))
