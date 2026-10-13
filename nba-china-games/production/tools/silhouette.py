"""Nike-style silhouette treatment for real footage.

usage: python tools/silhouette.py in.mp4 out_dir [--start N] [--end N] [--scale 1920] [--stills 10,40]
Writes PNG frames (out_dir/f_%04d.png) for ffmpeg to assemble.
Hero = person instance with the most red-jersey pixels; everyone else becomes a dimmer silhouette.
"""
import argparse, os
import cv2
import numpy as np
from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--end', type=int, default=10**9)
ap.add_argument('--width', type=int, default=1920)
ap.add_argument('--stills', default='')
ap.add_argument('--model', default='yolo11x-seg.pt')
ap.add_argument('--glow', default='0.58,0.30', help='backlight center (fraction x,y)')
ap.add_argument('--sam', default='', help='e.g. sam2.1_l.pt: refine YOLO boxes into masks with SAM')
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
stills = {int(s) for s in args.stills.split(',') if s}

model = YOLO(args.model)
sam = None
if args.sam:
    from ultralytics import SAM
    sam = SAM(args.sam)
cap = cv2.VideoCapture(args.src)
W0, H0 = int(cap.get(3)), int(cap.get(4))
W = args.width; H = round(H0 * W / W0 / 2) * 2
gx, gy = (float(v) for v in args.glow.split(','))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def radial(cx, cy, s):
    r2 = ((xx - cx * W) / W) ** 2 + ((yy - cy * H) / W) ** 2
    return np.exp(-r2 / s)

WARM = np.array([0.22, 0.58, 1.0], np.float32)  # BGR, warm gold-orange
RIM = np.array([0.62, 0.86, 1.0], np.float32)
rng = np.random.default_rng(7)

