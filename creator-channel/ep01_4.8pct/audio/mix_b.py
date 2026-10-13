"""B 站横版混音：音乐床（按段换曲、静音点靠剪曲子）、旁白、音效。不做闪避，音乐只用固定 EQ 和每段固定音量。
用法：python audio/mix_b.py [scenes/film_b.json] [out/b_mix.wav]
"""
import json
import sys

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from sfxlib import *  # noqa: F403

TL = json.loads((ROOT / (sys.argv[1] if len(sys.argv) > 1 else "scenes/film_b.json")).read_text())
DST = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "out/b_mix.wav")
DUR = TL["duration"]
N = int(SR * DUR)
VO = {v["id"]: v for v in TL["vo"]}
MK = TL["marks"]
S = lambda i: VO[i]["t"]  # noqa: E731
E = lambda i: VO[i]["t"] + VO[i]["dur"]  # noqa: E731
Wd = lambda i, w: VO[i]["words"][w]  # noqa: E731
music, vo, sfx, amb = Bus(N), Bus(N), Bus(N), Bus(N)
CH1_END = MK["ch1"] + 2.4


def track(path, pieces, fade_in=0.02, fade_out=0.15):
    """把一首曲子按 [(片头位置, 放到成片的起点, 终点)] 剪成若干段放进音乐床；段与段之间就是静音点。"""
    y = load(path)
    for src, t0, t1 in pieces:
        p = seg(y, src, src + (t1 - t0))
        fi, fo = int(fade_in * SR), int(fade_out * SR)
        p[:, :fi] *= ramp(fi)
        p[:, -fo:] *= ramp(fo, False)
        music.place(p, t0)


def scribble(dur, seed=0):
    """钢笔在纸上划：带通噪声 + 12 Hz 左右的笔触起伏。"""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    am = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * (10 + 4 * r.random()) * t + r.random() * 6))
    return bp(r.standard_normal(n), 1800, 6500, 2) * am * np.hanning(n) ** 0.5


def paper_slide(dur=0.45):
    return whoosh(dur, 500, 3500, 0.8) * 0.7 + bp(noise(dur), 2500, 8000) * np.hanning(int(dur * SR)) * 0.3


def radio_bed(dur):
    """老喇叭底噪：窄带嘶声 + 偶发爆音。"""
    n = int(dur * SR)
    hiss = bp(noise(dur), 900, 3200, 2) * 0.5
    pops = np.zeros(n)
    for k in rng.integers(0, n - 2000, int(dur * 6)):
        pops[k : k + 600] += click(0.0125, 1500, 0.002)[:600] * rng.uniform(0.5, 1.5)
    return (hiss + pops) * np.clip(np.arange(n) / (0.5 * SR), 0, 1) * np.clip((n - np.arange(n)) / (0.4 * SR), 0, 1)


