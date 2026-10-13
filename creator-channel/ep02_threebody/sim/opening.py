"""开头两次模拟：A（基准）和 B（球 1 挪动边长的百万分之一）。核对结局并出轨迹图、数据。
python sim/opening.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from search import G, PERIOD, ejected, first_break, initial, run  # noqa: E402

HERE = Path(__file__).parent
K, EPS, DELTA, T = 0.955, 1e-4, 1e-6, 200.0
COLORS = ["#ff5a5a", "#4fd07a", "#ffd24a"]


def energy(P, V):
    ke = 0.5 * np.sum(V ** 2, (1, 2))
    pe = sum(-G / np.linalg.norm(P[:, a] - P[:, b], axis=1) for a, b in ((0, 1), (1, 2), (0, 2)))
    return ke + pe


def report(name, t, P, V):
    i, n = ejected(P, V)
    o = [j for j in range(3) if j != i]
    r = np.linalg.norm(P[-1, o[0]] - P[-1, o[1]])
    eb = 0.25 * np.sum((V[-1, o[0]] - V[-1, o[1]]) ** 2) - G / r
    e = energy(P, V)
    out = dict(run=name, ejected=i, eject_loops=round(t[n] / PERIOD, 1),
               break_loops=round(t[first_break(P)] / PERIOD, 2),
               pair_bound=bool(eb < 0), pair_dist_end=round(float(r), 3),
               escaper_dist_end=round(float(np.linalg.norm(P[-1, i] - P[-1, o].mean(0))), 1),
               energy_drift=float(np.max(np.abs(e - e[0]))))
    print(out)
    return out


def main():
    p, v = initial(K)
    p[0] += np.array([EPS, 0.0])
    p2 = p.copy()
    p2[1] += np.array([DELTA, 0.0])
    tA, PA, VA = run(p, v, T)
    tB, PB, VB = run(p2, v, T)
    res = [report("A", tA, PA, VA), report("B", tB, PB, VB)]
    m = min(len(PA), len(PB))
    div = np.linalg.norm(PA[:m] - PB[:m], axis=2).max(1)
    for th in (1e-3, 0.01, 0.05, 0.3):
        print(f"两次最大偏差首次超过 {th}: 第 {tA[np.argmax(div > th)] / PERIOD:.2f} 圈")
    (HERE / "opening.json").write_text(json.dumps(dict(k=K, eps=EPS, delta=DELTA, period=PERIOD, result=res), ensure_ascii=False, indent=1))

    fig, ax = plt.subplots(1, 2, figsize=(14, 7), facecolor="#0b0f17")
    for a, (name, P, r) in zip(ax, (("A", PA, res[0]), ("B 绿球挪动百万分之一", PB, res[1]))):
        a.set_facecolor("#0b0f17")
        end = int(np.argmax(np.linalg.norm(P, axis=2).max(1) > 4)) or len(P)
        for j in range(3):
            a.plot(P[:end, j, 0], P[:end, j, 1], color=COLORS[j], lw=0.6, alpha=0.85)
            a.plot(*P[0, j], "o", color=COLORS[j], ms=8)
        a.set_xlim(-4, 4)
        a.set_ylim(-4, 4)
        a.set_aspect("equal")
        a.set_title(f"{name}  被甩出：{'红绿黄'[r['ejected']]}球（第 {r['eject_loops']} 圈）", color="w", fontname="PingFang SC")
        a.axis("off")
    fig.savefig(HERE / "opening.png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())


if __name__ == "__main__":
    main()
