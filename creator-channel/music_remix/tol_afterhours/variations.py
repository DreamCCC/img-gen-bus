"""主旋律变奏：音高序列和 melody_only 一样，只改节奏、速度和音符长短。

先把原唱提取出的音符清理一遍（滑音、装饰音并进相邻的长音），量化到三连音十六分网格（1/6 拍），
得到以拍为单位的谱，再按 VARIANTS 里的设置各渲染一版。

输出 variations/
  <名字>.mp3 / .mid      全曲，合成音色，只有旋律；mid 可以直接拖进 DAW 换音色、再改
  compare_chorus.mp3     第一段副歌对比：原 melody_only，然后按 VARIANTS 顺序，中间隔 1.5 秒
"""
import subprocess
import numpy as np
import soundfile as sf
from pathlib import Path
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfilt, fftconvolve

HERE = Path(__file__).parent
OUT = HERE / "variations"
SR = 44100
IBI = 0.75949                    # 79 BPM，同 guide.py
T0 = 0.083                       # 原曲第一小节第一拍
CHORUS = (96, 136)               # 第一段副歌 + 尾句，单位：拍


def extract():
    """同 melody_guide.py：原唱音高 → 半音 → (开始秒, 结束秒, midi)。"""
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
            s, e = i * hop, j * hop
            if notes and notes[-1][2] == q[i] and s - notes[-1][1] < 0.06:
                notes[-1] = (notes[-1][0], e, q[i])
            else:
                notes.append((s, e, q[i]))
        i = j
    return notes


def clean(notes):
    """短于 0.17 拍、和紧挨着的音只差 1–2 个半音的，算滑音或装饰音，并进较长的那个邻音。"""
    out = [list(n) for n in notes]
    short, gap = 0.17 * IBI, 0.08
    k = 0
    while k < len(out):
        s, e, m = out[k]
        if e - s >= short:
            k += 1
            continue
        prev = out[k - 1] if k > 0 and s - out[k - 1][1] < gap and abs(out[k - 1][2] - m) <= 2 else None
        nxt = out[k + 1] if k + 1 < len(out) and out[k + 1][0] - e < gap and abs(out[k + 1][2] - m) <= 2 else None
        if nxt and (prev is None or nxt[1] - nxt[0] >= prev[1] - prev[0]):
            nxt[0] = s
        elif prev:
            prev[1] = e
        else:
            k += 1
            continue
        del out[k]
        k = max(0, k - 1)
    return [tuple(n) for n in out]


def to_score(notes, grid=1 / 6):
    """秒 → 拍，起点和终点吸附到网格；同一格里撞车的只留长的。返回 [(拍, 时值拍, midi)]。"""
    sc = {}
    for s, e, m in notes:
        b = round((s - T0) / IBI / grid)
        d = max(1, round((e - T0) / IBI / grid) - b)
        if b not in sc or d > sc[b][1]:
            sc[b] = (b, d, m)
    return fit([(b * grid, d * grid, m) for b, d, m in sorted(sc.values())])


def fit(score, min_d=1 / 6):
    """按起点排序，每个音不盖过下一个音的起点。"""
    score = sorted(score)
    out = []
    for i, (b, d, m) in enumerate(score):
        if i + 1 < len(score):
            d = min(d, score[i + 1][0] - b)
        if d >= min_d * 0.99:
            out.append((b, d, m))
    return out


# ---------- 节奏变换，输入输出都是以拍为单位的谱 ----------

def straighten(score):
    """三连音 → 直拍。一拍里的三个三连八分 (0, 1/3, 2/3) 挪到 (0, 1/2, 3/4)，也就是「1 & a」的跑马节奏；
    其余位置按分段线性插值，再吸附到十六分。撞到前一个音就往后推一格，推不开就丢掉。"""
    xp, fp = [0, 1 / 3, 2 / 3, 1], [0, 1 / 2, 3 / 4, 1]
    warp = lambda x: np.floor(x) + np.interp(x % 1, xp, fp)
    out, last = [], -1
    for b, d, m in score:
        want = int(np.ceil(warp(b) * 4 - 0.5))        # 正好在两格中间时取前一格，弱起音不被推到正拍上
        slot = max(want, last + 1)
        if slot - want > 1:
            continue
        end = max(round(warp(b + d) * 4), slot + 1)
        out.append((slot / 4, (end - slot) / 4, m))
        last = slot
    return fit(out, 1 / 4)


