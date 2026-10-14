"""竖版跟拍 QA：每个 lay=crop 的比赛镜头出一张检查图，横屏原画面上画出 4:5 裁切框（白）、选中的球（橙）、场上球员（绿）。
只取成片实际用到的那段（0 到 b-a 秒），按 --fps 抽样；裁切框按 film.html 的 shv_crop 同样算（kb 推近、cx/cxk/track）。
用法：nba-tactics/.venv/bin/python tools/qa_track_vt.py [clip ...] [--fps 4] [--out out/vt/track_qa]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parents[1] / "tools"))
sys.path.insert(0, str(ROOT / "tools"))
import reframe  # noqa: E402
import track_vt  # noqa: E402

CROP_W = 1080 * 1080 / 1350
FPS = 30
TW, TH, COLS = 640, 360, 3


def ease(u):
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def keyed(ks, u):
    if u <= ks[0][0]:
        return ks[0][1]
    for (u0, v0), (u1, v1) in zip(ks[:-1], ks[1:]):
        if u < u1:
            return v0 + (v1 - v0) * ease((u - u0) / (u1 - u0))
    return ks[-1][1]


def crop_box(sh, lt, trk):
    z0, z1 = sh.get("kb", [1.0, 1.035])
    z = z0 + (z1 - z0) * min(1, max(0, lt / (sh["b"] - sh["a"])))
    if "cxk" in sh:
        cx = keyed(sh["cxk"], lt)
    elif "cx" in sh:
        cx = sh["cx"]
    elif trk:
        a = trk["cx"]
        q = lt * FPS
        i = min(max(int(q), 0), len(a) - 1)
        j = min(i + 1, len(a) - 1)
        cx = a[i] + (a[j] - a[i]) * min(1, max(0, q - i))
    else:
        cx = 960
    sw, shh = CROP_W / z, 1080 / z
    sx = min(max(cx - sw / 2, 0), 1920 - sw)
    sy = min(max((1080 - shh) * sh.get("fyv", 0.5), 0), 1080 - shh)
    return sx, sy, sw, shh, "cxk" if "cxk" in sh else "cx" if "cx" in sh else "track" if trk else "centre"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--fps", type=float, default=4)
    ap.add_argument("--out", default=str(ROOT / "out/vt/track_qa"))
    a = ap.parse_args()
    film = json.loads((ROOT / "scenes/film_vt.json").read_text())
    track = json.loads((ROOT / "scenes/track_vt.json").read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    shots = [s for s in film["shots"] if s.get("lay") == "crop" and s.get("clip")]
    for k, sh in enumerate(shots):
        name = sh["clip"]
        if a.clips and name not in a.clips:
            continue
        files = sorted((ROOT / "scenes/clips" / name).glob("*.jpg"))
        if not files:
            continue
        probe = cv2.imread(str(files[0]))
        if probe.shape[1] < probe.shape[0]:
            continue
        det_p = ROOT / "work/vt_det" / f"{name}.json"
        det = track_vt.prepare(json.loads(det_p.read_text()), name) if det_p.exists() else None
        balls = reframe.pick_balls(det) if det else None
        step = round(FPS / det["fps"]) if det else 2
        dur = sh["b"] - sh["a"]
        tiles = []
        for lt in np.arange(0, dur, 1 / a.fps):
            fi = min(int(lt * FPS), len(files) - 1)
            f = cv2.imread(str(files[fi]))
            sx, sy, sw, shh, src = crop_box(sh, lt, track.get(name))
            g = (f * 0.45).astype(np.uint8)
            x0, y0, x1, y1 = int(sx), int(sy), int(sx + sw), int(sy + shh)
            g[y0:y1, x0:x1] = f[y0:y1, x0:x1]
            if det:
                di = min(fi // step, len(det["frames"]) - 1)
                for p in det["frames"][di]["people"]:
                    if p[5]:
                        cv2.rectangle(g, (p[0], p[1]), (p[2], p[3]), (60, 200, 60), 3)
                b = balls[di]
                if b:
                    cv2.circle(g, (int(b[0]), int(b[1])), 22, (0, 140, 255) if b[2] > 0 else (0, 220, 255), 6)
            cv2.rectangle(g, (x0, y0), (x1 - 1, y1 - 1), (255, 255, 255), 8)
            t = cv2.resize(g, (TW, TH), interpolation=cv2.INTER_AREA)
            cv2.putText(t, f"{lt:4.2f}s  f{fi}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(t)
        while len(tiles) % COLS:
            tiles.append(np.zeros((TH, TW, 3), np.uint8))
        rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
        sheet = np.vstack(rows)
        head = np.zeros((40, sheet.shape[1], 3), np.uint8)
        cv2.putText(head, f"{name}  film {sh['a']:.2f}-{sh['b']:.2f}s  ({dur:.2f}s)  crop by {src}  kb {sh.get('kb', [1, 1.035])}",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        p = out / f"{k:02d}_{name}.jpg"
        cv2.imwrite(str(p), np.vstack([head, sheet]), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(p.name, len(tiles), src)


if __name__ == "__main__":
    main()
