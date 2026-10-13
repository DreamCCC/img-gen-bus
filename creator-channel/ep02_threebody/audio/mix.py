"""ep02 混音：歌单按词剪接成音乐床、合成音效、旁白。不做闪避：音乐只用固定 EQ 和每段固定音量。
用法：python audio/mix.py [out/ep02_mix.wav]
"""
import json
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from sfxlib import *  # noqa: F403

TL = json.loads((ROOT / "scenes/film.json").read_text())
DST = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "out/ep02_mix.wav")
DUR = TL["duration"]
N = int(SR * DUR)
VO = {v["id"]: v for v in TL["vo"]}
for v in VO.values():
    v["str"] = "".join(c[0] for c in v["chars"])
MK = TL["marks"]
S = lambda i: VO[i]["t"]  # noqa: E731
E = lambda i: VO[i]["t"] + VO[i]["dur"]  # noqa: E731


def at(i, ph, end=False):
    v = VO[i]
    k = v["str"].find(ph)
    assert k >= 0, f"{ph} 不在 {i}"
    return v["chars"][k + len(ph) - 1][2] if end else v["chars"][k][1]


music, vo, sfx = Bus(N), Bus(N), Bus(N)
POP = "assets/music/pop/"


def track(path, pieces, fade_in=0.02, fade_out=0.15, fx=None):
    """[(曲中位置, 成片起点, 成片终点)]；段与段之间就是静音点。fx 对每段做处理（比如只留低音）。"""
    y = load(path)
    for src, t0, t1 in pieces:
        p = seg(y, src, src + (t1 - t0))
        if fx:
            p = np.stack([fx(p[c]) for c in range(2)])
        fi, fo = int(fade_in * SR), int(fade_out * SR)
        p[:, :fi] *= ramp(fi)
        p[:, -fo:] *= ramp(fo, False)
        music.place(p, t0)


def peak_in(path, a, b):
    """曲子 [a, b] 秒内能量上冲最猛的位置（重音）。"""
    y, sr = librosa.load(ROOT / path, sr=22050, mono=True, offset=a, duration=b - a)
    o = librosa.onset.onset_strength(y=y, sr=sr)
    return a + librosa.frames_to_time(int(np.argmax(o)), sr=sr)


def first_tick(path, a=0.0, b=6.0):
    y, sr = librosa.load(ROOT / path, sr=22050, mono=True, offset=a, duration=b - a)
    on = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=False)
    return a + float(on[0]) if len(on) else a


# ---------------- 音乐床 ----------------
# 冷开场：Mountains。挪动整首，让一声滴答正好落在三颗星开始转的那一刻
t_spin = at("H04", "转起来") - 0.8
tick0 = first_tick(POP + "01_Mountains.opus")
k = int(np.floor((t_spin - tick0) / 1.254))
m_start = t_spin - (tick0 + k * 1.254)          # 成片里曲子 0 秒的位置（≤ 1.254）
while m_start > 0.6:
    m_start -= 1.254