def anticipate(score, beats=(0, 2)):
    """抢拍：落在第 1、3 拍正拍上的音提前一个十六分，结束时间不变；前一个音被截短让位。"""
    out = []
    for b, d, m in score:
        if abs(b % 1) < 1e-6 and int(round(b)) % 4 in beats:
            prev_end = out[-1][0] + out[-1][1] if out else -1
            if not out or out[-1][0] < b - 0.25:
                b, d = b - 0.25, d + 0.25
                if prev_end > b:
                    out[-1] = (out[-1][0], b - out[-1][0], out[-1][2])
        out.append((b, d, m))
    return fit(out, 1 / 8)


def staccato(score, cap):
    return [(b, min(d, cap), m) for b, d, m in score]


def legato(score, max_gap=1.0):
    """句子内部（间隔小于 max_gap 拍）的音一直连到下一个音。"""
    out = []
    for i, (b, d, m) in enumerate(score):
        if i + 1 < len(score) and score[i + 1][0] - (b + d) < max_gap:
            d = score[i + 1][0] - b
        out.append((b, d, m))
    return out


def chop(score, step=0.5, gate=0.6):
    """切片：一拍以上的长音拆成每 step 拍重复一次，像 EDM 里切碎的人声。"""
    out = []
    for b, d, m in score:
        if d < 1.0:
            out.append((b, min(d, step * gate) if d > step else d, m))
            continue
        k = 0
        while k * step < d - 1e-6:
            out.append((b + k * step, min(step * gate, d - k * step), m))
            k += 1
    return out


# ---------- 音色 ----------

midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def lead(m, dur):
    """同 melody_guide.py 的主旋律音色。"""
    n = int((dur + 0.06) * SR)
    t = np.arange(n) / SR
    f = midi(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))
    ph = np.cumsum(f) / SR
    s = (2 * (ph % 1) - 1) * 0.5 + np.sin(2 * np.pi * ph)
    env = np.minimum(1, t / 0.015) * np.clip((dur + 0.06 - t) / 0.06, 0, 1)
    return s * env


def pluck(m, dur):
    n = int((dur + 0.25) * SR)
    t = np.arange(n) / SR
    f = midi(m)
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + (2 * ((f * 1.004 * t) % 1) - 1) * 0.5
    s = sosfilt(butter(2, 2800, "low", fs=SR, output="sos"), s)
    env = np.minimum(1, t / 0.003) * np.exp(-t * 6) * np.clip((dur + 0.25 - t) / 0.25, 0, 1)
    return s * env


def pad_lead(m, dur):
    """慢版用：起音慢、尾巴长，带一点合唱效果。"""
    n = int((dur + 0.35) * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for det in (-0.08, 0.0, 0.08):
        f = midi(m) * 2 ** (det / 12) * (1 + 0.003 * np.sin(2 * np.pi * 4.8 * t))
        ph = np.cumsum(f) / SR
        s += (2 * (ph % 1) - 1) * 0.35 + np.sin(2 * np.pi * ph)
    s = sosfilt(butter(2, 2400, "low", fs=SR, output="sos"), s)
    env = np.minimum(1, t / 0.06) * np.clip((dur + 0.35 - t) / 0.35, 0, 1)
    return s * env / 3


rng = np.random.default_rng(3)
ir_t = np.arange(int(1.6 * SR)) / SR
IR = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.5)
IR /= np.sqrt((IR ** 2).sum())


