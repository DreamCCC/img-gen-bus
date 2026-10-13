"""成片混音：音乐床（剪接 + 第三幕合成 + 第四幕接曲）、旁白（自动压低音乐）、音效（全部来自 film_h.json 事件）。
用法：python audio/mix_film.py [scenes/film_h.json] [out/film_h_mix.wav]
"""
import json
import sys

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from sfxlib import *  # noqa: F403

TL = json.loads((ROOT / (sys.argv[1] if len(sys.argv) > 1 else "scenes/film_h.json")).read_text())
DST = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "out/film_h_mix.wav")
DUR = TL["duration"]
N = int(SR * DUR)
A, EV, S, M = TL["anchors"], TL["ev"], TL["scenes"], TL["music"]
T = np.arange(N) / SR
music, vo, sfx, amb = Bus(N), Bus(N), Bus(N), Bus(N)

# ---------------- 音乐床 ----------------
fa = load("assets/music/Five_Armies.mp3")
ha = load("assets/music/Heroic_Age.mp3")
xf = int(0.03 * SR)
p1 = seg(fa, 0, M["fa_cut_out"] + 0.03)
p2 = seg(fa, M["fa_cut_in"], M["fa_end"])
p1[:, -xf:] *= ramp(xf, False)
p2[:, :xf] *= ramp(xf, True)
p2[:, -int(0.025 * SR):] *= ramp(int(0.025 * SR), False)
music.place(p1, 0.0)
music.place(p2, M["fa_cut_out"])
hseg = seg(ha, M["ha_in"], min(ha.shape[1] / SR, M["ha_in"] + (DUR - M["ha_at"])))
hseg[:, : int(0.02 * SR)] *= ramp(int(0.02 * SR))
music.place(hseg, M["ha_at"])
music.x *= np.clip((DUR - T) / 1.5, 0, 1)


# ---------------- 冷开场 ----------------
for k, tb in enumerate(EV["openBounces"]):
    sfx.place(dribble_room(), tb, 0.6 * 0.72**k)
r0, r1 = EV["rewind"]
rw = noise_sweep(r1 - r0, 1500, 300, 0.8)
n = len(rw)
flutter = 1 + 0.35 * np.sin(2 * np.pi * np.cumsum(np.linspace(6, 22, n)) / SR)
rw = hp(rw, 200) * flutter * np.linspace(0.3, 1.0, n) ** 1.5
sfx.place(rw, r0, 0.22)
sfx.place(taiko(), r1, 0.75)
sfx.place(click(0.04, 800, 0.01), r1, 0.5)
sfx.place(braam(2.4, 41.2), r1, 0.18)

# ---------------- 第一幕 ----------------
a0, a1 = EV["arc"]
sfx.place(whoosh(a1 - a0 + 0.3, 200, 2500, 1.0), a0, 0.18)
sfx.place(piano(1318.5, 3.0, 0.25), a1, 0.5)
proj = bp(noise(S["bj1979"][1] - S["bj1979"][0]), 400, 4000, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 24 * np.arange(int((S["bj1979"][1] - S["bj1979"][0]) * SR)) / SR) ** 2)
amb.place(proj * np.clip(np.linspace(0, 6, len(proj)), 0, 1) * np.clip(np.linspace(6, 0, len(proj)), 0, 1), S["bj1979"][0], 0.025)
rl = EV["rulerLand"]
sfx.place(taiko(), rl, 0.8)
sfx.place(rim_clank() * 0.5, rl, 0.25)
tick_t = np.linspace(S["ruler"][0] + 0.4, rl - 0.05, 26) ** 1.0
for k, tt in enumerate(tick_t):
    sfx.place(click(0.01, 3000), tt, 0.05 + 0.1 * k / len(tick_t), pan=-0.2)
ty0, ty1 = EV["typing"]
for k in range(int((ty1 - ty0) / 0.11)):
    sfx.place(click(0.02, 1200, 0.006) + bp(noise(0.02), 150, 600) * env_exp(int(0.02 * SR), 0.005), ty0 + k * 0.11 + rng.uniform(-0.02, 0.02), 0.35, pan=rng.uniform(-0.3, 0.3))
sfx.place(piano(2093, 1.5, 0.3), ty1 + 0.05, 0.4)
sfx.place(tom(90, 50, 0.2), ty1 + 0.3, 0.6)

# ---------------- 斯特恩：时钟、录像带、电视亮起 ----------------
for k, tt in enumerate(EV["clockTicks"]):
    sfx.place(click(0.015, 2500 if k % 2 else 1800, 0.004), tt, 0.25, pan=0.4)