# ---------------- 音乐床 ----------------
# 冷开场：电子脉冲；"10 个有 9 个"之前硬停 1 秒再接着放；标题卡前停
cut = E("H05") + 0.12
track("assets/music/cand/Static Motion.mp3", [(0.0, 0.0, cut), (cut, S("H06"), MK["pre_title"] + 0.5)])
# 第一章：稀疏钢琴；"门口堵的人太多"前停 1 秒
cut2 = E("A12") + 0.1
off2 = cut2 - MK["ch1"]
track("assets/music/cand/Healing.mp3", [(0.0, MK["ch1"], cut2), (off2, S("A13"), MK["ch2"] - 0.2)], fade_in=1.2, fade_out=1.6)
# 第二章、第四章共用“分母主题”
track("assets/music/cand/Investigations.mp3", [(0.0, MK["ch2"], MK["pre_ch3"] + 0.6)], fade_out=0.8)
# 第三章 1998：“题目就是结论”前停 1 秒
cut3 = E("C04") + 0.1
track("assets/music/cand/Lightless Dawn.mp3", [(0.0, MK["ch3"], cut3), (cut3 - MK["ch3"], S("C05") - 0.05, S("C11") - 0.5)], fade_out=0.8)
# 1999：往上走
track("assets/music/cand/Interloper.mp3", [(70.0, S("C11") - 0.5, E("C17") + 0.5)], fade_in=0.8, fade_out=1.0)
# 2003：低持续音，编者按前硬停；之后换 Clean Soul
track("assets/music/cand/Lightless Dawn.mp3", [(34.0, S("C18") - 0.5, S("C21") - 1.3)], fade_in=0.6, fade_out=0.05)
track("assets/music/cand/Clean Soul.mp3", [(0.0, S("C22") - 0.6, MK["ch4"] + 1.0)], fade_in=0.6, fade_out=1.0)
track("assets/music/cand/Investigations.mp3", [(0.0, MK["ch4"], MK["ask2_hold"] + 1.5)], fade_out=1.2)
# 第五章：Ossuary 6 - Air 177 秒的重音对在“十几倍”盖章那一下，E07 一说完硬切，E08–E09 没有音乐
peak = Wd("E07", "难了十几倍")
track("assets/music/cand/Ossuary 6 - Air.mp3", [(177.0 - (peak - MK["ch5"]), MK["ch5"], E("E07") + 0.05)], fade_in=0.4, fade_out=0.03)
# E10 到片尾：钢琴放低；最后一问前停 1 秒
cut5 = E("F04") + 0.1
off5 = cut5 - (S("E10") - 0.5)
track("assets/music/cand/Unanswered Questions.mp3", [(0.0, S("E10") - 0.5, cut5), (off5, S("F05"), DUR)], fade_in=1.0)
T = np.arange(N) / SR
music.x *= np.clip((DUR - T) / 2.5, 0, 1)

# ---------------- 冷开场音效 ----------------
def typewriter(t0, n, cps, gain=0.35):
    for k in range(n):
        sfx.place(click(0.02, 1200, 0.006) + bp(noise(0.02), 150, 600) * env_exp(int(0.02 * SR), 0.005),
                  t0 + k / cps + rng.uniform(-0.012, 0.012), gain, pan=rng.uniform(-0.25, 0.25))


typewriter(0.15, 26, 16)
sfx.place(piano(2093, 1.2, 0.25), 0.15 + 27 / 16, 0.3)
sfx.place(scribble(0.4, 1), Wd("H02", "一百万人"), 0.25)
tj = Wd("H03", "一下子跳了起来")
sfx.place(add(thump(), tom(90, 45, 0.3)), tj, 0.7)
sfx.place(hp(noise(0.15), 2500) * env_exp(int(0.15 * SR), 0.03), tj, 0.2)
for k in range(24):
    sfx.place(click(0.01, 3500, 0.003), S("H05") + 0.2 + k / 3 * 0.35, 0.12, pan=-0.5 + k / 24)
sfx.place(thump(), Wd("H05", "一千多万") - 0.1, 0.45)
sfx.place(tom(120, 55, 0.35), Wd("H06", "十个有九个") - 0.1, 0.55)
sfx.place(add(thump(), click(0.03, 900, 0.01)), S("H07") - 0.2, 0.5)
ts = S("H08") + 0.1
for k in range(5):
    sfx.place(click(0.02, 1200, 0.006), ts + (k + 1) / 10, 0.3, pan=0.3)
