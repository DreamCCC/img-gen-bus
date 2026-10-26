"""混音：scenes/film.json 的时间轴 → out/mix.wav

旁白归一化；配乐固定挖人声频段、按段落固定音量，不随旁白起落；
开场原速段用原片现场声，慢放里球落地那一刻放原片里的真实反弹声；命中、出分、维度点亮配合成音效。
英文版：python audio/mix.py en → scenes/film_en.json + audio/vo_en/ → out/mix_en.wav
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfxlib import SR, ROOT, Bus, click, hp, impact, load, load_vo, ramp, shape_music, thump, vo_gain, whoosh  # noqa: E402

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
SUF = "_en" if EN else ""
D = json.loads((ROOT / f"scenes/film{SUF}.json").read_text())
BEAT = {b["id"]: b for b in D["beats"]}
VO = {v["id"]: v for v in D["vo"]}
K = D["keys"]
N = int(D["duration"] * SR) + SR
WORD = {"下肢加载": "lower-body load", "伸展速度": "extension speed", "出手姿势": "release form", "快速出手": "quick release",
        "随手动作得": "follow-through scores", "手腕加载": "wrist loading", "发力顺序": "kinetic chain",
        "躯干控制": "torso control", "落地前移": "forward sway"} if EN else {}


def vo_at(lid, word):
    v = VO[lid]
    if EN:
        plain = re.sub(r"[\s,.;:!?]", "", " ".join(c["text"] for c in v["chunks"])).lower()
        k = plain.find(re.sub(r"[\s,.;:!?]", "", WORD.get(word, word)).lower())
    else:
        plain = re.sub(r"[\s，。、；]", "", "".join(c["text"] for c in v["chunks"]))
        k = plain.find(word)
    return v["t"] + (max(k, 0) / len(plain)) * v["dur"]


def src_time(bid, frame):
    b = BEAT[bid]
    return b["t0"] + b["pre"] + (frame - b["a"]) / b["rate"] / D["fps"]


vo_bus, mus_bus, fx_bus = Bus(N), Bus(N), Bus(N)

for v in D["vo"]:
    vo_bus.place(load_vo(f"audio/vo{SUF}/{v['id']}.wav") * vo_gain(v["id"]), v["t"])

# 配乐：段落固定推子。开场原速段和片尾无旁白处推高
y = load("assets/music/Montauk_Point.mp3")
y = y[:, int(0.07 * SR):int(0.07 * SR) + N]
end_slate = BEAT["outro"]["t1"] - 2.8
mu = {"t": 0.0, "fin": 0.3, "fout": 2.2, "db": -19.0,
      "push": [[-2, BEAT["make"]["t0"] + 0.2, 5.0], [end_slate - 0.2, D["duration"] + 2, 5.0]]}
mus_bus.place(shape_music(y, mu), 0.0)

# 现场声：原速段原片同步；慢放段只放落地反弹那一下（原片 2.80 s ≈ 第 327 帧）
nat, _ = sf.read(ROOT / "work/nat.wav")
t_make = BEAT["make"]["t0"]
amb = nat[: int((t_make + 0.35) * SR)].copy()
amb[-int(0.35 * SR):] *= ramp(int(0.35 * SR), up=False)
fx_bus.place(amb * 2.2, 0.0)
bounce = nat[int(2.76 * SR): int(2.98 * SR)].copy()
bounce[-int(0.05 * SR):] *= ramp(int(0.05 * SR), up=False)
fx_bus.place(bounce * 1.1, src_time("make", 2.80 * D["srcFps"]) - 0.04)

fx_bus.place(impact(1.8) * 0.35, t_make)
fx_bus.place(thump() * 0.35, t_make)
fx_bus.place(impact(2.2) * 0.45, vo_at("L01", "54"))
fx_bus.place(whoosh(0.9, 6000, 300, 0.8) * 0.18, BEAT["rewind"]["t0"])
fx_bus.place(whoosh(0.8, 400, 4000) * 0.10, BEAT["phases"]["t0"])
for bid in ("rew2", "rew3"):
    fx_bus.place(whoosh(0.45, 5000, 400, 0.8) * 0.12, BEAT[bid]["t0"])

locks = {
    "lower_body": vo_at("L05", "下肢加载"), "extension_speed": vo_at("L06", "伸展速度"),
    "release_form": vo_at("L07", "出手姿势"), "quick_release": vo_at("L08", "快速出手"),
    "follow_through": vo_at("L09", "随手动作得"), "wrist_loading": vo_at("L10", "手腕加载"),
    "kinetic_chain": vo_at("L10", "发力顺序"), "torso_control": vo_at("L10", "躯干控制"),
    "forward_sway": vo_at("L10", "落地前移"), "make_result": src_time("makeAgain", K["make"]),
}
for key, t in locks.items():
    fx_bus.place(thump() * 0.22 + np.pad(click(0.02, 3000, 0.004) * 0.06, (0, len(thump()) - int(0.02 * SR))), t)
fx_bus.place(impact(1.6) * 0.3, locks["make_result"])

card = BEAT["card"]["t0"]
for i in range(10):
    fx_bus.place(hp(click(0.015, 2500, 0.004), 1800) * 0.06, card + 0.35 + i * 0.16)
fx_bus.place(impact(2.4) * 0.5, vo_at("L12", "54"))
fx_bus.place(impact(2.4) * 0.4, end_slate)

mix = vo_bus.x + mus_bus.x + fx_bus.x
mix = mix[:, : int(D["duration"] * SR)]
peak = np.abs(mix).max()
if peak > 0.95:
    mix *= 0.95 / peak
(ROOT / "out").mkdir(exist_ok=True)
sf.write(ROOT / f"out/mix{SUF}.wav", mix.T, SR, subtype="PCM_24")


def band_db(x, a, b):
    i0, i1 = int(a * SR), int(b * SR)
    seg = x[:, i0:i1].mean(axis=0)
    from sfxlib import bp
    s = bp(seg, 1000, 4000, 2)
    return 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-9)


worst = min(band_db(vo_bus.x, v["t"], v["t"] + v["dur"]) - band_db(mus_bus.x + fx_bus.x, v["t"], v["t"] + v["dur"]) for v in D["vo"])
print(f"out/mix{SUF}.wav  {D['duration']:.2f}s  peak {20*np.log10(peak):.1f} dBFS  旁白在人声频段最少高出背景 {worst:.1f} dB")
