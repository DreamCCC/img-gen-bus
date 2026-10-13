"""After Hours 风格引导轨：暗色合成器浪潮编曲 + 原曲主旋律（合成音色），不含任何原录音。

时间轴对齐原曲（79 BPM，拍点线性拟合），前面加 4 小节无鼓前奏、后面加 4 小节淡出。
和声：D→Bm9、G→Gmaj9、A→Aadd9、Em→Em9，原旋律音都在新和弦里，整体转向关系小调。
编曲按「空 → 满 → 空 → 最满」排：主歌前半无鼓，预副歌加鼓并在最后两拍全停，副歌双倍速四拍底鼓，
solo 段撤鼓再重新推起来，最后一遍副歌最满。

输出
  out/guide_backing.wav          只有伴奏
  out/guide_backing_stereo.wav   只有伴奏，立体声版，给 remix.py
  upload/tol_melody_guide.mp3    伴奏 + 主旋律，给 Suno 做 Cover
  upload/tol_original.mp3        原曲，先试这个，被拒再用上面那个
  out/preview_vocal_on_guide.mp3 原唱叠在伴奏上，检查对齐和味道
"""
import subprocess
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfilt, fftconvolve

HERE = Path(__file__).parent
SR = 44100
IBI = 0.75949                    # 79.00 BPM，352 个拍点线性拟合，残差 std 10 ms
T0 = 0.083                       # 原曲第一小节第一拍；拟合值 0.118 减去和原伴奏起音互相关测出的 35 ms
INTRO, OUTRO = 4, 4              # 小节
OFF = INTRO * 4 * IBI            # 原曲时间 + OFF = 引导轨时间
BAR = 4 * IBI
S16 = IBI / 4

SECTIONS = [("V", 16), ("PC", 8), ("CH", 8), ("PCH", 2), ("V", 16), ("PC", 8), ("CH", 8), ("PCH", 2),
            ("SOLO", 8), ("CH", 8), ("PCH", 4)]
NBAR = sum(n for _, n in SECTIONS)                     # 88
TOTAL = INTRO + NBAR + OUTRO
DUR = (TOTAL * BAR) + 3.0
N = int(DUR * SR)

CH = {  # 贝斯根音, 铺底音（无根音的九和弦配置，挤在 D3–D4 之间，暗、厚）
    "Bm9":   (35, [50, 54, 57, 61]),   # D F# A C#
    "Bm9/F#": (42, [50, 54, 57, 61]),
    "Gmaj9": (31, [54, 57, 59, 62]),   # F# A B D
    "Aadd9": (33, [52, 57, 59, 61]),   # E A B C#
    "Em9":   (40, [50, 54, 55, 59]),   # D F# G B
    "F#m7":  (42, [52, 54, 57, 61]),   # E F# A C#
    "Dmaj9": (38, [52, 54, 57, 61]),   # E F# A C#
}
V_PAIR = ["Bm9"] * 2 + ["Bm9/F#"] * 2 + ["Gmaj9"] * 2 + ["Aadd9"] * 2
PC8 = (["Em9"] * 4 + ["Aadd9"] * 2 + ["Bm9"] * 2 + ["Em9"] * 4 + ["Aadd9"] * 4) * 2
PCH2 = ["Bm9", "Aadd9", "Gmaj9", "F#m7", "Em9", "Em9", "Dmaj9", "Dmaj9"]


