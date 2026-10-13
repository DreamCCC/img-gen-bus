"""三个等质量球、等边三角形起步，搜一组适合开头的初始条件：
前几圈规矩 → 散架 → 一个被甩出去；把一个球挪百万分之一后，结局明显不同。
python sim/search.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

G = 1.0
M = np.ones(3)
HERE = Path(__file__).parent


def rhs(_, y):
    p = y[:6].reshape(3, 2)
    d = p[None, :, :] - p[:, None, :]
    r3 = np.sum(d * d, -1) ** 1.5
    np.fill_diagonal(r3, np.inf)
    a = G * np.sum(M[None, :, None] * d / r3[:, :, None], 1)
    return np.concatenate([y[6:], a.ravel()])


def initial(k, phase=0.0):
    """边长 1 的等边三角形，绕质心转，速度 = 圆轨道速度 × k。"""
    ang = phase + np.array([90, 210, 330]) * np.pi / 180
    r = 1 / np.sqrt(3)
    p = np.stack([r * np.cos(ang), r * np.sin(ang)], 1)
    w = np.sqrt(G * 3 / 1 ** 3)       # 等边拉格朗日解的角速度（m=1, 边长 1）
    v = k * w * np.stack([-p[:, 1], p[:, 0]], 1)
    return p, v


def run(p, v, T=150.0):
    y0 = np.concatenate([p.ravel(), v.ravel()])
    ts = np.linspace(0, T, int(T * 60) + 1)
    s = solve_ivp(rhs, (0, T), y0, method="DOP853", rtol=1e-12, atol=1e-12, t_eval=ts)
    return s.t, s.y[:6].T.reshape(-1, 3, 2), s.y[6:].T.reshape(-1, 3, 2)


def ejected(P, V):
    """返回 (球号, 时刻下标)：另外两个结成双星，这个球离它们 > 6 且相对它们能量为正。"""
    best = (None, None)
    for i in range(3):
        o = [j for j in range(3) if j != i]
        d = np.linalg.norm(P[:, i] - P[:, o].mean(1), axis=1)
        e = 0.5 * (2 / 3) * np.sum((V[:, i] - V[:, o].mean(1)) ** 2, 1) - G * 2 / np.maximum(d, 1e-9)
        r = np.linalg.norm(P[:, o[0]] - P[:, o[1]], axis=1)
        eb = 0.25 * np.sum((V[:, o[0]] - V[:, o[1]]) ** 2, 1) - G / r
        hit = np.nonzero((d > 6) & (e > 0) & (eb < 0) & (r < 2))[0]
        if len(hit) and (best[1] is None or hit[0] < best[1]):
            best = (i, int(hit[0]))
    return best


def first_break(P):
    """三条边长度比第一次偏离 1 超过 30% 的时刻下标（队形乱了）。"""
    d = np.stack([np.linalg.norm(P[:, a] - P[:, b], axis=1) for a, b in ((0, 1), (1, 2), (0, 2))], 1)
    hit = np.nonzero(d.max(1) / d.min(1) > 1.3)[0]
    return int(hit[0]) if len(hit) else None


PERIOD = 2 * np.pi / np.sqrt(3)


def one(arg):
    k, eps = arg
    p, v = initial(k)
    p[0] += np.array([eps, 0.0])  # 让不稳定性有个起点
    t, P, V = run(p, v)
    i, n = ejected(P, V)
    b = first_break(P)
    p2 = p.copy()
    p2[1] += np.array([1e-6, 0.0])
    t2, P2, V2 = run(p2, v)
    i2, n2 = ejected(P2, V2)
    m = min(len(P), len(P2))
    div = np.linalg.norm(P[:m] - P2[:m], axis=(1, 2))
    sep = int(np.argmax(div > 0.05)) if (div > 0.05).any() else None
    return dict(k=float(k), eps=eps, break_loops=None if b is None else round(t[b] / PERIOD, 2),
                eject=i, eject_loops=None if n is None else round(float(t[n]) / PERIOD, 1),
                eject2=i2, eject2_loops=None if n2 is None else round(float(t2[n2]) / PERIOD, 1),
                diverge_loops=None if sep is None else round(t[sep] / PERIOD, 2))


def main():
    from multiprocessing import Pool
    jobs = [(float(k), 1e-4) for k in np.round(np.arange(0.93, 1.0001, 0.005), 3)]
    rows = []
    with Pool(8) as pool:
        for row in pool.imap(one, jobs):
            row = {a: (float(b) if isinstance(b, np.floating) else b) for a, b in row.items()}
            rows.append(row)
            ok = None not in (row["eject"], row["eject2"]) and row["eject"] != row["eject2"] and row["diverge_loops"] > 4
            print("★" if ok else " ", row, flush=True)
    (HERE / "search.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
