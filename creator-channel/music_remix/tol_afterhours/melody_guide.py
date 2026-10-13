"""只有主旋律的上传音频：原唱分轨的音高 → 量化到半音 → 合成音色，不带伴奏，时间和原曲一致。
输出 upload/tol_melody_only.mp3
"""
import subprocess
import numpy as np
import soundfile as sf
from pathlib import Path
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfilt, fftconvolve

HERE = Path(__file__).parent
SR = 44100
DUR = 292.2

d = np.load(HERE / "f0.npz")
f0, rms, hop = d["f0"], d["rms"], float(d["hop"])
ok = np.isfinite(f0) & (rms > rms.max() * 0.05)
mm = np.where(ok, 12 * np.log2(np.nan_to_num(f0, nan=1.0) / 440) + 69, 0)
q = np.round(median_filter(mm, size=9))
q[~ok] = 0
q[(q < 47) | (q > 79)] = 0

notes = []                      # (start, end, midi)
i = 0
while i < len(q):
    j = i
    while j < len(q) and q[j] == q[i]:
        j += 1
    if q[i] > 0 and (j - i) * hop >= 0.07:
        s, e = i * hop, j * hop
        if notes and notes[-1][2] == q[i] and s - notes[-1][1] < 0.06:
            notes[-1] = (notes[-1][0], e, q[i])
        else:
            notes.append((s, e, q[i]))
    i = j


def lead(m, dur):
    n = int((dur + 0.06) * SR)
    t = np.arange(n) / SR
    f = 440 * 2 ** ((m - 69) / 12) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))
    ph = np.cumsum(f) / SR
    s = (2 * (ph % 1) - 1) * 0.5 + np.sin(2 * np.pi * ph)
    env = np.minimum(1, t / 0.015) * np.clip((dur + 0.06 - t) / 0.06, 0, 1)
    return s * env


n = int(DUR * SR)
mel = np.zeros(n)
for s, e, m in notes:
    sig = lead(m, e - s)
    a = int(s * SR)
    k = min(len(sig), n - a)
    mel[a:a + k] += sig[:k]
mel = sosfilt(butter(2, 3500, "low", fs=SR, output="sos"), mel)
rng = np.random.default_rng(3)
ir_t = np.arange(int(1.2 * SR)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 4)
ir /= np.sqrt((ir ** 2).sum())
mel = mel + fftconvolve(mel, ir)[:n] * 0.15
mel /= np.abs(mel).max() / 0.89

tmp = HERE / "out/_melody_only.wav"
sf.write(tmp, mel, SR)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-b:a", "320k",
                str(HERE / "upload/tol_melody_only.mp3")], check=True)
tmp.unlink()
print(len(notes), "notes,", f"{notes[0][0]:.2f}–{notes[-1][1]:.2f}s")
