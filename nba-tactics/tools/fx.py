"""render_play 的加强特效。只有 EDL 里写了对应的图层或开关才会启用，旧 EDL 照原样出片。

地板图层（画在地板上，被球员挡住）：
  {"type": "space", "gold": "KD", "label": "右侧空档", "anim": [a, b], "on": ..., "off": ...}
      空间控制图：每块地板归离它最近的球员，按队着色，gold 球员那块金色；anim 期间从 gold 球员向外铺开。
  {"type": "cone", "key": "TB", "to": "SG", "len": 14, "half": 24, "label": "只盯申京", "anim": [a, b], ...}
      防守视线锥：从 key 指向 to 的扇形，越远越淡。
  {"type": "wave", "key": "KD", "color": "gold", "on": t, "off": t + 时长}
      接球冲击波：on 时刻起两圈地板波纹向外扩散。
传球图层加 "flow": true：传球线带光晕，画线时有光点领头，画完后有流光沿线循环。
时停段加 "glow": true：背景压暗并虚化，重点球员上浮几像素、描一圈本队颜色的光。
  {"type": "goal", "src_on": 178, "on": ..., "off": ...}
      进球：篮筐爆闪、两圈光环、火花，画面轻震；pop 图层加 "fx": true 换成带光晕和回弹的大号得分。
"""
from __future__ import annotations

import cv2
import numpy as np

from court import device

HALF = np.float32([(0, -25), (47, -25), (47, 25), (0, 25)])   # 半场边线
CONE = (170, 225, 255)


def apply_h(Hm: np.ndarray, pts) -> np.ndarray:
    p = np.asarray(pts, np.float64).reshape(-1, 2)
    q = np.c_[p, np.ones(len(p))] @ Hm.T
    return q[:, :2] / q[:, 2:3]


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back_out(x: float, k: float = 2.2) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


# ---------------------------------------------------------------- 空间控制图

def space_cells(r, s: float):
    """每块地板归离它最近的球员（Voronoi），裁到半场内。返回 [(球员 key, 球场坐标多边形)]。"""
    keys = [k for k in r.P.d if r.P.uv(k, s) is not None]
    if len(keys) < 2:
        return []
    off = 200.0                                              # Subdiv2D 只收正坐标
    sub = cv2.Subdiv2D((0, 0, 2 * off, 2 * off))
    for k in keys:
        u, v = r.P.uv(k, s)
        sub.insert((float(np.clip(u, -150, 150) + off), float(np.clip(v, -150, 150) + off)))
    facets, centers = sub.getVoronoiFacetList([])
    out = []
    for fc, c in zip(facets, centers):
        u, v = c[0] - off, c[1] - off
        key = min(keys, key=lambda k: float(np.sum((r.P.uv(k, s) - (u, v)) ** 2)))
        _, poly = cv2.intersectConvexConvex(np.float32(fc - off), HALF)
        if poly is not None and len(poly) >= 3:
            out.append((key, poly.reshape(-1, 2)))
    return out


def draw_space(r, cv, proj, ly, s, T, al):
    from render_play import COL, TEAM
    gold = ly.get("gold")
    g = r.P.uv(gold, s) if gold else None
    p = r.anim(ly, T) if "_anim" in ly else 1.0
    cells = space_cells(r, s)
    for kk, poly in cells:
        f = 1.0 if g is None else float(np.clip((p * 75 - np.linalg.norm(poly.mean(0) - g)) / 10, 0, 1))
        col = COL["gold"] if kk == gold else TEAM[r.P.d[kk]["team"]]
        cv.fill(proj(poly), col, al * f * (0.40 if kk == gold else 0.24))
    for kk, poly in cells:
        f = 1.0 if g is None else float(np.clip((p * 75 - np.linalg.norm(poly.mean(0) - g)) / 10, 0, 1))
        cv.line(proj(poly), (255, 255, 255), 2 * proj.k + 1, al * f * 0.5, closed=True)
    for kk, poly in cells:
        if kk == gold:
            cv.line(proj(poly), COL["gold"], 5 * proj.k, al * ease((p - 0.5) / 0.5), closed=True)


