"""Real-footage segment: 2004 China Games, Yao putback dunk vs Kings (NBA official Douyin 7693738271586651428).

Slot: sample 6.0–10.4 s (4.4 s). Slam lands on 2.81 s (sample 8.81, audio cue `slam`).
Inputs:
  out/r04_x4.mp4   RIFE x4 of source frames 220..305, cropped 1080x1400 (drops burned-in captions), scaled 834x1080
  out/sample2d_shift.mp4  code page; its last tactic-board frame is the iris source
usage: python tools/seg_dunk2004.py out/dunk2004.mp4 [--stills 0.2,1.5,2.82,3.4,4.2]
       NOIRIS=1 python tools/seg_dunk2004.py scenes/clips/dunk/   (frame sequence; the page draws the iris)
       EN=1 NOIRIS=1 python tools/seg_dunk2004.py scenes/clips/dunk_en/   (no baked HUD, NBA colours; film_en.html draws the HUD)
"""
import os, subprocess, sys
from pathlib import Path
import cv2
import numpy as np
import fx

out_path = sys.argv[1]
stills = [float(s) for s in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[2] == '--stills' else None
NOIRIS = bool(os.environ.get('NOIRIS'))
EN = bool(os.environ.get('EN'))

FPS, W, H = 30, 1920, 1080
DUR, T_SLAM = 4.4, 2.81
SLAM_SRC = 45            # source frame (relative to 220) where the ball goes through the rim
DOT = (1160, 575)        # 姚明 dot on the tactic board at 5.97 s
PW, PH = 834, 1080
PX = (W - PW) // 2
RIM = (PX + 400, 760)    # rim on screen at the slam frame

cap = cv2.VideoCapture('out/r04_x4.mp4')
X = []
while True:
    ok, fr = cap.read()
    if not ok: break
    X.append(fr)
if not NOIRIS:
    cap = cv2.VideoCapture('out/sample2d_shift.mp4')
    cap.set(cv2.CAP_PROP_POS_FRAMES, 179)
    board = cap.read()[1].astype(np.float32) / 255

# speed curve: frames-per-output-frame. Decelerate into the slam, hit-stop, then recover.
N = round(DUR * FPS); n_slam = round(T_SLAM * FPS)
v = np.zeros(N)
for n in range(N):
    t = n / FPS
    if t < T_SLAM:
        s = t / T_SLAM; v[n] = 0.25 + 0.75 * (1 - s) ** 2
    elif t < 3.6:
        u = (t - T_SLAM) / (3.6 - T_SLAM); v[n] = 0.12 + 0.88 * u ** 1.5
    elif t < 4.1:
        v[n] = 1.0
pos = np.zeros(N); pos[0] = 2.0
k = (SLAM_SRC - 2.0) / v[:n_slam].sum()
v[:n_slam] *= k
for n in range(1, N):
    pos[n] = pos[n - 1] + v[n - 1]
pos = np.minimum(pos, (len(X) - 2) / 4)

def src(p):
    q = p * 4; i = int(q); a = q - i
    f0 = X[i].astype(np.float32); f1 = X[min(i + 1, len(X) - 1)].astype(np.float32)
    return (f0 * (1 - a) + f1 * a) / 255

hud_l = (fx.TextLayer(W, H)
         .text('NBA CHINA GAMES', 120, 410, 30, font='num', color=fx.GREY, spacing=5)
         .text('2004', 116, 450, 150, font='num', color=fx.GOLD)
         .text('火箭  vs  国王', 122, 615, 36, color=fx.WHITE)
         .line([(122, 672), (400, 672)], color=fx.GOLD, width=2, alpha=150).done())
hud_r = (fx.TextLayer(W, H)
         .text('11', W - 120, 405, 150, font='num', color=fx.GOLD_HI, anchor='ra')
         .text('姚明', W - 122, 570, 46, color=fx.WHITE, anchor='ra')
         .text('YAO MING  ·  2.26 M', W - 122, 640, 26, font='num', color=fx.GREY, anchor='ra')
         .line([(W - 400, 690), (W - 122, 690)], color=fx.GOLD, width=2, alpha=150).done())
frame_lines = fx.TextLayer(W, H)
for x in (PX - 1, PX + PW):
    frame_lines.line([(x, 0), (x, H)], color=(211, 206, 195) if EN else fx.GOLD, width=2, alpha=120 if EN else 170)
frame_lines.done()

VIG = fx.vignette(H, W, 0.5)
rng = np.random.default_rng(2004)
GOLDF = np.array((255, 235, 215) if EN else fx.GOLD_HI, np.float32) / 255

def compose(n):
    t = n / FPS
    dt = t - T_SLAM
    hit = np.exp(-max(dt, 0) * 9) if dt >= 0 else 0.0

    p = src(pos[n])
    p = np.clip(p + (p - cv2.GaussianBlur(p, (0, 0), 2.2)) * 0.9, 0, 1)
    p = fx.grade(p, contrast=1.28, sat=1.1, warm=1.0, bloom=0.45)
    p = fx.scanlines(p, 0.07, 3)
    breathe = 1.0 + 0.07 * fx.ease(min(t / T_SLAM, 1))
    p = fx.zoom(p, breathe, 0.45, 0.35)

    small = cv2.resize(p, (W // 8, int(PH * W / PW) // 8))
    oy = (small.shape[0] - H // 8) // 2
    bg = cv2.GaussianBlur(small[oy:oy + H // 8], (0, 0), 3)
    bg = cv2.resize(bg, (W, H)) * (0.2 + 0.45 * hit) * np.array([0.8, 0.95, 1.1], np.float32)
    img = bg
    img[:, PX:PX + PW] = p
    img = frame_lines.over(img, 1.0)
    if not EN:
        img = hud_l.over(img, fx.prog(t, 0.35, 0.8) * (1 - 0.7 * hit * (n % 2)))
        img = hud_r.over(img, fx.prog(t, 1.3, 1.8) * (1 - 0.7 * hit * (n % 2)))

    # suck-in before the slam, then impact
    if 2.56 <= t < T_SLAM:
        img *= 1 - 0.35 * fx.prog(t, 2.56, T_SLAM)
    if t < T_SLAM:
        amp = 3 * fx.prog(t, 2.0, T_SLAM)
        img = fx.zoom(img, 1.0, dx=rng.normal(0, amp), dy=rng.normal(0, amp))
        img = fx.chroma(img, 2.5 * fx.prog(t, 2.2, T_SLAM))
    else:
        img = fx.radial_blur(img, 0.05 * hit, RIM[0] / W, RIM[1] / H)
        img = fx.zoom(img, 1 + 0.06 * hit, RIM[0] / W, RIM[1] / H,
                      dx=rng.normal(0, 14 * hit), dy=rng.normal(0, 14 * hit))
        img = fx.chroma(img, 9 * hit)
        r = 80 + 1500 * fx.ease(dt / 0.6)
        if dt < 0.6:
            _, d = fx.iris(H, W, RIM[0], RIM[1], r)
            ring = np.exp(-((d - r) / 6) ** 2) * (1 - dt / 0.6) * 1.2
            img += ring[..., None] * GOLDF
        img += GOLDF * (0.95 * np.exp(-dt * 13))

    # iris in from the tactic-board dot
    if t < 0.4 and not NOIRIS:
        u = fx.ease(t / 0.4)
        b = fx.zoom(board, 1 + 0.25 * u, DOT[0] / W, DOT[1] / H)
        r = 30 + 2300 * u ** 1.6
        m, d = fx.iris(H, W, DOT[0], DOT[1], r, 4)
        ring = np.exp(-((d - r) / 4) ** 2)[..., None] * GOLDF * 1.4
        img = b * (1 - m) + img * m + ring

    img = img * VIG
    img = fx.grain(img, 0.022, rng)
    if t >= 4.1:
        img = fx.crt_off(img, fx.prog(t, 4.1, 4.37))
    return np.clip(img, 0, 1)

if stills:
    for t in stills:
        cv2.imwrite(f'out/d04_{t:.2f}.png', (compose(min(round(t * FPS), N - 1)) * 255).astype(np.uint8))
    sys.exit()

if out_path.endswith('/'):
    Path(out_path).mkdir(parents=True, exist_ok=True)
    for n in range(N):
        cv2.imwrite(f'{out_path}{n:05d}.jpg', (compose(n) * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 94])
    print('done', N)
    sys.exit()

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                       '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', out_path],
                      stdin=subprocess.PIPE)
for n in range(N):
    ff.stdin.write((compose(n) * 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
print('done', N, 'pos@slam', round(pos[n_slam], 2), 'pos end', round(pos[-1], 2))
