"""把开头 A/B 两次模拟导出成画面用的轨迹：每个模拟时间单位 60 个采样，坐标保留 4 位小数。
python sim/export.py  →  scenes/data/opening.json
"""
import json
from pathlib import Path

import numpy as np

from opening import DELTA, EPS, K
from search import PERIOD, initial, run

OUT = Path(__file__).resolve().parent.parent / "scenes/data/opening.json"
T = 260.0


def main():
    p, v = initial(K)
    p[0] += np.array([EPS, 0.0])
    p2 = p.copy()
    p2[1] += np.array([DELTA, 0.0])
    runs, raw = {}, {}
    for name, q in (("A", p), ("B", p2)):
        t, P, _ = run(q, v, T)
        raw[name] = P
        runs[name] = np.round(P.reshape(len(P), 6), 4).tolist()
    # 两次之间最大的位置差（全精度，三位有效数字），每 1/60 模拟时间一个
    gap = np.linalg.norm(raw["A"] - raw["B"], axis=2).max(1)
    runs["gap"] = [float(f"{x:.3g}") for x in gap]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(rate=60, period=PERIOD, colors=["red", "green", "yellow"], **runs), separators=(",", ":")))
    print(OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
