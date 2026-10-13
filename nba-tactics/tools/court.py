"""球场坐标工具：像素 ↔ 球场（英尺），支持小数帧（慢放插帧用）。

球场坐标: u = 距底线英尺，v = 横向英尺（0 为篮筐中轴，靠近机位为正）。篮筐中心在 (5.25, 0)。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RIM = np.array([5.25, 0.0])


class Cam:
    def __init__(self, path: Path):
        d = json.load(open(path))
        self.court = np.array(d["court"])               # 像素 → 球场
        self.img = np.array([np.linalg.inv(H) for H in self.court])  # 球场 → 像素
        self.img /= self.img[:, 2:3, 2:3]
        self.n = len(self.court)

    def _H(self, arr: np.ndarray, f: float) -> np.ndarray:
        f = min(max(f, 0.0), self.n - 1.0)
        a = int(np.floor(f))
        b = min(a + 1, self.n - 1)
        t = f - a
        return arr[a] * (1 - t) + arr[b] * t

    def to_court(self, f: float, pts) -> np.ndarray:
        p = np.asarray(pts, float).reshape(-1, 2)
        q = np.c_[p, np.ones(len(p))] @ self._H(self.court, f).T
        return q[:, :2] / q[:, 2:3]

    def to_img(self, f: float, pts) -> np.ndarray:
        p = np.asarray(pts, float).reshape(-1, 2)
        q = np.c_[p, np.ones(len(p))] @ self._H(self.img, f).T
        return q[:, :2] / q[:, 2:3]

    def floor_ellipse(self, f: float, center, r: float, n: int = 72) -> np.ndarray:
        """球场上半径 r 英尺的圆，投影到画面上（透视椭圆）。"""
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        c = np.asarray(center, float)
        return self.to_img(f, np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)])
