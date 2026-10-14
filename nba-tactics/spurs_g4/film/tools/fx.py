"""Shared effects for real-footage segments. Images are float32 BGR in [0, 1]."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GOLD = (106, 180, 216)       # BGR of #d8b46a
GOLD_HI = (160, 226, 255)    # #ffe2a0
WHITE = (230, 239, 244)
GREY = (144, 133, 125)
BG = (10, 6, 5)

FONT_CN = '/System/Library/Fonts/Supplemental/Songti.ttc'
FONT_NUM = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'
LUMA = np.array([0.114, 0.587, 0.299], np.float32)


def _songti_bold_index():
    for i in range(12):
        try:
            f = ImageFont.truetype(FONT_CN, 20, index=i)
        except OSError:
            break
        name = ' '.join(f.getname())
        if 'SC' in name and 'Bold' in name:
            return i
    return 0
SONGTI_BOLD = _songti_bold_index()


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def prog(t, a, b):
    return float(np.clip((t - a) / (b - a), 0, 1))


def s_curve(x, k=1.3):
    x = np.clip(x, 0, 1)
    return 0.5 + (x - 0.5) * k / (1 + (k - 1) * np.abs(2 * x - 1))


def grade(f, contrast=1.3, sat=1.08, warm=1.0, crush=0.03, bloom=0.5):
    """Cinematic grade: S-curve, teal shadows / warm highlights, highlight bloom."""
    lum = f @ LUMA
    hi = np.clip((lum - 0.7) * 3.0, 0, 1)[..., None] * f
    bl = cv2.GaussianBlur(hi, (0, 0), 12) * 0.6 + cv2.GaussianBlur(hi, (0, 0), 36) * 0.4
    g = s_curve(f, contrast)
    t = np.clip(g @ LUMA, 0, 1)[..., None]
    shadow = np.array([1.08, 1.01, 0.88], np.float32)
    high = np.array([1 - 0.12 * warm, 1 - 0.01 * warm, 1 + 0.08 * warm], np.float32)
    g = g * (shadow * (1 - t) + high * t)
    gray = (g @ LUMA)[..., None]
    g = gray + (g - gray) * sat
    g = np.clip(g - crush, 0, None) / (1 - crush)
    return g + bl * bloom


def scanlines(img, strength=0.08, period=3):
    H = img.shape[0]
    rows = (np.arange(H) % period == 0).astype(np.float32) * strength
    return img * (1 - rows)[:, None, None]


def grain(img, amt, rng):
    H, W = img.shape[:2]
    n = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)
    return img + n[..., None] * amt


def vignette(H, W, amt=0.45):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = ((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.5) ** 2) * 2.4
    return (1 - amt * np.clip(r, 0, 1) ** 1.3)[..., None]


def zoom(img, s, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    H, W = img.shape[:2]
    M = np.float32([[s, 0, cx * W * (1 - s) + dx], [0, s, cy * H * (1 - s) + dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def chroma(img, px):
    if px < 0.5:
        return img
    H, W = img.shape[:2]
    out = img.copy()
    for ch, d in ((2, -px), (0, px)):
        M = np.float32([[1, 0, d], [0, 1, 0]])
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


def radial_blur(img, amt, cx=0.5, cy=0.5, n=8):
    if amt < 1e-3:
        return img
    acc = np.zeros_like(img)
    for k in range(n):
        acc += zoom(img, 1 + amt * k / n, cx, cy)
    return acc / n


def iris(H, W, cx, cy, r, feather=6.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip((r - d) / feather + 0.5, 0, 1)[..., None], d


def crt_off(img, u):
    """Old-TV switch-off: squash to a bright line (u 0..0.65), then shrink to a dot (0.65..1)."""
    H, W = img.shape[:2]
    out = np.zeros_like(img)
    if u < 0.65:
        a = ease(u / 0.65)
        h = max(2, int(H * (1 - a) ** 2.2))
        sq = cv2.resize(img, (W, h), interpolation=cv2.INTER_AREA) * (1 + 2.5 * a)
        y0 = (H - h) // 2
        out[y0:y0 + h] = sq
    else:
        a = ease((u - 0.65) / 0.35)
        w = max(2, int(W * (1 - a) ** 1.6))
        x0 = (W - w) // 2
        out[H // 2 - 1:H // 2 + 2, x0:x0 + w] = np.array(GOLD_HI, np.float32) / 255 * (1.4 - a)
    return cv2.GaussianBlur(out, (0, 0), 1.2) + cv2.GaussianBlur(out, (0, 0), 10) * 0.6


class TextLayer:
    """Pre-rendered text/line overlay (premultiplied BGR + alpha) for cheap per-frame blending."""

    def __init__(self, W, H):
        self.img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def text(self, s, x, y, size, font='cn', color=GOLD, anchor='la', spacing=0, alpha=255):
        f = ImageFont.truetype(FONT_CN, size, index=SONGTI_BOLD) if font == 'cn' else ImageFont.truetype(FONT_NUM, size)
        rgb = (color[2], color[1], color[0], alpha)
        if spacing:
            cx = x
            for ch in s:
                self.d.text((cx, y), ch, font=f, fill=rgb, anchor=anchor)
                cx += self.d.textlength(ch, font=f) + spacing
        else:
            self.d.text((x, y), s, font=f, fill=rgb, anchor=anchor)
        return self

    def line(self, pts, color=GOLD, width=1, alpha=255):
        self.d.line(pts, fill=(color[2], color[1], color[0], alpha), width=width)
        return self

    def done(self):
        a = np.asarray(self.img).astype(np.float32) / 255
        self.alpha = a[..., 3:4]
        self.bgr = a[..., [2, 1, 0]] * self.alpha
        glow = cv2.GaussianBlur(self.bgr, (0, 0), 6) * 0.5
        self.bgr = self.bgr + glow
        return self

    def over(self, img, opacity):
        if opacity <= 0:
            return img
        return img * (1 - self.alpha * opacity) + self.bgr * opacity
