"""Speed-ramp the silhouette frames into a 4.4 s clip with the slam at 2.81 s.

usage: python tools/assemble_sil.py frames_dir slowmo_rise.mp4 out.mp4
slowmo_rise.mp4: f_0000..f_0016 interpolated to 0.35x (made by ffmpeg minterpolate).
"""
import subprocess, sys, glob
import cv2
import numpy as np

src, rise_mp4, out = sys.argv[1:4]
FPS = 30
frames = sorted(glob.glob(f'{src}/f_*.png'))
F = lambda i: cv2.imread(frames[i]).astype(np.float32) / 255

cap = cv2.VideoCapture(rise_mp4)
rise = []
while True:
    ok, fr = cap.read()
    if not ok: break
    rise.append(fr.astype(np.float32) / 255)

T_SLAM = 2.81
R_N = round(T_SLAM * FPS) - len(rise)  # freeze-reveal length so the last rise frame lands on the slam
seq = [('reveal', rise[0], k) for k in range(R_N)]
seq += [('rise', f, k) for k, f in enumerate(rise)]
seq += [('land', F(i), k) for k, i in enumerate(range(17, 31))]
roar = list(range(66, 87))
for k in range(int(len(roar) / 0.6)):
    x = k * 0.6; i0 = int(x); a = x - i0
    f = F(roar[min(i0, len(roar) - 1)]) * (1 - a) + F(roar[min(i0 + 1, len(roar) - 1)]) * a
    seq.append(('roar', f, k))
N = round(4.4 * FPS)
seq = seq[:N]
H, W = seq[0][1].shape[:2]

def zoom(img, s, cx=0.58, cy=0.35):
    M = np.float32([[s, 0, cx * W * (1 - s)], [0, s, cy * H * (1 - s)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                       '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '15',
                       '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for n, (kind, img, k) in enumerate(seq):
    t = n / FPS
    if kind == 'reveal':
        u = k / max(R_N - 1, 1)
        img = zoom(img, 1.10 - 0.04 * u) * (u ** 1.8)
    elif kind == 'rise':
        u = k / max(len(rise) - 1, 1)
        img = zoom(img, 1.06 - 0.06 * u)
    dt = t - T_SLAM
    if 0 <= dt < 0.5:
        punch = np.exp(-dt * 9)
        img = zoom(img, 1 + 0.05 * punch)
        img = img + np.array([0.55, 0.8, 1.0], np.float32) * (0.85 * np.exp(-dt * 14))
    if t > 3.95:
        img = img * max(0.0, 1 - (t - 3.95) / 0.45)
    ff.stdin.write(np.clip(img * 255, 0, 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
print('frames', len(seq), 'reveal', R_N, 'rise', len(rise))