def space_label(r, ly, s):
    gold = ly.get("gold")
    for kk, poly in space_cells(r, s):
        if kk == gold:
            pi = r.cam.to_img(s, poly).astype(np.float32)
            scr = np.float32([(80, 80), (r.W - 80, 80), (r.W - 80, r.H - 220), (80, r.H - 220)])
            area, cut = cv2.intersectConvexConvex(pi, scr)   # 格子常延伸到画外，标签放在画面内那部分的重心
            if area > 1 and cut is not None:
                mo = cv2.moments(cut.reshape(-1, 2))
                return (np.array([mo["m10"] / mo["m00"], mo["m01"] / mo["m00"]]), ly["label"], "gold")
            return (r.cam.to_img(s, [poly.mean(0)])[0], ly["label"], "gold")
    return None


# ---------------------------------------------------------------- 视线锥

def cone_poly(r, ly, s, T, frac=1.0):
    A, B = r.P.uv(ly["key"], s), r.P.uv(ly["to"], s)
    if A is None or B is None:
        return None, None
    d = (B - A) / (np.linalg.norm(B - A) + 1e-6)
    p = r.anim(ly, T) if "_anim" in ly else 1.0
    L = ly.get("len", 14) * ease_out(p) * frac
    h = np.radians(ly.get("half", 24))
    a0 = np.arctan2(d[1], d[0])
    ang = np.linspace(a0 - h, a0 + h, 28)
    return A, np.vstack([A, A + L * np.c_[np.cos(ang), np.sin(ang)]])


def draw_cone(r, cv, proj, ly, s, T, al, board=False):
    A, poly = cone_poly(r, ly, s, T)
    if poly is None:
        return
    for frac, a in ((1.0, 0.16), (0.78, 0.24), (0.56, 0.33), (0.34, 0.42)):
        _, pp = cone_poly(r, ly, s, T, frac)
        cv.fill(proj(pp), CONE, al * a * (1.4 if board else 1.0))
    if not board:
        cv.line(proj(np.vstack([poly[1], A, poly[-1]])), CONE, 3 * proj.k + 1, al * 0.95)
        cv.line(proj(poly[1:]), CONE, 4 * proj.k + 1, al * 0.75)


def cone_label(r, ly, s, T):
    A, poly = cone_poly(r, ly, s, T)
    if poly is None or r.anim(ly, T) < 0.9:
        return None
    return (r.cam.to_img(s, [poly[1:].mean(0)])[0], ly["label"], "blue")


# ---------------------------------------------------------------- 冲击波和流光

def draw_wave(r, cv, proj, ly, s, T):
    from render_play import COL
    u = r.P.uv(ly["key"], s)
    if u is None:
        return
    dur = ly["_off"] - ly["_on"]
    col = COL[ly.get("color", "gold")]
    for n, delay in enumerate((0.0, 0.16)):
        q = (T - ly["_on"] - delay) / (dur - 0.16)
        if not 0 <= q <= 1:
            continue
        rr = 1.2 + ly.get("r", 8.5) * ease_out(q)
        if n == 0:
            cv.fill(proj.circle(u, rr, 72), col, 0.20 * (1 - q))
        cv.line(proj.circle(u, rr, 72), col, (7 * (1 - q) + 2) * proj.k, (1 - q) ** 1.3, closed=True)


def flow_under(cv, pts, col, k, al):
    """传球线下面的光晕。"""
    cv.line(pts, col, 22 * k + 6, al * 0.14)
    cv.line(pts, col, 12 * k + 3, al * 0.22)


def flow_over(cv, pts, col, k, al, T, p):
    """画线时的领头光点；画完后沿线循环的流光。"""
    if len(pts) < 2:
        return
    if p < 0.999:
        cv.disc(pts[-1], 24 * k + 6, col, al * 0.35)
        cv.disc(pts[-1], 11 * k + 3, (255, 255, 255), al * 0.95)
        return
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] < 10:
        return
    ph = (T * 0.75) % 1.0 * 1.3
    t1, t0 = ph * cum[-1], (ph - 0.22) * cum[-1]
    ts = np.linspace(max(0, t0), min(cum[-1], t1), 24)
    if ts[-1] - ts[0] < 4:
        return
    sub = np.c_[np.interp(ts, cum, pts[:, 0]), np.interp(ts, cum, pts[:, 1])]
    for i in range(1, len(sub)):
        a = i / len(sub)
        cv.line(sub[i - 1:i + 1], (255, 255, 255), (2 + 5 * a) * k + 1, al * 0.9 * a)


