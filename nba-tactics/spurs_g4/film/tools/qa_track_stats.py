"""竖版跟拍体检：逐个 lay=crop 镜头算裁切框的运动和球的位置，只看成片实际用到的那段。
  speed  = 裁切中心每秒移动多少素材像素（p95 / 最大），超过 900 px/s 观感就是“甩”
  flips  = 0.5 秒内来回反向且幅度都超过 120px 的次数（左右摆）
  out    = 真检测到的球落在裁切框外的帧数 / 有球的帧数
  edge   = 球在框内但离边不到 12% 的帧数
用法：nba-tactics/.venv/bin/python tools/qa_track_stats.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parents[1] / "tools"))
sys.path.insert(0, str(ROOT / "tools"))
import reframe  # noqa: E402
import track_vt  # noqa: E402
from qa_track_vt import crop_box  # noqa: E402

FPS = 30


def main():
    film = json.loads((ROOT / "scenes/film_vt.json").read_text())
    track = json.loads((ROOT / "scenes/track_vt.json").read_text())
    print(f"{'clip':18s} {'dur':>5s} {'src':>5s} {'p95':>5s} {'max':>5s} {'flips':>5s} {'ball':>5s} {'out':>4s} {'edge':>4s}  flag")
    for sh in film["shots"]:
        if sh.get("lay") != "crop" or not sh.get("clip"):
            continue
        name = sh["clip"]
        if not (ROOT / "scenes/clips" / name).exists():
            continue
        dur = sh["b"] - sh["a"]
        n = int(dur * FPS)
        boxes = [crop_box(sh, i / FPS, track.get(name)) for i in range(n)]
        if not boxes:
            continue
        src = boxes[0][4]
        cx = np.array([b[0] + b[2] / 2 for b in boxes])
        v = np.abs(np.diff(cx)) * FPS if n > 1 else np.zeros(1)
        if src == "track" and (ROOT / "work/vt_det" / f"{name}.json").exists():
            for c in track_vt.find_cuts(name):
                for f in range((c - 1) * track_vt.STEP, c * track_vt.STEP + 1):
                    if 0 <= f - 1 < len(v):
                        v[f - 1] = 0
        flips = 0
        d = np.diff(cx[::5])
        for i in range(1, len(d) - 1):
            if abs(d[i - 1] + d[i]) < 0.3 * (abs(d[i - 1]) + abs(d[i])) and abs(d[i - 1]) > 120 and abs(d[i]) > 120:
                flips += 1
        det_p = ROOT / "work/vt_det" / f"{name}.json"
        out = edge = seen = 0
        if det_p.exists():
            det = track_vt.prepare(json.loads(det_p.read_text()), name)
            balls = reframe.pick_balls(det)
            step = round(FPS / det["fps"])
            for i in range(0, n, step):
                b = balls[min(i // step, len(balls) - 1)]
                if not b or b[2] <= 0:
                    continue
                seen += 1
                sx, _, sw, _, _ = boxes[i]
                if b[0] < sx or b[0] > sx + sw:
                    out += 1
                elif min(b[0] - sx, sx + sw - b[0]) < 0.12 * sw:
                    edge += 1
        flag = []
        if np.percentile(v, 95) > 900 or v.max() > 2500:
            flag.append("FAST")
        if flips:
            flag.append("WOBBLE")
        if seen and out / seen > 0.08:
            flag.append("BALL-OUT")
        print(f"{name:18s} {dur:5.2f} {src:>5s} {np.percentile(v, 95):5.0f} {v.max():5.0f} {flips:5d} {seen:5d} {out:4d} {edge:4d}  {' '.join(flag)}")


if __name__ == "__main__":
    main()