sfx.place(add(tom(160, 90, 0.08), click(0.03, 900, 0.01)), EV["tapeIn"], 0.5)
sfx.place(whoosh(1.6, 150, 3000, 1.6), A["act2"] - 1.5, 0.25)
sfx.place(pitch_sweep(80, 35, 1.5, 0.4), A["act2"], 0.6)
st = bp(noise(1.2), 1500, 9000) * env_exp(int(1.2 * SR), 0.25)
sfx.place(st, A["act2"], 0.25)
tvb = S["tvwall"]
static = bp(noise(tvb[1] - tvb[0]), 800, 7000, 2)
amb.place(static * np.clip(np.linspace(1, 0, len(static)) * 2, 0, 1), tvb[0], 0.02)

# ---------------- 姚明 ----------------
sfx.place(tom(120, 55, 0.3), EV["yaoRuler"], 0.6)
sfx.place(impact(2.2), EV["yaoRoar"], 0.7)
cr = crowd_layer(3.4, 1)
sfx.place(cr * np.exp(-np.arange(len(cr)) / (1.4 * SR)) * np.clip(np.arange(len(cr)) / (0.05 * SR), 0, 1), EV["yaoRoar"], 0.4)

# ---------------- 票根、2004 现场、一万一千人 ----------------
sfx.place(add(taiko() * 0.7, click(0.05, 600, 0.02)), EV["stamp"], 0.8)
sfx.place(whoosh(0.5, 600, 4000), EV["stamp"] + 0.4, 0.2)
cb = crowd_layer(S["crowd"][1] - EV["stamp"], 2)
g = np.clip(np.arange(len(cb)) / (0.6 * SR), 0, 1) * 0.35
tt = EV["stamp"] + np.arange(len(cb)) / SR
for b in EV["chant"]:
    g = g + 0.6 * (tt >= b) * np.exp(-np.clip(tt - b, 0, None) / 0.22)
sfx.place(cb * g, EV["stamp"], 0.35)

# ---------------- 战术板 → 扣篮 ----------------
b0 = S["board"][0]
for k in range(12):
    ping = np.sin(2 * np.pi * (2400 + 900 * rng.random()) * np.arange(int(0.12 * SR)) / SR) * env_exp(int(0.12 * SR), 0.03)
    sfx.place(ping, b0 + 0.1 + k * 0.06, 0.05, pan=rng.uniform(-0.6, 0.6))
sfx.place(whoosh(0.8, 800, 3000), EV["shot"], 0.18)
sfx.place(rim_clank(), EV["rimOut"], 0.35, pan=0.2)
sfx.place(whoosh(0.5, 1200, 5000), EV["putback"], 0.22)
sfx.place(tom(110, 60, 0.2), EV["putback"] + 0.45, 0.4)
z0, z1 = EV["boardZoom"]
sfx.place(whoosh(z1 - z0 + 0.3, 300, 6000, 1.6), z0, 0.3)
sl = A["slam"]
r0, r1 = EV["dunk"]["riser"]
sfx.place(riser(r1 - r0), r0, 0.35)
for k in range(int((EV["dunk"]["suck"] - S["dunk"][0]) / 0.25)):
    sfx.place(click(0.03, 6000, 0.008), S["dunk"][0] + k * 0.25, 0.12 if k % 2 else 0.2, pan=0.3 if k % 2 else -0.3)
sfx.place(impact(2.6), sl, 0.95)
sfx.place(braam(3.0), sl, 0.25)
sfx.place(bp(noise(0.35), 2000, 7000) * env_exp(int(0.35 * SR), 0.1), sl + 0.04, 0.25)
cr = crowd_layer(4.5, 3)
env = np.clip(np.arange(len(cr)) / (0.03 * SR), 0, 1) * (0.3 + 0.9 * np.exp(-np.arange(len(cr)) / (1.3 * SR))) * np.clip((len(cr) - np.arange(len(cr))) / (1.0 * SR), 0, 1)
sfx.place(cr * env, sl, 0.55)
crt = S["dunk"][1] - 0.3
sfx.place(pitch_sweep(900, 60, 0.35, 0.12), crt, 0.25)

# ---------------- 计分牌、十五年 ----------------
fl = EV["flapLand"]
for k in range(int(0.9 / 0.03)):
    sfx.place(click(), fl - 0.9 + k * 0.03, 0.15, pan=rng.uniform(-0.4, 0.4))
sfx.place(tom(110, 60, 0.25), fl, 0.55)
c0, c1 = EV["spanCount"]
for cc in (c0, c1):
    for k in range(14):
        sfx.place(click(0.01, 3500), cc - 0.9 + 0.9 * (k / 14) ** 0.6, 0.08)
    sfx.place(tom(130, 65, 0.25), cc, 0.5)

# ---------------- 翻页蒙太奇 ----------------
for k, pg in enumerate(TL["flips"]):
    for j in range(5):
        sfx.place(click(), pg["t"] + j * 0.028, 0.14, pan=rng.uniform(-0.5, 0.5))
    big = pg["beats"] >= 4
    sfx.place(tom(120, 55, 0.25) if big else tom(170, 80, 0.12), pg["t"], 0.35 + 0.25 * big + 0.02 * k)
sfx.place(impact(1.5), A["lastHit"], 0.8)

