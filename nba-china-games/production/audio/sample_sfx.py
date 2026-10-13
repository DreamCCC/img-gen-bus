"""按时间轴 JSON 的时间点合成样片音效，与画面共用同一份时间轴。
用法：python sample_sfx.py [out.wav] [cues.json]
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
CUE = json.loads((Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "scenes/sample_cues.json").read_text())
SR = 48000
N = int(SR * CUE["duration"])
rng = np.random.default_rng(3)
mix = np.zeros((2, N))


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, hi, order=4):
    return sosfilt(butter(order, hi, btype="low", fs=SR, output="sos"), x)


def hp(x, lo, order=4):
    return sosfilt(butter(order, lo, btype="high", fs=SR, output="sos"), x)


def place(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    th = (pan + 1) * np.pi / 4
    mix[0, i : i + len(sig)] += sig * np.cos(th) * np.sqrt(2)
    mix[1, i : i + len(sig)] += sig * np.sin(th) * np.sqrt(2)


def pitch_sweep(f0, f1, dur, tau):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / (dur / 4))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, tau)


def noise_sweep(dur, f0, f1, power=1.0):
    """分块带通扫频噪声：用于转场呼啸和上升音。"""
    n = int(dur * SR)
    out = np.zeros(n)
    hop, win = 960, 1920
    w = np.hanning(win)
    src = rng.standard_normal(n + win)
    for s in range(0, n, hop):
        k = (s / n) ** power
        fc = f0 * (f1 / f0) ** k
        seg = bp(src[s : s + win], max(40, fc * 0.7), min(SR / 2 - 100, fc * 1.4), order=2) * w
        out[s : s + win][: max(0, min(win, n - s))] += seg[: max(0, min(win, n - s))]
    return out / (np.abs(out).max() + 1e-9)


def tom(f0=140, f1=55, tau=0.35):
    s = pitch_sweep(f0, f1, 0.9, tau)
    click = hp(rng.standard_normal(int(0.006 * SR)), 2000) * 0.3
    s[: len(click)] += click
    return s


def taiko():
    s = pitch_sweep(95, 40, 1.4, 0.5)
    body = bp(rng.standard_normal(int(1.4 * SR)), 70, 420) * env_exp(int(1.4 * SR), 0.12) * 0.6
    return s + body


def crowd_layer(dur):
    """多段共振峰噪声叠加，各自随机起伏，模拟大量人声汇成的声浪。"""
    n = int(dur * SR)
    out = np.zeros(n)
    for lo, hi in [(250, 600), (500, 1100), (900, 1800), (1800, 3500)]:
        lfo = np.interp(np.arange(n), np.linspace(0, n, 60), 0.6 + 0.4 * rng.random(60))
        out += bp(rng.standard_normal(n), lo, hi) * lfo
    return out / np.abs(out).max()


T = np.arange(N) / SR

# 1. 低音铺底：开头渐入，扣篮前 0.25 秒抽空，扣篮后回来
drone = sum(np.sin(2 * np.pi * f * T) * g for f, g in [(55, 1), (82.5, 0.5), (110, 0.35)])
dg = np.clip(T / 1.5, 0, 1)
dg *= np.where((T > CUE["suck"]) & (T < CUE["slam"]), 0.1, 1)
dg *= np.clip((CUE["duration"] - T) / 0.8, 0, 1)
place(lp(drone, 300) * dg, 0, 0.10)

# 2. 观众：A 段随呼喊节拍起伏；B 段压低；扣篮瞬间爆发
crowd = crowd_layer(CUE["duration"])
cg = 0.25 * np.clip(T / 1.2, 0, 1)
for b in CUE["chant"]:
    cg += 0.55 * (T >= b) * np.exp(-np.clip(T - b, 0, None) / 0.22) * np.clip((T - b) / 0.03, 0, 1)
cg *= np.where(T > CUE["dive"][0], np.clip(1 - (T - CUE["dive"][0]) / 0.5, 0.18, 1), 1)
cg *= np.where((T > CUE["suck"]) & (T < CUE["slam"]), 0.0, 1)
roar = (T >= CUE["slam"]) * (0.25 + 0.95 * np.exp(-np.clip(T - CUE["slam"], 0, None) / 1.1))
cg = np.where(T >= CUE["slam"], roar, cg)
cg *= np.clip((CUE["duration"] - T) / 1.0, 0, 1)
place(crowd * cg, 0, 0.55)

# 3. 俯冲转场的呼啸
d0, d1 = CUE["dive"]
place(noise_sweep(d1 - d0 + 0.2, 300, 5000, 0.7) * np.hanning(int((d1 - d0 + 0.2) * SR)), d0, 0.35)

# 4. 球场线描绘时的细碎高频
for k in range(16):
    t0 = CUE["courtDraw"][0] + k * 0.055
    ping = np.sin(2 * np.pi * (2400 + 900 * rng.random()) * np.arange(int(0.12 * SR)) / SR) * env_exp(int(0.12 * SR), 0.03)
    place(ping, t0, 0.05, pan=rng.uniform(-0.6, 0.6))

# 5. 鼓：每拍一记低鼓，逐渐加重；三处大鼓
for i, t0 in enumerate(CUE["toms"]):
    place(tom(), t0, 0.35 + 0.05 * i)
for t0 in CUE["taiko"]:
    place(taiko(), t0, 0.6)
for k in range(int((CUE["suck"] - 4.0) / 0.25)):
    t0 = 4.0 + k * 0.25
    tick = hp(rng.standard_normal(int(0.03 * SR)), 6000) * env_exp(int(0.03 * SR), 0.008)
    place(tick, t0, 0.12 if k % 2 else 0.2, pan=0.3 if k % 2 else -0.3)

# 6. 传球呼啸
place(noise_sweep(CUE["passArrive"] - CUE["pass"] + 0.1, 900, 3500) * np.hanning(int((CUE["passArrive"] - CUE["pass"] + 0.1) * SR)), CUE["pass"], 0.3)

# 7. 上升音：在扣篮前 0.25 秒硬切
r0, r1 = CUE["riser"]
rn = int((r1 - r0) * SR)
rt = np.arange(rn) / SR
riser = noise_sweep(r1 - r0, 200, 7000, 1.4) * (rt / rt[-1]) ** 2
tone = np.sin(2 * np.pi * np.cumsum(200 * (4 ** (rt / rt[-1]))) / SR) * (rt / rt[-1]) ** 3
place(riser * 0.8 + tone * 0.25, r0, 0.45)

# 8. 扣篮冲击
ts = CUE["slam"]
place(pitch_sweep(62, 28, 2.5, 1.2), ts, 0.95)
place(hp(rng.standard_normal(int(0.15 * SR)), 1200) * env_exp(int(0.15 * SR), 0.03), ts, 0.6)
place(bp(rng.standard_normal(int(1.0 * SR)), 90, 900) * env_exp(int(1.0 * SR), 0.18), ts, 0.5)
bn = int(3.0 * SR)
bt = np.arange(bn) / SR
saw = sum(((bt * f) % 1 * 2 - 1) * g for f, g in [(55, 1), (82.5, 0.6), (110, 0.5), (164.8, 0.3)])
braam = lp(saw, 500) * np.clip(bt / 0.05, 0, 1) * np.exp(-bt / 1.2)
place(braam, ts, 0.22)
place(bp(rng.standard_normal(int(0.35 * SR)), 2000, 7000) * env_exp(int(0.35 * SR), 0.1), ts + 0.04, 0.25)

# 9. 球落地弹跳（与画面同一条物理公式）
def thump():
    return pitch_sweep(130, 70, 0.3, 0.07) + bp(rng.standard_normal(int(0.3 * SR)), 300, 2500) * env_exp(int(0.3 * SR), 0.01) * 0.4


if "bounceTimes" in CUE:
    for k, tb in enumerate(CUE["bounceTimes"]):
        place(thump(), tb, 0.55 * 0.56**k)
else:
    b = CUE["ball"]
    t1 = np.sqrt(2 * (b["groundY"] - b["startY"]) / b["g"])
    tb, v = ts + t1, b["g"] * t1
    for k in range(b["bounces"] + 1):
        place(thump(), tb, 0.55 * (v / (b["g"] * t1)))
        v *= b["e"]
        tb += 2 * v / b["g"]

# 10. 翻牌声，最后一记落在 flapLand
fs, fl = CUE["flapStart"], CUE["flapLand"]
for k in range(int((fl - fs) / 0.03)):
    clk = hp(rng.standard_normal(int(0.01 * SR)), 2500) * env_exp(int(0.01 * SR), 0.003)
    place(clk, fs + k * 0.03, 0.15, pan=rng.uniform(-0.4, 0.4))
place(tom(110, 60, 0.25), fl, 0.5)
place(hp(rng.standard_normal(int(0.02 * SR)), 1500) * env_exp(int(0.02 * SR), 0.006), fl, 0.4)

# 混响 + 限幅
ir_n = int(2.2 * SR)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.55 * SR))
ir = lp(ir, 5000) / np.sqrt(np.sum(ir**2))
wet = np.stack([fftconvolve(mix[c], ir)[:N] for c in range(2)])
out = mix + 0.22 * wet
out = np.tanh(out * 1.2)
out /= np.abs(out).max() / 0.89

dst = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out/sample_sfx.wav"
sf.write(dst, out.T, SR)
print("wrote", dst, f"{out.shape[1] / SR:.2f}s")
