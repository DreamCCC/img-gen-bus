"""冷开场样片混音：旁白 + 原片原声 + 合成音效 + 配乐，全部从 scenes/film_h.json 读时间。不做闪避。

用法：python audio/mix_cold.py  →  out/cold_mix.wav
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfxlib import SFX, SR, Bus, ROOT, load_vo, ramp, shape_music

TL = json.loads((ROOT / "scenes/film_h.json").read_text())
N = int((TL["duration"] + 0.5) * SR)
vo, orig, fx = Bus(N), Bus(N), Bus(N)


def src_audio(path, t0, dur):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", str(ROOT / path), "-vn",
                        "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    y = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).T.copy()
    k = int(0.03 * SR)
    y[:, :k] *= ramp(k)
    y[:, -k:] *= ramp(k, up=False)
    return y


for path, s0, t, dur, db in TL["orig"]:
    orig.place(src_audio(path, s0, dur), t, 10 ** (db / 20))

for v in TL["vo"]:
    vo.place(load_vo(f"audio/vo/{v['id']}.wav"), v["t"], 1.0)


for name, t in TL["sfx"]:
    fx.place(SFX[name](), t, 10 ** (-10 / 20))

mus = Bus(N)
for mu in TL.get("music", []):
    y = src_audio(mu["src"], mu["s0"], mu["dur"])
    mus.place(shape_music(y, mu), mu["t"])

mix = vo.x * 10 ** (0 / 20) + orig.x * 10 ** (-9 / 20) + fx.x + mus.x
tmp = ROOT / "out/cold_mix_raw.wav"
sf.write(tmp, mix.T, SR, subtype="FLOAT")
meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "ebur128=peak=true", "-f", "null", "-"],
                      capture_output=True, text=True).stderr
lufs = float(meas.rsplit("I:", 1)[1].split("LUFS")[0])
gain = -16 - lufs
out = ROOT / "out/cold_mix.wav"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-af",
                f"volume={gain:.2f}dB,alimiter=limit=0.7:attack=2:release=60:level=false",
                "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True)
print(f"integrated {lufs:.1f} LUFS, gain {gain:+.1f} dB -> {out}")