t_liu = S("H21") - 0.25
track(POP + "01_Mountains.opus", [(-m_start, 0.0, t_liu)] if m_start < 0 else [(0.0, m_start, t_liu)], fade_in=1.5, fade_out=0.6)
# 提到《三体》：换《跟太阳系说再见》，铺到两个天体那段淡出
track(POP + "02_跟太阳系说再见_三体定制版.opus", [(1.0, t_liu, S("H26") + 0.5)], fade_in=0.3, fade_out=3.0)
# 标题：查拉图斯特拉。曲中 27.53 秒（第一声号角）对齐标题卡；前面的低音持续铺在 H25 之后
Z0 = MK["title"] - 27.53
track(POP + "03_查拉图斯特拉如是说_日出.opus", [(0.0, Z0, MK["ch1_end"] + 2.6)], fade_in=2.0, fade_out=2.2)
# 第一章：Day One 开头的钢琴和管风琴
track(POP + "04_Day_One.opus", [(0.0, MK["ch1_end"] - 0.4, MK["pre_ch2"] + 0.8)], fade_in=1.5, fade_out=1.0)
# 第二章：Experience。曲中第一个高点对在“上万颗小行星”；布伦斯那段只留低音
ex_peak = peak_in(POP + "05_Experience.opus", 100, 112)
ex0 = ex_peak - (at("B12", "上万颗") - MK["ch2"])
track(POP + "05_Experience.opus", [(ex0, MK["ch2"], S("B13") - 0.1)], fade_in=0.8, fade_out=0.4)
track(POP + "05_Experience.opus", [(ex0 + S("B13") - 0.1 - MK["ch2"], S("B13") - 0.1, MK["pre_ch3"] + 0.7)], fade_in=0.4, fade_out=1.0, fx=lambda x: lp(x, 260))
# 第三章上：Gymnopédie，发现错误那一刻硬停
t_err = at("C14", "发现了一个错误")
track(POP + "06_Gymnopedie_No1.opus", [(3.0, MK["ch3_end"] - 0.5, t_err)], fade_in=1.2, fade_out=0.05)
# 发现错误到停印：Mountains 的滴答回来；“整版已销毁”之前静 1 秒
t_dest = at("C20", "整版已销毁")
track(POP + "01_Mountains.opus", [(0.0, t_err + 0.25, t_dest - 1.0)], fade_in=0.05, fade_out=0.08)
# 混沌：No Time for Caution 最后的管风琴高潮，最强一下对在“混沌”
nt_peak = peak_in(POP + "07_No_Time_for_Caution.opus", 224, 232)
t_chaos = at("C24", "混沌")
nt0 = nt_peak - (t_chaos - (S("C21") - 0.3))
track(POP + "07_No_Time_for_Caution.opus", [(nt0, S("C21") - 0.3, MK["pre_ch4"] + 0.9)], fade_in=1.0, fade_out=1.2)
# 第四章：Can You Hear the Music，越转越快，“十的八十次方”硬切；之后 Day One 回来收尾
t_80 = at("D11", "十的八十次方", end=True) + 0.15
track(POP + "08_Can_You_Hear_The_Music.opus", [(0.0, MK["ch4_end"] - 0.4, t_80)], fade_in=0.8, fade_out=0.03)
track(POP + "04_Day_One.opus", [(2.0, S("D12") - 0.4, MK["pre_ch5"] + 1.0)], fade_in=1.2, fade_out=1.0)
# 第五章：人列计算机（合唱只落在章节卡上，有人声处用后段纯器乐）→ 卡农
track(POP + "09_人列计算机_原理.flac", [(42.0, MK["ch5"], S("E05") + 0.6)], fade_in=0.6, fade_out=1.2)
track(POP + "10_卡农_原始编制.opus", [(0.0, S("E05") - 0.4, MK["pre_ch6"] + 1.0)], fade_in=1.0, fade_out=1.0)
# 第六章：Cornfield Chase，大段进入对在一镜到底拉远
cc_peak = peak_in(POP + "11_Cornfield_Chase.opus", 36, 44)
cc0 = cc_peak - (T_pull := at("F04", "比邻星")) + MK["ch6"] - 0.3
track(POP + "11_Cornfield_Chase.opus", [(max(0.0, cc0), MK["ch6"] - 0.3, E("F12") + 0.8)], fade_in=1.5, fade_out=2.5)
# 结尾：《跟太阳系说再见》收尾段，曲子自然结束在片尾
z_end = 368.0
track(POP + "02_跟太阳系说再见_三体定制版.opus", [(z_end - (DUR - (S("F13") - 1.5)), S("F13") - 1.5, DUR)], fade_in=2.0, fade_out=0.5)
T = np.arange(N) / SR
music.x *= np.clip((DUR - T) / 2.0, 0, 1)

# ---------------- 音效 ----------------
def card(t0, f=41.2, g=0.4):
    sfx.place(impact(1.8), t0, g)
    sfx.place(braam(2.2, f), t0, g * 0.25)


def lock_click(t0, g=0.3, pan=0.0):
    sfx.place(add(click(0.012, 2500, 0.002), click(0.03, 900, 0.008) * 0.6), t0, g, pan=pan)


def typewriter(t0, n, cps, gain=0.3):
    for i in range(n):
        sfx.place(click(0.02, 1200, 0.006) + bp(noise(0.02), 150, 600) * env_exp(int(0.02 * SR), 0.005),
                  t0 + i / cps + rng.uniform(-0.012, 0.012), gain, pan=rng.uniform(-0.25, 0.25))


def press(t0, dur, bpm=150, g=0.25):
    """印刷机：低沉的机械冲压 + 纸张摩擦。"""
    for i in range(int(dur * bpm / 60)):
        tt = t0 + i * 60 / bpm
        sfx.place(add(thump() * 0.8, click(0.04, 700, 0.012)), tt, g, pan=-0.2)
        sfx.place(bp(noise(0.18), 2000, 7000) * np.hanning(int(0.18 * SR)) * 0.4, tt + 0.18, g * 0.5, pan=0.2)


def stamp(t0, g=0.5):
    sfx.place(add(thump(), tom(160, 70, 0.12) * 0.6, click(0.03, 900, 0.01)), t0, g)


