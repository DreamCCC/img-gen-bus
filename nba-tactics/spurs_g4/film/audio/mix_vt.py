"""竖版混音：全部时间从 scenes/film_vt.json 读，规则同 mix_full.py（没有冷开场，旁白目录换成 audio/vo_vt）。

用法：python audio/mix_vt.py  →  out/vt_mix.wav
"""
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfxlib import SFX, SR, Bus, ROOT, load_vo, ramp, shape_music

TL = json.loads((ROOT / "scenes/film_vt.json").read_text())
N = int((TL["duration"] + 0.5) * SR)
ORIG_RMS = -26.0
ORIG_BUS = -9.0
UNDER_DB, CARVE, PAD = -5.0, 0.75, (0.25, 0.35)

vo, game, bed, qbus, mus, fx = (Bus(N) for _ in range(6))


def src_audio(path, t0, dur, fade=0.03):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", str(ROOT / path), "-vn",
                        "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    y = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).T.copy()
    k = min(int(fade * SR), y.shape[1] // 2)
    if k:
        y[:, :k] *= ramp(k)
        y[:, -k:] *= ramp(k, up=False)
    return y


def active_rms_db(y, rel=0.08):
    m = y.mean(axis=0) if y.ndim == 2 else y
    fr = librosa.util.frame(np.pad(m, (0, 1200)), frame_length=1200, hop_length=1200)
    e = np.sqrt((fr ** 2).mean(axis=0))
    act = e[e > e.max() * rel]
    return 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-9)


# ---------------- 旁白 ----------------
MOOD = {l["id"]: l.get("mood") for l in json.loads((ROOT / "audio/vo_vt.json").read_text())}
HYPE_DB = 2.0
vo_gain = {}
for v in TL["vo"]:
    raw, _ = librosa.load(ROOT / f"audio/vo_vt/{v['id']}.wav", sr=SR, mono=True)
    y = load_vo(f"audio/vo_vt/{v['id']}.wav")
    vo_gain[v["id"]] = float(np.sqrt((y ** 2).sum() / ((raw ** 2).sum() + 1e-12)))
    vo.place(y, v["t"], 10 ** (HYPE_DB / 20) if MOOD.get(v["id"]) == "hype" else 1.0)

# ---------------- 发布会原声 ----------------
speech_spans = [(v["t"], v["t"] + v["dur"]) for v in TL["vo"]]
for q in TL["qaudio"]:
    y = src_audio(q["src"], q["s0"], q["dur"], fade=0.06)
    g = 10 ** ((-20.5 - active_rms_db(y)) / 20)
    qbus.place(y, q["t"], g)
    speech_spans.append((q["t"], q["t"] + q["dur"]))

# ---------------- 原声镜头 + 人声让位 ----------------
for o in TL["orig"]:
    y = src_audio(o["src"], o["s0"], o["dur"], fade=0.08)
    g = np.clip(ORIG_RMS - active_rms_db(y, 0.2), -12, 12) + o["db"] + ORIG_BUS
    game.place(y, o["t"], 10 ** (g / 20))
sos = butter(4, [250, 4000], "bandpass", fs=SR, output="sos")
speech = sosfiltfilt(sos, game.x, axis=1)
under = (game.x - CARVE * speech) * 10 ** (UNDER_DB / 20)
m = np.zeros(N)
for a, b in speech_spans:
    m[max(0, int((a - PAD[0]) * SR)):int((b + PAD[1]) * SR)] = 1.0
kk = int(0.25 * SR)
m = np.convolve(m, np.ones(kk) / kk, "same")
game.x = game.x * (1 - m) + under * m

# ---------------- 战术拆解底轨 ----------------
for b in TL["beds"]:
    y, sr = sf.read(ROOT / b["src"], always_2d=True)
    y = y.T if y.shape[1] <= 2 else y
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    if sr != SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    ids = [v["id"] for v in TL["vo"] if b["t"] <= v["t"] < b["t"] + b["dur"]]
    g = float(np.exp(np.mean([np.log(vo_gain[i]) for i in ids]))) if ids else 1.0
    bed.place(y[:, : int(b["dur"] * SR)], b["t"], g)
    print(f"bed {Path(b['src']).stem}: gain {20 * np.log10(g):+.1f} dB ({len(ids)} lines)")

# ---------------- 配乐 ----------------
for mu in TL["music"]:
    mus.place(shape_music(src_audio(mu["src"], mu["s0"], mu["dur"], fade=0.01), mu), mu["t"])

# ---------------- 音效 ----------------
for name, t in TL["sfx"]:
    fx.place(SFX[name](), max(0.0, t), 10 ** (-12 / 20))

mix = vo.x + qbus.x + game.x + bed.x + mus.x + fx.x
tmp = ROOT / "out/vt_mix_raw.wav"
sf.write(tmp, mix[:, : int((TL["duration"] + 0.2) * SR)].T, SR, subtype="FLOAT")
meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "ebur128=peak=true", "-f", "null", "-"],
                      capture_output=True, text=True).stderr
lufs = float(meas.rsplit("I:", 1)[1].split("LUFS")[0])
gain = -16 - lufs
out = ROOT / "out/vt_mix.wav"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-af",
                f"volume={gain:.2f}dB,alimiter=limit=0.7:attack=2:release=60:level=false",
                "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True)
print(f"integrated {lufs:.1f} LUFS, gain {gain:+.1f} dB -> {out}")
for name, b in [("vo", vo), ("quotes", qbus), ("game", game), ("beds", bed), ("music", mus), ("sfx", fx)]:
    print(f"  {name:7s} rms {20 * np.log10(np.sqrt((b.x ** 2).mean()) + 1e-9):6.1f} dBFS  peak {20 * np.log10(np.abs(b.x).max() + 1e-9):6.1f}")
