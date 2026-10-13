"""竖版混音：音效按镜头从横版分轨搬运，翻页/钩子/对阵卡/片尾为竖版原生音效，音乐按 film_v.json 重新剪接。
先跑 mix_film.py 生成 out/film_h_mix_sfxstem.wav。
用法：python audio/mix_film_v.py [scenes/film_v.json] [out/film_v_mix.wav]
"""
import json
import sys

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

from sfxlib import *  # noqa: F403

TL = json.loads((ROOT / (sys.argv[1] if len(sys.argv) > 1 else "scenes/film_v.json")).read_text())
DST = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "out/film_v_mix.wav")
DUR = TL["duration"]
N = int(SR * DUR)
M, EV, SH = TL["music"], TL["ev"], TL["shots"]
T = np.arange(N) / SR
music, vo, sfx, stem = Bus(N), Bus(N), Bus(N), Bus(N)
STOP, BOOM = M["stop"], M["boom"]
FLIPS = [s for s in SH if s["layout"] == "regions" and s.get("native") != "six"]

# ---------------- 音乐 ----------------
fa = load("assets/music/Five_Armies.mp3")
ha = load("assets/music/Heroic_Age.mp3")
p = seg(fa, M["fa0"], M["fa0"] + STOP)
p[:, : int(0.25 * SR)] *= ramp(int(0.25 * SR))
p[:, -int(0.025 * SR):] *= ramp(int(0.025 * SR), False)
music.place(p, 0.0)
pre = 1.5
h = seg(ha, M["ha_boom"] - pre, M["ha_boom"] - pre + (DUR - BOOM + pre))
h[:, : int(1.0 * SR)] *= ramp(int(1.0 * SR))
music.place(h, BOOM - pre)
music.x *= np.clip((DUR - T) / 2.5, 0, 1)

act3 = (T >= STOP) & (T < BOOM)
drone = sum(np.sin(2 * np.pi * f * T) * g for f, g in [(41.2, 1), (61.7, 0.4), (82.4, 0.25)])
music.x += lp(drone, 200) * act3 * np.clip((T - STOP - 0.8) / 1.5, 0, 1) * np.clip((BOOM - T) / 0.3, 0, 1) * 0.06
music.place(piano(329.6, 5.0, 0.5) + piano(164.8, 5.0, 0.2), STOP + 2.4, 0.45)
music.place(piano(246.9, 4.0, 0.5) + piano(123.5, 4.0, 0.2), EV["six"], 0.45)

# ---------------- 横版音效分轨按镜头搬运 ----------------
hs, _ = sf.read(ROOT / "out/film_h_mix_sfxstem.wav", always_2d=True)
hs = hs.T
fade = int(0.008 * SR)
for s in SH:
    if s["h0"] is None or s in FLIPS:
        continue
    piece = hs[:, int(s["h0"] * SR) : int((s["h0"] + s["v1"] - s["v0"]) * SR)].copy()
    piece[:, :fade] *= ramp(fade)
    piece[:, -fade:] *= ramp(fade, False)
    stem.place(piece, s["v0"])

# ---------------- 竖版原生音效 ----------------
for k, tt in enumerate(EV["hook"]):
    sfx.place(add(taiko(), click(0.04, 800, 0.01)), tt, 0.55 + 0.15 * k)
sfx.place(braam(2.4, 41.2), EV["hook"][-1], 0.15)
sfx.place(add(whoosh(0.35, 800, 5000), tom(130, 60, 0.15)), 19.9 - 0.05, 0.3)
for k, s in enumerate(FLIPS):
    for j in range(5):
        sfx.place(click(), s["v0"] + j * 0.028, 0.14, pan=rng.uniform(-0.5, 0.5))
    big = s["v1"] - s["v0"] > 0.8
    sfx.place(tom(120, 55, 0.25) if big else tom(170, 80, 0.12), s["v0"], 0.35 + 0.25 * big + 0.02 * k)
sfx.place(impact(1.5), FLIPS[-1]["v0"], 0.8)
for k, tt in enumerate([BOOM - 2.1, BOOM - 1.15, BOOM - 0.55]):
    sfx.place(dribble_room(), tt, 0.4 + 0.15 * k)
sfx.place(riser(1.6), BOOM - 1.6, 0.25)
c0, c1 = EV["card"]
sfx.place(add(whoosh(0.4, 1500, 6000) * 0.6, tom(150, 60, 0.12)), c0 - 0.05, 0.4)
sfx.place(impact(2.2), c1, 0.7)
sfx.place(braam(2.4, 49), c1, 0.2)
for k, tt in enumerate(EV["endBounces"]):
    sfx.place(dribble_room(), tt, 0.55 * 0.8**k)

# ---------------- 旁白、压低、总线 ----------------
vg = np.zeros(N)
for v in TL["vo"]:
    vo.place(load_vo(v["wav"]), v["t"], 0.5 * vo_gain(v["id"]))
    vg[int(v["t"] * SR) : int((v["t"] + v["dur"]) * SR)] = 1
ir = room_ir()
sfx_out = sfx.x + 0.2 * np.stack([fftconvolve(sfx.x[c], ir)[:N] for c in range(2)])
vo_out = vo.x + 0.06 * np.stack([fftconvolve(vo.x[c], ir)[:N] for c in range(2)])

G_MUSIC, G_SFX, G_VO = 0.46, 0.5, 3.3
V_SLAM = 23.4
music_level = section_gain(N, [(V_SLAM + 0.8, STOP + 1.5, -3.0)])
bed = vocal_pocket(music.x) * music_level * G_MUSIC + sfx_out * G_SFX + stem.x
voc = vo_out * G_VO
worst = []
for v in TL["vo"]:
    i0, i1 = int(v["t"] * SR), int((v["t"] + v["dur"]) * SR)
    vb = np.stack([bp(voc[c, i0:i1], 300, 4000, 2) for c in range(2)])
    bb = np.stack([bp(bed[c, i0:i1], 300, 4000, 2) for c in range(2)])
    worst.append((round(rms_db(vb) - rms_db(bb), 1), v["id"]))
print("VO over bed (dB), lowest first:", sorted(worst)[:6])
mix = bed + voc
mix *= 0.93 / np.abs(mix).max()
sf.write(DST, mix.T.astype(np.float32), SR, subtype="PCM_24")
print("wrote", DST, f"{DUR:.2f}s", "rms", round(rms_db(mix), 1), "dB")
