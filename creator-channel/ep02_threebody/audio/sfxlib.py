"""横竖版混音共用：总线、读音频、滤波器和合成音效。"""
import json
from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
rng = np.random.default_rng(47)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, hi, order=4):
    return sosfilt(butter(order, hi, btype="low", fs=SR, output="sos"), x)


def hp(x, lo, order=4):
    return sosfilt(butter(order, lo, btype="high", fs=SR, output="sos"), x)


class Bus:
    def __init__(self, n):
        self.n = n
        self.x = np.zeros((2, n))

    def place(self, sig, t0, gain=1.0, pan=0.0):
        N = self.n
        i = int(round(t0 * SR))
        if i >= N or len(sig) == 0:
            return
        if sig.ndim == 1:
            th = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(th), sig * np.sin(th)]) * np.sqrt(2)
        j0 = max(0, -i)
        sig = sig[:, j0 : N - i]
        i = max(i, 0)
        self.x[:, i : i + sig.shape[1]] += sig * gain


def load(path):
    y, _ = librosa.load(ROOT / path, sr=SR, mono=False)
    return y if y.ndim == 2 else np.stack([y, y])


def seg(y, a, b):
    return y[:, int(a * SR) : int(b * SR)].copy()


def ramp(n, up=True):
    r = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    return r if up else r[::-1]


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9)


def load_vo(path):
    """读一句旁白并把有声部分的响度统一到 -20 dBFS（百炼各句音量差异很大）。"""
    y, _ = librosa.load(ROOT / path, sr=SR, mono=True)
    fr = librosa.util.frame(np.pad(y, (0, 1200)), frame_length=1200, hop_length=1200)
    e = np.sqrt((fr**2).mean(axis=0))
    act = e[e > e.max() * 0.08]
    return y * 10 ** (-20 / 20) / (np.sqrt((act**2).mean()) + 1e-9)


MOOD_DB = {"hype": 1.0, "quiet": -2.5}


def vo_gain(lid):
    """归一化抹平了句间轻重，按台词表的 mood 补回：高潮句略推，安静句收住。"""
    for f in ("audio/vo_lines.json",):
        for ln in json.loads((ROOT / f).read_text()):
            if ln["id"] == lid:
                return 10 ** (MOOD_DB.get(ln.get("mood"), 0.0) / 20)
    return 1.0


def vocal_pocket(x, depth=0.6):
    """固定 EQ：把音乐 1–4 kHz 压低约 8 dB，给旁白留位置；不随旁白起落，所以没有抽吸感。"""
    return x - depth * np.stack([bp(x[c], 1000, 4000, 2) for c in range(x.shape[0])])


def section_gain(n, sections, ramp=1.5):
    """按段落的固定音量（混音推子自动化）：sections = [(t0, t1, dB)]，段落边界用 ramp 秒缓变。"""
    t = np.arange(n) / SR
    g = np.zeros(n)
    for t0, t1, db in sections:
        g += db * np.clip((t - t0) / ramp, 0, 1) * np.clip((t1 - t) / ramp, 0, 1)
    return 10 ** (g / 20)


def duck_curve(vg):
    d = uniform_filter1d(vg, int(0.45 * SR))
    return np.clip(uniform_filter1d(d, int(0.12 * SR)) * 1.6, 0, 1)


def room_ir(dur=2.2):
    n = int(dur * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.55 * SR))
    return lp(ir, 5000) / np.sqrt(np.sum(ir**2))


def pitch_sweep(f0, f1, dur, tau):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / (dur / 4))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, tau)


def noise_sweep(dur, f0, f1, power=1.0):
    n = int(dur * SR)
    out = np.zeros(n)
    hop, win = 960, 1920
    w = np.hanning(win)
    src = rng.standard_normal(n + win)
    for s in range(0, n, hop):
        k = (s / n) ** power
        fc = f0 * (f1 / f0) ** k
        piece = bp(src[s : s + win], max(40, fc * 0.7), min(SR / 2 - 100, fc * 1.4), order=2) * w
        m = max(0, min(win, n - s))
        out[s : s + m] += piece[:m]
    return out / (np.abs(out).max() + 1e-9)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def add(*xs):
    out = np.zeros(max(len(x) for x in xs))
    for x in xs:
        out[: len(x)] += x
    return out


def tom(f0=140, f1=55, tau=0.35):
    s = pitch_sweep(f0, f1, 0.9, tau)
    c = hp(noise(0.006), 2000) * 0.3
    s[: len(c)] += c
    return s


def taiko():
    return pitch_sweep(95, 40, 1.4, 0.5) + bp(noise(1.4), 70, 420) * env_exp(int(1.4 * SR), 0.12) * 0.6


def thump():
    return pitch_sweep(130, 70, 0.3, 0.07) + bp(noise(0.3), 300, 2500) * env_exp(int(0.3 * SR), 0.01) * 0.4


def click(dur=0.012, lo=2500, tau=0.003):
    return hp(noise(dur), lo) * env_exp(int(dur * SR), tau)


def crowd_layer(dur, seed=0):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    for lo, hi in [(250, 600), (500, 1100), (900, 1800), (1800, 3500)]:
        lfo = np.interp(np.arange(n), np.linspace(0, n, max(4, int(dur * 2))), 0.6 + 0.4 * r.random(max(4, int(dur * 2))))
        out += bp(r.standard_normal(n), lo, hi) * lfo
    return out / np.abs(out).max()


def impact(dur=2.5):
    s = pitch_sweep(62, 28, dur, 1.0)
    s[: int(0.15 * SR)] += hp(noise(0.15), 1200) * env_exp(int(0.15 * SR), 0.03) * 0.6
    s[: int(1.0 * SR)] += bp(noise(1.0), 90, 900) * env_exp(int(1.0 * SR), 0.18) * 0.5
    return s


def braam(dur=3.0, f=55):
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = sum(((t * f * m) % 1 * 2 - 1) * g for m, g in [(1, 1), (1.5, 0.6), (2, 0.5), (3, 0.3)])
    return lp(saw, 500) * np.clip(t / 0.05, 0, 1) * np.exp(-t / 1.2)


def whoosh(dur, f0=300, f1=5000, power=0.7):
    return noise_sweep(dur, f0, f1, power) * np.hanning(int(dur * SR))


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / t[-1]
    tone = np.sin(2 * np.pi * np.cumsum(200 * (4 ** u)) / SR) * u**3
    return noise_sweep(dur, 200, 7000, 1.4) * u**2 * 0.8 + tone * 0.25


def piano(freq, dur=4.0, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, g in [(1, 1), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.06)]:
        fk = freq * k * (1 + 0.0004 * k * k)
        s += g * np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.6 + 0.5 * k))
    s[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return s * vel


def rim_clank():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) * g for f, d, g in [(620, 9, 1), (1340, 12, 0.6), (2210, 16, 0.4), (3170, 22, 0.25)])
    return add(s, click(0.01, 1500, 0.004) * 2)


def dribble_room():
    """空球馆里的拍球声：短促低频 + 长混响尾巴。"""
    d = thump()
    tail = fftconvolve(d, rng.standard_normal(int(1.6 * SR)) * env_exp(int(1.6 * SR), 0.45))[: int(1.9 * SR)]
    tail = lp(tail, 3000)
    tail /= np.abs(tail).max() + 1e-9
    out = np.zeros(len(tail))
    out[: len(d)] += d
    return out + tail * 0.35
