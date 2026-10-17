#!/usr/bin/env python3
"""战术拆解渲染器：EDL（JSON）驱动。

原片 / 4 倍插帧慢放 / 时停定格，叠加地板战术线（被球员身体遮挡）、球员圈与名牌、
小战术板、字幕；按同一时间轴混旁白、原声、音效。EDL 格式见 kd_macau/e464_edl.json。

用法:
  python render_play.py kd_macau/e464_edl.json                   # 全片
  python render_play.py kd_macau/e464_edl.json --preview 12,250    # 只出这些输出帧（jpg）
  python render_play.py kd_macau/e464_edl.json --sheet 2.0         # 每 2 秒一格的联系表
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
sys.modules.setdefault("render_play", sys.modules[__name__])  # fx 里 from render_play import COL 要拿到被 EDL 改过的同一份
from court import RIM, Cam, device  # noqa: E402
import fx  # noqa: E402

FONTS = Path(__file__).resolve().parent.parent / "assets/fonts"
# 服务器上没有 ~/Library/Fonts，同名字体装在这里
SERVER_FONTS = Path("/usr/share/fonts/img-gen-bus")
COL = {"gold": (255, 196, 40), "orange": (255, 104, 52), "white": (240, 240, 240), "blue": (78, 168, 255),
       "pass": (255, 236, 150), "red": (226, 44, 52), "navy": (14, 22, 40)}
TEAM = {"HOU": (214, 36, 48), "DAL": (34, 102, 214)}
GAP = 0.15


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


FONT_SPEC = {"zh": (FONTS / "NotoSansSC-Bold.otf", None), "zhr": (FONTS / "NotoSansSC-Regular.otf", None),
             "num": (FONTS / "BarlowCondensed-SemiBold.ttf", None)}
FONT_FALLBACK = {"numw": "num", "ko": "num", "sub": "zh"}


def font(size: int, kind: str = "zh") -> ImageFont.FreeTypeFont:
    """EDL 的 fonts 里第二项是字符串时当可变字体的实例名，是整数时当 ttc 里的字体序号。"""
    if (size, kind) not in _font_cache:
        k = kind
        while k not in FONT_SPEC or not Path(FONT_SPEC[k][0]).exists():
            k = FONT_FALLBACK.get(k, "zh")
        path, var = FONT_SPEC[k]
        f = ImageFont.truetype(str(path), size, index=var if isinstance(var, int) else 0)
        if isinstance(var, str):
            f.set_variation_by_name(var)
        _font_cache[(size, kind)] = f
    return _font_cache[(size, kind)]


NUM_RUN = re.compile(r"[#+]?\d+(?:[.:]\d+)*")


def mixed_runs(text: str, size: int, zh: str = "zh", num: str = "num", scale: float = 1.28):
    """中文和数字分开排：数字段用 Action NBA，其余用中文字体。返回 [(文字, 字体)] 和总宽。"""
    runs, i = [], 0
    for m in NUM_RUN.finditer(text):
        if m.start() > i:
            runs.append((text[i:m.start()], font(size, zh)))
        runs.append((m.group(), font(int(size * scale), num)))
        i = m.end()
    if i < len(text):
        runs.append((text[i:], font(size, zh)))
    return runs, sum(f.getlength(s) for s, f in runs)


def draw_mixed(dr, xy, text, size, fill, a=1.0, anchor="lm", zh="zh", num="num", stroke=0, scale=1.28):
    """按基线对齐画中文和数字混排；anchor 只认 lm / mm / rm。"""
    runs, w = mixed_runs(text, size, zh, num, scale)
    x = float(xy[0]) - {"l": 0, "m": w / 2, "r": w}[anchor[0]]
    base = float(xy[1]) + size * 0.36
    for s, f in runs:
        dr.text((x, base), s, font=f, fill=tuple(fill) + (int(255 * a),), anchor="ls",
                stroke_width=stroke, stroke_fill=(0, 0, 0, int(200 * a)))
        x += f.getlength(s)
    return w


_font_cache: dict = {}
NBA_SKEW = -0.21


# ---------------------------------------------------------------- 时间轴

class Timeline:
    def __init__(self, edl: dict, base: Path):
        self.edl, self.fps = edl, edl["fps"]
        vo = json.load(open(base / edl["vo"]["lines"]))
        self.vo_text = {v["id"]: v["text"] for v in vo}
        self.vo_dir = base / edl["vo"]["dir"]
        dur = json.load(open(self.vo_dir / "durations.json"))
        self.segs, self.vo = [], {}
        gap = edl.get("vo_gap", GAP)
        frame, last = 0, -1.0
        for sg in edl["segments"]:
            st = frame / self.fps
            n = None
            if sg["kind"] == "play":
                n = round((sg["to"] - sg["from"]) / sg["speed"])
            elif sg["kind"] == "rewind":
                n = round(sg["dur"] * self.fps)
            for vid, off in sg.get("vo", []):
                if isinstance(off, dict):
                    t = st + off["end"] - dur[vid]
                else:
                    t = st + off
                t = max(t, last + gap)
                self.vo[vid] = (t, t + dur[vid])
                last = t + dur[vid]
            if n is None:
                d = sg.get("dur") or max(last + sg.get("pad", 0.5) - st, sg.get("min", 0.8))
                n = round(d * self.fps)
            self.segs.append(dict(sg, start=st, end=(frame + n) / self.fps, f0=frame, n=n))
            frame += n
        self.n = frame
        self.by_id = {s["id"]: s for s in self.segs}

    def resolve(self, e) -> float:
        if e is None:
            return float("nan")
        if isinstance(e, (int, float)):
            return float(e)
        m = re.fullmatch(r"([A-Za-z0-9_]+)(\.end)?([+-][\d.]+)?", e)
        if not m:
            raise ValueError(f"时间写法不认识: {e}")
        k, end, off = m.group(1), m.group(2), float(m.group(3) or 0)
        if k in self.by_id:
            s = self.by_id[k]
            return (s["end"] if end else s["start"]) + off
        if k in self.vo:
            return self.vo[k][1 if end else 0] + off
        raise KeyError(f"找不到段或旁白: {k}")

    def at(self, i: int):
        for sg in self.segs:
            if sg["f0"] <= i < sg["f0"] + sg["n"]:
                j = i - sg["f0"]
                if sg["kind"] == "play":
                    s = sg["from"] + j * sg["speed"]
                elif sg["kind"] == "rewind":
                    s = round(sg["from"] + (sg["to"] - sg["from"]) * j / max(1, sg["n"] - 1))
                else:
                    s = sg["at"]
                return sg, j / self.fps, float(s)
        raise IndexError(i)

    def zoom_state(self, i: int):
        """虚拟推镜：每段的 zoom = [段末倍率, 焦点]，焦点是球员 key、像素 [x, y] 或 null（沿用上一段）。
        段内从上一段末状态缓动过去。返回 (起点状态, 终点状态, 进度)。"""
        prev = (1.0, None)
        for sg in self.segs:
            want = prev
            if "zoom" in sg:
                z, foc = sg["zoom"]
                want = (z, foc if foc is not None else prev[1])
            if sg["f0"] <= i < sg["f0"] + sg["n"]:
                return prev, want, ease((i - sg["f0"]) / max(1, sg["n"] - 1))
            prev = want
        return prev, prev, 1.0


# ---------------------------------------------------------------- 数据

class Players:
    def __init__(self, path: Path):
        self.d = json.load(open(path))

    def _pair(self, arr, s):
        a = int(np.floor(s))
        t = s - a
        pa = arr[a] if 0 <= a < len(arr) else None
        pb = arr[a + 1] if 0 <= a + 1 < len(arr) else None
        return pa, pb, t

    def uv(self, k, s):
        pa, pb, t = self._pair(self.d[k]["uv"], s)
        if pa is not None and pb is not None:
            return np.array(pa) * (1 - t) + np.array(pb) * t
        q = pa if pa is not None else pb
        return None if q is None else np.array(q)

    def box(self, k, s, near: int = 4):
        arr = self.d[k]["box"]
        pa, pb, t = self._pair(arr, s)
        if pa is not None and pb is not None:
            return np.array(pa) * (1 - t) + np.array(pb) * t
        c = int(round(s))
        for d in range(near + 1):
            for f in (c - d, c + d):
                if 0 <= f < len(arr) and arr[f] is not None:
                    return np.array(arr[f])
        return None

    def height(self, k, s):
        arr = self.d[k]["box"]
        c = int(round(s))
        for d in range(80):
            for f in (c - d, c + d):
                if 0 <= f < len(arr) and arr[f] is not None:
                    return arr[f][3] - arr[f][1]
        return 200.0

    def head(self, k, s, cam):
        b = self.box(k, s)
        if b is not None:
            return np.array([(b[0] + b[2]) / 2, b[1]])
        u = self.uv(k, s)
        if u is None:
            return None
        foot = cam.to_img(s, [u])[0]
        return foot - [0, self.height(k, s)]


class Masks:
    def __init__(self, work: Path, players: Players):
        self.dir, self.extra, self.hq, self.P = work / "masks", work / "masks_extra", work / "masks_hq", players
        self.cache: dict = {}

    def _load(self, f):
        if f not in self.cache:
            p = self.dir / f"{f:04d}.npz"
            self.cache = {f: dict(np.load(p)) if p.exists() else {}}
        return self.cache[f]

    def of(self, keys, s, shape, feather=2.0):
        f = int(round(s))
        z = self._load(f)
        m = np.zeros(shape[:2], np.float32)
        for k in keys:
            tid = self.P.d[k]["tid"][f] if 0 <= f < len(self.P.d[k]["tid"]) else None
            hq, ex = self.hq / f"{f:04d}_{k}.npz", self.extra / f"{f:04d}_{k}.npz"
            if hq.exists() or ex.exists():
                e = np.load(hq if hq.exists() else ex)
                x1, y1 = e["xy"]
                mm = e["m"]
            elif tid is not None and str(tid) in z:
                x1, y1 = z[str(tid)]
                mm = z[f"m{tid}"]
            else:
                continue
            h, w = mm.shape
            m[y1:y1 + h, x1:x1 + w] = np.maximum(m[y1:y1 + h, x1:x1 + w], mm.astype(np.float32))
        if feather:
            m = cv2.GaussianBlur(m, (0, 0), feather)
        return m

    def everyone(self, s, shape):
        f = int(round(s))
        z = self._load(f)
        m = np.zeros(shape[:2], np.float32)
        for k, v in z.items():
            if k.startswith("m"):
                x1, y1 = z[k[1:]]
                h, w = v.shape
                m[y1:y1 + h, x1:x1 + w] = np.maximum(m[y1:y1 + h, x1:x1 + w], v.astype(np.float32))
        for ex in [*self.extra.glob(f"{f:04d}_*.npz"), *self.hq.glob(f"{f:04d}_*.npz")]:
            e = np.load(ex)
            x1, y1 = e["xy"]
            h, w = e["m"].shape
            m[y1:y1 + h, x1:x1 + w] = np.maximum(m[y1:y1 + h, x1:x1 + w], e["m"].astype(np.float32))
        return cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 1.5)


# ---------------------------------------------------------------- 画布

class Canvas:
    """RGB + alpha 两张 uint8 图，cv2 抗锯齿画形状。"""

    def __init__(self, h, w):
        self.c = np.zeros((h, w, 3), np.uint8)
        self.a = np.zeros((h, w), np.uint8)

    @staticmethod
    def _p(pts):
        return np.clip(np.round(np.asarray(pts, float) * 4), -40000, 40000).astype(np.int32).reshape(-1, 1, 2)

    def line(self, pts, col, th, alpha=1.0, closed=False):
        if len(pts) < 2 or alpha <= 0:
            return
        th = max(1, int(round(th)))
        p = [self._p(pts)]
        cv2.polylines(self.c, p, closed, col, th, cv2.LINE_AA, 2)
        cv2.polylines(self.a, p, closed, int(255 * alpha), th, cv2.LINE_AA, 2)

    def fill(self, pts, col, alpha):
        if len(pts) < 3 or alpha <= 0:
            return
        p = [self._p(pts)]
        cv2.fillPoly(self.c, p, col, cv2.LINE_AA, 2)
        cv2.fillPoly(self.a, p, int(255 * alpha), cv2.LINE_AA, 2)

    def disc(self, c, r, col, alpha, th=-1):
        if alpha <= 0:
            return
        cc = tuple(int(round(v * 4)) for v in c)
        rr = int(round(r * 4))
        cv2.circle(self.c, cc, rr, col, th if th < 0 else max(1, int(th)), cv2.LINE_AA, 2)
        cv2.circle(self.a, cc, rr, int(255 * alpha), th if th < 0 else max(1, int(th)), cv2.LINE_AA, 2)

    def rrect(self, x1, y1, x2, y2, r, col, alpha):
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        self.fill([(x1 + r, y1), (x2 - r, y1), (x2, y1 + r), (x2, y2 - r), (x2 - r, y2), (x1 + r, y2), (x1, y2 - r), (x1, y1 + r)],
                  col, alpha)
        for cx, cy in ((x1 + r, y1 + r), (x2 - r, y1 + r), (x1 + r, y2 - r), (x2 - r, y2 - r)):
            self.disc((cx, cy), r, col, alpha)

    def rect(self, x1, y1, x2, y2, col, alpha):
        self.fill([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], col, alpha)

    def slab(self, x1, y1, x2, y2, col, alpha, skew=NBA_SKEW):
        """NBA 图文的斜切色块（平行四边形），和 film.html 的 slab 同一斜率。"""
        k = (y2 - y1) * skew / 2
        self.fill([(x1 - k, y1), (x2 - k, y1), (x2 + k, y2), (x1 + k, y2)], col, alpha)

    def arrow(self, pts, col, size, alpha):
        pts = np.asarray(pts, float)
        if len(pts) < 2:
            return
        tip = pts[-1]
        back = pts[max(0, len(pts) - 6)]
        d = tip - back
        n = np.linalg.norm(d)
        if n < 1e-3:
            return
        d /= n
        q = np.array([-d[1], d[0]])
        self.fill([tip + d * size * 0.35, tip - d * size + q * size * 0.62, tip - d * size - q * size * 0.62], col, alpha)

    def dashed(self, pts, col, th, alpha, on=22.0, off=13.0, shift=0.0):
        pts = np.asarray(pts, float)
        if len(pts) < 2:
            return
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cum = np.r_[0, np.cumsum(seg)]
        if cum[-1] < 1:
            return
        ts = np.arange(0, cum[-1], 2.0)
        xs = np.interp(ts, cum, pts[:, 0])
        ys = np.interp(ts, cum, pts[:, 1])
        period = on + off
        phase = (ts - shift) % period < on
        start = None
        for i, v in enumerate(phase):
            if v and start is None:
                start = i
            if (not v or i == len(phase) - 1) and start is not None:
                if i - start >= 1:
                    self.line(np.c_[xs[start:i + 1], ys[start:i + 1]], col, th, alpha)
                start = None

    def over(self, other, rect):
        """把另一张画布在 rect 范围内叠到本画布上（rect 外的内容丢掉）。"""
        x1, y1, x2, y2 = (int(round(v)) for v in rect)
        oa = other.a[y1:y2, x1:x2].astype(np.float32)[..., None] / 255.0
        self.c[y1:y2, x1:x2] = (self.c[y1:y2, x1:x2] * (1 - oa) + other.c[y1:y2, x1:x2] * oa).astype(np.uint8)
        self.a[y1:y2, x1:x2] = np.maximum(self.a[y1:y2, x1:x2], other.a[y1:y2, x1:x2])

    def composite(self, img, occ=None, mul=1.0):
        a = self.a.astype(np.float32) / 255.0 * mul
        if occ is not None:
            a *= 1.0 - occ
        a = a[..., None]
        return img * (1 - a) + self.c.astype(np.float32) * a


def stroke_line(cv, pts, col, th, alpha, dash=False):
    """深色描边 + 彩色主线，让线在木地板上也看得清。"""
    if dash:
        cv.dashed(pts, (10, 10, 10), th + 4, alpha * 0.45)
        cv.dashed(pts, col, th, alpha)
    else:
        cv.line(pts, (10, 10, 10), th + 4, alpha * 0.45)
        cv.line(pts, col, th, alpha)


# ---------------------------------------------------------------- 投影

class ImgProj:
    def __init__(self, cam: Cam, s: float):
        self.cam, self.s, self.k = cam, s, 1.0

    def __call__(self, uv):
        return self.cam.to_img(self.s, uv)

    def circle(self, c, r, n=72):
        return self.cam.floor_ellipse(self.s, c, r, n)


class BoardProj:
    U0, U1, V0, V1 = -1.5, 41.5, -26.0, 26.0

    def __init__(self, x0, y0, k):
        self.x0, self.y0, self.kk = x0, y0, k
        self.k = k / 14.0

    def __call__(self, uv):
        uv = np.asarray(uv, float).reshape(-1, 2)
        return np.c_[self.x0 + (uv[:, 0] - self.U0) * self.kk, self.y0 + (uv[:, 1] - self.V0) * self.kk]

    def circle(self, c, r, n=48):
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return self(np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)])

    @property
    def size(self):
        return (self.U1 - self.U0) * self.kk, (self.V1 - self.V0) * self.kk


def court_lines():
    """半场线（英尺）：每条是一串 uv 点。"""
    L = []
    L.append([(0, -25), (0, 25)])
    L.append([(0, -25), (41.5, -25)])
    L.append([(0, 25), (41.5, 25)])
    L.append([(0, -8), (19, -8), (19, 8), (0, 8)])
    a = np.linspace(-np.pi / 2, np.pi / 2, 40)
    L.append(list(zip(19 + 6 * np.cos(a), 6 * np.sin(a))))
    lim = np.arcsin(22 / 23.75)
    a = np.linspace(-lim, lim, 80)
    arc = list(zip(RIM[0] + 23.75 * np.cos(a), 23.75 * np.sin(a)))
    L.append([(0, -22), (arc[0][0], -22)] + arc + [(0, 22)])
    a = np.linspace(-np.pi / 2, np.pi / 2, 20)
    L.append(list(zip(RIM[0] + 4 * np.cos(a), 4 * np.sin(a))))
    return L


def three_line():
    lim = np.arcsin(22 / 23.75)
    a = np.linspace(-lim, lim, 120)
    arc = np.c_[RIM[0] + 23.75 * np.cos(a), 23.75 * np.sin(a)]
    return np.r_[[[0, -22]], arc, [[0, 22]]]


# ---------------------------------------------------------------- 渲染器

class Renderer:
    def __init__(self, edl_path: Path):
        self.base = edl_path.parent
        self.edl = json.load(open(edl_path))
        for k, (path, var) in self.edl.get("fonts", {}).items():
            p = Path(path).expanduser() if Path(path).expanduser().is_absolute() else self.base / path
            if not p.exists() and (SERVER_FONTS / p.name).exists():
                p = SERVER_FONTS / p.name
            FONT_SPEC[k] = (p, var)
        _font_cache.clear()
        COL.update({k: tuple(v) for k, v in self.edl.get("colors", {}).items()})
        TEAM.update({k: tuple(v) for k, v in self.edl.get("teams", {}).items()})
        self.nba = self.edl.get("chrome") == "nba"
        self.en = self.edl.get("lang") == "en"
        self._panels, self._ui_text = [], []
        self.logo = None
        if self.edl.get("logo"):
            lg = Image.open(self.base / self.edl["logo"]).convert("RGBA")
            lh = self.edl.get("logo_h", 96)
            self.logo = lg.resize((round(lg.width * lh / lg.height), lh), Image.LANCZOS)
        self.tl = Timeline(self.edl, self.base)
        self.work = self.base / self.edl["work"]
        self.cam = Cam(self.work / "cam.json")
        self.P = Players(self.work / "players.json")
        for k, nm in self.edl.get("names", {}).items():
            self.P.d[k]["name"] = nm
        self.M = Masks(self.work, self.P)
        self.W, self.H = self.edl["size"]
        self.layers = []
        for ly in self.edl["layers"]:
            ly = dict(ly)
            ly["_on"] = self.tl.resolve(ly.get("on")) if "on" in ly else -1e9
            ly["_off"] = self.tl.resolve(ly.get("off")) if "off" in ly else 1e9
            ly["_imgoff"] = self.tl.resolve(ly["img_off"]) if "img_off" in ly else 1e9
            if "anim" in ly:
                ly["_anim"] = [self.tl.resolve(x) for x in ly["anim"]]
            self.layers.append(ly)
        self.by_id = {ly["id"]: ly for ly in self.layers if "id" in ly}
        self.ball_w = [(f, self.cam.to_court(f, [(x, y)])[0]) for f, x, y in self.edl.get("ball", [])]
        rf, rx, ry = self.edl["anchors"]["rim"]
        self.rim_w = self.cam.to_court(rf, [(rx, ry)])[0]
        self.slow = self.edl.get("slow")
        self.subs = self._subs()

    # ---- 取帧
    def src_frame(self, sg, s):
        if sg["kind"] == "play" and sg["speed"] < 1 and self.slow:
            k = int(round((s - self.slow["from"]) * self.slow["mul"]))
            p = self.base / self.slow["dir"] / f"{k:04d}.jpg"
            if p.exists():
                return cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
        p = self.base / self.edl["orig"] / f"{int(round(s)):04d}.jpg"
        return cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)

    # ---- 字幕：按标点切块，按字数分配时长
    def _subs(self):
        out = []
        for vid, (a, b) in self.tl.vo.items():
            text = self.tl.vo_text[vid]
            if self.en:
                chunks = []
                for sent in [x for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]:
                    cur = ""
                    for p in [x for x in re.split(r"(?<=,)\s+", sent) if x]:
                        if cur and len(cur) + len(p) + 1 > self.edl.get("sub_chars", 44):
                            chunks.append(cur)
                            cur = p
                        else:
                            cur = f"{cur} {p}".strip()
                    chunks.append(cur)
                n = sum(len(c) for c in chunks)
                t = a
                for k, c in enumerate(chunks):
                    d = (b - a) * len(c) / n
                    out.append((t, t + d + (0.25 if k == len(chunks) - 1 else 0), c.rstrip(",")))
                    t += d
                continue
            chunks = []
            for sent in [x for x in re.split(r"(?<=[。！？])", text) if x.strip()]:
                cur = ""
                for p in [x for x in re.split(r"(?<=，)", sent) if x]:
                    if cur and len(cur) + len(p) > 16:
                        chunks.append(cur)
                        cur = p
                    else:
                        cur += p
                chunks.append(cur)
            n = sum(len(c) for c in chunks)
            t = a
            for k, c in enumerate(chunks):
                d = (b - a) * len(c) / n
                shown = re.sub(r"[，。]$", "", c).replace("，", "　").replace("。", "　")
                out.append((t, t + d + (0.25 if k == len(chunks) - 1 else 0), shown))
                t += d
        return out

    # ---- 图层可见度
    def vis(self, ly, T, s):
        if "src_on" in ly and s < ly["src_on"]:
            return 0.0
        if T < ly["_on"] or T >= ly["_off"]:
            return 0.0
        a = min(1.0, (T - ly["_on"]) / 0.2) if ly["_on"] > -1e8 else 1.0
        b = min(1.0, (ly["_off"] - T) / 0.2) if ly["_off"] < 1e8 else 1.0
        return max(0.0, min(a, b))

    def anim(self, ly, T):
        if "_anim" not in ly:
            return 1.0
        a, b = ly["_anim"]
        return ease((T - a) / max(1e-3, b - a))

    # ---- 地板图层（同一套代码画在画面和战术板上）
    ZORDER = {"space": -1, "zone": -0.5, "hull": 0, "radius": 0, "shotline": 0, "cone": 0.5, "path": 1, "pass": 2,
              "tether": 3, "wave": 3.5, "ring": 4}

    @staticmethod
    def zone_poly(ly):
        if "lane" in ly:
            u0, u1, hw = ly["lane"]
            return np.array([(u0, -hw), (u1, -hw), (u1, hw), (u0, hw)], float)
        return np.array(ly["poly"], float)

    def floor_layers(self):
        return sorted((ly for ly in self.layers if ly["type"] in self.ZORDER), key=lambda ly: self.ZORDER[ly["type"]])

    def floor_layer(self, cv, proj, ly, s, T, al, board=False):
        t = ly["type"]
        k = proj.k
        if t == "space":
            if not board:
                fx.draw_space(self, cv, proj, ly, s, T, al)
            return
        if t == "cone":
            fx.draw_cone(self, cv, proj, ly, s, T, al, board)
            return
        if t == "wave":
            if not board:
                fx.draw_wave(self, cv, proj, ly, s, T)
            return
        if t == "zone":
            p = self.anim(ly, T)
            if "lane" in ly:
                u0, u1, hw = ly["lane"]
                poly = self.zone_poly({"lane": [u0, u0 + (u1 - u0) * max(p, 0.02), hw]})
            else:
                poly = self.zone_poly(ly)
                poly = poly.mean(0) + (poly - poly.mean(0)) * max(p, 0.02)
            dense = np.vstack([np.linspace(poly[i], poly[(i + 1) % len(poly)], 12, endpoint=False) for i in range(len(poly))])
            im = proj(dense)
            col = COL[ly.get("color", "gold")]
            cv.fill(im, col, al * ly.get("fill", 0.22))
            stroke_line(cv, np.r_[im, im[:1]], col, 3 * k + 1, al, dash=True)
            return
        if t == "ring":
            for key in ly["keys"]:
                u = self.P.uv(key, s)
                if u is None:
                    continue
                sty = self.edl["style"][key]
                col = COL[sty] if sty in COL else TEAM[self.P.d[key]["team"]]
                r = ly.get("r", 2.1)
                if board:
                    if ly.get("r"):
                        continue
                    c = proj([u])[0]
                    cv.disc(c, 15 * k * 1.0 + 4, col, al * 0.9, th=2)
                    continue
                if ly.get("pulse"):
                    ph = (T * 1.6) % 1.0
                    rr = r * (0.7 + 0.6 * ph)
                    cv.line(proj.circle(u, rr), col, 4, al * (1 - ph), closed=True)
                    cv.line(proj.circle(u, r), col, 3, al * 0.8, closed=True)
                    continue
                e = proj.circle(u, r)
                cv.fill(e, col, al * 0.22)
                cv.line(e, (10, 10, 10), 7, al * 0.4, closed=True)
                cv.line(e, col, 4, al, closed=True)
        elif t == "pass":
            (ka, fa), (kb, fb) = ly["a"], ly["b"]
            A, B = self.P.uv(ka, fa), self.P.uv(kb, fb)
            if A is None or B is None:
                return
            p = max(self.anim(ly, T) if "_anim" in ly else 0.0, (s - fa) / max(1e-3, fb - fa))
            p = min(max(p, 0.0), 1.0)
            if p <= 0.02:
                return
            d = B - A
            q = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
            ctrl = (A + B) / 2 + q * np.linalg.norm(d) * 0.12 * ly.get("bend", 1)
            ts = np.linspace(0, p, max(4, int(48 * p)))[:, None]
            curve = (1 - ts) ** 2 * A + 2 * (1 - ts) * ts * ctrl + ts ** 2 * B
            pts = proj(curve)
            col = COL[ly.get("color", "pass")]
            flow = ly.get("flow") and not board
            if flow:
                fx.flow_under(cv, pts, col, k, al)
            stroke_line(cv, pts, col, 5 * k + (0 if board else 1), al, dash=True)
            cv.arrow(pts, col, 26 * k, al)
            if flow:
                fx.flow_over(cv, pts, col, k, al, T, p)
        elif t == "path":
            f0, f1 = ly["from"], min(s, ly["to"])
            if f1 <= f0 + 0.5:
                return
            fs = list(np.arange(f0, f1, 1.0)) + [f1]
            uvs = [self.P.uv(ly["key"], f) for f in fs]
            uvs = np.array([u for u in uvs if u is not None])
            if len(uvs) < 2:
                return
            if len(uvs) > 7:
                ker = np.ones(5) / 5
                sm = np.c_[np.convolve(np.pad(uvs[:, 0], 2, mode="edge"), ker, "valid"),
                           np.convolve(np.pad(uvs[:, 1], 2, mode="edge"), ker, "valid")]
                sm[0], sm[-1] = uvs[0], uvs[-1]
                uvs = sm
            col = COL[ly.get("color", "white")]
            w, head = ly.get("w", 1.0), ly.get("head", 1.0)
            if ly.get("origin") and not board:
                o = proj.circle(uvs[0], 1.1)
                cv.line(o, (10, 10, 10), 7 * w, al * 0.45, closed=True)
                cv.line(o, col, 4 * w, al, closed=True)
            gap = ly.get("gap", 0.0)
            if gap > 0:
                seg = np.linalg.norm(np.diff(uvs, axis=0), axis=1)
                cum = np.r_[0, np.cumsum(seg)]
                L = cum[-1] - gap
                if L <= 1.0:
                    return
                i = int(np.searchsorted(cum, L, side="right")) - 1
                t = (L - cum[i]) / max(1e-6, seg[i])
                uvs = np.r_[uvs[:i + 1], [uvs[i] + (uvs[i + 1] - uvs[i]) * t]]
            pts = proj(uvs)
            th = (6 * k + (0 if board else 1)) * w
            style = "solid" if board else ly.get("style", "solid")
            if style in ("dash", "flow"):
                on, off = 26 * w, 16 * w
                shift = (T * 90 * w) % (on + off) if style == "flow" else 0.0
                cv.dashed(pts, (10, 10, 10), th + 4, al * 0.45, on, off, shift)
                cv.dashed(pts, col, th, al, on, off, shift)
            elif style == "chevron":
                fx.chevrons(cv, pts, col, th, 18 * w, 34 * w, al, T * 70 * w)
            else:
                stroke_line(cv, pts, col, th, al)
            if head != 1.0 and not board:
                cv.arrow(pts, (10, 10, 10), 28 * k * head + 8, al * 0.5)
            cv.arrow(pts, col, 28 * k * head, al)
        elif t == "hull":
            pts = []
            for key in ly["keys"]:
                u = self.P.uv(key, s)
                if u is not None:
                    a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
                    pts += list(np.c_[u[0] + 3 * np.cos(a), u[1] + 3 * np.sin(a)])
            if len(pts) < 3:
                return
            hull = cv2.convexHull(np.float32(pts)).reshape(-1, 2)
            dense = []
            for i in range(len(hull)):
                a, b = hull[i], hull[(i + 1) % len(hull)]
                for tt in np.linspace(0, 1, 8, endpoint=False):
                    dense.append(a * (1 - tt) + b * tt)
            im = proj(np.array(dense))
            cv.fill(im, COL["blue"], al * 0.28)
            cv.line(im, COL["blue"], 3 * k + 1, al, closed=True)
        elif t == "tether":
            A, B = self.P.uv(ly["a"], s), self.P.uv(ly["b"], s)
            if A is None or B is None:
                return
            pts = proj(np.linspace(A, B, 24))
            stroke_line(cv, pts, COL["white"], 3 * k + 1, al * 0.95, dash=True)
        elif t == "radius":
            c = self.P.uv(ly["key"], s)
            if c is None:
                return
            ds = [(np.linalg.norm(self.P.uv(d, s) - c), d) for d in ly["defs"] if self.P.uv(d, s) is not None]
            if not ds:
                return
            r, near = min(ds)
            p = self.anim(ly, T)
            e = proj.circle(c, r * p, 96)
            cv.fill(e, COL["gold"], al * 0.13)
            stroke_line(cv, np.r_[e, e[:1]], COL["gold"], 3 * k + 1, al, dash=True)
            if p > 0.95:
                stroke_line(cv, proj(np.linspace(c, self.P.uv(near, s), 20)), COL["white"], 3 * k + 1, al)
        elif t == "shotline":
            c = self.P.uv(ly["key"], ly.get("at", s))
            if c is None:
                return
            tl = proj(three_line())
            cv.line(tl, COL["gold"], 10 * k, al * 0.35)
            cv.line(tl, COL["gold"], 4 * k, al)
            stroke_line(cv, proj(np.linspace(RIM, c, 30)), COL["white"], 4 * k, al, dash=True)

    def floor_labels(self, ly, s, T):
        """地板图层附带的文字：返回 [(画面像素, 文字, 颜色)]。"""
        t = ly["type"]
        out = []
        if t == "tether" and ly.get("label", True):
            A, B = self.P.uv(ly["a"], s), self.P.uv(ly["b"], s)
            if A is not None and B is not None:
                m = self.cam.to_img(s, [(A + B) / 2])[0]
                dist = np.linalg.norm(A - B)
                out.append((m, f"{dist:.1f} FT" if self.en else f"{dist * 0.3048:.1f} 米", "white"))
        elif t == "hull":
            us = [self.P.uv(k, s) for k in ly["keys"] if self.P.uv(k, s) is not None]
            if us:
                top = min((self.cam.to_img(s, [u])[0] for u in us), key=lambda p: p[1])
                hs = self.P.height(ly["keys"][0], s)
                out.append((top - [0, hs + 70], ly["label"], "blue"))
        elif t == "radius" and self.anim(ly, T) > 0.95:
            c = self.P.uv(ly["key"], s)
            ds = [(np.linalg.norm(self.P.uv(d, s) - c), d) for d in ly["defs"] if self.P.uv(d, s) is not None]
            r, near = min(ds)
            m = self.cam.to_img(s, [(c + self.P.uv(near, s)) / 2])[0]
            out.append((m + [0, 0], f"CLOSEST DEFENDER {r:.1f} FT" if self.en else f"最近防守人 {r * 0.3048:.1f} 米", "gold"))
        elif t == "shotline":
            c = self.P.uv(ly["key"], ly.get("at", s))
            if c is not None:
                m = self.cam.to_img(s, [RIM * 0.45 + c * 0.55])[0]
                out.append((m + [0, 34], ly["label"], "gold"))
        elif t == "space" and ly.get("label") and self.anim(ly, T) > 0.6:
            lb = fx.space_label(self, ly, s)
            if lb:
                out.append(lb)
        elif t == "cone" and ly.get("label"):
            lb = fx.cone_label(self, ly, s, T)
            if lb:
                out.append(lb)
        elif t == "zone" and ly.get("label") and self.anim(ly, T) > 0.9:
            c = np.array(ly["label_uv"], float) if "label_uv" in ly else self.zone_poly(ly).mean(0)
            out.append((self.cam.to_img(s, [c])[0], ly["label"], ly.get("color", "gold")))
        elif t == "path" and ly.get("label") and s > ly["from"] + 4:
            u = self.P.uv(ly["key"], min(s, ly["to"]))
            if u is not None:
                out.append((self.cam.to_img(s, [u])[0] + [0, 40], ly["label"], ly.get("color", "white")))
        return out

    # ---- 画面空间图层（不被遮挡）
    def world_to_img(self, s, w):
        return self.cam.to_img(s, [w])[0]

    def ball_pos(self, f):
        fs = [b[0] for b in self.ball_w]
        if f < fs[0] or f > fs[-1]:
            return None
        for (fa, wa), (fb, wb) in zip(self.ball_w[:-1], self.ball_w[1:]):
            if fa <= f <= fb:
                t = (f - fa) / max(1e-6, fb - fa)
                return wa * (1 - t) + wb * t
        return None

    def screen_layer(self, cv, ly, s, T, al):
        t = ly["type"]
        if t == "ball":
            f1 = min(s, ly["to"])
            if f1 <= ly["from"]:
                return
            trail = [self.ball_pos(f) for f in np.arange(max(ly["from"], f1 - 5), f1 + 1e-6, 0.25)]
            pts = np.array([self.world_to_img(s, w) for w in trail if w is not None])
            if len(pts) >= 2:
                n = len(pts)
                for i in range(1, n):
                    a = (i / n) ** 1.5
                    cv.line(pts[i - 1:i + 1], COL["pass"], 3 + 12 * a, al * a * 0.75)
            if len(pts) and s <= ly["to"] + 0.5:
                cv.disc(pts[-1], 30, COL["pass"], al * 0.35)
                cv.disc(pts[-1], 22, COL["gold"], al, th=4)
        elif t == "arc":
            at = ly["at"]
            hd = self.P.head(ly["key"], at, self.cam)
            rim = self.world_to_img(at, self.rim_w)
            if hd is None:
                return
            rel = hd + [6, -14]
            xs = np.linspace(0, 1, 60)
            apex = min(rel[1], rim[1]) - 260
            px = rel[0] + (rim[0] - rel[0]) * xs
            py = (1 - xs) ** 2 * rel[1] + 2 * (1 - xs) * xs * apex + xs ** 2 * rim[1]
            p = self.anim(ly, T)
            n = max(2, int(60 * p))
            w = self.cam.to_court(at, np.c_[px[:n], py[:n]])
            pts = self.cam.to_img(s, w)
            cv.line(pts, COL["gold"], 12, al * 0.3)
            cv.dashed(pts, COL["gold"], 5, al, on=16, off=10)

    # ---- UI（推镜之后）
    def ui(self, img, sg, T, s, j, zt):
        H, W = self.H, self.W
        cv = Canvas(H, W)
        pil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(pil)

        def txt(xy, text, f, fill=(255, 255, 255), anchor="mm", stroke=4, a=1.0):
            dr.text(tuple(map(float, xy)), text, font=f, fill=fill + (int(255 * a),), anchor=anchor,
                    stroke_width=stroke, stroke_fill=(0, 0, 0, int(200 * a)))

        texts = []
        pills = []
        bodies = {}
        self._panels = []
        self._ui_text = []
        if self.logo is not None:
            lx, ly0 = self.edl.get("logo_xy", (56, 46))
            self._panels.append(dict(name="logoman", a=1.0, rect=[lx, ly0, lx + self.logo.width, ly0 + self.logo.height]))
        self._layout = {"pills": [], "subs": [], "panels": self._panels, "bodies": bodies}

        def want(anchor, text, col, a, f=None, dark=False, prio=5, lift=34, owner=None):
            f = f or font(30)
            x1, y1, x2, y2 = dr.textbbox((0, 0), text, font=f, anchor="mm")
            if self.nba:
                x1, x2 = 0, mixed_runs(text, f.size)[1] + 8
            pills.append(dict(anchor=np.asarray(anchor, float), cx=float(anchor[0]), cy=float(anchor[1] - lift),
                              w=x2 - x1 + 30, h=max(46, y2 - y1 + 18), text=text, f=f, col=col, a=a, dark=dark, prio=prio,
                              owner=owner))

        # 球员名牌、注记、地板图层文字
        for ly in self.layers:
            al = self.vis(ly, T, s)
            if al <= 0:
                continue
            if ly["type"] == "tag":
                for key in ly["keys"]:
                    h = self.P.head(key, s, self.cam)
                    if h is None:
                        continue
                    d = self.P.d[key]
                    sty = self.edl["style"][key]
                    b = self.P.box(key, s)
                    if sty in ("gold", "orange") and b is not None:
                        bodies[key] = np.concatenate([zt(b[:2]), zt(b[2:])])
                    col = COL[sty] if sty in ("gold", "orange") else TEAM[d["team"]]
                    want(zt(h), f"#{d['num']} {d['name']}", col, al, dark=sty == "gold",
                         prio=0 if sty == "gold" else 1 if sty == "orange" else 3, owner=key)
            elif ly["type"] == "note":
                h = self.P.head(ly["key"], s, self.cam)
                if h is not None:
                    sc = 1 + 0.25 * (1 - ease((T - ly["_on"]) / 0.3))
                    want(zt(h), ly["text"], COL[ly.get("color", "gold")], al, f=font(int(40 * sc)), dark=True,
                         prio=0, lift=92)
            elif ly["type"] == "pop":
                rim = zt(self.world_to_img(s, self.rim_w))
                age = T - self._src_time(ly["src_on"], ly["_on"])
                if ly.get("fx"):
                    fx.score_pop(pil, rim + [0, -130], ly["text"], age, al,
                                 (lambda sz, kind: font(sz, "numw")) if self.nba else font)
                    continue
                sc = 0.6 + 0.6 * ease(age / 0.25) - 0.15 * ease((age - 0.25) / 0.3)
                txt(rim + [0, -120], ly["text"], font(int(150 * sc), "num"), COL["gold"], stroke=8, a=al)
            elif ly["type"] in ("tether", "hull", "radius", "shotline", "path", "space", "cone", "zone") and T < ly["_imgoff"]:
                for p, text, c in self.floor_labels(ly, s, T):
                    want(zt(p), text, (25, 30, 45) if c == "white" else COL[c], al, f=font(28), dark=c == "gold",
                         prio=4 if ly["type"] != "hull" else 2, lift=0)
            elif ly["type"] == "title":
                self._title(cv, txt, ly, al)
            elif ly["type"] == "board":
                self._board(cv, texts, ly, s if "s" not in ly else ly["s"], T, al)
        # 名牌避让：按优先级落位，和已放的重叠就往上推，推开了画一根引线指回球员
        sub_y, sub_f = self.edl.get("sub_y", H - 172), font(self.edl.get("sub_size", 54))
        placed = [(W / 2, sub_y, sub_f.getlength(c) + 40, sub_f.size * 1.55) for a, b, c in self.subs if a <= T < b]
        panels = [pn["rect"] for pn in self._panels if pn["a"] > 0]

        def off_panels(cx, cy, w, h):
            """名牌不压战术板和信息卡：挪到上下左右里位移最小、且不出画的那一侧。"""
            for px1, py1, px2, py2 in panels:
                if not (px1 - w / 2 < cx < px2 + w / 2 and py1 - h / 2 < cy < py2 + h / 2):
                    continue
                opts = [(px1 - w / 2 - 6, cy), (px2 + w / 2 + 6, cy), (cx, py2 + h / 2 + 6), (cx, py1 - h / 2 - 6)]
                opts = [o for o in opts if w / 2 + 12 <= o[0] <= W - w / 2 - 12 and h / 2 + 12 <= o[1] <= H - h / 2 - 12]
                if opts:
                    cx, cy = min(opts, key=lambda o: np.hypot(o[0] - cx, o[1] - cy))
            return cx, cy

        for p in sorted(pills, key=lambda q: (q["prio"], -q["anchor"][1])):
            w, h = p["w"], p["h"]
            cx = float(np.clip(p["cx"], w / 2 + 12, W - w / 2 - 12))
            cy = float(np.clip(p["cy"], h / 2 + 12, H - h / 2 - 12))
            # 名牌不压重点球员的身体：横向让到离自己锚点近的那一侧
            for k, (bx1, by1, bx2, by2) in bodies.items():
                if k == p["owner"] or not (bx1 - w / 2 < cx < bx2 + w / 2 and by1 - h / 2 < cy < by2 + h / 2):
                    continue
                left, right = bx1 - w / 2 - 6, bx2 + w / 2 + 6
                cx = left if abs(left - p["anchor"][0]) <= abs(right - p["anchor"][0]) else right
                cx = float(np.clip(cx, w / 2 + 12, W - w / 2 - 12))
            for _ in range(12):
                hit = [q for q in placed if abs(q[0] - cx) < (q[2] + w) / 2 + 6 and abs(q[1] - cy) < (q[3] + h) / 2 + 4]
                if not hit:
                    break
                cy = min(q[1] - (q[3] + h) / 2 - 4 for q in hit)
            cy = max(cy, h / 2 + 12)
            cx, cy = off_panels(cx, cy, w, h)
            placed.append((cx, cy, w, h))
            self._layout["pills"].append(dict(text=p["text"], owner=p["owner"], a=float(p["a"]),
                                              rect=[cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                                              moved=float(np.hypot(p["cx"] - cx, p["cy"] - cy))))
            if np.hypot(p["cx"] - cx, p["cy"] - cy) > 10:
                cv.line([(cx, cy + h / 2), (p["anchor"][0], p["anchor"][1] - 8)], (255, 255, 255), 2, p["a"] * 0.8)
            if self.nba:
                cv.slab(cx - w / 2 + 3, cy - h / 2 + 4, cx + w / 2 + 3, cy + h / 2 + 4, (0, 0, 0), p["a"] * 0.35)
                cv.slab(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, p["col"], p["a"] * 0.95)
                reddish = p["col"][0] > 150 and p["col"][1] < 80 and p["col"][2] < 100
                acc = COL.get("nbablue", COL["blue"]) if reddish else COL["red"]
                cv.slab(cx + w / 2 - 9, cy - h / 2, cx + w / 2, cy + h / 2, acc, p["a"])
            else:
                cv.rrect(cx - w / 2 + 2, cy - h / 2 + 3, cx + w / 2 + 2, cy + h / 2 + 3, 12, (0, 0, 0), p["a"] * 0.35)
                cv.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 12, p["col"], p["a"] * 0.92)
            texts.append((cx, cy - 1, p["text"], p["f"], (20, 20, 20) if p["dark"] else (255, 255, 255), p["a"],
                          self.nba))
        # 段角标
        if sg.get("badge"):
            self._badge(cv, txt, sg, j)
        for ly in self.layers:
            if ly["type"] == "huazi" and self.vis(ly, T, s) > 0:
                self._huazi(cv, texts, ly, T)
        # 字幕（subs=false 时字幕交给成片时间线，这里只保留上面的避让位）
        sf = font(self.edl.get("sub_size", 54), "sub" if self.nba else "zh")
        for a, b, c in self.subs if self.edl.get("subs", True) else []:
            if a <= T < b:
                al = min(1.0, (T - a) / 0.12, (b - T) / 0.12)
                if self.nba:
                    dr.text((W / 2 + 3, sub_y + 4), c, font=sf, fill=(0, 0, 0, int(140 * al)), anchor="mm",
                            stroke_width=7, stroke_fill=(0, 0, 0, int(140 * al)))
                txt((W / 2, sub_y), c, sf, stroke=6, a=al)
                self._layout["subs"].append(dict(text=c, a=float(al), rect=list(
                    dr.textbbox((W / 2, sub_y), c, font=sf, anchor="mm", stroke_width=6))))
        img = cv.composite(img)
        for cx, cy, text, f, fill, a, *mx in texts:
            if mx and mx[0]:
                draw_mixed(dr, (cx, cy), text, f.size, fill, a, anchor="mm", zh=mx[1] if len(mx) > 1 else "zh",
                           num=mx[2] if len(mx) > 2 else "num")
            else:
                dr.text((cx, cy), text, font=f, fill=fill + (int(255 * a),), anchor="mm")
        for kind, xy, text, size, fill, a, *anc in self._ui_text:
            anchor = anc[0] if anc else "lm"
            if kind == "mix":
                draw_mixed(dr, xy, text, size, fill, a, anchor=anchor)
            else:
                dr.text(tuple(map(float, xy)), text, font=font(size, kind), fill=tuple(fill) + (int(255 * a),), anchor=anchor)
        if self.logo is not None:
            pil.alpha_composite(self.logo, tuple(self.edl.get("logo_xy", (56, 46))))
        pa = np.asarray(pil).astype(np.float32)
        al = pa[..., 3:4] / 255.0
        return img * (1 - al) + pa[..., :3] * al

    def _src_time(self, f, after=-1e9):
        """原片第 f 帧在成片里的时刻。同一帧可能在原速段和慢放段各出现一次，取 after 之后的第一次。"""
        for sg in self.tl.segs:
            if sg["kind"] == "play" and sg["from"] <= f <= sg["to"] and sg["end"] > after:
                return sg["start"] + (f - sg["from"]) / sg["speed"] / self.tl.fps
        return -1e9

    def _title(self, cv, txt, ly, al):
        if self.nba:
            return self._title_nba(cv, ly, al)
        x, y = 48, 44
        lines = ly["lines"]
        w = 70 + max(font(26, "zhr").getlength(lines[0]), font(38).getlength(lines[1]), font(34).getlength(lines[2]))
        self._panels.append(dict(name="信息卡", a=float(al), rect=[x, y, x + w, y + 176]))
        cv.rrect(x, y, x + w, y + 176, 16, COL["navy"], al * 0.82)
        cv.rrect(x, y, x + 10, y + 176, 4, TEAM["HOU"], al)
        txt((x + 34, y + 34), lines[0], font(26, "zhr"), (200, 210, 230), anchor="lm", stroke=0, a=al)
        txt((x + 34, y + 84), lines[1], font(38), anchor="lm", stroke=0, a=al)
        txt((x + 34, y + 138), lines[2], font(34), COL["gold"], anchor="lm", stroke=0, a=al)

    def _title_nba(self, cv, ly, al):
        """信息卡：蓝色眉条写英文赛事名（Knockout），墨黑底两行，数字用 Action NBA，左侧红条。"""
        x, y = self.edl.get("badge_xy", (130, 46))
        lines, kick = ly["lines"], ly.get("kicker", "")
        bar = font(26, "ko").getlength(kick) + 28 + font(22, "zhr").getlength(lines[0])
        w = 64 + max(bar, mixed_runs(lines[1], 38)[1], mixed_runs(lines[2], 32)[1])
        h = 48 + 116
        self._panels.append(dict(name="信息卡", a=float(al), rect=[x, y, x + w, y + h]))
        cv.rect(x, y, x + w, y + 48, COL.get("nbablue", COL["blue"]), al)
        cv.rect(x, y + 48, x + w, y + h, COL["navy"], al * 0.86)
        cv.rect(x, y, x + 10, y + h, COL["red"], al)
        self._ui_text.append(("ko", (x + 32, y + 25), kick, 26, (255, 255, 255), al))
        self._ui_text.append(("zhr", (x + w - 22, y + 25), lines[0], 22, (195, 206, 211), al, "rm"))
        self._ui_text.append(("mix", (x + 32, y + 48 + 36), lines[1], 38, (255, 255, 255), al))
        self._ui_text.append(("mix", (x + 32, y + 48 + 86), lines[2], 32, COL["gold"], al))

    def _huazi(self, cv, texts, ly, T):
        """花字：斜切色块从左擦入（slam 时从大砸到原大），白色黑体，右侧异色细条，上方英文小标加红色短线。"""
        age = T - ly["_on"]
        a = min(1.0, (ly["_off"] - T) / 0.2)
        if a <= 0 or age < 0:
            return
        size = ly.get("size", 96)
        sc = 1 + 0.5 * (1 - ease(age / 0.16)) if ly.get("style") == "slam" else 1.0
        sz = int(size * sc)
        hf = font(sz, "ko" if self.en else "zh")
        tw = hf.getlength(ly["text"])
        bw, bh = tw + sz * 0.9, sz * 1.36
        cx, cy = ly["pos"]
        x1, y1 = cx - bw / 2, cy - bh / 2
        wipe = ease(age / 0.22) if ly.get("style") != "slam" else 1.0
        a *= min(1.0, age / 0.08) if ly.get("style") == "slam" else 1.0
        bg = COL[ly.get("bg", "red")]
        acc = COL.get("nbablue", COL["blue"]) if bg == COL["red"] else COL["red"]
        self._panels.append(dict(name="花字", a=float(a), rect=[x1, y1 - 40, x1 + bw, y1 + bh]))
        cv.slab(x1 + 6, y1 + 8, x1 + 6 + bw * wipe, y1 + bh + 8, (0, 0, 0), a * 0.35)
        cv.slab(x1, y1, x1 + bw * wipe, y1 + bh, bg, a)
        if wipe > 0.98:
            cv.slab(x1 + bw - 4, y1, x1 + bw + 14, y1 + bh, acc, a)
        ta = a * ease((age - 0.08) / 0.15) if ly.get("style") != "slam" else a
        texts.append((cx, cy, ly["text"], hf, (255, 255, 255), ta))
        if ly.get("kicker"):
            ks = max(24, int(sz * 0.3))
            kf = font(ks, "ko")
            kw = kf.getlength(ly["kicker"].upper())
            self._ui_text.append(("ko", (x1 + 8, y1 - ks * 0.9), ly["kicker"].upper(), ks, (255, 255, 255), ta))
            cv.rect(x1 + kw + 24, y1 - ks * 0.9 - 2, x1 + kw + 24 + sz * 1.2, y1 - ks * 0.9 + 3, COL["red"], ta)

    def _box(self, cv, x1, y1, x2, y2, r, col, al):
        (cv.rect(x1, y1, x2, y2, col, al) if self.nba else cv.rrect(x1, y1, x2, y2, r, col, al))

    def _badge(self, cv, txt, sg, j):
        x, y = self.edl.get("badge_xy", (48, 44))
        label = sg["badge"]
        f = font(34)
        w = 70 + int(f.getlength(label) if not self.nba else mixed_runs(label, 34)[1])
        a = min(1.0, j / 0.2)
        self._panels.append(dict(name="角标", a=float(a), rect=[x, y, x + w, y + 58]))
        if self.nba:
            cv.slab(x, y, x + w, y + 58, COL["navy"], 0.88 * a)
            cv.slab(x, y, x + 9, y + 58, COL["red"], a)
        else:
            cv.rrect(x, y, x + w, y + 58, 14, COL["navy"], 0.8 * a)
        cx, cy = x + 30, y + 29
        if sg["kind"] in ("freeze",):
            cv.fill([(cx - 9, cy - 12), (cx - 3, cy - 12), (cx - 3, cy + 12), (cx - 9, cy + 12)], COL["gold"], a)
            cv.fill([(cx + 3, cy - 12), (cx + 9, cy - 12), (cx + 9, cy + 12), (cx + 3, cy + 12)], COL["gold"], a)
        elif sg["kind"] == "rewind":
            for dx in (-10, 2):
                cv.fill([(cx + dx + 10, cy - 11), (cx + dx + 10, cy + 11), (cx + dx - 2, cy)], COL["gold"], a)
        else:
            cv.disc((cx, cy), 10, COL["red"], a)
        if self.nba:
            self._ui_text.append(("mix", (x + 52, y + 29), label, 34, (255, 255, 255), a))
        else:
            txt((x + 52, y + 29), label, f, (255, 255, 255), anchor="lm", stroke=0, a=a)

    def _board(self, cv, texts, ly, s, T, al):
        if ly.get("pos") == "card":
            k, x0, y0 = 10.4, 1270, 248
        else:
            k = 6.2
            bw = (BoardProj.U1 - BoardProj.U0) * k
            x0, y0 = self.W - 34 - bw, 84
        pr = BoardProj(x0, y0, k)
        bw, bh = pr.size
        self._panels.append(dict(name="战术板", a=float(al), rect=[x0 - 14, y0 - 54, x0 + bw + 14, y0 + bh + 52]))
        self._box(cv, x0 - 14, y0 - 54, x0 + bw + 14, y0 + bh + 14, 16, COL["navy"], al * 0.86)
        title = "PLAY DIAGRAM" if self.en else "战术板"
        if self.nba:
            cv.rect(x0 - 14, y0 - 54, x0 - 6, y0 - 4, COL["red"], al)
            tf = font(28 if k < 8 else 36, "ko" if self.en else "zh")
            texts.append((x0 + 6 + tf.getlength(title) / 2, y0 - 28, title, tf, (255, 255, 255), al))
        else:
            texts.append((x0 + 2 + 48, y0 - 28, title, font(28 if k < 8 else 36), (255, 255, 255), al))
        teams = (("HOU", TEAM["HOU"]), ("DAL", TEAM["DAL"])) if self.en else (("火箭", TEAM["HOU"]), ("独行侠", TEAM["DAL"]))
        for i, (tn, c) in enumerate(teams):
            lx = x0 + bw - 150 + i * 72
            cv.disc((lx, y0 - 28), 7, c, al)
            tf = font(22, "ko") if self.en else font(20, "zhr")
            texts.append((lx + 12 + tf.getlength(tn) / 2 if self.en else lx + 28 + 6 * i, y0 - 28, tn, tf, (220, 225, 235), al))
        cv.fill(pr([(0, -25), (41.5, -25), (41.5, 25), (0, 25)]), (64, 52, 40), al * 0.9)
        cv.fill(pr([(0, -8), (19, -8), (19, 8), (0, 8)]), (40, 62, 130), al * 0.9)
        for ln in court_lines():
            cv.line(pr(ln), (225, 225, 235), 1.6 if k < 8 else 2.2, al * 0.85)
        cv.disc(pr([RIM])[0], 0.75 * k, (255, 120, 40), al, th=2)
        show = ly.get("show")
        fl = Canvas(self.H, self.W)
        for o in self.floor_layers():
            if o["type"] == "shotline":
                continue
            if show is not None:
                if o.get("id") in show:
                    ss = o["to"] if o["type"] == "path" else o["b"][1] if o["type"] == "pass" else s
                    self.floor_layer(fl, pr, dict(o, _anim=[-2.0, -1.0]), ss, 1e9, al, board=True)
                continue
            oa = self.vis(o, T, s)
            if oa > 0:
                self.floor_layer(fl, pr, o, s, T, al * oa, board=True)
        cv.over(fl, (x0, y0, x0 + bw, y0 + bh))
        dots = [pr([self.P.uv(q, s)])[0] for q in self.P.d if self.P.uv(q, s) is not None]
        for key, d in self.P.d.items():
            u = self.P.uv(key, s)
            if u is None:
                continue
            c = pr([u])[0]
            sty = self.edl["style"][key]
            fill = COL["gold"] if sty == "gold" else TEAM[d["team"]]
            r = 11 * k / 6.2
            cv.disc(c, r + 2, (255, 255, 255), al)
            cv.disc(c, r, fill, al)
            texts.append((c[0], c[1] - 1, d["num"], font(int(17 * k / 6.2), "num"), (20, 20, 20) if sty == "gold" else (255, 255, 255), al))
            if show is not None and sty in ("gold", "orange"):
                f26 = font(26)
                half = f26.getlength(d["name"]) / 2
                cands = [(c[0] + r + 8 + half, c[1]), (c[0] - r - 8 - half, c[1]),
                         (c[0], c[1] - r - 20), (c[0], c[1] + r + 20)]

                def clear(p):
                    return all(abs(p[0] - q[0]) > half + r + 2 or abs(p[1] - q[1]) > 15 + r
                               for q in dots if np.hypot(q[0] - c[0], q[1] - c[1]) > 1)
                p = next((p for p in cands if clear(p)), cands[0])
                texts.append((p[0], p[1], d["name"], f26, COL[sty], al))
        # 线型图例
        ly0 = y0 + bh + 30
        self._box(cv, x0 - 14, y0 + bh + 8, x0 + bw + 14, y0 + bh + 52, 12, COL["navy"], al * 0.86)
        names = ("CUT", "PASS", "DEF") if self.en else ("跑位", "传球", "防守")
        items = tuple(zip(names, (COL["orange"], COL["pass"], COL["blue"]), (False, True, False)))
        fz = font(22 if k < 8 else 30, "ko") if self.en else font(20 if k < 8 else 26, "zhr")
        step = bw / len(items)
        for n, (name, c, dash) in enumerate(items):
            lx = x0 + n * step + 4
            seg = [(lx, ly0), (lx + 26, ly0)]
            (cv.dashed(seg, c, 3, al, on=8, off=5) if dash else cv.line(seg, c, 3, al))
            texts.append((lx + 34 + fz.getlength(name) / 2, ly0, name, fz, (220, 225, 235), al))

    def _card(self, img, sg, j):
        H, W = self.H, self.W
        a = ease(j / 0.5)
        blur = cv2.GaussianBlur(img, (0, 0), 14) * 0.38
        push = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + 0.05 * j / (sg["n"] / self.tl.fps))
        blur = cv2.warpAffine(blur, push, (W, H), borderMode=cv2.BORDER_REFLECT)
        img = img * (1 - a) + blur * a
        cv = Canvas(H, W)
        pil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(pil)
        if self.nba:
            return self._card_nba(img, cv, pil, dr, sg, j, a)
        home, hs, vs, away = sg["score"]
        y = 300
        cv.rrect(120, y - 90, 1130, y + 90, 22, COL["navy"], a * 0.85)
        cv.rrect(120, y - 90, 136, y + 90, 6, TEAM["HOU"], a)
        dr.text((200, y), home, font=font(64), fill=(255, 255, 255, int(255 * a)), anchor="lm")
        dr.text((520, y + 6), hs, font=font(150, "num"), fill=COL["gold"] + (int(255 * a),), anchor="mm")
        dr.text((640, y + 6), ":", font=font(110, "num"), fill=(220, 220, 220, int(255 * a)), anchor="mm")
        dr.text((760, y + 6), vs, font=font(150, "num"), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        dr.text((880, y), away, font=font(64), fill=(255, 255, 255, int(255 * a)), anchor="lm")
        for i, (who, what) in enumerate(sg["rows"]):
            ra = ease((j - 0.5 - 0.35 * i) / 0.35)
            yy = 500 + i * 110
            cv.rrect(120, yy - 42, 1130, yy + 42, 16, (24, 32, 54), ra * 0.85)
            dr.text((160, yy), who, font=font(46), fill=COL["gold"] + (int(255 * ra),), anchor="lm")
            dr.text((420, yy), what, font=font(42, "zhr"), fill=(255, 255, 255, int(255 * ra)), anchor="lm")
        dr.text((W / 2, H - 40), sg["credit"], font=font(24, "zhr"), fill=(170, 175, 190, int(255 * a)), anchor="mm")
        img = cv.composite(img)
        pa = np.asarray(pil).astype(np.float32)
        al = pa[..., 3:4] / 255.0
        return img * (1 - al) + pa[..., :3] * al

    def _card_nba(self, img, cv, pil, dr, sg, j, a):
        H, W = self.H, self.W
        home, hs, vs, away = sg["score"]
        A = lambda al: int(255 * al)  # noqa: E731
        texts = []
        if sg.get("head"):
            zh, en = sg["head"]
            self._ui_text = []
            self._huazi(cv, texts, dict(text=zh, kicker=en, pos=(120 + (font(60, "ko" if self.en else "zh").getlength(zh) + 54) / 2, 168), size=60,
                                        _on=sg["start"] + 0.15, _off=1e9), sg["start"] + j)
            heads = self._ui_text
        else:
            heads = []
        y = 345
        cv.slab(120, y - 84, 1130, y + 84, COL["navy"], a * 0.88)
        cv.slab(120, y - 84, 420, y + 84, TEAM["HOU"], a)
        cv.slab(830, y - 84, 1130, y + 84, TEAM["DAL"], a)
        cv.slab(1122, y - 84, 1138, y + 84, COL["red"], a)
        rows = sg["rows"]
        for i in range(len(rows)):
            ra = ease((j - 0.5 - 0.35 * i) / 0.35)
            yy = 555 + i * 108
            cv.rect(120, yy - 42, 1130, yy + 42, COL["navy"], ra * 0.86)
            cv.rect(120, yy - 42, 130, yy + 42, COL["red"], ra)
        img = cv.composite(img)
        tf = font(64, "ko") if self.en else font(60)
        dr.text((270, y), home, font=tf, fill=(255, 255, 255, A(a)), anchor="mm")
        dr.text((980, y), away, font=tf, fill=(255, 255, 255, A(a)), anchor="mm")
        dr.text((540, y + 8), hs, font=font(150, "numw"), fill=(255, 255, 255, A(a)), anchor="mm")
        dr.text((625, y + 4), ":", font=font(110, "numw"), fill=(195, 206, 211, A(a)), anchor="mm")
        dr.text((710, y + 8), vs, font=font(150, "numw"), fill=(195, 206, 211, A(a)), anchor="mm")
        for i, (who, what) in enumerate(rows):
            ra = ease((j - 0.5 - 0.35 * i) / 0.35)
            yy = 555 + i * 108
            dr.text((160, yy), who, font=font(44, "ko") if self.en else font(44), fill=(255, 255, 255, A(ra)), anchor="lm")
            draw_mixed(dr, (400, yy), what, 40, (213, 217, 221), ra, zh="zhr")
        for cx, cy, text, f, fill, al in texts:
            dr.text((cx, cy), text, font=f, fill=fill + (A(al),), anchor="mm")
        for kind, xy, text, size, fill, al, *anc in heads:
            dr.text(tuple(map(float, xy)), text, font=font(size, kind), fill=tuple(fill) + (A(al),), anchor="lm")
        dr.text((W / 2, H - 40), sg["credit"], font=font(24, "zhr"), fill=(170, 175, 190, A(a)), anchor="mm")
        pa = np.asarray(pil).astype(np.float32)
        al = pa[..., 3:4] / 255.0
        return img * (1 - al) + pa[..., :3] * al

    def _view(self, i, s):
        """虚拟推镜：返回 (倍率, 裁切左上角 x, y)。"""
        W, H = self.W, self.H
        (za, ka), (zb, kb), p = self.tl.zoom_state(i)
        z = za + (zb - za) * p
        if z <= 1.001:
            return z, 0.0, 0.0

        def center(key):
            if isinstance(key, list):
                return np.array(key, float)
            u = self.P.uv(key, s) if key else None
            return self.cam.to_img(s, [u])[0] - [0, 150] if u is not None else np.array([W / 2, H / 2])
        fc = center(ka) * (1 - p) + center(kb) * p
        cw, ch = W / z, H / z
        return z, float(np.clip(fc[0] - cw / 2, 0, W - cw)), float(np.clip(fc[1] - ch / 2, 0, H - ch))

    def layout(self, i: int) -> dict:
        """只算 UI 布局不出画面：名牌、字幕、面板、重点球员身体框的最终位置（供 check_labels.py）。"""
        sg, j, s = self.tl.at(i)
        z, x0, y0 = self._view(i, s)
        self.ui(np.zeros((self.H, self.W, 3), np.float32), sg, i / self.tl.fps, s, j,
                lambda p: (np.asarray(p, float) - [x0, y0]) * z)
        return dict(self._layout, i=i, t=round(i / self.tl.fps, 2), seg=sg["id"])

    # ---- 一帧
    def frame(self, i: int) -> np.ndarray:
        sg, j, s = self.tl.at(i)
        T = i / self.tl.fps
        img = self.src_frame(sg, s).astype(np.float32)
        H, W = img.shape[:2]

        if sg["kind"] == "rewind":
            g = img.mean(axis=2, keepdims=True)
            img = img * 0.55 + g * 0.45
            rng = np.random.default_rng(i)
            for _ in range(5):
                y, h = int(rng.integers(0, H - 30)), int(rng.integers(4, 26))
                img[y:y + h] = np.roll(img[y:y + h], int(rng.integers(-40, 40)), axis=1)
            img[..., 0] = np.roll(img[..., 0], 6, axis=1)
            img *= 0.9

        stop = 0.0
        if sg.get("stop"):
            d = sg["n"] / self.tl.fps
            stop = min(ease(j / 0.3), ease((d - j) / 0.22))
            src = img
            if sg.get("glow"):
                img = fx.glow_freeze(self, img, sg, s, stop)
            else:
                spot = self.M.of(sg["spot"], s, img.shape, feather=2.5)
                g = img @ np.array([0.3, 0.59, 0.11], np.float32)
                bg = (g[..., None] * 0.42) * np.array([0.82, 0.92, 1.18], np.float32)
                fg = np.clip(img * 1.06, 0, 255)
                ts = bg * (1 - spot[..., None]) + fg * spot[..., None]
                img = img * (1 - stop) + ts * stop
            if self.edl.get("keep"):
                km = np.zeros((H, W), np.float32)
                for x1, y1, x2, y2 in self.edl["keep"]:
                    km[y1:y2, x1:x2] = 1.0
                km = cv2.GaussianBlur(km, (0, 0), 4)[..., None]
                img = img * (1 - km) + src * km

        if sg["kind"] != "card":
            occ = self.M.everyone(s, img.shape)
            floor = Canvas(H, W)
            scr = Canvas(H, W)
            proj = ImgProj(self.cam, s)
            for ly in self.floor_layers():
                al = self.vis(ly, T, s)
                if al > 0 and T < ly["_imgoff"]:
                    self.floor_layer(scr if ly.get("top") else floor, proj, ly, s, T, al)
            for ly in self.layers:
                al = self.vis(ly, T, s)
                if al > 0 and ly["type"] in ("ball", "arc"):
                    self.screen_layer(scr, ly, s, T, al)
            img = floor.composite(img, occ)
            img = scr.composite(img)
            for ly in self.layers:
                if ly["type"] == "ghost" and self.vis(ly, T, s) > 0:
                    lift = 9.0 * stop if sg.get("glow") and ly["key"] in sg["spot"] else 0.0
                    img = fx.draw_ghost(self, img, ly, s, self.vis(ly, T, s), lift)
            for ly in self.layers:
                if ly["type"] == "goal" and self.vis(ly, T, s) > 0:
                    img = fx.goal_burst(img, self.world_to_img(s, self.rim_w), fx.goal_age(self, ly, T))

        if sg.get("stop") and j < 0.45:
            u = self.P.uv(sg["focus"], s)
            if u is not None:
                c = self.cam.to_img(s, [u])[0]
                rip = Canvas(H, W)
                r = 60 + 1500 * ease(j / 0.45)
                rip.disc(c, r, (255, 255, 255), 0.55 * (1 - j / 0.45), th=10)
                img = rip.composite(img)
            if j < 0.1:
                img = img * (1 - 0.35 * (1 - j / 0.1)) + 255 * 0.35 * (1 - j / 0.1)

        z, x0, y0 = self._view(i, s)
        if z > 1.001:
            M = np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR)
        for ly in self.layers:
            if ly["type"] == "goal" and self.vis(ly, T, s) > 0:
                dx, dy, zz = fx.shake(fx.goal_age(self, ly, T))
                if zz > 1.0:
                    sm = np.float32([[zz, 0, dx - W * (zz - 1) / 2], [0, zz, dy - H * (zz - 1) / 2]])
                    img = cv2.warpAffine(img, sm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        def zt(p):
            return (np.asarray(p, float) - [x0, y0]) * z

        if sg["kind"] == "card":
            img = self._card(img, sg, j)
            img = self.ui(img, sg, T, s, j, zt)
        else:
            img = self.ui(img, sg, T, s, j, zt)
        return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 预处理：补蒙版

def extra_masks(r: Renderer):
    """时停段要提亮的球员如果没有现成蒙版（跟踪丢失、人工补点），用 YOLO-seg 在该帧现抠。"""
    need = []
    for sg in r.tl.segs:
        if not sg.get("stop"):
            continue
        f = int(sg["at"])
        z = r.M._load(f)
        for k in sg["spot"]:
            tid = r.P.d[k]["tid"][f]
            if (tid is None or str(tid) not in z) and not (r.M.extra / f"{f:04d}_{k}.npz").exists():
                need.append((f, k))
    if not need:
        return
    from ultralytics import YOLO
    model = YOLO(str(r.work.parent / "yolo11x-seg.pt"))
    r.M.extra.mkdir(exist_ok=True)
    for f, k in need:
        img = cv2.imread(str(r.base / r.edl["orig"] / f"{f:04d}.jpg"))
        res = model.predict(img, classes=[0], conf=0.2, imgsz=1280, retina_masks=True, verbose=False, device=device())[0]
        foot = r.cam.to_img(f, [r.P.uv(k, f)])[0]
        best, bm = 1e9, None
        for b, m in zip(res.boxes.xyxy.cpu().numpy(), res.masks.data.cpu().numpy()):
            d = np.hypot((b[0] + b[2]) / 2 - foot[0], b[3] - foot[1])
            if d < best:
                best, bm = d, m > 0.5
        if bm is None or best > 90:
            print(f"  补蒙版失败 f{f} {k}（最近 {best:.0f}px）")
            continue
        ys, xs = np.nonzero(bm)
        x1, y1 = xs.min(), ys.min()
        np.savez_compressed(r.M.extra / f"{f:04d}_{k}.npz", xy=np.array([x1, y1]),
                            m=bm[y1:ys.max() + 1, x1:xs.max() + 1].astype(np.uint8))
        print(f"  补蒙版 f{f} {k}（脚底偏差 {best:.0f}px）")


def hq_masks(r: Renderer):
    """glow 时停帧的重点球员用 SAM2 按跟踪框重新精细分割，存 masks_hq/（YOLO 蒙版边缘粗、常漏掉深色部位）。
    跟踪框不准或缺失时，在 EDL 的 mask_box 里给框：{"128": {"ZR": [x1, y1, x2, y2]}}。"""
    need = []
    for sg in r.tl.segs:
        if not (sg.get("stop") and sg.get("glow")):
            continue
        f = int(sg["at"])
        for k in sg["spot"]:
            if not (r.M.hq / f"{f:04d}_{k}.npz").exists():
                need.append((f, k))
    if not need:
        return
    from ultralytics import SAM
    model = SAM(str(r.work.parent / "sam2.1_l.pt"))
    r.M.hq.mkdir(exist_ok=True)
    for f in sorted({f for f, _ in need}):
        keys = [k for ff, k in need if ff == f]
        boxes = []
        for k in keys:
            b = r.edl.get("mask_box", {}).get(str(f), {}).get(k)
            b = np.array(b, float) if b is not None else r.P.box(k, f)
            ex = r.M.extra / f"{f:04d}_{k}.npz"
            if b is None and ex.exists():                      # 人工补点的帧没有跟踪框，用补抠蒙版的外框
                e = np.load(ex)
                (x1, y1), (h, w) = e["xy"], e["m"].shape
                b = np.array([x1, y1, x1 + w, y1 + h], float)
            boxes.append(b)
        ok = [(k, b) for k, b in zip(keys, boxes) if b is not None]
        for k, b in zip(keys, boxes):
            if b is None:
                print(f"  精细蒙版缺框 f{f} {k}，在 EDL 的 mask_box 里补")
        if not ok:
            continue
        img = cv2.imread(str(r.base / r.edl["orig"] / f"{f:04d}.jpg"))
        H, W = img.shape[:2]
        res = model(img, bboxes=[list(map(float, b)) for _, b in ok], verbose=False, device=device())[0]
        for (k, b), mm in zip(ok, res.masks.data.cpu().numpy()):
            m = (mm > 0.5).astype(np.uint8)
            x1, y1, x2, y2 = b
            pw, ph = (x2 - x1) * 0.12, (y2 - y1) * 0.08
            keep = np.zeros_like(m)
            keep[int(max(0, y1 - ph)):int(min(H, y2 + ph)), int(max(0, x1 - pw)):int(min(W, x2 + pw))] = 1
            m = cv2.morphologyEx(m * keep, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(m)
            if n > 2:
                big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
                m = np.isin(lab, [i for i in range(1, n) if i == big or st[i, cv2.CC_STAT_AREA] > 0.08 * st[big, cv2.CC_STAT_AREA]]).astype(np.uint8)
            ys, xs = np.nonzero(m)
            if not len(xs):
                print(f"  精细蒙版为空 f{f} {k}")
                continue
            np.savez_compressed(r.M.hq / f"{f:04d}_{k}.npz", xy=np.array([xs.min(), ys.min()]),
                                m=m[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
            print(f"  精细蒙版 f{f} {k}（{len(xs)} 像素）")


# ---------------------------------------------------------------- 声音

def sfx(kind: str, sr: int = 48000) -> np.ndarray:
    rng = np.random.default_rng(7)
    if kind == "stop":
        n = int(0.7 * sr)
        t = np.arange(n) / sr
        f = 900 * np.exp(-t * 7) + 70
        tone = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 5)
        noise = rng.standard_normal(n) * np.exp(-t * 9)
        noise = np.convolve(noise, np.ones(12) / 12, "same")
        thump = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 10)
        return 0.32 * tone + 0.35 * noise + 0.5 * thump
    if kind == "resume":
        n = int(0.35 * sr)
        t = np.arange(n) / sr
        noise = rng.standard_normal(n)
        env = np.sin(np.pi * t / t[-1]) ** 2
        k = np.linspace(40, 4, n).astype(int)
        out = np.array([noise[max(0, i - k[i]):i + 1].mean() for i in range(n)])
        return 0.5 * out * env
    if kind == "rewind":
        n = int(0.9 * sr)
        t = np.arange(n) / sr
        f = 300 + 1100 * t / t[-1] + 60 * np.sin(2 * np.pi * 13 * t)
        saw = 2 * ((np.cumsum(f) / sr) % 1) - 1
        env = np.minimum(1, t / 0.08) * np.minimum(1, (t[-1] - t) / 0.1)
        return 0.16 * saw * env + 0.08 * rng.standard_normal(n) * env
    if kind == "boom":
        n = int(1.4 * sr)
        t = np.arange(n) / sr
        thump = np.sin(2 * np.pi * (42 + 60 * np.exp(-t * 25)) * t) * np.exp(-t * 5)
        noise = np.convolve(rng.standard_normal(n), np.ones(30) / 30, "same") * np.exp(-t * 14) * 3
        shimmer = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((2637, 3322, 3951, 5274))) / 4
        shimmer *= np.exp(-t * 3.2) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t)) * np.minimum(1, t / 0.02)
        return 0.75 * thump + 0.35 * noise + 0.12 * shimmer
    if kind == "wave":
        n = int(0.6 * sr)
        t = np.arange(n) / sr
        sweep = np.sin(2 * np.pi * np.cumsum(70 + 160 * np.exp(-t * 9)) / sr) * np.exp(-t * 6)
        air = np.convolve(rng.standard_normal(n), np.ones(60) / 60, "same") * np.sin(np.pi * t / t[-1]) * 4
        return 0.55 * sweep + 0.25 * air
    if kind == "pop":
        n = int(0.9 * sr)
        t = np.arange(n) / sr
        return 0.7 * np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 20)) * t) * np.exp(-t * 4.5)
    raise ValueError(kind)


def mix(r: Renderer, out_wav: Path):
    sr = 48000
    tl = r.tl
    total = tl.n / tl.fps
    buf = np.zeros(int(total * sr) + sr)
    import librosa
    orig, _ = librosa.load(str(r.base / r.edl["audio_src"]), sr=sr, mono=True)

    def put(sig, t, gain_db=0.0):
        a = int(t * sr)
        sig = sig[: max(0, len(buf) - a)]
        buf[a:a + len(sig)] += sig * 10 ** (gain_db / 20)

    live = np.zeros_like(buf)
    for sg in tl.segs:
        if sg["kind"] == "play" and sg["speed"] == 1 and "audio_db" in sg:
            a = int(sg["from"] / tl.fps * sr)
            seg = orig[a:a + int(sg["n"] / tl.fps * sr)].copy()
            fade = int(0.12 * sr)
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
            b = int(sg["start"] * sr)
            seg = seg[: len(live) - b]
            live[b:b + len(seg)] += seg * 10 ** (sg["audio_db"] / 20)
    uv = r.edl.get("under_vo")
    if uv:
        # 旁白期间原声让位：压低并削掉人声频段（转播解说），旁白前后各留一点过渡
        from scipy.signal import butter, sosfiltfilt
        speech = sosfiltfilt(butter(4, [250, 4000], "bandpass", fs=sr, output="sos"), live)
        under = (live - uv.get("carve", 0.75) * speech) * 10 ** (uv.get("db", -16) / 20)
        m = np.zeros_like(live)
        pre, post = uv.get("pad", [0.25, 0.35])
        for vid, (a, b) in tl.vo.items():
            m[max(0, int((a - pre) * sr)):int((b + uv.get("post", {}).get(vid, post)) * sr)] = 1.0
        k = int(0.25 * sr)
        c = np.concatenate([[0.0], np.cumsum(m)])
        j = np.arange(len(m)) + (k - 1) // 2
        m = (c[np.minimum(j + 1, len(m))] - c[np.clip(j + 1 - k, 0, len(m))]) / k
        live = live * (1 - m) + under * m
    buf += live
    for sg in tl.segs:
        if sg.get("sfx"):
            put(sfx(sg["sfx"]), sg["start"] - (0.05 if sg["sfx"] == "stop" else 0), -6)
        if sg.get("stop"):
            d = sg["n"] / tl.fps
            t = np.arange(int(d * sr)) / sr
            pad = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((98, 147, 196, 294))) / 4
            pad *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)) * np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.25)
            put(pad, sg["start"], -30)
    for ly in r.layers:
        if ly["type"] == "pop":
            put(sfx("pop"), r._src_time(ly["src_on"], ly["_on"]), -4)
        elif ly["type"] == "goal":
            put(sfx("boom"), r._src_time(ly["src_on"], ly["_on"]) - 0.02, -7)
        elif ly["type"] == "wave":
            put(sfx("wave"), ly["_on"], -9)
    bed = r.edl.get("bed", False)
    for vid, (a, b) in ([] if bed else tl.vo.items()):
        y, _ = librosa.load(str(tl.vo_dir / f"{vid}.wav"), sr=sr, mono=True)
        put(y, a, 0)
    buf = buf[: int((total + 0.1) * sr)]
    peak = np.abs(buf).max()
    if not bed:
        buf = buf / peak * 10 ** (-1.0 / 20)
    elif peak > 0.98:
        buf *= 0.98 / peak
    import soundfile as sf
    sf.write(str(out_wav), buf.astype(np.float32), sr)


def manifest(r: Renderer, out: Path):
    """成片时间线要用的清单：片段里每段、每句旁白的相对时刻（秒）。"""
    tl = r.tl
    d = {"duration": round(tl.n / tl.fps, 3), "fps": tl.fps,
         "segments": [{k: sg[k] for k in ("id", "kind", "start", "end") } | {"badge": sg.get("badge")} for sg in tl.segs],
         "vo": [{"id": vid, "t": round(a, 3), "end": round(b, 3)} for vid, (a, b) in tl.vo.items()]}
    out.write_text(json.dumps(d, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- 入口

_R: Renderer | None = None


def _init(path):
    global _R
    _R = Renderer(Path(path))


def _job(i):
    return _R.frame(i).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--preview")
    ap.add_argument("--sheet", type=float)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out")
    ap.add_argument("--range", help="只渲染这段输出帧 a,b（含声音），用于局部小样")
    ap.add_argument("--audio-only", action="store_true", help="画面不动，只重混声音并换进已有成片")
    a = ap.parse_args()
    edl = Path(a.edl).resolve()
    r = Renderer(edl)
    tl = r.tl
    print(f"{tl.n} 帧 / {tl.n / tl.fps:.2f} 秒")
    for sg in tl.segs:
        print(f"  {sg['id']:6s} {sg['kind']:7s} {sg['start']:6.2f}–{sg['end']:6.2f}s")
    for vid, (x, y) in tl.vo.items():
        print(f"  旁白 {vid:4s} {x:6.2f}–{y:6.2f}s")
    extra_masks(r)
    hq_masks(r)
    fx.ghost_prep(r)
    prev = r.work / "preview"
    if a.preview or a.sheet:
        prev.mkdir(exist_ok=True)
        idx = [int(x) for x in a.preview.split(",")] if a.preview else list(range(0, tl.n, int(a.sheet * tl.fps)))
        with ProcessPoolExecutor(min(a.workers, len(idx)), initializer=_init, initargs=(str(edl),)) as ex:
            frames = list(ex.map(_job, idx))
        tiles = []
        for i, b in zip(idx, frames):
            im = np.frombuffer(b, np.uint8).reshape(r.H, r.W, 3)
            cv2.imwrite(str(prev / f"{i:05d}.jpg"), cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
            t = cv2.resize(cv2.cvtColor(im, cv2.COLOR_RGB2BGR), (480, 270), interpolation=cv2.INTER_AREA)
            cv2.putText(t, f"{i} {i / tl.fps:.1f}s", (6, 262), 0, 0.6, (0, 255, 255), 2)
            tiles.append(t)
        if a.sheet:
            cols = 4
            rows = [np.hstack(tiles[k:k + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[k:k + cols])))
                    for k in range(0, len(tiles), cols)]
            cv2.imwrite(str(prev / "sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"预览 -> {prev}")
        return
    out = Path(a.out) if a.out else edl.parent / r.edl["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest(r, out.with_suffix(".json"))
    wav = out.with_suffix(".wav") if r.edl.get("bed") else r.work / "mix.wav"
    mix(r, wav)
    if a.audio_only:
        tmp = out.with_name(out.stem + "_a" + out.suffix)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(tmp)],
                       check=True)
        tmp.replace(out)
        print(f"-> {out}（只换声音）")
        return
    f0, f1 = (int(x) for x in a.range.split(",")) if a.range else (0, tl.n)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{r.W}x{r.H}",
           "-r", str(tl.fps), "-i", "-", "-ss", f"{f0 / tl.fps:.4f}", "-i", str(wav), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(r.edl.get("crf", 18)), "-maxrate", "40M", "-bufsize", "80M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(str(edl),)) as ex:
        for k, b in enumerate(ex.map(_job, range(f0, f1), chunksize=4)):
            ff.stdin.write(b)
            if k % 150 == 0:
                print(f"  {k}/{f1 - f0}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"-> {out}")


if __name__ == "__main__":
    main()