# ---------------- 第三幕：灯灭、2190 天、心跳 ----------------
act3 = (T >= A["stop"]) & (T < A["act4"])
drone = sum(np.sin(2 * np.pi * f * T) * gg for f, gg in [(41.2, 1), (61.7, 0.4), (82.4, 0.25)])
dg = act3 * np.clip((T - A["stop"] - 1.2) / 3.0, 0, 1) * np.clip((A["act4"] - T) / 0.4, 0, 1)
dg *= 0.6 + 0.4 * np.clip((T - S["cold"][0]) / (A["act4"] - S["cold"][0]), 0, 1)
music.x += lp(drone, 200) * dg * 0.06
rows = EV["lightsRows"]
for k, tt in enumerate(rows):
    sw = add(tom(70, 40, 0.15) * 0.8, click(0.03, 500, 0.012) * 1.5)
    tail = fftconvolve(sw, rng.standard_normal(int(1.5 * SR)) * env_exp(int(1.5 * SR), 0.35))[: int(1.8 * SR)]
    tail = lp(tail, 4000) / (np.abs(tail).max() + 1e-9)
    s2 = np.zeros(len(tail)); s2[: len(sw)] += sw
    sfx.place(s2 + tail * 0.3, tt, 0.35 + 0.35 * (k == len(rows) - 1), pan=(k % 2 - 0.5) * 0.4)
notes = [(rows[-1] + 1.6, 329.6), (EV["counter"][0] - 0.2, 246.9), (EV["counter"][1], 196.0), (S["cold"][0] + 0.8, 220.0), (S["cold"][0] + 4.3, 261.6), (S["cold"][0] + 7.0, 293.7)]
for tt, fq in notes:
    music.place(piano(fq, 5.0, 0.5) + piano(fq / 2, 5.0, 0.2), tt, 0.45)
c0, c1 = EV["counter"]
for k in range(60):
    u = k / 59
    tt = c0 + (c1 - c0) * (0.5 - 0.5 * np.cos(np.pi * u))
    sfx.place(click(0.008, 4000, 0.002), tt, 0.06)
sfx.place(tom(100, 50, 0.3), c1, 0.4)
for k, tt in enumerate(EV["hearts"]):
    sfx.place(dribble_room(), tt, 0.35 + 0.35 * k / len(EV["hearts"]))
sfx.place(riser(1.6), A["act4"] - 1.6, 0.2)

# ---------------- 第四幕 ----------------
sfx.place(impact(3.0), A["boom"], 0.9)
sfx.place(braam(3.2, 49), A["boom"], 0.25)
cr = crowd_layer(6.0, 4)
env = np.clip(np.arange(len(cr)) / (0.03 * SR), 0, 1) * (0.35 + 0.8 * np.exp(-np.arange(len(cr)) / (1.8 * SR))) * np.clip((len(cr) - np.arange(len(cr))) / (1.5 * SR), 0, 1)
sfx.place(cr * env, A["boom"], 0.5)
for k, tt in enumerate(EV["rosterCuts"]):
    sfx.place(add(whoosh(0.25, 1500, 6000) * 0.6, tom(150, 60, 0.12) * 0.6), tt - 0.02, 0.25)
for k, tt in enumerate(EV["endBounces"]):
    sfx.place(dribble_room(), tt, 0.55 * 0.8**k)

# ---------------- 旁白与压低音乐 ----------------
vg = np.zeros(N)
for v in TL["vo"]:
    vo.place(load_vo(f"audio/vo/{v['id']}.wav"), v["t"], 0.5 * vo_gain(v["id"]))
    i0, i1 = int(v["t"] * SR), int((v["t"] + v["dur"]) * SR)
    vg[i0:i1] = 1
# ---------------- 混响与总线 ----------------
ir = room_ir()
wet = np.stack([fftconvolve(sfx.x[c], ir)[:N] for c in range(2)])
sfx_out = sfx.x + 0.2 * wet
vo_out = vo.x
vo_out = vo_out + 0.06 * np.stack([fftconvolve(vo.x[c], ir)[:N] for c in range(2)])

G_MUSIC, G_SFX, G_VO = 0.46, 0.5, 3.3
sf.write(DST.with_name(DST.stem + "_sfxstem.wav"), (sfx_out * G_SFX + amb.x).T.astype(np.float32), SR, subtype="FLOAT")
music_level = section_gain(N, [(A["slam"] + 0.8, A["stop"] + 1.5, -3.0)])
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
peak = np.abs(mix).max()
mix *= 0.93 / peak
sf.write(DST, mix.T.astype(np.float32), SR, subtype="PCM_24")
print("wrote", DST, f"{DUR:.2f}s", "rms", round(rms_db(mix), 1), "dB",
      "music", round(rms_db(music.x), 1), "vo", round(rms_db(vo.x[:, vg > 0]), 1), "sfx", round(rms_db(sfx_out), 1))
