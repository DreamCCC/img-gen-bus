"""Thinking Out Loud (After Hours Remix)：原唱人声分轨 + guide.py 的立体声伴奏。

人声：降噪门去分离残留 → 均衡 → 压缩 → 长混响 + 附点八分延迟（左右来回）→ 副歌叠加倍人声。
伴奏：低频加厚，给人声让出 700 Hz 和 2.5 kHz，人声一响伴奏轻压 1.5 dB。
母带：总线压缩 → 响度 −14 LUFS → 限幅 −1 dBTP。

先跑 guide.py 生成 out/guide_backing_stereo.wav。
输出 out/tol_afterhours_remix.wav、out/tol_afterhours_remix.mp3
"""
import subprocess
import numpy as np
import soundfile as sf
import librosa
import pyloudnorm as pyln
from pathlib import Path
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from pedalboard import (Pedalboard, HighpassFilter, LowpassFilter, PeakFilter, HighShelfFilter, LowShelfFilter,
                        Compressor, Reverb, PitchShift)

HERE = Path(__file__).parent
SR = 44100
IBI = 0.75949
T0 = 0.083
BAR = 4 * IBI
OFF = 16 * IBI
CHORUS_BARS = [(24, 34), (58, 68), (76, 88)]   # 含尾句；最后一段最满
FINAL = CHORUS_BARS[-1]

back, sr = sf.read(HERE / "out/guide_backing_stereo.wav", dtype="float32")
assert sr == SR
N = len(back)

v, _ = librosa.load(HERE / "stems/htdemucs_ft/tol_original/vocals.wav", sr=SR, mono=True)
voc = np.zeros(N, dtype=np.float32)
a0 = int(OFF * SR)
m = min(len(v), N - a0)
voc[a0:a0 + m] = v[:m]


def env_db(x, win):
    e = np.sqrt(uniform_filter1d(x.astype(np.float64) ** 2, int(win * SR)) + 1e-12)
    return 20 * np.log10(e)


# 降噪门：−40 dB 以下压到 −30 dB（不完全静音，免得一顿一顿），保持 150 ms，开 5 ms、关 120 ms
open_ = maximum_filter1d((env_db(voc, 0.02) > -40).astype(np.float32), int(0.15 * SR))
g = np.where(open_ > 0, 1.0, 10 ** (-30 / 20)).astype(np.float32)
up, down = 1 - np.exp(-1 / (0.005 * SR)), 1 - np.exp(-1 / (0.12 * SR))
gs = np.empty_like(g)
s = g[0]
for i in range(0, N, 64):                      # 64 样本一块做平滑，够用且快
    tgt = g[i]
    s += (tgt - s) * (1 - (1 - (up if tgt > s else down)) ** 64)
    gs[i:i + 64] = s
voc *= gs

chain = Pedalboard([
    HighpassFilter(110),
    PeakFilter(320, -3.0, 1.0),
    PeakFilter(3200, 2.5, 0.8),
    HighShelfFilter(9000, 2.0),
    Compressor(threshold_db=-22, ratio=3.5, attack_ms=4, release_ms=90),
    Compressor(threshold_db=-10, ratio=8, attack_ms=1, release_ms=40),
])
dry = chain(voc[None, :], SR)[0]


def bar_mask(spans, ramp=0.25):
    msk = np.zeros(N, dtype=np.float32)
    for b0, b1 in spans:
        i0, i1 = int((T0 + (4 + b0) * BAR) * SR), int((T0 + (4 + b1) * BAR) * SR)
        msk[i0:i1] = 1
    k = int(ramp * SR)
    return uniform_filter1d(msk, k)


ch_mask = bar_mask(CHORUS_BARS)
fin_mask = bar_mask([FINAL])

# 加倍人声：两份各移 ±12 音分、晚 18 / 27 ms，左右分开；副歌 −11 dB，最后一段副歌 −7 dB
def shifted(x, cents, ms):
    y = Pedalboard([PitchShift(cents / 100)])(x[None, :], SR)[0]
    d = int(ms / 1000 * SR)
    return np.concatenate([np.zeros(d, dtype=np.float32), y[:N - d]])