def counter(t0, dur, rate=14, g=0.12):
    for i in range(int(dur * rate)):
        sfx.place(click(0.008, 3500, 0.002), t0 + i / rate, g * (0.6 + 0.4 * rng.random()), pan=rng.uniform(-0.3, 0.3))


# 冷开场
sfx.place(whoosh(3.0, 120, 1500, 1.0), 0.2, 0.12)
sfx.place(whoosh(2.0, 150, 2500, 0.8), at("H04", "转起来") - 0.6, 0.12)
t_ej = at("H07", "甩了出去")
sfx.place(whoosh(1.6, 300, 4500, 0.6), t_ej - 0.25, 0.35, pan=-0.3)
sfx.place(add(thump(), tom(90, 40, 0.4)), t_ej + 0.3, 0.45)
sfx.place(noise_sweep(1.2, 4000, 300, 1.0) * np.hanning(int(1.2 * SR)), S("H09") - 0.1, 0.2)       # 倒带
for w in ("百万分之一",):
    lock_click(at("H12", w), 0.3)
lock_click(at("H13", "一毫米"), 0.35)
sfx.place(whoosh(1.0, 300, 2500, 0.8), at("H16", "对不上了") - 0.3, 0.22)
sfx.place(whoosh(1.6, 300, 4500, 0.6), at("H17", "黄星") - 0.2, 0.3, pan=0.3)
sfx.place(impact(2.0), at("H19", "结局完全不一样"), 0.35)
for i in ("H22", "H23"):
    sfx.place(whoosh(0.8, 300, 3000, 0.8), S(i) - 0.2, 0.18)
stamp(at("H27", "写出了"), 0.35)
# 第一章
card(MK["ch1"] + 0.1, 41.2, 0.25)
lock_click(at("A06", "锁死"), 0.35)
sfx.place(whoosh(0.7, 400, 3000, 0.8), at("A08", "解析解") - 0.2, 0.15)
# 第二章
card(MK["ch2"], 36.7, 0.35)
sfx.place(add(click(0.03, 600, 0.02), tom(220, 120, 0.15) * 0.5), at("B07", "铅笔") + 1.6, 0.3)
lock_click(at("B11", "发现了"), 0.3)
counter(at("B12", "上万颗") - 0.3, 1.8, 18, 0.1)
t10 = at("B17", "那十个")
for i in range(10):
    lock_click(t10 - 0.5 + i * 0.13, 0.22, pan=-0.6 + i * 0.13)
sfx.place(thump(), at("B18", "锁不住"), 0.35)
# 第三章
card(MK["ch3"], 41.2, 0.35)
stamp(at("C11", "拿了奖"), 0.35)
press(S("C13") + 0.2, at("C13", "弗拉格曼") + 1.2 - S("C13"), 140, 0.18)
sfx.place(impact(2.4), t_err, 0.5)
sfx.place(braam(2.0, 36.7), t_err, 0.12)
typewriter(at("C16", "发电报"), 18, 11, 0.32)
sfx.place(whoosh(0.5, 500, 3500, 0.8) * 0.7, S("C17") - 0.2, 0.25)
for i in range(12):
    sfx.place(whoosh(0.35, 500, 3500, 0.8), S("C18") + 0.2 + i * 0.22, 0.12, pan=rng.uniform(-0.6, 0.6))
sfx.place(add(impact(2.6), braam(2.4, 32.7) * 0.4), t_dest, 0.55)
sfx.place(riser(2.2), t_chaos - 2.2, 0.18)
sfx.place(impact(2.6), t_chaos, 0.45)
# 第四章
card(MK["ch4"], 36.7, 0.35)
stamp(at("D02", "写出来了"), 0.35)
sfx.place(add(thump(), click(0.03, 900, 0.01)), at("D04", "同时撞到一起"), 0.3)
counter(S("D07"), at("D08", "十的八百万") - S("D07"), 16, 0.1)
sfx.place(impact(2.0), at("D08", "十的八百万"), 0.45)
sfx.place(whoosh(2.4, 150, 3000, 1.2), S("D10"), 0.18)
sfx.place(impact(2.2), t_80 - 0.15, 0.4)
# 第五章
card(MK["ch5"], 41.2, 0.3)
t3 = at("E03", "切成")
for i in range(int((E("E03") - t3) / 0.6)):
    sfx.place(click(0.015, 1800, 0.004), t3 + i * 0.6, 0.18)