sfx.place(thump(), Wd("H08", "百分之九十多") - 0.15, 0.4, pan=0.3)
sfx.place(paper_slide(0.4), Wd("H08", "一九七七年只有") - 0.2, 0.3, pan=-0.4)
sfx.place(impact(1.8), S("H09"), 0.55)
sfx.place(hp(noise(0.25), 1500) * env_exp(int(0.25 * SR), 0.05), S("H09"), 0.3)
sfx.place(scribble(0.5, 2), Wd("H09", "根本不是一回事"), 0.3)
sfx.place(whoosh(2.4, 200, 1800, 1.2), S("H10") + 0.2, 0.12)
sfx.place(scribble(0.6, 3), Wd("H10", "被藏了好几年的分母"), 0.25, pan=-0.3)
# 标题卡
sfx.place(impact(2.2), MK["title"], 0.8)
sfx.place(braam(2.4, 41.2), MK["title"], 0.2)
music.place(piano(220.0, 4.0, 0.5) + piano(110.0, 4.0, 0.3), MK["ch1"] + 0.1, 0.4)

# ---------------- 第一章音效 ----------------
amb.place(radio_bed(S("A02") - 0.3 - CH1_END), CH1_END, 0.03)
sfx.place(paper_slide(), Wd("A01", "高考恢复了") - 0.3, 0.35, pan=0.4)
te, tw = Wd("A02", "最早的"), Wd("A02", "最晚的")
sfx.place(scribble(tw + 0.8 - te - 0.3, 4) * 0.6, te + 0.3, 0.18, pan=0.2)
sfx.place(scribble(0.8, 5), Wd("A03", "也就一个多月") - 0.4, 0.28)
sfx.place(scribble(0.7, 6), Wd("A05", "五毛钱") - 0.3, 0.3, pan=-0.2)
for k, w in enumerate(["户口跟着转走", "在学校有助学金", "毕业国家分配工作"]):
    sfx.place(scribble(0.3, 10 + k), Wd("A07", w) + 0.05, 0.25, pan=-0.3)
sfx.place(scribble(0.6, 14), Wd("A09", "三十一岁") + 0.1, 0.25)
sfx.place(paper_slide(0.5), S("A10") - 0.3, 0.35, pan=0.4)
for k in range(5):
    sfx.place(click(0.01, 3500, 0.003), S("A11") + 0.2 + k * 0.24, 0.22, pan=0.3)
sfx.place(scribble(0.5, 15), Wd("A12", "原计划只招二十万"), 0.22, pan=0.3)
sfx.place(whoosh(1.4, 250, 2500, 1.0), Wd("A14", "十几届的人"), 0.15)
for w in ("七七级", "七八级"):
    sfx.place(click(0.02, 1200, 0.006), Wd("A15", w) + 0.2, 0.3)
sfx.place(scribble(0.7, 16), Wd("A15", "只差半年") - 0.2, 0.22)
music.place(piano(392.0, 4.0, 0.4) + piano(196.0, 4.0, 0.2), S("A16") - 0.2, 0.35)


def card(t0, f=41.2):
    sfx.place(impact(1.8), t0, 0.5)
    sfx.place(braam(2.2, f), t0, 0.12)


# ---------------- 第二章 ----------------
card(MK["ch2"])
for w in ("一九八零年", "一九八一年", "一九八三年", "一九八五年"):
    sfx.place(click(0.02, 1200, 0.006), Wd("B02", w) + 0.25, 0.3, pan=0.2)
for w in ("一九八零年三百", "一九八一年二百", "一九八三年只有"):
    sfx.place(click(0.02, 900, 0.006), Wd("B03", w) + 0.25, 0.3, pan=-0.2)
sfx.place(scribble(0.6, 21), S("B04") + 0.3, 0.22)
sfx.place(scribble(0.5, 22), S("B05"), 0.25, pan=0.3)
tc = Wd("B06", "先筛一轮")
sfx.place(paper_slide(0.5), tc - 0.1, 0.3, pan=0.3)
sfx.place(tom(110, 50, 0.3), tc + 0.1, 0.4)
sfx.place(scribble(0.6, 23), Wd("B08", "分母里少了一大块人"), 0.28)
sfx.place(scribble(0.6, 24), S("B09") + 0.2, 0.2, pan=-0.3)

