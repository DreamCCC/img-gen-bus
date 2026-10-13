"""Cinematic treatment for real footage (no cut-outs: people stay photographic).

usage: python tools/grade_real.py in.mp4 out_dir [--start N] [--end N] [--stills 18,30] [--spot 0.55]
Writes out_dir/f_%04d.png (or s_<idx>.png for stills).
--spot: how much to darken everything except the hero (red-jersey person), via a heavily feathered mask.
"""
import argparse, os
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--end', type=int, default=10**9)
ap.add_argument('--width', type=int, default=1920)
ap.add_argument('--stills', default='')
ap.add_argument('--spot', type=float, default=0.45)
ap.add_argument('--model', default='yolo11x-seg.pt')
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
stills = {int(s) for s in args.stills.split(',') if s}

model = None
if args.spot > 0:
    from ultralytics import YOLO
    model = YOLO(args.model)

cap = cv2.VideoCapture(args.src)
W0, H0 = int(cap.get(3)), int(cap.get(4))
W = args.width; H = round(H0 * W / W0 / 2) * 2
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.42 * np.clip(((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.5) ** 2) * 2.4, 0, 1) ** 1.3
rng = np.random.default_rng(11)

SHADOW = np.array([1.10, 1.02, 0.86], np.float32)  # BGR: teal shadows
HIGH = np.array([0.86, 0.98, 1.10], np.float32)    # warm highlights

def s_curve(x, k=1.35):
    x = np.clip(x, 0, 1)
    return 0.5 + (x - 0.5) * k / (1 + (k - 1) * np.abs(2 * x - 1))

def hero_mask(frame):
    res = model.predict(frame, imgsz=1088, conf=0.25, classes=[0], retina_masks=True, verbose=False)[0]
    m = np.zeros(frame.shape[:2], np.float32)
    if res.masks is None: return m
    b, g, r = [frame[..., i].astype(np.float32) for i in range(3)]
    red = ((r > 90) & (r > g * 1.7) & (r > b * 1.6)).astype(np.float32)
    best, score = None, 0
    for mk in res.masks.data.cpu().numpy().astype(np.float32):
        s = (red * mk).sum() * mk.sum() ** 0.35
        if s > score: best, score = mk, s
    return m if best is None else best

prev = None; idx = -1; n = 0
while True:
    ok, frame = cap.read()
    if not ok: break
    idx += 1
    if idx < args.start: continue
    if idx > args.end: break
    if stills and idx not in stills: continue

    f = cv2.resize(frame, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    f = np.clip(f + (f - cv2.GaussianBlur(f, (0, 0), 2.0)) * 0.6, 0, 1)

    # spotlight on the hero: feathered, so it reads as light falloff rather than a matte
    if model is not None:
        m = cv2.resize(hero_mask(frame), (W, H))
        m = cv2.GaussianBlur(cv2.dilate(m, np.ones((25, 25), np.uint8)), (0, 0), 45)
        m = np.clip(m * 1.6, 0, 1)
        if prev is not None and not stills: m = 0.55 * m + 0.45 * prev
        prev = m
        f = f * (1 - args.spot * (1 - m))[..., None]

    lum = f @ np.array([0.114, 0.587, 0.299], np.float32)
    # bloom + anamorphic streak from the arena lights
    hi = np.clip((lum - 0.72) * 3.5, 0, 1)
    hi3 = (f * hi[..., None])
    bloom = cv2.GaussianBlur(hi3, (0, 0), 14) * 0.55 + cv2.GaussianBlur(hi3, (0, 0), 40) * 0.35
    sm = cv2.resize(hi3, (W // 4, H // 4))
    streak = cv2.resize(cv2.blur(sm, (161, 1)), (W, H)) * np.array([1.0, 0.8, 0.55], np.float32) * 1.4

    g = s_curve(f, 1.32)
    gl = g @ np.array([0.114, 0.587, 0.299], np.float32)
    t = np.clip(gl, 0, 1)[..., None]
    g = g * (SHADOW * (1 - t) + HIGH * t)
    gray = (g @ np.array([0.114, 0.587, 0.299], np.float32))[..., None]
    g = gray + (g - gray) * 1.12
    g = np.clip(g - 0.025, 0, None) / 0.975          # crush blacks a touch
    g = g + bloom * np.array([0.8, 0.9, 1.0], np.float32) + streak
    g *= vig[..., None]
    grain = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)[..., None]
    g += grain * 0.022
    g = 1 - np.exp(-np.clip(g, 0, None) * 1.05) / 1  # filmic shoulder
    g = g / (1 - np.exp(-1.05))
    name = f's_{idx:04d}.png' if stills else f'f_{n:04d}.png'
    cv2.imwrite(os.path.join(args.out, name), np.clip(g * 255, 0, 255).astype(np.uint8))
    n += 1
    if n % 20 == 0: print('frame', idx, flush=True)
print('done', n)