def render(score, bpm, voice, wet=0.15, b0=0.0, b1=np.inf, lead_in=0.3):
    """b0 ≤ 起点 < b1 的音，按 bpm 排到时间轴上；b0 对齐到 lead_in 秒。"""
    spb = 60 / bpm
    sel = [(b, d, m) for b, d, m in score if b0 <= b < b1]
    end = min(b1, max(b + d for b, d, _ in sel))
    n = int(((end - b0) * spb + lead_in + 2.0) * SR)
    x = np.zeros(n)
    for b, d, m in sel:
        d = min(d, b1 - b)
        sig = voice(m, d * spb)
        i = int(((b - b0) * spb + lead_in) * SR)
        k = min(len(sig), n - i)
        x[i:i + k] += sig[:k]
    x = sosfilt(butter(2, 3500, "low", fs=SR, output="sos"), x)
    x = x + fftconvolve(x, IR)[:n] * wet
    return x / (np.abs(x).max() / 0.89)


def write_mid(path, score, bpm, ppq=480):
    def vlq(v):
        out = [v & 0x7F]
        v >>= 7
        while v:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        return bytes(reversed(out))

    ev = []
    for b, d, m in score:
        ev += [(round(b * ppq), 1, int(m)), (round((b + d) * ppq), 0, int(m))]
    ev.sort(key=lambda e: (e[0], e[1]))
    tr = bytearray(b"\x00\xff\x51\x03" + round(6e7 / bpm).to_bytes(3, "big"))
    tr += b"\x00\xff\x58\x04\x04\x02\x18\x08"
    last = 0
    for tick, on, m in ev:
        tr += vlq(tick - last) + bytes([0x90 if on else 0x80, m, 90 if on else 0])
        last = tick
    tr += b"\x00\xff\x2f\x00"
    head = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + ppq.to_bytes(2, "big")
    path.write_bytes(head + b"MTrk" + len(tr).to_bytes(4, "big") + bytes(tr))


def mp3(x, dst):
    tmp = dst.with_suffix(".wav")
    sf.write(tmp, x, SR)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-b:a", "320k", str(dst)], check=True)
    tmp.unlink()


raw = extract()
cleaned = clean(raw)
base = to_score(cleaned)
straight = straighten(base)

VARIANTS = [  # 名字, BPM, 谱, 音色, 混响, 说明
    ("v0_quant_79", 79, base, lead, 0.15,
     "对照组：原节奏（三连音律动）、原速，只做了清理和量化"),
    ("v1_straight_92", 92, straight, lead, 0.15,
     "三连音改直拍「1 & a」，提速到 92"),
    ("v2_push_108", 108, staccato(anticipate(straight), 0.75), lead, 0.12,
     "直拍 + 第 1、3 拍的音提前一个十六分（抢拍），长音截到 3/4 拍，108 BPM（After Hours 的速度）"),
    ("v3_chop_96", 96, chop(straight), pluck, 0.25,
     "直拍，一拍以上的长音切成八分音符重复，拨弦音色，96 BPM"),
    ("v4_slow_66", 66, legato(base), pad_lead, 0.45,
     "保留三连音，降到 66，句内全部连奏，慢起音长尾巴"),
]

OUT.mkdir(exist_ok=True)
print(f"原始 {len(raw)} 个音 → 清理后 {len(cleaned)} → 量化后 {len(base)}；直拍版 {len(straight)}")

gap = np.zeros(int(1.5 * SR))
orig = [((s - T0) / IBI, (e - s) / IBI, m) for s, e, m in raw]
parts = [render(orig, 79, lead, b0=CHORUS[0], b1=CHORUS[1]), gap]
cursor = len(parts[0]) / SR + 1.5
marks = [("原 melody_only", 0.0)]
for name, bpm, score, voice, wet, desc in VARIANTS:
    mp3(render(score, bpm, voice, wet), OUT / f"{name}.mp3")
    write_mid(OUT / f"{name}.mid", score, bpm)
    seg = render(score, bpm, voice, wet, b0=CHORUS[0], b1=CHORUS[1])
    marks.append((name, cursor))
    parts += [seg, gap]
    cursor += len(seg) / SR + 1.5
    last = max(b + d for b, d, _ in score)
    print(f"  {name:16s} {len(score):4d} 音  {last * 60 / bpm / 60:4.1f} 分钟  {desc}")
mp3(np.concatenate(parts), OUT / "compare_chorus.mp3")

print("compare_chorus.mp3：")
for name, t in marks:
    print(f"  {int(t // 60)}:{t % 60:05.2f}  {name}")