sfx.place(add(click(0.02, 2000, 0.004), click(0.06, 600, 0.02) * 0.5), at("E05", "周期解"), 0.3)
counter(at("E09", "六百九十五") - 0.2, 1.6, 18, 0.1)
counter(at("E09", "十三万五千") - 0.2, 1.8, 22, 0.1)
counter(at("E09", "一万多个") - 0.2, 1.5, 18, 0.1)
# 第六章
card(MK["ch6"], 36.7, 0.3)
sfx.place(whoosh(4.5, 80, 1500, 1.4), S("F04") - 0.3, 0.22)
sfx.place(whoosh(1.0, 300, 2500, 0.8), S("F06") - 0.3, 0.15)
sfx.place(riser(3.0), at("F11", "一点五亿公里") - 3.0, 0.12)
sfx.place(impact(2.0), at("F11", "一点五亿公里"), 0.3)
sfx.place(whoosh(3.0, 100, 1200, 1.2), S("F13") - 0.8, 0.15)

# ---------------- 旁白 ----------------
vg = np.zeros(N)
for v in TL["vo"]:
    y = load_vo(f"audio/vo/{v['id']}.wav")
    for a, b, t0 in v["segs"]:
        vo.place(y[int(a * SR):int(b * SR)], t0, 0.5 * vo_gain(v["id"]))
    vg[int(v["t"] * SR): int((v["t"] + v["dur"]) * SR)] = 1

# ---------------- 混响与总线 ----------------
ir = room_ir()
sfx_out = sfx.x + 0.15 * np.stack([fftconvolve(sfx.x[c], ir)[:N] for c in range(2)])
vo_out = vo.x + 0.05 * np.stack([fftconvolve(vo.x[c], ir)[:N] for c in range(2)])
G_MUSIC, G_SFX, G_VO = 0.46, 0.5, 3.3
music_level = section_gain(N, [
    (0, S("H21") - 0.25, -1.0),
    (S("H21") - 0.25, S("H24"), -7.0), (S("H24"), Z0, -9.0),
    (Z0, MK["title"] - 0.6, -2.0), (MK["title"] - 0.6, MK["ch1_end"] + 0.4, 1.0),
    (MK["ch1_end"] + 0.4, MK["ch2"], -3.0),
    (MK["ch2"], S("B11"), -6.0), (S("B11"), S("B13"), -8.5), (S("B13"), MK["ch3"], -6.0),
    (MK["ch3"], t_err, -9.0),
    (t_err, S("C16"), -3.0), (S("C16"), t_dest, -1.5),
    (S("C21") - 0.3, t_chaos - 0.6, -9.0), (t_chaos - 0.6, E("C24") + 0.6, -2.0), (E("C24") + 0.6, MK["ch4"], -11.0),
    (MK["ch4"], t_80, -8.0), (t_80, MK["ch5"], -5.0),
    (MK["ch5"], S("E01") - 0.7, -4.0), (S("E01") - 0.7, S("E05"), -10.0), (S("E05"), MK["ch6"], -8.0),
    (MK["ch6"], S("F06"), -6.0), (S("F06"), E("F12") + 1, -10.0),
    (E("F12") + 1, E("F13") + 0.2, -5.0), (E("F13") + 0.2, DUR + 5, -0.5),
], ramp=0.4)
bed = vocal_pocket(music.x) * music_level * G_MUSIC + sfx_out * G_SFX
voc = vo_out * G_VO
worst = []
for v in TL["vo"]:
    i0, i1 = int(v["t"] * SR), int((v["t"] + v["dur"]) * SR)
    vb = np.stack([bp(voc[c, i0:i1], 300, 4000, 2) for c in range(2)])
    bb = np.stack([bp(bed[c, i0:i1], 300, 4000, 2) for c in range(2)])
    worst.append((round(rms_db(vb) - rms_db(bb), 1), v["id"]))
print("VO over bed (dB), lowest first:", sorted(worst)[:12])
print("lines under 12 dB:", sum(1 for d, _ in worst if d < 12), "/", len(worst))
mix = bed + voc
mix *= 0.93 / np.abs(mix).max()
sf.write(DST, mix.T.astype(np.float32), SR, subtype="PCM_24")
print("wrote", DST, f"{DUR:.2f}s", "rms", round(rms_db(mix), 1), "dB",
      "music", round(rms_db(music.x), 1), "vo", round(rms_db(vo.x[:, vg > 0]), 1), "sfx", round(rms_db(sfx_out), 1))
print("align: mountains start", round(m_start, 3), "tick0", round(tick0, 3), "| exp peak", round(ex_peak, 2),
      "| ntfc peak", round(nt_peak, 2), "->", round(t_chaos, 2), "| cornfield peak", round(cc_peak, 2))
