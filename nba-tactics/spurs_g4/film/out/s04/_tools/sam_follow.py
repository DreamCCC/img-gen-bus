"""Follow one player with SAM2 video segmentation and inject him into tracks.json/masks as a synthetic track id.

usage: sam_follow.py work f0 f1 seed "x1,y1,x2,y2;x1,y1,x2,y2..." --tid 9001 --team SAS [--sheet out.jpg]
First box = the player to follow; extra boxes (nearby defenders) are prompted as separate objects so the
non-overlapping SAM2 masks keep them apart. Runs forward seed->f1 and backward seed->f0.
Writes: work/sam_<tid>.json {frame: box}, work/masks/NNNN.npz (keys "<tid>", "m<tid>", merged),
        work/tracks.json gets {"id": tid, "box": ...} added (original kept once in tracks_yolo.json).
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from ultralytics.models.sam import SAM2VideoPredictor

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("f0", type=int)
ap.add_argument("f1", type=int)
ap.add_argument("seed", type=int)
ap.add_argument("boxes")
ap.add_argument("--tid", type=int, default=9001)
ap.add_argument("--team", default="SAS")
ap.add_argument("--sheet")
ap.add_argument("--model", default=str(Path(__file__).resolve().parents[4] / "work" / "sam2.1_l.pt"))
a = ap.parse_args()

work = Path(a.work)
orig = work / "fr" / "orig"
boxes = [[float(v) for v in b.split(",")] for b in a.boxes.split(";")]


def run(frames):
    tmp = Path(tempfile.mkdtemp())
    for k, f in enumerate(frames):
        shutil.copy(orig / f"{f:04d}.jpg", tmp / f"{k:04d}.jpg")
    vid = tmp / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(tmp / "%04d.jpg"),
                    "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", str(vid)], check=True)
    pred = SAM2VideoPredictor(overrides=dict(conf=0.25, task="segment", mode="predict", imgsz=1024,
                                             model=a.model, verbose=False, save=False))
    out = {}
    for k, r in enumerate(pred(source=str(vid), bboxes=boxes, stream=True)):
        if r.masks is None:
            continue
        m = r.masks.data.cpu().numpy()
        if m.shape[1:] != (1080, 1920):
            m = np.stack([cv2.resize(x.astype(np.uint8), (1920, 1080), interpolation=cv2.INTER_NEAREST) for x in m])
        out[frames[k]] = m[0] > 0.5 if len(m) else None
    shutil.rmtree(tmp, ignore_errors=True)
    return out


res = run(list(range(a.seed, a.f1 + 1)))
if a.f0 < a.seed:
    res.update({f: m for f, m in run(list(range(a.seed, a.f0 - 1, -1))).items() if f != a.seed})

T_path = work / "tracks.json"
bak = work / "tracks_yolo.json"
if not bak.exists():
    shutil.copy(T_path, bak)
T = json.load(open(T_path))
(work / "masks").mkdir(exist_ok=True)
got = {}
for f in sorted(res):
    m = res[f]
    if m is None or m.sum() < 400:
        print(f"  f{f}: empty mask")
        continue
    m = m.astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    keep = [i for i in range(1, n) if i == big or st[i, cv2.CC_STAT_AREA] > 0.1 * st[big, cv2.CC_STAT_AREA]]
    m = np.isin(lab, keep).astype(np.uint8)
    ys, xs = np.nonzero(m)
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    got[f] = [x1, y1, x2, y2]
    fr = [d for d in T["frames"][f] if d["id"] != a.tid]
    fr.append({"id": a.tid, "box": [float(x1), float(y1), float(x2), float(y2)], "conf": 1.0, "team": a.team})
    T["frames"][f] = fr
    p = work / "masks" / f"{f:04d}.npz"
    z = dict(np.load(p)) if p.exists() else {}
    z[str(a.tid)] = np.array([x1, y1])
    z[f"m{a.tid}"] = m[y1:y2, x1:x2]
    np.savez_compressed(p, **z)
json.dump(T, open(T_path, "w"))
json.dump({str(f): b for f, b in got.items()}, open(work / f"sam_{a.tid}.json", "w"))
print(f"tid {a.tid}: {len(got)} frames {min(got)}-{max(got)}")

if a.sheet:
    tiles = []
    bb = np.array(list(got.values()))
    cx0, cy0 = int(max(0, bb[:, 0].min() - 100)), int(max(0, bb[:, 1].min() - 60))
    cx1, cy1 = int(min(1920, bb[:, 2].max() + 100)), int(min(1080, bb[:, 3].max() + 40))
    for f in range(a.f0, a.f1 + 1, 3):
        im = cv2.imread(str(orig / f"{f:04d}.jpg"))
        if f in got:
            z = np.load(work / "masks" / f"{f:04d}.npz")
            x1, y1 = z[str(a.tid)]
            mm = z[f"m{a.tid}"].astype(bool)
            sub = im[y1:y1 + mm.shape[0], x1:x1 + mm.shape[1]]
            sub[mm] = (sub[mm] * 0.5 + np.array([0, 200, 255]) * 0.5).astype(np.uint8)
            b = got[f]
            cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 2)
        t = im[cy0:cy1, cx0:cx1]
        sc = 200 / t.shape[1]
        t = cv2.resize(t, None, fx=sc, fy=sc)
        cv2.putText(t, f"f{f}", (4, 20), 0, 0.6, (0, 255, 255), 2)
        tiles.append(t)
    cols = 6
    rows = [np.hstack(tiles[r:r + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[r:r + cols])))
            for r in range(0, len(tiles), cols)]
    cv2.imwrite(a.sheet, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("sheet", a.sheet)