# ---------------- 第三章 ----------------
card(MK["ch3"], 36.7)
amb.place(lp(noise(S("C03") - 0.2 - (MK["ch3"] + 2.5)), 600, 2) * 0.6, MK["ch3"] + 2.5, 0.05)
for w in ("亚洲金融危机", "国企改革", "经济增长百分之八"):
    sfx.place(click(0.02, 1200, 0.006), Wd("C02", w) - 0.1, 0.28)
typewriter(Wd("C04", "题目叫") + 0.4, 28, 9, 0.3)
sfx.place(scribble(0.5, 31), S("C05") - 0.1, 0.3)
for w in ("只有百分之四", "菲律宾", "泰国"):
    sfx.place(whoosh(0.4, 400, 2500, 0.8), Wd("C07", w) - 0.15, 0.15)
sfx.place(scribble(0.3, 32), S("C08") + 0.3, 0.2)
sfx.place(scribble(0.3, 33), S("C09"), 0.2)
sfx.place(scribble(0.5, 34), Wd("C10", "很快被采纳了"), 0.3)
sfx.place(paper_slide(0.4), S("C11") - 0.3, 0.3)
ps = Wd("C12", "部长同意了")
sfx.place(scribble(0.5, 35), ps, 0.3)
sfx.place(scribble(0.4, 36), ps + 0.7, 0.25)
sfx.place(thump(), Wd("C13", "涨了百分之四十七") - 0.2, 0.55)
for w in ("两千年", "两千零一年", "两千零二年"):
    sfx.place(tom(130, 60, 0.25), Wd("C14", w) - 0.1, 0.4)
sfx.place(paper_slide(0.5), S("C15") - 0.3, 0.3, pan=-0.3)
sfx.place(whoosh(0.6, 300, 2500, 0.8), Wd("C16", "到二零零五年"), 0.18)
for k in range(10):
    sfx.place(click(0.01, 3500, 0.003), S("C18") + k * 0.05, 0.12, pan=-0.4 + k * 0.08)
sfx.place(tom(80, 40, 0.5), Wd("C20", "还有一百多万人没找到工作") - 0.1, 0.45)
amb.place(lp(noise(S("C22") - 0.6 - (S("C21") - 1.3)), 300, 2) * 0.5, S("C21") - 1.3, 0.03)
sfx.place(paper_slide(0.7), S("C21") - 1.1, 0.25)
sfx.place(scribble(0.7, 37), Wd("C24", "中间用了十七年"), 0.25)
sfx.place(paper_slide(0.5), S("C25") - 0.3, 0.28)
sfx.place(paper_slide(0.4), S("C28") - 0.3, 0.3)
sfx.place(whoosh(1.2, 300, 2500, 0.8), E("C28") + 0.2, 0.15)

# ---------------- 第四章 ----------------
card(MK["ch4"])
sfx.place(scribble(0.6, 41), S("D03"), 0.3)
sfx.place(tom(110, 50, 0.3), Wd("D04", "单独招生") - 0.1, 0.4)
sfx.place(scribble(0.6, 42), S("D05") + 0.2, 0.25)
sfx.place(whoosh(0.7, 300, 2000, 0.8), Wd("D06", "走进六月统考考场的是") - 0.3, 0.15)
sfx.place(tom(110, 50, 0.3), Wd("D06", "另外二十二万多人") - 0.1, 0.4)
for w in ("全国本科招了", "专科招了"):
    sfx.place(click(0.02, 1200, 0.006), Wd("D07", w) - 0.1, 0.3)
sfx.place(scribble(0.5, 43), Wd("D08", "不到四成"), 0.25)
sfx.place(paper_slide(0.4), Wd("D09", "回答的是") - 0.2, 0.25)
sfx.place(paper_slide(0.4), S("D10") + 0.3, 0.2, pan=0.4)
sfx.place(click(0.03, 900, 0.01), S("D11") - 0.1, 0.3)

