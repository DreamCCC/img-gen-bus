"""成片用的其余模拟数据，全部真实积分：
  8 字形与 Šuvakov–Dmitrašinović 2013 的周期轨道（先验证一个周期后回到初值）
  混沌之网：开场初值上加一组极小扰动的多次模拟
  特洛伊小行星：太阳-木星圆型限制性三体，旋转坐标系
输出 scenes/data/film.json（小数据）和 scenes/data/*.bin（Float32 大数组）
python sim/film_data.py
"""
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from opening import EPS, K
from search import initial, rhs

OUT = Path(__file__).resolve().parent.parent / "scenes/data"


def run(p, v, T, n):
    y0 = np.concatenate([np.ravel(p), np.ravel(v)])
    ts = np.linspace(0, T, n)
    s = solve_ivp(rhs, (0, T), y0, method="DOP853", rtol=1e-12, atol=1e-12, t_eval=ts)
    return s.y[:6].T, s.y[:, -1]


def periodic():
    f8 = dict(name="figure8", p=[[0.97000436, -0.24308753], [-0.97000436, 0.24308753], [0, 0]],
              v3=[-0.93240737, -0.86473146], T=6.32591398)
    f8["v"] = [[-f8["v3"][0] / 2, -f8["v3"][1] / 2]] * 2 + [f8["v3"]]
    table = [  # p1, p2, T；x1=(-1,0) x2=(1,0) x3=(0,0)，v1=v2=(p1,p2)，v3=-2(p1,p2)
        ("butterfly", 0.306893, 0.125507, 6.235641),
        ("moth", 0.464445, 0.396060, 14.893911),
        ("bumblebee", 0.184279, 0.587188, 63.534541),
        ("yinyang", 0.513938, 0.304736, 17.328370),
        ("butterfly2", 0.392955, 0.097579, 7.003988),
        ("goggles", 0.083300, 0.127889, 10.466222),
        ("dragonfly", 0.080584, 0.588836, 21.270975),
        ("moth3", 0.383444, 0.377364, 25.840608),
        ("yinyang2", 0.416822, 0.330333, 55.789829),
    ]
    orbits = [f8] + [dict(name=n, p=[[-1, 0], [1, 0], [0, 0]], v=[[a, b], [a, b], [-2 * a, -2 * b]], T=T) for n, a, b, T in table]
    out = {}
    for o in orbits:
        n = int(o["T"] * 120) + 1
        P, yend = run(o["p"], o["v"], o["T"], n)
        y0 = np.concatenate([np.ravel(o["p"]), np.ravel(o["v"])])
        err = float(np.max(np.abs(yend - y0)))
        print(f"{o['name']:11s} T={o['T']:9.4f} 回到初值误差 {err:.2e}")
        if err < 2e-2:
            out[o["name"]] = dict(T=o["T"], pts=np.round(P, 4).tolist())
    return out


def web(m=48, T=60.0, rate=30):
    """开场 A 的初值，红星位置再加 m 个不同的极小扰动；返回 [m, 帧, 6]。"""
    p, v = initial(K)
    p[0] += np.array([EPS, 0.0])
    runs = []
    for i in range(m):
        q = p.copy()
        a = 2 * np.pi * i / m
        q[1] += 3e-6 * np.array([np.cos(a), np.sin(a)])
        P, _ = run(q, v, T, int(T * rate) + 1)
        runs.append(P)
    arr = np.array(runs, dtype=np.float32)
    (OUT / "web.bin").write_bytes(arr.tobytes())
    return dict(m=m, n=arr.shape[1], rate=rate)


def trojans(n=9000, periods=14, per=10):
    """圆型限制性三体（旋转系，日木距离 1，木星周期 2π），L4/L5 附近撒点，积分得到蝌蚪形摆动。"""
    mu = 9.537e-4
    rng = np.random.default_rng(3)
    side = np.where(np.arange(n) < n // 2, 1.0, -1.0)
    th = side * np.pi / 3 + rng.normal(0, 0.16, n)
    r = 1 + rng.normal(0, 0.012, n)
    x, y = r * np.cos(th) - mu, r * np.sin(th)
    vx = rng.normal(0, 0.006, n)
    vy = rng.normal(0, 0.006, n)
    xs, ys = (x, y), None

    def acc(x, y, vx, vy):
        r1 = np.sqrt((x + mu) ** 2 + y ** 2) ** 3
        r2 = np.sqrt((x - 1 + mu) ** 2 + y ** 2) ** 3
        ax = 2 * vy + x - (1 - mu) * (x + mu) / r1 - mu * (x - 1 + mu) / r2
        ay = -2 * vx + y - (1 - mu) * y / r1 - mu * y / r2
        return ax, ay

    dt = 2 * np.pi / 400
    steps = periods * 400
    keep = 400 // per
    out = np.zeros((periods * per + 1, n, 2), np.float32)
    out[0] = np.stack([x, y], 1)
    s = np.array([x, y, vx, vy])
    for k in range(1, steps + 1):
        def f(s):
            ax, ay = acc(*s)
            return np.array([s[2], s[3], ax, ay])
        k1 = f(s); k2 = f(s + dt / 2 * k1); k3 = f(s + dt / 2 * k2); k4 = f(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if k % keep == 0:
            out[k // keep] = s[:2].T
    d = np.hypot(out[-1, :, 0], out[-1, :, 1])
    print(f"特洛伊：{n} 颗，{periods} 个木星周期后仍在 0.8–1.2 之间的比例 {np.mean((d > 0.8) & (d < 1.2)):.3f}")
    (OUT / "trojans.bin").write_bytes(out.tobytes())
    del xs, ys
    return dict(n=n, frames=out.shape[0], per=per, mu=mu)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = dict(periodic=periodic(), web=web(), trojans=trojans())
    (OUT / "film.json").write_text(json.dumps(data, separators=(",", ":")))
    print(OUT / "film.json", (OUT / "film.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