# ---------------------------------------------------------------- 时停：浮起和发光

def glow_freeze(r, img, sg, s, stop):
    from render_play import COL, TEAM
    H, W = img.shape[:2]
    keys = sg["spot"]
    g = img @ np.array([0.3, 0.59, 0.11], np.float32)
    bg = (g[..., None] * 0.40) * np.array([0.82, 0.92, 1.18], np.float32)
    bg = cv2.GaussianBlur(bg, (0, 0), 1 + 5 * stop)
    spot0 = r.M.of(keys, s, img.shape, feather=2.5)
    bg *= 1.0 - 0.6 * spot0[..., None]                       # 原位置留一道影子，人看起来浮起来了
    L = 9.0 * stop
    sh = np.float32([[1, 0, 0], [0, 1, -L]])
    fg = cv2.warpAffine(np.clip(img * 1.08, 0, 255), sh, (W, H), borderMode=cv2.BORDER_REPLICATE)
    spot1 = cv2.warpAffine(spot0, sh, (W, H))
    ts = bg * (1 - spot1[..., None]) + fg * spot1[..., None]
    for k in keys:
        m = cv2.warpAffine(r.M.of([k], s, img.shape, feather=0), sh, (W, H))
        ys, xs = np.nonzero(m > 0.5)
        if not len(xs):
            continue
        x1, y1 = max(0, xs.min() - 40), max(0, ys.min() - 40)
        x2, y2 = min(W, xs.max() + 41), min(H, ys.max() + 41)
        mc = m[y1:y2, x1:x2]
        sty = r.edl["style"][k]
        col = np.array(COL[sty] if sty in ("gold", "orange") else COL["blue"] if r.P.d[k]["team"] == "DAL"
                       else (255, 255, 255), np.float32)
        halo = cv2.GaussianBlur(cv2.dilate(mc, np.ones((7, 7), np.uint8)), (0, 0), 9)
        halo = np.clip(halo * 1.5, 0, 1) * (1 - mc)
        edge = np.clip(cv2.dilate(mc, np.ones((5, 5), np.uint8)) - mc, 0, 1)
        a = (np.maximum(halo * 0.75, edge * 0.95) * stop)[..., None]
        ts[y1:y2, x1:x2] = ts[y1:y2, x1:x2] * (1 - a) + col * a
    return img * (1 - stop) + ts * stop


# ---------------------------------------------------------------- 残影

def ghost_box(r, k, f):
    """SAM 提示框：有跟踪框用跟踪框，人工补点的帧用脚底点和身高推一个。"""
    b = r.P.box(k, f, near=0)
    if b is not None:
        return np.asarray(b, float)
    u = r.P.uv(k, f)
    if u is None:
        return None
    x, y = r.cam.to_img(f, [u])[0]
    h = r.P.height(k, f)
    return np.array([x - 0.3 * h, y - 1.04 * h, x + 0.3 * h, y + 8])