def chart():
    beats, secs = [], []
    for name, n in SECTIONS:
        seq = {"V": V_PAIR * (n // 2), "CH": V_PAIR * (n // 2), "SOLO": V_PAIR * (n // 2),
               "PC": PC8, "PCH": PCH2 * (n // 2)}[name]
        beats += seq
        secs += [(name, i) for i in range(n)]
    return beats, secs


BEATS, SECS = chart()
FIRST_V_END = 16                 # 第一段主歌之后的 V 都算第二段
LAST_CH_START = 76


def arr(g):
    """第 g 小节（含前奏）的编曲参数。"""
    a = dict(kick=None, snare=False, hats=0.0, bass=0.0, cut=1200, pad=1.0, arp=0.0,
             riser=False, brk=False, big=False)
    if g < INTRO:
        a.update(cut=800 + g * 300, pad=0.55, arp=0.2 * max(0, g - 1), riser=g == INTRO - 1)
        return a
    c = g - INTRO
    if c >= NBAR:
        o = c - NBAR
        a.update(cut=1400 - o * 250, pad=0.5 - o * 0.1, arp=max(0.0, 0.4 - o * 0.12))
        return a
    name, i = SECS[c]
    if name == "V" and c < FIRST_V_END:
        a.update(bass=0.45, cut=1100, pad=0.45, arp=0.3)
        if i >= 8:
            a.update(kick="half", hats=0.35, bass=0.65, cut=1400, pad=0.6)
    elif name == "V":
        a.update(kick="quarter", snare=True, hats=0.55, bass=0.8, cut=1500, pad=0.6, arp=0.45)
    elif name == "PC":
        a.update(kick="quarter", snare=True, hats=0.6, bass=0.85, cut=1600 + i * 300, arp=0.5,
                 riser=i >= 6, brk=i == 7)
    elif name in ("CH", "PCH"):
        big = c >= LAST_CH_START
        a.update(kick="eighth", snare=True, hats=1.0, bass=1.0, cut=5000 if big else 4000,
                 pad=1.25 if big else 1.0, arp=0.75 if big else 0.6, big=big)
    elif name == "SOLO":
        if i < 4:
            a.update(cut=900 + i * 150, pad=0.5, arp=0.5)
        else:
            a.update(kick="quarter" if i < 6 else "eighth", snare=i >= 6, hats=0.3 + 0.15 * (i - 4),
                     bass=0.5 + 0.15 * (i - 4), cut=1500 + (i - 4) * 600, arp=0.6, riser=i >= 6, brk=i == 7)
    return a


midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(7)
bus = {k: np.zeros(N) for k in ("pad", "arp", "bass", "drums", "lead", "fx")}


def place(name, sig, t, g=1.0):
    i = int(round(t * SR))
    if i >= N:
        return
    j = max(0, -i)
    i = max(0, i)
    m = min(len(sig) - j, N - i)
    if m > 0:
        bus[name][i:i + m] += sig[j:j + m] * g


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def saw(f, t, ph=0.0):
    return 2 * ((f * t + ph) % 1.0) - 1


def pad_seg(notes, dur, cut):
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in notes:
        f = midi(m)
        for det in (-0.07, 0.0, 0.07):
            s += saw(f * 2 ** (det / 12), t, rng.random())
    s = lp(s, cut, 4)
    env = np.minimum(1, t / 0.12) * np.clip((dur + 0.6 - t) / 0.6, 0, 1)
    return s * env / len(notes)


def pluck(f, dur, cut):
    t = np.arange(int(dur * SR)) / SR
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.6 + saw(f * 1.003, t) * 0.4
    return lp(s, cut, 2) * np.exp(-t * 14) * np.minimum(1, t / 0.003)


def bass_note(f, dur):
    t = np.arange(int(dur * SR)) / SR
    s = saw(f, t) * 0.6 + np.sin(2 * np.pi * f * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t * 7)
    return lp(s, 700, 2) * env


def kick():
    t = np.arange(int(0.4 * SR)) / SR
    f = 45 + 110 * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    s[: int(0.004 * SR)] += rng.standard_normal(int(0.004 * SR)) * 0.3
    return np.tanh(s * 1.5)


def gated_snare():
    """80 年代门限混响军鼓：一声之后跟一段平的混响尾巴，250 ms 处突然切掉。"""
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.7
    crack = hp(rng.standard_normal(n), 1800) * np.exp(-t * 25)
    tail = lp(hp(rng.standard_normal(n), 600), 6000) * 0.45
    gate = np.clip((0.25 - t) / 0.012, 0, 1) * np.minimum(1, t / 0.01)
    return body + crack + tail * gate


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000, 4) * np.exp(-t * (18 if open_ else 70))


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 2048
    for i in range(0, n, blk):
        fc = 400 + 7000 * (i / n) ** 2
        out[i:i + blk] = lp(x[i:i + blk], fc, 2)
    return out * (t / dur) ** 2


bar_t = lambda g: T0 + g * BAR
kick_times = []

for g in range(TOTAL):
    a = arr(g)
    tb = bar_t(g)
    c = g - INTRO
    for b in range(4):
        if 0 <= c < NBAR:
            name = BEATS[c * 4 + b]
        else:
            name = "Bm9" if g < INTRO else "Dmaj9"
        root, notes = CH[name]
        t = tb + b * IBI
        muted = a["brk"] and b >= 2
        new_chord = b == 0 or (0 <= c < NBAR and BEATS[c * 4 + b] != BEATS[c * 4 + b - 1])
        if new_chord:
            dur = IBI if 0 <= c < NBAR else BAR
            bb = b + 1
            while bb < 4 and 0 <= c < NBAR and BEATS[c * 4 + bb] == name:
                dur += IBI
                bb += 1
            pn = notes + ([n + 12 for n in notes[1:]] if a["big"] else [])
            place("pad", pad_seg(pn, dur, a["cut"]), t, 0.5 * a["pad"])
        if a["arp"] > 0:
            tones = [n + 12 for n in notes]
            for s in range(4):
                m = tones[(b * 4 + s) % len(tones)] + (12 if s == 3 else 0)
                place("arp", pluck(midi(m), S16 * 1.8, 1200 + a["cut"] * 0.4), t + s * S16, 0.22 * a["arp"])
        if a["bass"] > 0 and not muted:
            for s in range(4):
                oct_ = 12 if s == 2 else 0
                place("bass", bass_note(midi(root + oct_), S16 * 0.9), t + s * S16, 0.8 * a["bass"])
        if muted:
            continue
        if a["kick"] == "half" and b in (0, 2) or a["kick"] == "quarter" or a["kick"] == "eighth":
            place("drums", kick(), t, 1.0)
            kick_times.append(t)
        if a["kick"] == "eighth":
            place("drums", kick(), t + IBI / 2, 0.8)
            kick_times.append(t + IBI / 2)
        if a["snare"] and b in (1, 3):
            place("drums", gated_snare(), t, 0.42)
        if a["hats"] > 0:
            for s in (1, 3):
                place("drums", hat(open_=(s == 3 and a["kick"] == "eighth")), t + s * S16, 0.09 * a["hats"])
    if a["riser"]:
        place("fx", riser(BAR), tb, 0.12)

# 侧链压缩：底鼓一响，铺底和贝斯往下一压再回弹，这是这类曲风「呼吸感」的来源
duck = np.ones(N)
tt = np.arange(int(0.35 * SR)) / SR
shape = 1 - 0.55 * np.exp(-tt / 0.11)
for t in kick_times:
    i = int(t * SR)
    m = min(len(shape), N - i)
    duck[i:i + m] = np.minimum(duck[i:i + m], shape[:m])

ir_t = np.arange(int(2.2 * SR)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
ir = lp(ir, 5000)
ir /= np.sqrt((ir ** 2).sum())        # 单位能量：wet 就是湿声和干声的能量比


def verb(x, wet):
    return x + fftconvolve(x, ir)[:N] * wet


def delay(x, d, fb=0.35, taps=4):
    y = x.copy()
    k = int(d * SR)
    for i in range(1, taps + 1):
        y[k * i:] += x[:-k * i] * fb ** i
    return y


pad = verb(bus["pad"] * duck, 0.5)
arp = verb(delay(bus["arp"], IBI * 0.75), 0.4) * duck
bass = bus["bass"] * duck
drums = bus["drums"]
fx = verb(bus["fx"], 0.6)
backing = pad + arp + bass + drums + fx
fade = np.ones(N)
fs = int(bar_t(INTRO + NBAR) * SR)
fe = int(bar_t(TOTAL) * SR)
fade[fs:fe] = np.linspace(1, 0, fe - fs) ** 1.5
fade[fe:] = 0
backing *= fade
scale = 0.89 / np.abs(backing).max()
backing *= scale

OUT = HERE / "out"
UP = HERE / "upload"
OUT.mkdir(exist_ok=True)
UP.mkdir(exist_ok=True)
sf.write(OUT / "guide_backing.wav", np.stack([backing, backing], 1), SR)

# 立体声版（给 remix.py）：干声居中，铺底和效果左右用两条不同的混响尾巴，琶音延迟左右来回弹
ir_r = lp(rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6), 5000)
ir_r /= np.sqrt((ir_r ** 2).sum())
wet = lambda x, h: fftconvolve(x, h)[:N]
pd = bus["pad"] * duck
a_dry = bus["arp"]
k = int(IBI * 0.75 * SR)
a_l, a_r = a_dry.copy(), a_dry.copy()
for i in range(1, 5):
    tap = np.concatenate([np.zeros(k * i), a_dry[:-k * i]]) * 0.4 ** i
    (a_l if i % 2 else a_r)[:] += tap
L = pd + wet(pd, ir) * 0.5 + (a_l + wet(a_l, ir) * 0.4) * duck + bus["fx"] + wet(bus["fx"], ir) * 0.6
R = pd + wet(pd, ir_r) * 0.5 + (a_r + wet(a_r, ir_r) * 0.4) * duck + bus["fx"] + wet(bus["fx"], ir_r) * 0.6
C = bass + drums
st = np.stack([L + C, R + C], 1) * fade[:, None] * scale
sf.write(OUT / "guide_backing_stereo.wav", st / max(1.0, np.abs(st).max() / 0.95), SR)

# 主旋律：原唱分轨的音高 → 量化到半音 → 合成音色
d = np.load(HERE / "f0.npz")
f0, rms, hop = d["f0"], d["rms"], float(d["hop"])
ok = np.isfinite(f0) & (rms > rms.max() * 0.05)
mm = np.where(ok, 12 * np.log2(np.nan_to_num(f0, nan=1.0) / 440) + 69, 0)
q = np.round(median_filter(mm, size=9))
q[~ok] = 0
q[(q < 47) | (q > 79)] = 0
notes = []
i = 0
while i < len(q):
    j = i
    while j < len(q) and q[j] == q[i]:
        j += 1
    if q[i] > 0 and (j - i) * hop >= 0.07:
        s, e = i * hop + OFF, j * hop + OFF
        if notes and notes[-1][2] == q[i] and s - notes[-1][1] < 0.06:
            notes[-1] = (notes[-1][0], e, q[i])
        else:
            notes.append((s, e, q[i]))
    i = j


def lead(m, dur):
    n = int((dur + 0.06) * SR)
    t = np.arange(n) / SR
    f = midi(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))
    ph = np.cumsum(f) / SR
    s = (2 * (ph % 1) - 1) * 0.5 + np.sin(2 * np.pi * ph)
    env = np.minimum(1, t / 0.015) * np.clip((dur + 0.06 - t) / 0.06, 0, 1)
    return s * env


for s, e, m in notes:
    place("lead", lead(m, e - s), s)
mel = verb(lp(bus["lead"], 3500), 0.3)
mel *= 0.55 / (np.abs(mel).max() + 1e-9)
mix = backing * 0.62 + mel
mix /= np.abs(mix).max() / 0.9
tmp = OUT / "_melody_guide.wav"
sf.write(tmp, mix, SR)


def mp3(src, dst):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-b:a", "320k", str(dst)], check=True)


mp3(tmp, UP / "tol_melody_guide.mp3")
tmp.unlink()
if not (UP / "tol_original.mp3").exists():
    mp3(HERE / "src/tol_original.wav", UP / "tol_original.mp3")

voc, _ = librosa.load(HERE / "stems/htdemucs_ft/tol_original/vocals.wav", sr=SR, mono=True)
vv = np.zeros(N)
a0 = int(OFF * SR)
m = min(len(voc), N - a0)
vv[a0:a0 + m] = voc[:m]
pre = backing * 0.7 + vv * 0.95
pre /= np.abs(pre).max() / 0.9
tmp = OUT / "_pre.wav"
sf.write(tmp, pre, SR)
mp3(tmp, OUT / "preview_vocal_on_guide.mp3")
tmp.unlink()

print(f"{len(notes)} notes; {TOTAL} bars, {TOTAL * BAR:.1f}s; offset {OFF:.2f}s")
g = INTRO
for name, n in SECTIONS:
    t = bar_t(g)
    o = t - OFF
    print(f"  {name:5s} bar {g - INTRO:3d}  guide {int(t // 60)}:{t % 60:05.2f}  orig {int(o // 60)}:{o % 60:05.2f}")
    g += n
