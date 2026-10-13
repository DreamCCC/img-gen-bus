"""和声引导轨：Ebmaj9 – Cm9 – Abmaj9 – Bb9sus，每个和弦两小节，速度和起点对齐原曲。
输出 out/guide.wav（给 Suno 当上传素材）和 out/preview_vocal_on_guide.mp3（原唱叠在引导轨上，检查对齐）。
"""
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

ROOT = Path(__file__).parent
SR = 44100
IBI = 0.46155                    # 一拍的秒数（130.0 BPM，64/128/192 拍长距自相关一致）
T0 = 0.955 - 0.016 - 32 * IBI    # 0.955 s 是降E 和弦块的第一小节第一拍；-16 ms 抵消合成音起音延迟；往前推一整轮从负时间起步
DUR = 219.0
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CH = [  # (贝斯根音, 和弦音) —— City Pop 常用的七、九和弦配置
    (39, [55, 58, 62, 65, 67]),   # Ebmaj9：G Bb D F G
    (36, [55, 58, 62, 63, 67]),   # Cm9：G Bb D Eb G
    (44, [55, 60, 63, 67, 70]),   # Abmaj9：G C Eb G Bb
    (46, [56, 60, 63, 65, 68]),   # Bb9sus：Ab C Eb F Ab
]
n = int(DUR * SR)
mix = np.zeros(n)


def place(sig, t, g=1.0):
    i = int(t * SR)
    if i >= n:
        return
    j = max(0, -i)
    i = max(0, i)
    m = min(len(sig) - j, n - i)
    if m > 0:
        mix[i:i + m] += sig[j:j + m] * g


def rhodes(f, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    mod = np.sin(2 * np.pi * f * 1.0 * t) * 1.2 * np.exp(-t * 3)
    s = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 1.6)
    s += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    s *= 1 + 0.15 * np.sin(2 * np.pi * 5 * t)
    s[: 200] *= np.linspace(0, 1, 200)
    return s * vel


def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 8)
    env = np.minimum(1, t / 0.005) * np.exp(-t * 2.5)
    return s * env


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


rng = np.random.default_rng(1)


def noise_hit(dur, tau, lo):
    s = rng.standard_normal(int(dur * SR))
    s = np.diff(np.concatenate([[0], s])) if lo > 3000 else s
    return s * np.exp(-np.arange(len(s)) / (tau * SR))


bar = 4 * IBI
k = 0
t = T0
while t < DUR:
    root, notes = CH[(k // 2) % 4]
    # 电钢：每小节第 1 拍、第 2 拍后半的切分
    for off, vel in ((0, 1.0), (1.5, 0.7), (3.0, 0.55)):
        for m in notes:
            place(rhodes(midi(m), IBI * 1.6, vel), t + off * IBI, 0.07)
    # 贝斯：八分音符的跳跃（根音、八度）
    for i, (off, oct_) in enumerate(((0, 0), (0.75, 12), (1.5, 0), (2, 0), (2.75, 12), (3.5, 7))):
        place(bass(midi(root + oct_), IBI * 0.7), t + off * IBI, 0.32)
    # 鼓：1、3 拍底鼓，2、4 拍军鼓，八分踩镲
    for b in range(4):
        tb = t + b * IBI
        if b in (0, 2):
            place(kick(), tb, 0.5)
        else:
            place(noise_hit(0.25, 0.05, 1000), tb, 0.12)
        for h in (0, 0.5):
            place(noise_hit(0.05, 0.012, 6000), tb + h * IBI, 0.05)
    t += bar
    k += 1

mix /= np.abs(mix).max() * 1.12
sf.write(OUT / "guide.wav", np.stack([mix, mix], 1), SR)

voc, _ = librosa.load(ROOT / "stems/htdemucs_ft/baby_original/vocals.wav", sr=SR, mono=False)
m = min(voc.shape[1], n)
pre = np.stack([mix[:m] * 0.6, mix[:m] * 0.6]) + voc[:, :m] * 0.9
pre /= np.abs(pre).max() * 1.05
sf.write(OUT / "preview_vocal_on_guide.wav", pre.T, SR)
print("ok", OUT)