# ---------------- 第五章 ----------------
card(MK["ch5"], 36.7)
sfx.place(whoosh(1.0, 300, 2500, 0.8), MK["ch5"] + 2.7, 0.15)
for i in ("E02", "E03", "E04"):
    sfx.place(whoosh(0.9, 200, 1600, 1.0), S(i) + 0.3, 0.15)
sfx.place(scribble(0.4, 51), S("E05") + 0.2, 0.2)
for k in range(4):
    sfx.place(click(0.01, 3500, 0.003), Wd("E06", "一千个人里不到四个") + k * 0.2, 0.18)
ts = Wd("E07", "难了十几倍")
sfx.place(impact(2.0), ts, 0.7)
sfx.place(braam(2.0, 36.7), ts, 0.15)
sfx.place(scribble(0.6, 52), Wd("E09", "卷的恰恰就是这九所"), 0.25)
for w in ("北京考生进C九的比例", "是全国平均的四倍多"):
    sfx.place(whoosh(0.5, 300, 2000, 0.8), Wd("E11", w) - 0.15, 0.15)

# ---------------- 结尾 ----------------
sfx.place(paper_slide(0.6), MK["ending"] + 0.1, 0.3)
sfx.place(whoosh(1.2, 200, 1500, 1.0), S("F02") - 0.3, 0.12)

# ---------------- 旁白 ----------------
vg = np.zeros(N)
for v in TL["vo"]:
    vo.place(load_vo(f"audio/vo_b/{v['id']}.wav"), v["t"], 0.5)
    vg[int(v["t"] * SR) : int((v["t"] + v["dur"]) * SR)] = 1

# ---------------- 混响与总线 ----------------
ir = room_ir()
sfx_out = sfx.x + 0.15 * np.stack([fftconvolve(sfx.x[c], ir)[:N] for c in range(2)])
vo_out = vo.x + 0.05 * np.stack([fftconvolve(vo.x[c], ir)[:N] for c in range(2)])
G_MUSIC, G_SFX, G_VO = 0.46, 0.5, 3.3
# 每段固定音量（dB）
music_level = section_gain(N, [
    (0, MK["title"], -1.0), (MK["title"], MK["ch1"], 0.0), (MK["ch1"], MK["ch2"], -3.0),
    (MK["ch2"], MK["ch3"], -4.0), (MK["ch3"], S("C11") - 0.5, -4.0), (S("C11") - 0.5, S("C18") - 0.5, -3.0),
    (S("C18") - 0.5, S("C22") - 0.6, -5.0), (S("C22") - 0.6, MK["ch4"], -4.0), (MK["ch4"], MK["ch5"], -5.0),
    (MK["ch5"], S("E08"), -3.0), (S("E08"), E("F05") + 0.3, -6.0), (E("F05") + 0.3, DUR + 5, -3.0),
], ramp=0.3)
bed = vocal_pocket(music.x) * music_level * G_MUSIC + sfx_out * G_SFX + amb.x
voc = vo_out * G_VO
worst = []
for v in TL["vo"]:
    i0, i1 = int(v["t"] * SR), int((v["t"] + v["dur"]) * SR)
    vb = np.stack([bp(voc[c, i0:i1], 300, 4000, 2) for c in range(2)])
    bb = np.stack([bp(bed[c, i0:i1], 300, 4000, 2) for c in range(2)])
    worst.append((round(rms_db(vb) - rms_db(bb), 1), v["id"]))
print("VO over bed (dB), lowest first:", sorted(worst)[:8])
mix = bed + voc
mix *= 0.93 / np.abs(mix).max()
sf.write(DST, mix.T.astype(np.float32), SR, subtype="PCM_24")
print("wrote", DST, f"{DUR:.2f}s", "rms", round(rms_db(mix), 1), "dB",
      "music", round(rms_db(music.x), 1), "vo", round(rms_db(vo.x[:, vg > 0]), 1), "sfx", round(rms_db(sfx_out), 1))
