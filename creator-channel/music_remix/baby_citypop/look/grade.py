"""80–90 年代日本质感调色。所有素材（万相、代码、影视）最后都过同一套 grade()，保证全片统一。

两套方案：
  tv89   —— 1989 年电视播出再录到录像带上：奶油黑位、偏青阴影、色度渗色、亮边、扫描线、磁带噪点
  film89 —— 当年 35mm 富士胶片电影：暖高光、柔光扩散、红色光晕、胶片颗粒、暗角

用法：python grade.py in.png out_dir   → 输出 *_tv89.jpg / *_film89.jpg
视频逐帧调用 grade(img, look, seed=帧号)。
"""
import sys
from pathlib import Path

from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

LOOKS = {
    "tv89": dict(lift=(0.09, 0.09, 0.11), gain=(0.95, 0.92, 0.88), shadow_tint=(-0.015, 0.02, 0.03),
                 high_tint=(0.04, 0.005, -0.02), sat=0.80, green_shift=0.5, diffusion=0.14, halation=0.08,
                 luma_w=540, chroma_w=110, chroma_shift=5, edge_halo=0.5, scan=0.09, noise=0.035,
                 grain=0.0, vignette=0.22),
    "film89": dict(lift=(0.08, 0.065, 0.065), gain=(0.97, 0.93, 0.85), shadow_tint=(0.0, 0.01, 0.02),
                   high_tint=(0.05, 0.018, -0.03), sat=0.84, green_shift=0.6, diffusion=0.30, halation=0.22,
                   luma_w=1000, chroma_w=420, chroma_shift=0, edge_halo=0.0, scan=0.0, noise=0.0,
                   grain=0.07, vignette=0.32),
}

TO_YIQ = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]])
TO_RGB = np.linalg.inv(TO_YIQ).astype(np.float32)
TO_YIQ = TO_YIQ.astype(np.float32)
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def gaussian_filter(a, sigma):
    """sigma 为标量或 (sy, sx[, 0])，通道维不模糊。"""
    sy, sx = (sigma, sigma) if np.isscalar(sigma) else sigma[:2]
    return cv2.GaussianBlur(a, (0, 0), sigmaX=sx, sigmaY=sy, borderType=cv2.BORDER_REFLECT)


def gaussian_filter1d(a, sigma, axis=1):
    sx, sy = (sigma, 1e-6) if axis == 1 else (1e-6, sigma)
    k = int(4 * sigma + 0.5) * 2 + 1
    return cv2.GaussianBlur(a, (k, 1) if axis == 1 else (1, k), sigmaX=sx, sigmaY=sy, borderType=cv2.BORDER_REFLECT)


def _resample_w(ch, w):
    h, W = ch.shape
    small = cv2.resize(ch, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (W, h), interpolation=cv2.INTER_LINEAR)


def _luma(x):
    return cv2.transform(x, LUMA[None])


def _tone_lut():
    x = np.linspace(0, 1, 4096, dtype=np.float32)
    x = x + 0.15 * x * (1 - x) * (2 * x - 1)
    return ((1 - np.exp(-0.9 * x)) / (1 - np.exp(-0.9))).astype(np.float32)


TONE = _tone_lut()


@lru_cache(8)
def _vignette(h, w, v):
    yy, xx = np.mgrid[-1:1:h * 1j, -1:1:w * 1j]
    return (1 - v * np.clip(xx ** 2 * 0.6 + yy ** 2 - 0.25, 0, None)).astype(np.float32)[..., None]


