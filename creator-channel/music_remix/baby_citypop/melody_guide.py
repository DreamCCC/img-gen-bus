"""备用上传音频：从原唱人声提取的主旋律（合成音色）叠在和声引导轨上。
Suno 拒收原曲录音时，用 upload/baby_melody_guide.mp3 去做 Cover。"""
import numpy as np
import soundfile as sf
from pathlib import Path
from scipy.ndimage import median_filter

HERE = Path(__file__).parent
SR = 44100
IBI = 0.46155
D0 = 0.955                      # 降E 块第一小节第一拍
RAP = (D0 + 72 * 4 * IBI, D0 + 88 * 4 * IBI)   # 说唱段，第 72–87 小节，不写旋律

d = np.load(HERE / "f0.npz")
f0, hop = d["f0"], float(d["hop"])
midi = np.where(np.isfinite(f0), 12 * np.log2(np.nan_to_num(f0, nan=1.0) / 440) + 69, np.nan)
filled = np.nan_to_num(midi, nan=0.0)
q = np.round(median_filter(filled, size=7))
q[~np.isfinite(midi)] = 0

notes = []                      # (start, end, midi)
i = 0
while i < len(q):
    j = i
    while j < len(q) and q[j] == q[i]:
        j += 1
    if q[i] > 0 and (j - i) * hop >= 0.06:
        s, e = i * hop, j * hop
        if not (RAP[0] <= s < RAP[1]):
            if notes and notes[-1][2] == q[i] and s - notes[-1][1] < 0.05:
                notes[-1] = (notes[-1][0], e, q[i])
            else:
                notes.append((s, e, q[i]))
    i = j


def lead(m, dur):
    n = int((dur + 0.05) * SR)
    t = np.arange(n) / SR
    f = 440 * 2 ** ((m - 69) / 12)
    sig = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 7) if f * k < 8000)
    env = np.minimum(1, t / 0.012) * np.clip((dur + 0.05 - t) / 0.05, 0, 1)
    return sig * env


n = int(219.0 * SR)
mel = np.zeros(n)
for s, e, m in notes:
    sig = lead(m, e - s)
    a = int(s * SR)
    k = min(len(sig), n - a)
    mel[a:a + k] += sig[:k]
mel *= 0.18 / (np.abs(mel).max() + 1e-9) * 1.6

g, gsr = sf.read(HERE / "out/guide.wav")
g = g.mean(1) if g.ndim > 1 else g
assert gsr == SR
mix = 0.3 * g[:n] + mel[:len(g[:n])]
mix /= np.abs(mix).max() / 0.9
out = HERE / "upload"
out.mkdir(exist_ok=True)
sf.write(out / "baby_melody_guide.wav", mix, SR)
print(len(notes), "notes, rap gap %.1f–%.1fs" % RAP)