# smoke field: low-frequency noise, drifted per frame
def noise(scale, seed):
    r = np.random.default_rng(seed)
    n = r.random((H // scale + 3, W // scale + 3)).astype(np.float32)
    return np.clip(cv2.resize(n, (W + 3 * scale, H + 3 * scale), interpolation=cv2.INTER_CUBIC), 0, 1)
smoke_a, smoke_b = noise(160, 1), noise(60, 2)

prev_hero = prev_other = prev_ball = None
idx = -1; n_out = 0
while True:
    ok, frame = cap.read()
    if not ok: break
    idx += 1
    if idx < args.start: continue
    if idx > args.end: break
    if stills and idx not in stills: continue

    res = model.predict(frame, imgsz=1088, conf=0.25, classes=[0, 32], retina_masks=True, verbose=False)[0]
    hero = np.zeros((H0, W0), np.float32); other = hero.copy(); ball = hero.copy()
    if res.masks is not None:
        ms = res.masks.data.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy().astype(int)
        if sam is not None:
            boxes = res.boxes.xyxy.cpu().numpy()
            sr = sam.predict(frame, bboxes=boxes.tolist(), verbose=False)[0]
            if sr.masks is not None and len(sr.masks.data) == len(ms):
                ms = sr.masks.data.cpu().numpy().astype(np.float32)
        b, g, r = [frame[..., i].astype(np.float32) for i in range(3)]
        red = ((r > 90) & (r > g * 1.7) & (r > b * 1.6)).astype(np.float32)
        best, best_score = -1, 0
        for i, m in enumerate(ms):
            if cls[i] != 0: continue
            area = m.sum()
            score = (red * m).sum() * (area ** 0.35)
            if score > best_score: best, best_score = i, score
        for i, m in enumerate(ms):
            if cls[i] == 32: ball = np.maximum(ball, m)
            elif i == best: hero = np.maximum(hero, m)
            else: other = np.maximum(other, m)
    # temporal smoothing of soft masks to kill flicker
    def ema(cur, prev, a=0.6):
        return cur if prev is None or stills else a * cur + (1 - a) * prev
    hero = ema(cv2.GaussianBlur(hero, (0, 0), 1.2), prev_hero); prev_hero = hero
    other = ema(cv2.GaussianBlur(other, (0, 0), 1.2), prev_other); prev_other = other
    ball = ema(ball, prev_ball, 0.8); prev_ball = ball

    f = cv2.resize(frame, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    hero = cv2.resize(hero, (W, H)); other = cv2.resize(other, (W, H)); ball = cv2.resize(ball, (W, H))
    hero = np.clip((hero - 0.35) * 3.3, 0, 1); other = np.clip((other - 0.35) * 3.3, 0, 1)
    ball = np.clip((ball - 0.3) * 3, 0, 1)

    lum = f @ np.array([0.114, 0.587, 0.299], np.float32)
    # background: original pushed to near-black, highlights (arena lights, backboard) kept as warm bloom
    hi = np.clip((lum - 0.55) * 2.2, 0, 1)
    bloom = cv2.GaussianBlur(hi, (0, 0), 18) * 1.4 + cv2.GaussianBlur(hi, (0, 0), 5) * 0.6
    base = lum ** 1.6 * 0.10
    t = (idx if stills else n_out) / 30
    ox, oy = int(t * 40) % 160, int(t * 12) % 160
    sm = smoke_a[oy:oy + H, ox:ox + W] * 0.65 + smoke_b[(oy * 2) % 60:(oy * 2) % 60 + H, (ox * 3) % 60:(ox * 3) % 60 + W] * 0.35
    glow = radial(gx, gy, 0.004) * 1.3 + radial(gx, gy, 0.03) * 0.30 + radial(gx, gy, 0.15) * 0.06
    glow = glow * (0.45 + 1.1 * sm ** 1.5)
    bg = (base[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
          + (glow + bloom * 0.55)[..., None] * WARM)

    # silhouettes: black fill, thin rim on edges facing the backlight
    def rim_of(m, width):
        er = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=width)
        edge = np.clip(m - er, 0, 1)
        gyv, gxv = np.gradient(cv2.GaussianBlur(m, (0, 0), 3))
        lx, ly = (gx * W - xx), (gy * H - yy)
        ln = np.sqrt(lx ** 2 + ly ** 2) + 1e-3
        facing = np.clip(-(gxv * lx + gyv * ly) / ln / (np.sqrt(gxv ** 2 + gyv ** 2) + 1e-4), 0, 1)
        return cv2.GaussianBlur(edge * (0.2 + 0.8 * facing ** 2), (0, 0), 0.8) * m

    def zoom_blur(img, n=20, amt=0.35):
        acc = np.zeros_like(img)
        cx, cy = gx * W, gy * H
        for k in range(n):
            s = 1 - amt * k / n
            M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
            acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return acc / n

    occ = np.maximum(hero, other)
    out = bg * (1 - occ[..., None])
    small = cv2.resize(out, (W // 2, H // 2))
    Wf, Hf = W, H; W, H = W // 2, H // 2
    rays = cv2.resize(zoom_blur(np.clip(small - 0.12, 0, None)), (Wf, Hf)); W, H = Wf, Hf
    out += rays * 0.9 * (1 - 0.9 * occ[..., None])
    out += (f * 0.015) * hero[..., None]
    out += rim_of(hero, 3)[..., None] * RIM * 1.1
    out += rim_of(other, 2)[..., None] * RIM * 0.3
    # ball keeps its orange
    ball_col = np.array([0.05, 0.30, 0.95], np.float32) * (0.25 + 0.75 * lum[..., None])
    out = out * (1 - ball[..., None]) + ball_col * ball[..., None]

    # grade: vignette, grain
    vig = 1 - 0.55 * np.clip(((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 2.2, 0, 1)
    out *= vig[..., None]
    out += rng.normal(0, 0.012, (H, W, 1)).astype(np.float32)
    out = 1 - np.exp(-np.clip(out, 0, None) * 1.6)  # soft filmic shoulder
    cv2.imwrite(os.path.join(args.out, f'f_{n_out:04d}.png' if not stills else f's_{idx:04d}.png'),
                np.clip(out * 255, 0, 255).astype(np.uint8))
    n_out += 1
    if n_out % 10 == 0: print('frame', idx, flush=True)
print('done', n_out)