@lru_cache(8)
def _scan(h, step, amount):
    rows = (np.arange(h) // step) % 2
    return (1 - amount * rows).astype(np.float32)[:, None, None]


def grade(img, look="tv89", seed=0):
    """img: float32 RGB [0,1], HxWx3。"""
    p = LOOKS[look]
    rng = np.random.default_rng(seed)
    x = img.astype(np.float32)
    h, w, _ = x.shape

    # 1. 色彩：降饱和、绿色往黄青偏（富士/当年显像管的绿色不那么纯）、保住霓虹粉
    lum = _luma(x)
    x = lum[..., None] + (x - lum[..., None]) * p["sat"]
    g_excess = np.clip(x[..., 1] - np.maximum(x[..., 0], x[..., 2]), 0, None)
    x[..., 1] -= g_excess * p["green_shift"] * 0.5
    x[..., 0] += g_excess * p["green_shift"] * 0.25
    x[..., 2] += g_excess * p["green_shift"] * 0.15

    # 2. 影调：柔和 S 曲线 + 高光肩部压缩
    x = TONE[(np.clip(x, 0, 1) * 4095 + 0.5).astype(np.int16)]

    # 3. 分离色调：阴影偏青蓝，高光偏暖粉
    lum = _luma(x)[..., None]
    x = x + (1 - lum) ** 2 * np.array(p["shadow_tint"], np.float32) + lum ** 2 * np.array(p["high_tint"], np.float32)

    # 4. 黑位抬起（奶油黑）、白位压低
    lift, gain = np.array(p["lift"], np.float32), np.array(p["gain"], np.float32)
    x = lift + np.clip(x, 0, 1) * (gain - lift)

    # 5. 柔光扩散 + 红橙光晕（亮部向外渗出）
    s = max(h, w) / 1920
    if p["diffusion"]:
        x = x * (1 - p["diffusion"]) + gaussian_filter(x, (8 * s, 8 * s, 0)) * p["diffusion"]
    if p["halation"]:
        hi = np.clip((x.max(2) - 0.62) / 0.38, 0, 1)
        halo = gaussian_filter(hi, 14 * s)[..., None] * np.array([1.0, 0.38, 0.18], np.float32)
        x = 1 - (1 - x) * (1 - halo * p["halation"] * 2.2)

    # 6. 分辨率：亮度降到当年的水平清晰度，色度分辨率更低并向右偏移（录像带渗色）
    yiq = cv2.transform(x, TO_YIQ)
    yiq[..., 0] = _resample_w(yiq[..., 0], int(p["luma_w"] * w / 1920))
    for c in (1, 2):
        ch = gaussian_filter1d(_resample_w(yiq[..., c], int(p["chroma_w"] * w / 1920)), 2 * s, axis=1)
        if p["chroma_shift"]:
            ch = np.roll(ch, int(p["chroma_shift"] * s), axis=1)
        yiq[..., c] = ch
    if p["edge_halo"]:
        blur = gaussian_filter1d(yiq[..., 0], 3.5 * s, axis=1)
        yiq[..., 0] += (yiq[..., 0] - blur) * p["edge_halo"] * 2
    x = cv2.transform(yiq, TO_RGB)

    # 7. 扫描线、磁带噪点、胶片颗粒
    if p["scan"]:
        x *= _scan(h, max(1, int(2 * s)), p["scan"])
    if p["noise"]:
        n = rng.standard_normal((h, w // 2 + 1), np.float32) * p["noise"]
        x += cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)[..., None]
        for _ in range(rng.integers(0, 3)):
            r = rng.integers(0, h)
            x[r:r + max(1, int(2 * s))] += rng.uniform(0.05, 0.15)
    if p["grain"]:
        g = gaussian_filter(rng.standard_normal((h, w), np.float32), 0.7 * s)
        lum = np.clip(_luma(x), 0, 1)
        x += (g * p["grain"] * (0.5 + 2 * lum * (1 - lum)))[..., None]

    # 8. 暗角
    x *= _vignette(h, w, p["vignette"])
    return np.clip(x, 0, 1)


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    im = np.asarray(Image.open(src).convert("RGB").resize((1920, 1080), Image.LANCZOS), np.float32) / 255
    for lk in LOOKS:
        Image.fromarray((grade(im, lk, seed=7) * 255).astype(np.uint8)).save(out / f"{src.stem}_{lk}.jpg", quality=92)
    print("ok", src.stem)
