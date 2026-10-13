"""代码画面组件。

场景（整帧）：scene_<名字>(ctx, **参数) → HxWx3 float32 [0,1]
叠层：overlay_<名字>(ctx, **参数) → HxWx4 float32（预乘前的 RGBA）
ctx: t 镜头内时间，d 镜头时长，T 歌曲时间，beats 全曲拍点（秒），env(T) 音量包络 0–1，seed
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FONTS = {
    "maru": "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
    "mincho": "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
    "futura": "/System/Library/Fonts/Supplemental/Futura.ttc",
    "bodoni": "/System/Library/Fonts/Supplemental/Bodoni 72.ttc",
    "script": "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc",
    "din": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "osd": "/System/Library/Fonts/Supplemental/Silom.ttf",
}
NAVY, PINK, CYAN, GOLD = (14, 18, 52), (255, 79, 163), (62, 230, 255), (255, 204, 92)


@lru_cache(None)
def font(name, size, index=0):
    return ImageFont.truetype(FONTS[name], size, index=index)


def rgb(im):
    return np.asarray(im.convert("RGB"), np.float32) / 255


def rgba(im):
    return np.asarray(im, np.float32) / 255


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def blank(color=(0, 0, 0), mode="RGB"):
    return Image.new(mode, (W, H), color)


def gradient(top, bottom):
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) / 255 * (1 - y) + np.array(bottom, np.float32) / 255 * y
    return np.broadcast_to(g, (H, W, 3)).copy()


def text_c(d, xy, s, f, fill, stroke=0, sfill=(0, 0, 0), anchor="mm"):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)


def glow(lay, r=12, k=1.6):
    """霓虹辉光：把 RGBA 层模糊后叠回去。"""
    g = lay.filter(ImageFilter.GaussianBlur(r))
    a = np.asarray(g, np.float32)
    a[..., 3] = np.clip(a[..., 3] * k, 0, 255)
    return Image.alpha_composite(Image.fromarray(a.astype(np.uint8)), lay)


def beats_between(ctx, a, b):
    return [x for x in ctx.beats if a <= x < b]


# ---------------------------------------------------------------- 场景

def scene_snow(ctx, amount=1.0):
    rng = np.random.default_rng(ctx.seed)
    n = rng.random((H // 2, W // 2), dtype=np.float32) * amount
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)
    return np.repeat(n[..., None], 3, 2) * 0.8


def scene_black(ctx):
    return np.zeros((H, W, 3), np.float32)


@lru_cache(None)
def _skyline_layout(seed=7):
    rng = np.random.default_rng(seed)
    blds, x = [], -20
    while x < W + 20:
        w = int(rng.integers(70, 190))
        h = int(rng.integers(220, 640))
        if abs(x + w / 2 - W * 0.62) < 140:
            h = int(rng.integers(160, 300))
        blds.append((x, H - h, w, h, int(rng.integers(0, 3))))
        x += w + int(rng.integers(-10, 14))
    order = rng.permutation(len(blds))
    return blds, order


def scene_skyline(ctx):
    """霓虹天际线：楼按拍一栋栋亮起，东京塔最后亮。"""
    sky = gradient((8, 10, 34), (52, 22, 74))
    im = Image.fromarray((sky * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(3)
    for _ in range(160):
        x, y = rng.integers(0, W), rng.integers(0, H // 2)
        b = int(rng.integers(90, 220))
        d.point((int(x), int(y)), fill=(b, b, b))
    blds, order = _skyline_layout()
    bt = beats_between(ctx, ctx.T - ctx.t, ctx.T - ctx.t + ctx.d)
    n_lit = sum(1 for b in bt if b <= ctx.T) * 3
    tower_on = ctx.t > ctx.d - 0.9
    tx, ty = int(W * 0.62), 300
    neon = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dn = ImageDraw.Draw(neon)
    cols = [PINK, CYAN, (255, 170, 60)]
    for k, (x, y, w, h, c) in enumerate(blds):
        lit = np.where(order == k)[0][0] < n_lit
        d.rectangle([x, y, x + w, H], fill=(18, 16, 40) if not lit else (30, 24, 62))
        if lit:
            wr = np.random.default_rng(k)
            for wy in range(y + 18, H - 10, 26):
                for wx in range(x + 10, x + w - 14, 22):
                    if wr.random() < 0.55:
                        d.rectangle([wx, wy, wx + 10, wy + 12], fill=(255, 226, 150))
            dn.rectangle([x + 4, y + 4, x + w - 4, y + 10], fill=cols[c] + (255,))
            if w > 110:
                dn.rectangle([x + w // 2 - 6, y + 30, x + w // 2 + 6, y + 30 + min(200, h // 2)], fill=cols[(c + 1) % 3] + (255,))
    tc = (255, 120, 40, 255) if tower_on else (60, 40, 50, 255)
    tl = neon if tower_on else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tl)
    base_w = 230
    for k in range(18):
        f0, f1 = k / 18, (k + 1) / 18
        y0, y1 = H - (H - ty) * f0, H - (H - ty) * f1
        w0, w1 = base_w * (1 - f0) ** 1.6 + 6, base_w * (1 - f1) ** 1.6 + 6
        dt.line([(tx - w0, y0), (tx - w1, y1)], fill=tc, width=5)
        dt.line([(tx + w0, y0), (tx + w1, y1)], fill=tc, width=5)
        dt.line([(tx - w0, y0), (tx + w1, y1)], fill=tc, width=2)
        dt.line([(tx + w0, y0), (tx - w1, y1)], fill=tc, width=2)
    dt.line([(tx, ty), (tx, ty - 90)], fill=tc, width=5)
    for fy in (0.35, 0.62):
        y = H - (H - ty) * fy
        ww = base_w * (1 - fy) ** 1.6 + 6
        dt.rectangle([tx - ww - 14, y - 10, tx + ww + 14, y + 6], fill=tc)
    if not tower_on:
        im = Image.alpha_composite(im, tl)
    im = Image.alpha_composite(im, glow(neon, 14, 1.8))
    return rgb(im)


def scene_image(ctx, path, zoom=(1.0, 1.08), pan=(0, 0)):
    """静图慢推。"""
    im = _load(path)
    z = zoom[0] + (zoom[1] - zoom[0]) * ctx.t / max(ctx.d, 1e-3)
    return _crop_zoom(im, z, pan)


@lru_cache(8)
def _load(path):
    im = Image.open(path).convert("RGB")
    s = max(W / im.width, H / im.height)
    return im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)


def _crop_zoom(im, z, pan=(0, 0)):
    cw, ch = W / z, H / z
    cx = im.width / 2 + pan[0] * (im.width - cw) / 2
    cy = im.height / 2 + pan[1] * (im.height - ch) / 2
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return rgb(im.resize((W, H), Image.BILINEAR, box=box))


def scene_title(ctx, path):
    """片名卡：City Pop 唱片封面式排版。"""
    base = scene_image(ctx, path, zoom=(1.06, 1.0)) * 0.82
    im = Image.fromarray((base * 255).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    p = ease_out(ctx.t / 0.6)
    d.rectangle([140, 140, W - 140, H - 140], outline=(255, 255, 255, int(220 * p)), width=3)
    f1 = font("bodoni", 260)
    text_c(d, (W // 2, H // 2 - 70), "BABY", f1, (255, 255, 255, int(255 * p)))
    f2 = font("script", 120)
    q = ease_out((ctx.t - 0.5) / 0.7)
    text_c(d, (W // 2 + 60, H // 2 + 150), "Tokyo 1989", f2, PINK + (int(255 * q),), stroke=5, sfill=(28, 18, 64, int(255 * q)))
    f3 = font("futura", 40)
    text_c(d, (W // 2, H - 200), "M I N A", f3, (255, 255, 255, int(240 * q)), stroke=3, sfill=(28, 18, 64, int(220 * q)))
    im = Image.alpha_composite(im, glow(lay, 10, 1.0))
    return rgb(im)


def scene_mirrorball(ctx, speed=1.0, warm=False, cx=None, cy=None, r=300):
    """镜球：经纬网格的镜面小方块，旋转时闪烁；光斑扫过全屏。"""
    bg = gradient((10, 8, 30), (36, 14, 54)) if not warm else gradient((36, 16, 20), (70, 30, 30))
    im = Image.fromarray((bg * 255).astype(np.uint8)).convert("RGBA")
    ang = ctx.T * speed * 1.2
    cx, cy = cx or W // 2, cy or H // 2 - 40
    spots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(spots)
    rng = np.random.default_rng(11)
    pal = [(255, 255, 255), PINK, CYAN, GOLD] if not warm else [(255, 220, 160), (255, 170, 90), (255, 240, 210)]
    for k in range(70):
        ph, el = rng.uniform(0, 2 * math.pi), rng.uniform(-1, 1)
        x = (((ph + ang) % (2 * math.pi)) / (2 * math.pi)) * (W + 400) - 200
        y = H / 2 + el * H * 0.6
        s = rng.uniform(6, 16)
        c = pal[k % len(pal)]
        ds.ellipse([x - s, y - s * 0.7, x + s, y + s * 0.7], fill=c + (200,))
    im = Image.alpha_composite(im, spots.filter(ImageFilter.GaussianBlur(2.5)))
    ball = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(ball)
    db.line([(cx, 0), (cx, cy - r)], fill=(160, 160, 170, 255), width=4)
    nl, nm = 16, 32
    fr = np.random.default_rng(5).random((nl, nm))
    for i in range(nl):
        la0, la1 = -math.pi / 2 + math.pi * i / nl, -math.pi / 2 + math.pi * (i + 1) / nl
        for j in range(nm):
            lo0 = 2 * math.pi * j / nm + ang
            lo1 = lo0 + 2 * math.pi / nm
            pts, zs = [], []
            for la, lo in ((la0, lo0), (la0, lo1), (la1, lo1), (la1, lo0)):
                x, y, z = math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)
                pts.append((cx + x * r, cy + y * r))
                zs.append(z)
            if sum(zs) <= 0:
                continue
            z = sum(zs) / 4
            sparkle = (math.sin(lo0 * 3 + fr[i, j] * 20 + ctx.T * 6) + 1) / 2
            b = 0.25 + 0.45 * z + (0.6 * sparkle ** 8)
            c = tuple(int(clamp(b * v / 255) * 255) for v in ((230, 230, 245) if not warm else (255, 225, 190)))
            db.polygon(pts, fill=c + (255,), outline=(40, 40, 60, 255))
    im = Image.alpha_composite(im, glow(ball, 18, 0.9))
    return rgb(im)


def scene_nikkei(ctx):
    """日经平均：曲线一路冲出画面顶部，数字滚到 38,915.87。"""
    bg = gradient((10, 30, 90), (4, 10, 40))
    im = Image.fromarray((bg * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 200, W - 160, H - 220, 120
    for k in range(6):
        y = y0 - (y0 - y1) * k / 5
        d.line([(x0, y), (x1, y)], fill=(70, 100, 170), width=1)
        d.text((x0 - 20, y), f"{10000 + k * 5000:,}", font=font("din", 34), fill=(150, 180, 230), anchor="rm")
    for k, yr in enumerate(range(1985, 1990)):
        x = x0 + (x1 - x0) * (k + 0.5) / 5
        d.text((x, y0 + 40), str(yr), font=font("din", 38), fill=(150, 180, 230), anchor="mm")
    n = 240
    u = np.linspace(0, 1, n)
    val = 12500 + 26400 * u ** 1.5 + 1500 * np.sin(u * 18) * u - 4000 * np.exp(-((u - 0.55) / 0.03) ** 2)
    val[-1] = 38915.87
    p = ease_out(ctx.t / (ctx.d * 0.8))
    m = max(2, int(n * p))
    vmax_screen = 34000
    pts = [(x0 + (x1 - x0) * u[i], y0 - (y0 - y1) * (val[i] - 10000) / (vmax_screen - 10000)) for i in range(m)]
    line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(line).line(pts, fill=(255, 220, 60, 255), width=8, joint="curve")
    im = Image.alpha_composite(im, glow(line, 10, 1.4))
    d = ImageDraw.Draw(im)
    v = val[m - 1]
    d.rectangle([0, H - 150, W, H], fill=(0, 0, 0, 255))
    d.text((80, H - 75), "日経平均株価", font=font("maru", 54), fill=(255, 255, 255), anchor="lm")
    d.text((W - 80, H - 75), "円", font=font("maru", 70), fill=(255, 226, 64), anchor="rm")
    d.text((W - 160, H - 75), f"{v:,.2f}", font=font("din", 120), fill=(255, 226, 64), anchor="rm")
    if ctx.t > ctx.d * 0.8:
        d.rectangle([W - 560, 40, W - 60, 120], fill=(200, 20, 40))
        d.text((W - 310, 80), "1989.12.29 終値", font=font("maru", 48), fill=(255, 255, 255), anchor="mm")
    return rgb(im)


def scene_ledger(ctx):
    """酒店预约台帐：12/24 的「満室」印章一个接一个盖满屏幕（虚构酒店）。"""
    paper = gradient((246, 238, 220), (232, 222, 200))
    im = Image.fromarray((paper * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.text((W // 2, 80), "ホテル・ミラージュ東京　ご予約台帳　1989年12月", font=font("mincho", 52), fill=(60, 40, 30), anchor="mm")
    for k in range(13):
        y = 160 + k * 70
        d.line([(120, y), (W - 120, y)], fill=(170, 150, 130), width=2)
        d.text((150, y + 35), "12/24（日）", font=font("mincho", 38), fill=(60, 40, 30), anchor="lm")
        d.text((560, y + 35), f"スイート {k + 1:02d}　様　2名", font=font("mincho", 38), fill=(90, 70, 60), anchor="lm")
    bt = beats_between(ctx, ctx.T - ctx.t, ctx.T)
    rng = np.random.default_rng(4)
    for k, b in enumerate(bt):
        x, y = rng.uniform(260, W - 260), rng.uniform(220, H - 160)
        a = rng.uniform(-18, 18)
        age = ctx.T - b
        s = 1.6 - 0.6 * ease_out(age / 0.12)
        st = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
        ds = ImageDraw.Draw(st)
        ds.rounded_rectangle([40, 110, 380, 310], radius=24, outline=(200, 30, 40, 235), width=14)
        ds.text((210, 210), "満室", font=font("mincho", 150), fill=(200, 30, 40, 235), anchor="mm")
        st = st.rotate(a, resample=Image.BICUBIC).resize((int(420 * s), int(420 * s)), Image.BICUBIC)
        im.alpha_composite(st, (int(x - st.width / 2), int(y - st.height / 2)))
    return rgb(im)


def scene_board(ctx, rows=None):
    """车站发车牌（翻牌式）。"""
    rows = rows or [("とき", "苗場 SKI 号", "越後湯沢", " 7:12", "20"),
                    ("あさひ", "シュプール 号", "越後湯沢", " 7:36", "21"),
                    ("とき", "苗場 SKI 号", "越後湯沢", " 8:00", "20")]
    im = blank((20, 20, 24)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle([80, 120, W - 80, H - 120], fill=(8, 8, 10), outline=(90, 90, 100), width=6)
    heads = ["種別", "列車名", "行先", "発車", "番線"]
    xs = [180, 480, 1050, 1440, 1700]
    for x, h in zip(xs, heads):
        d.text((x, 190), h, font=font("maru", 46), fill=(170, 170, 180), anchor="lm")
    pool = "アイウエオカキクケコサシスセソ0123456789"
    rng = np.random.default_rng(int(ctx.T * 30))
    for r, row in enumerate(rows):
        y = 330 + r * 190
        for c, (x, s) in enumerate(zip(xs, row)):
            settle = 0.25 + 0.12 * c + 0.18 * r
            out = s if ctx.t > settle else "".join(pool[rng.integers(len(pool))] if ch != " " else " " for ch in s)
            col = (255, 150, 40) if c == 0 else (255, 255, 255)
            d.text((x, y), out, font=font("maru", 78), fill=col, anchor="lm")
        d.line([(120, y + 80), (W - 120, y + 80)], fill=(40, 40, 50), width=3)
    return rgb(im)


def scene_boombox(ctx):
    """复古收录机：音量旋钮拧到 MAX，电平表顶满，喇叭跟着鼓点鼓动。"""
    bg = gradient((60, 20, 80), (255, 110, 160))
    im = Image.fromarray((bg * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    e = ctx.env(ctx.T)
    bx0, by0, bx1, by1 = 260, 260, W - 260, 900
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=60, fill=(196, 198, 206), outline=(90, 92, 100), width=8)
    d.rounded_rectangle([bx0 + 380, by0 - 90, bx1 - 380, by0 + 10], radius=30, outline=(120, 122, 130), width=18)
    for cx in (bx0 + 250, bx1 - 250):
        R = 190 + 16 * e
        d.ellipse([cx - 210, 600 - 210, cx + 210, 600 + 210], fill=(50, 50, 56))
        d.ellipse([cx - R, 600 - R, cx + R, 600 + R], fill=(28, 28, 32))
        d.ellipse([cx - R * 0.35, 600 - R * 0.35, cx + R * 0.35, 600 + R * 0.35], fill=(90, 90, 100))
    mx = W // 2
    d.rounded_rectangle([mx - 230, 470, mx + 230, 720], radius=14, fill=(30, 30, 36))
    d.rectangle([mx - 160, 540, mx + 160, 650], fill=(240, 236, 220))
    d.text((mx, 595), "C-60  CITY POP MIX", font=font("futura", 30), fill=(60, 60, 70), anchor="mm")
    for k, side in enumerate((-1, 1)):
        x0 = mx + side * 40 - (160 if side < 0 else 0)
        lv = clamp(e * 1.15 + 0.12 * math.sin(ctx.T * 23 + k))
        for s in range(12):
            on = s / 12 < lv
            col = (255, 60, 60) if s >= 9 else (255, 220, 60) if s >= 6 else (80, 255, 120)
            d.rectangle([x0 + s * 13, 330, x0 + s * 13 + 9, 400], fill=col if on else (60, 60, 64))
    p = ease_out(ctx.t / (ctx.d * 0.7))
    kx, ky = mx + 330, 360
    d.ellipse([kx - 60, ky - 60, kx + 60, ky + 60], fill=(70, 70, 78), outline=(30, 30, 30), width=4)
    a = math.radians(-225 + 270 * p)
    d.line([(kx, ky), (kx + 50 * math.cos(a), ky + 50 * math.sin(a))], fill=(255, 255, 255), width=8)
    d.text((kx + 90, ky + 50), "MAX", font=font("futura", 40), fill=(255, 60, 60) if p > 0.95 else (120, 120, 130), anchor="lm")
    d.text((mx - 330, 365), "VOLUME", font=font("futura", 36), fill=(60, 60, 70), anchor="mm")
    return rgb(im)


def scene_bubbles(ctx, textures, base=None, n=7, seed=2):
    """肥皂泡缓缓上升，每个泡泡表面映着一段前面出现过的画面。"""
    bg = base if base is not None else gradient((20, 16, 60), (120, 70, 140))
    im = Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    rng = np.random.default_rng(seed)
    for k in range(n):
        R = rng.uniform(120, 260)
        x = rng.uniform(R, W - R) + 40 * math.sin(ctx.T * 0.8 + k)
        speed = rng.uniform(90, 160)
        y = H + R - ((ctx.t + rng.uniform(0, 6)) * speed) % (H + 2 * R)
        tex = textures[k % len(textures)]
        im.alpha_composite(_bubble(tex, int(R), ctx.T + k), (int(x - R), int(y - R)))
    return rgb(im)


def _bubble(tex, R, phase):
    S = 2 * R
    t = Image.fromarray((np.clip(tex, 0, 1) * 255).astype(np.uint8)).resize((S, S), Image.BILINEAR)
    yy, xx = np.mgrid[-1:1:S * 1j, -1:1:S * 1j]
    rr = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip((1 - rr) * R / 2, 0, 1)
    body = np.asarray(t, np.float32) / 255 * 0.75
    hue = (np.arctan2(yy, xx) / (2 * np.pi) + phase * 0.1) % 1
    rim = np.clip(1 - np.abs(rr - 0.93) / 0.08, 0, 1)[..., None]
    irid = np.stack([0.5 + 0.5 * np.cos(2 * np.pi * (hue + o)) for o in (0, 0.33, 0.66)], -1)
    col = body * (1 - rim) + irid * rim
    hl = np.clip(1 - np.sqrt((xx + 0.4) ** 2 + (yy + 0.45) ** 2) / 0.22, 0, 1)[..., None]
    col = col + hl * 0.8
    alpha = a * (0.55 + 0.45 * rim[..., 0] + 0.4 * hl[..., 0])
    out = np.concatenate([np.clip(col, 0, 1), np.clip(alpha, 0, 1)[..., None]], -1)
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def scene_bigtext(ctx, text, sub="", style="karaoke"):
    """卡拉 OK 大字闪现。"""
    bg = gradient((10, 12, 70), (50, 10, 80))
    im = Image.fromarray((bg * 255).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = 0.8 + 0.2 * ease_back(ctx.t / 0.3)
    f = font("maru", int(200 * s))
    p = clamp(ctx.t / (ctx.d * 0.8))
    text_c(d, (W // 2, H // 2 - 40), text, f, (255, 255, 255, 255), stroke=14, sfill=(24, 48, 170, 255))
    tw = d.textlength(text, font=f)
    cut = int(W / 2 - tw / 2 + tw * p)
    lay2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(lay2)
    text_c(d2, (W // 2, H // 2 - 40), text, f, PINK + (255,), stroke=14, sfill=(24, 48, 170, 255))
    m = Image.new("L", (W, H), 0)
    m.paste(255, (0, 0, max(0, cut), H))
    lay = Image.composite(lay2, lay, m)
    if sub:
        text_c(ImageDraw.Draw(lay), (W // 2, H // 2 + 150), sub, font("maru", 64), (255, 255, 255, 255), stroke=6, sfill=(24, 48, 170, 255))
    im = Image.alpha_composite(im, glow(lay, 8, 0.8))
    return rgb(im)


def scene_cover(ctx, path, credits=None):
    """结尾：唱片封面插画定格 + 金色 1989 + 滚动片尾字幕。"""
    base = scene_image(ctx, path, zoom=(1.12, 1.0))
    im = Image.fromarray((base * 255).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    q = ease_out((ctx.t - 0.8) / 1.5)
    text_c(d, (520, 300), "1989", font("bodoni", 230), GOLD + (int(255 * q),), stroke=3, sfill=(120, 70, 10, int(255 * q)))
    text_c(d, (520, 450), "BABY  —  MINA", font("futura", 46), (255, 255, 255, int(230 * q)))
    im = Image.alpha_composite(im, glow(lay, 12, 1.2))
    if credits:
        c0 = 2.0
        if ctx.t > c0:
            cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(cl)
            dc.rectangle([W - 760, 0, W, H], fill=(0, 0, 20, 150))
            speed = (len(credits) * 58 + H) / max(ctx.d - c0 - 1.2, 1)
            y = H + 20 - (ctx.t - c0) * speed
            for line in credits:
                if -60 < y < H + 60:
                    big = line.startswith("■")
                    dc.text((W - 380, y), line.lstrip("■"), font=font("maru", 40 if big else 30),
                            fill=(255, 226, 64, 255) if big else (255, 255, 255, 255), anchor="mm")
                y += 58
            im = Image.alpha_composite(im, cl)
    return rgb(im)


def scene_grid_wall(ctx):
    return gradient((12, 10, 40), (40, 14, 60))


# ---------------------------------------------------------------- 叠层

def _layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def overlay_osd(ctx, text="▶ PLAY", date="1989.12.29 FRI", clock="PM 11:58", tracking=1.5):
    lay = _layer()
    d = ImageDraw.Draw(lay)
    if text and (ctx.t > 1.0 or int(ctx.t * 4) % 2 == 0):
        green, dark = (60, 255, 110, 255), (0, 40, 0, 255)
        sym, word = text.split(" ", 1) if " " in text else ("", text)
        if sym == "▶":
            d.polygon([(110, 100), (110, 160), (162, 130)], fill=green, outline=dark, width=3)
        elif sym == "■":
            d.rectangle([110, 102, 162, 156], fill=green, outline=dark, width=3)
        d.text((185, 90), word, font=font("osd", 72), fill=green, stroke_width=3, stroke_fill=dark)
    if date:
        d.text((W - 110, H - 170), date, font=font("osd", 56), fill=(255, 255, 255, 255), anchor="ra", stroke_width=3, stroke_fill=(0, 0, 0, 255))
        d.text((W - 110, H - 100), clock, font=font("osd", 56), fill=(255, 255, 255, 255), anchor="ra", stroke_width=3, stroke_fill=(0, 0, 0, 255))
    out = rgba(lay)
    if ctx.t < tracking:
        rng = np.random.default_rng(ctx.seed)
        y = int((ctx.t / tracking) * (H + 200)) - 100
        y0, y1 = max(0, y - 40), min(H, y + 40)
        if y1 > y0:
            n = rng.random((y1 - y0, W)).astype(np.float32)
            band = np.stack([n, n, n, (n > 0.4) * 0.8], -1)
            out[y0:y1] = np.maximum(out[y0:y1], band)
    return out


def overlay_yen(ctx, y=420, rot=12):
    """一张风格化的「¥10000」卡片飞过画面（不仿真钞）。"""
    lay = _layer()
    card = Image.new("RGBA", (560, 260), (0, 0, 0, 0))
    dc = ImageDraw.Draw(card)
    dc.rounded_rectangle([0, 0, 559, 259], radius=26, fill=(236, 226, 196, 255), outline=(140, 110, 60, 255), width=8)
    dc.ellipse([30, 50, 190, 210], outline=(170, 130, 70, 255), width=6)
    dc.text((110, 130), "¥", font=font("bodoni", 110), fill=(150, 110, 50, 255), anchor="mm")
    dc.text((380, 110), "10000", font=font("bodoni", 96), fill=(120, 80, 40, 255), anchor="mm")
    dc.text((380, 200), "BUBBLE  YEN", font=font("futura", 30), fill=(150, 110, 60, 255), anchor="mm")
    p = ctx.t / ctx.d
    a = rot * math.sin(ctx.t * 6)
    c = card.rotate(a, expand=True, resample=Image.BICUBIC)
    x = int(-600 + (W + 1200) * p)
    lay.alpha_composite(c, (x - c.width // 2, int(y + 60 * math.sin(p * 3)) - c.height // 2))
    return rgba(lay)


def overlay_prop(ctx, title="ショルダーフォン", lines=("1985年　登場", "重さ　約3kg"), icon="phone"):
    """80 年代商品目录风道具卡。"""
    lay = _layer()
    cw, ch = 620, 380
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    dc = ImageDraw.Draw(card)
    dc.rectangle([0, 0, cw - 1, ch - 1], fill=(250, 248, 240, 245), outline=(30, 30, 30, 255), width=4)
    dc.rectangle([0, 0, cw - 1, 84], fill=(220, 30, 50, 255))
    dc.text((24, 42), title, font=font("maru", 54), fill=(255, 255, 255, 255), anchor="lm")
    if icon == "phone":
        dc.rounded_rectangle([30, 120, 230, 330], radius=16, fill=(60, 60, 64, 255))
        dc.rectangle([50, 140, 210, 200], fill=(150, 200, 150, 255))
        for i in range(3):
            for j in range(3):
                dc.rectangle([60 + j * 50, 220 + i * 34, 95 + j * 50, 244 + i * 34], fill=(200, 200, 205, 255))
        dc.line([(130, 120), (260, 100)], fill=(30, 30, 30, 255), width=6)
    for k, s in enumerate(lines):
        dc.text((270, 160 + k * 80), s, font=font("maru", 46), fill=(30, 30, 30, 255), anchor="lm")
    p = ease_back(ctx.t / 0.35) if ctx.t < ctx.d - 0.25 else 1 - ease_out((ctx.t - ctx.d + 0.25) / 0.25)
    x = int(W - 80 - cw * p)
    lay.alpha_composite(card.rotate(3, expand=True, resample=Image.BICUBIC), (x, 120))
    return rgba(lay)


def overlay_clock(ctx, h0=21.0, h1=29.0):
    """办公室挂钟：指针从 21:00 飞转到天亮。"""
    lay = _layer()
    d = ImageDraw.Draw(lay)
    cx, cy, R = W - 300, 290, 200
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(250, 250, 245, 240), outline=(40, 40, 40, 255), width=14)
    for k in range(12):
        a = math.radians(k * 30 - 90)
        d.line([(cx + 0.82 * R * math.cos(a), cy + 0.82 * R * math.sin(a)), (cx + 0.94 * R * math.cos(a), cy + 0.94 * R * math.sin(a))], fill=(40, 40, 40, 255), width=8)
    hr = h0 + (h1 - h0) * ease_out(ctx.t / ctx.d)
    for v, L, w in ((hr / 12, 0.5, 14), (hr % 1, 0.78, 8)):
        a = math.radians(v * 360 - 90)
        d.line([(cx, cy), (cx + L * R * math.cos(a), cy + L * R * math.sin(a))], fill=(20, 20, 20, 255), width=w)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(200, 30, 40, 255))
    return rgba(lay)


def overlay_card_bags(ctx):
    """金卡一刷，购物袋按拍越叠越高。"""
    lay = _layer()
    d = ImageDraw.Draw(lay)
    p = ease_out(ctx.t / 0.5)
    x = int(-500 + 900 * p)
    d.rounded_rectangle([x, 640, x + 420, 900], radius=22, fill=(230, 180, 60, 255), outline=(150, 100, 20, 255), width=6)
    d.rectangle([x + 40, 700, x + 120, 760], fill=(200, 200, 160, 255))
    d.text((x + 40, 820), "1989  GOLD", font=font("futura", 40), fill=(110, 70, 10, 255))
    bt = beats_between(ctx, ctx.T - ctx.t + 0.5, ctx.T)
    cols = [(255, 79, 163), (62, 200, 230), (255, 255, 255), (250, 200, 60), (120, 90, 200)]
    for k, _ in enumerate(bt[:8]):
        bx, by = W - 560 + (k % 2) * 160, H - 60 - (k // 2) * 200 - 230
        d.rectangle([bx, by + 40, bx + 230, by + 230], fill=cols[k % 5] + (255,), outline=(40, 40, 40, 255), width=4)
        d.arc([bx + 60, by - 20, bx + 170, by + 90], 180, 360, fill=(40, 40, 40, 255), width=8)
        d.text((bx + 115, by + 140), ["SHIBUYA", "GINZA", "AOYAMA", "ROPPONGI"][k % 4], font=font("futura", 28), fill=(30, 30, 30, 255), anchor="mm")
    return rgba(lay)


def overlay_money(ctx, n=60, seed=9):
    """钞票雨（风格化纸币）。"""
    lay = _layer()
    rng = np.random.default_rng(seed)
    note = Image.new("RGBA", (220, 104), (0, 0, 0, 0))
    dn = ImageDraw.Draw(note)
    dn.rounded_rectangle([0, 0, 219, 103], radius=10, fill=(232, 222, 190, 255), outline=(140, 110, 60, 255), width=4)
    dn.text((110, 52), "¥10000", font=font("bodoni", 44), fill=(120, 80, 40, 255), anchor="mm")
    for k in range(n):
        x = rng.uniform(-100, W + 100) + 60 * math.sin(ctx.t * 1.5 + k)
        y = -120 + ((ctx.t + rng.uniform(0, 3)) * rng.uniform(260, 420)) % (H + 240)
        fx = abs(math.cos(ctx.t * rng.uniform(2, 5) + k))
        w = max(8, int(220 * fx))
        im = note.resize((w, 104)).rotate(rng.uniform(-40, 40), expand=True, resample=Image.BICUBIC)
        lay.alpha_composite(im, (int(x), int(y)))
    return rgba(lay)


def overlay_hearts(ctx, times=(), seed=1):
    """每个 "baby" 弹出一颗霓虹爱心。"""
    lay = _layer()
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    for k, t0 in enumerate(times):
        x, y = rng.uniform(260, W - 260), rng.uniform(180, H - 380)
        age = ctx.T - t0
        if not 0 <= age < 0.8:
            continue
        s = 70 + 80 * ease_back(age / 0.25)
        a = int(255 * (1 - clamp((age - 0.4) / 0.4)))
        pts = [(x + s * 16 * math.sin(u) ** 3 / 16, y - s * (13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)) / 16)
               for u in np.linspace(0, 2 * math.pi, 60)]
        d.line(pts + [pts[0]], fill=PINK + (a,), width=12, joint="curve")
    return rgba(glow(lay, 14, 1.6))


def overlay_confetti(ctx, n=220, seed=4):
    lay = _layer()
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    cols = [PINK, CYAN, GOLD, (255, 255, 255), (160, 120, 255)]
    for k in range(n):
        x0, sp = rng.uniform(0, W), rng.uniform(200, 380)
        y = -40 + (ctx.t + rng.uniform(-0.6, 0)) * sp
        if y < -40 or y > H + 40:
            continue
        x = x0 + 50 * math.sin(ctx.t * rng.uniform(2, 4) + k)
        w = 8 + 10 * abs(math.cos(ctx.t * rng.uniform(4, 9) + k))
        d.rectangle([x, y, x + w, y + 16], fill=cols[k % 5] + (255,))
    return rgba(lay)


def overlay_flash(ctx, color=(255, 255, 255), dur=0.25):
    a = 1 - clamp(ctx.t / dur)
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = np.array(color, np.float32) / 255
    out[..., 3] = a
    return out


def overlay_rank(ctx):
    """80 年代排行榜节目：「今週の第1位」+ 得点滚动。"""
    lay = _layer()
    d = ImageDraw.Draw(lay)
    p = ease_back(ctx.t / 0.4) if ctx.t < ctx.d - 0.3 else 1 - ease_out((ctx.t - ctx.d + 0.3) / 0.3)
    x0 = int(-700 + 800 * p)
    d.rounded_rectangle([x0, 70, x0 + 600, 330], radius=18, fill=(10, 20, 90, 235), outline=GOLD + (255,), width=6)
    d.text((x0 + 30, 115), "今週の第1位", font=font("maru", 52), fill=(255, 255, 255, 255), anchor="lm")
    d.text((x0 + 120, 240), "1", font=font("bodoni", 180), fill=GOLD + (255,), anchor="mm")
    d.text((x0 + 230, 205), "BABY", font=font("futura", 64), fill=(255, 255, 255, 255), anchor="lm")
    pts = int(9999 * ease_out(ctx.t / (ctx.d * 0.7)))
    d.text((x0 + 230, 280), f"{pts:,} 点", font=font("din", 60), fill=PINK + (255,), anchor="lm")
    return rgba(lay)


def overlay_label(ctx, text, corner="tl"):
    lay = _layer()
    d = ImageDraw.Draw(lay)
    x, y, an = (60, 50, "la") if corner == "tl" else (W - 60, 50, "ra")
    d.text((x, y), text, font=font("maru", 34), fill=(255, 255, 255, 230), anchor=an, stroke_width=3, stroke_fill=(0, 0, 0, 200))
    return rgba(lay)


def overlay_bigcue(ctx, text="みんなで!", y=170):
    lay = _layer()
    d = ImageDraw.Draw(lay)
    s = 0.7 + 0.3 * ease_back(ctx.t / 0.25)
    text_c(d, (W // 2, y), text, font("maru", int(110 * s)), (255, 255, 255, 255), stroke=10, sfill=(24, 48, 170, 255))
    return rgba(glow(lay, 8, 0.8))


def overlay_countdown(ctx, t_end, step=0.736):
    """最后 2 小节 5-4-3-2-1。"""
    lay = _layer()
    d = ImageDraw.Draw(lay)
    remain = t_end - ctx.T
    n = int(math.ceil(remain / step))
    if 1 <= n <= 5:
        f = (remain % step) / step
        s = 1 + 0.4 * f
        text_c(d, (W // 2, H // 2), str(n), font("bodoni", int(420 * s)), (255, 255, 255, int(255 * (0.4 + 0.6 * f))), stroke=10, sfill=PINK + (255,))
    return rgba(glow(lay, 16, 1.2))