def ghost_prep(r) -> None:
    """残影要用的轮廓：每个 ghost 图层按 step 取帧，SAM2 抠出该球员，存 masks_ghost/。"""
    lys = [ly for ly in r.layers if ly["type"] == "ghost"]
    if not lys:
        return
    out = r.work / "masks_ghost"
    need = []
    for ly in lys:
        for f in range(ly["from"], ly["to"] + 1, ly.get("step", 4)):
            if not (out / f"{f:04d}_{ly['key']}.npz").exists():
                need.append((f, ly["key"]))
    if not need:
        return
    from ultralytics import SAM
    model = SAM(str(r.work.parent / "sam2.1_l.pt"))
    out.mkdir(exist_ok=True)
    hand = {(int(f), ly["key"]): v for ly in lys for f, v in ly.get("prompt", {}).items()}
    for f, k in need:
        h = hand.get((f, k), {})
        b = np.asarray(h["box"], float) if "box" in h else ghost_box(r, k, f)
        if b is None:
            continue
        img = cv2.imread(str(r.base / r.edl["orig"] / f"{f:04d}.jpg"))
        kw = {"bboxes": [list(map(float, b))]}
        if h.get("pos") or h.get("neg"):              # 两人重叠时框不够，用正/负点指认
            pts = [*h.get("pos", []), *h.get("neg", [])]
            kw = {"points": [pts], "labels": [[1] * len(h.get("pos", [])) + [0] * len(h.get("neg", []))]}
        m = (model(img, **kw, verbose=False, device=device())[0].masks.data[0].cpu().numpy() > 0.5)
        x1, y1, x2, y2 = b.astype(int)
        m[:max(0, y1)], m[y2 + 1:], m[:, :max(0, x1)], m[:, x2 + 1:] = 0, 0, 0, 0
        m = m.astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if n > 2:
            m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
        ys, xs = np.nonzero(m)
        if len(xs):
            np.savez_compressed(out / f"{f:04d}_{k}.npz", xy=np.array([xs.min(), ys.min()]),
                                m=m[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
    print(f"  残影轮廓 {len(need)} 帧 -> {out}")


_SRC: dict = {}


def _orig(r, f):
    if f not in _SRC:
        if len(_SRC) > 12:
            _SRC.clear()
        _SRC[f] = cv2.cvtColor(cv2.imread(str(r.base / r.edl["orig"] / f"{f:04d}.jpg")), cv2.COLOR_BGR2RGB).astype(np.float32)
    return _SRC[f]


def draw_ghost(r, img, ly, s, al, lift=0.0):
    """球员身后的残影：往前取几张轮廓，按镜头运动对齐到当前帧，越旧越淡，染成本队强调色；不盖住当前的人。"""
    from render_play import COL
    H, W = img.shape[:2]
    k, step, n = ly["key"], ly.get("step", 4), ly.get("n", 6)
    col = np.array(COL[r.edl["style"][k]] if r.edl["style"][k] in COL else COL["gold"], np.float32)
    cur = r.M.of([k], s, img.shape, feather=0)
    if lift:
        cur = cv2.warpAffine(cur, np.float32([[1, 0, 0], [0, 1, -lift]]), (W, H))
    cur = cv2.GaussianBlur(cv2.dilate(cur, np.ones((9, 9), np.uint8)), (0, 0), 2)
    c2i = np.linalg.inv(r.cam._H(r.cam.court, s))
    layer = np.zeros_like(img)
    acc = np.zeros((H, W), np.float32)
    fs = [f for f in range(ly["from"], ly["to"] + 1, step) if s - step * (n + 0.5) <= f <= s - 1.5]
    for f in sorted(fs):                                      # 旧的先画，新的盖在上面
        p = r.work / "masks_ghost" / f"{f:04d}_{k}.npz"
        if not p.exists():
            continue
        e = np.load(p)
        (x1, y1), mm = e["xy"], e["m"].astype(np.float32)
        m = np.zeros((H, W), np.float32)
        m[y1:y1 + mm.shape[0], x1:x1 + mm.shape[1]] = mm
        Hm = c2i @ r.cam._H(r.cam.court, f)
        m = cv2.GaussianBlur(cv2.warpPerspective(m, Hm, (W, H)), (0, 0), 1.2)
        src = cv2.warpPerspective(_orig(r, f), Hm, (W, H))
        age = (s - f) / (step * (n + 0.5))
        a = m * (0.85 * (1 - age) ** 1.1)
        tint = np.clip(src * 0.3 + col * 0.8, 0, 255)
        edge = np.clip(cv2.dilate(m, np.ones((3, 3), np.uint8)) - cv2.erode(m, np.ones((3, 3), np.uint8)), 0, 1)
        tint = tint * (1 - edge[..., None]) + 255 * edge[..., None]
        layer = layer * (1 - a[..., None]) + tint * a[..., None]
        acc = acc + a * (1 - acc)
    keep = ((1 - cur) * al)[..., None]                       # layer 是叠在黑底上的预乘色，acc 是累计覆盖
    return img * (1 - acc[..., None] * keep) + layer * keep


# ---------------------------------------------------------------- 进球

def goal_age(r, ly, T):
    return T - r._src_time(ly["src_on"], ly["_on"])


def goal_burst(img, rim, age):
    """篮筐处的爆闪、光环和火花（推镜之前画，跟着画面一起缩放）。"""
    from render_play import Canvas, COL
    H, W = img.shape[:2]
    if age < 0 or age > 1.3:
        return img
    x, y = float(rim[0]), float(rim[1])
    # 爆闪：以篮筐为中心的径向光，叠加
    R = 60 + 260 * ease_out(age / 0.5)
    k = max(0.0, 1 - age / 0.55) ** 1.5
    if k > 0:
        x1, y1, x2, y2 = int(max(0, x - 2 * R)), int(max(0, y - 2 * R)), int(min(W, x + 2 * R)), int(min(H, y + 2 * R))
        if x2 > x1 and y2 > y1:
            yy, xx = np.mgrid[y1:y2, x1:x2].astype(np.float32)
            d2 = ((xx - x) ** 2 + ((yy - y) * 1.6) ** 2) / (R * R)
            glow = np.exp(-d2 * 2.2)[..., None] * k
            img[y1:y2, x1:x2] += glow * np.array([255, 205, 90], np.float32) * 0.9
    # 整屏一闪
    f = 0.22 * max(0.0, 1 - age / 0.16)
    if f > 0:
        img = img * (1 - f) + 255 * f
    cv = Canvas(H, W)
    for n, delay in enumerate((0.0, 0.12)):
        q = (age - delay) / 0.65
        if 0 <= q <= 1:
            rr = 24 + 300 * ease_out(q)
            a = np.linspace(0, 2 * np.pi, 96)
            pts = np.c_[x + rr * np.cos(a), y + rr * 0.42 * np.sin(a)]
            cv.line(pts, COL["gold"] if n == 0 else (255, 255, 255), 10 * (1 - q) + 2, (1 - q) ** 1.2, closed=True)
    rng = np.random.default_rng(11)
    n = 54
    ang = rng.uniform(-np.pi * 0.95, -np.pi * 0.05, n)      # 主要往上和两侧溅
    spd = rng.uniform(380, 1050, n)
    life = rng.uniform(0.55, 1.05, n)
    grav = 1500.0
    for i in range(n):
        if age > life[i]:
            continue
        v = spd[i] * np.array([np.cos(ang[i]), np.sin(ang[i])])

        def pos(t):
            return np.array([x, y]) + v * t + np.array([0, 0.5 * grav * t * t])
        t0 = max(0.0, age - 0.045)
        q = age / life[i]
        cv.line([pos(t0), pos(age)], COL["gold"] if i % 3 else (255, 255, 255), 4 * (1 - q) + 1.5, (1 - q) ** 1.1)
    return cv.composite(img)


def shake(age):
    """进球后的画面轻震：返回 (x 偏移, y 偏移, 放大倍率)；放大用来盖住偏移露出的边。"""
    if age < 0 or age > 0.6:
        return 0.0, 0.0, 1.0
    a = np.exp(-age * 7.5)
    return 15 * a * np.sin(age * 2 * np.pi * 13), 9 * a * np.cos(age * 2 * np.pi * 11), 1 + 0.03 * a


def score_pop(pil, xy, text, age, al, font):
    """带光晕和回弹的大号得分。"""
    from PIL import Image, ImageDraw, ImageFilter
    sc = max(0.05, back_out(age / 0.38))
    size = int(200 * sc)
    x, y = float(xy[0]), float(xy[1]) - 30 * ease(age / 1.2)
    f = font(size, "num")
    w = int(size * 2.6)
    h = int(size * 1.8)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((w / 2, h / 2), text, font=f, fill=(255, 190, 40, int(230 * al)), anchor="mm",
                             stroke_width=10, stroke_fill=(255, 150, 20, int(200 * al)))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.12))
    gx, gy = int(x - w / 2), int(y - h / 2)
    glow = glow.crop((max(0, -gx), max(0, -gy), w, h))
    pil.alpha_composite(glow, (max(0, gx), max(0, gy)))
    dr = ImageDraw.Draw(pil)
    dr.text((x, y), text, font=f, fill=(255, 232, 140, int(255 * al)), anchor="mm",
            stroke_width=9, stroke_fill=(110, 50, 0, int(235 * al)))