dbl_gain = ch_mask * (10 ** (-11 / 20)) + fin_mask * (10 ** (-7 / 20) - 10 ** (-11 / 20))
dl = shifted(dry, 12, 18) * dbl_gain
dr = shifted(dry, -12, 27) * dbl_gain

# 混响：预延迟 40 ms，暗一点的长尾巴（混响前先切掉低频和齿音）
pre = int(0.04 * SR)
send = Pedalboard([HighpassFilter(250), LowpassFilter(6500)])(dry[None, :], SR)[0]
send = np.concatenate([np.zeros(pre, dtype=np.float32), send[:N - pre]])
rv = Pedalboard([Reverb(room_size=0.9, damping=0.55, wet_level=1.0, dry_level=0.0, width=1.0)])(
    np.stack([send, send]), SR)

# 附点八分延迟，左右来回，越往后越暗
dly = np.zeros((2, N), dtype=np.float32)
k = int(0.75 * IBI * SR)
tap = Pedalboard([HighpassFilter(300), LowpassFilter(4000)])(dry[None, :], SR)[0]
for i in range(1, 5):
    if k * i >= N:
        break
    dly[i % 2, k * i:] += tap[:N - k * i] * (0.42 ** i)
    tap = Pedalboard([LowpassFilter(3000)])(tap[None, :], SR)[0]

wet_gain = 0.32 + 0.08 * ch_mask
vox = np.stack([dry + dl * 0.9 + dr * 0.35, dry + dr * 0.9 + dl * 0.35]) + rv * wet_gain + dly * 0.22

# 伴奏：低频按 After Hours 的比例加厚，挖掉 700 Hz 的闷和 2.5 kHz 给人声让位；人声响时再整体轻压 1.5 dB
bk = Pedalboard([LowShelfFilter(120, 6.0), PeakFilter(700, -2.0, 0.8), PeakFilter(2500, -2.0, 0.9)])(back.T.copy(), SR)
vact = uniform_filter1d((env_db(dry, 0.03) > -35).astype(np.float32), int(0.2 * SR))
bk *= (1 - (1 - 10 ** (-1.5 / 20)) * vact)[None, :]

# 人声电平：副歌里人声干声 RMS 比伴奏低 3 dB
seg = slice(int((T0 + 28 * BAR) * SR), int((T0 + 36 * BAR) * SR))
rms = lambda x: np.sqrt(np.mean(x ** 2))
vg = rms(bk[:, seg]) / rms(dry[seg][dry[seg] != 0]) * 10 ** (-3 / 20)
mix = bk + vox * vg

def limit(x, ceil_db=-1.0, look=0.005, release=0.08):
    """前视限幅：增益提前 5 ms 降下来，80 ms 慢慢回升。pedalboard 的 Limiter 会自带补偿增益，不用它。"""
    ceil = 10 ** (ceil_db / 20)
    w = int(look * SR)
    pk = maximum_filter1d(np.abs(x).max(0), 2 * w + 1)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    g = np.empty_like(need)
    c = 1 - np.exp(-64 / (release * SR))
    s = 1.0
    for i in range(0, len(need), 64):
        tgt = need[i:i + 64].min()
        s = tgt if tgt < s else s + (tgt - s) * c
        g[i:i + 64] = s
    g = uniform_filter1d(g, w)
    return np.clip(x * g[None, :], -ceil, ceil)


master = Pedalboard([Compressor(threshold_db=-14, ratio=2, attack_ms=30, release_ms=200)])
mix = master(mix.astype(np.float32), SR)
meter = pyln.Meter(SR)
lufs = meter.integrated_loudness(mix.T)
for _ in range(2):
    mix = limit(mix * 10 ** ((-14 - meter.integrated_loudness(mix.T)) / 20))

out = HERE / "out/tol_afterhours_remix.wav"
sf.write(out, mix.T, SR, subtype="PCM_24")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out), "-b:a", "320k",
                str(out.with_suffix(".mp3"))], check=True)
print(f"vocal gain {20 * np.log10(vg):+.1f} dB; before norm {lufs:.1f} LUFS; "
      f"final {meter.integrated_loudness(mix.T):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS")
