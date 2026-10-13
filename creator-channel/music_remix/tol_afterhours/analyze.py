"""原曲测量：速度、调性、人声区段、伴奏响度、主旋律音高（存 f0.npz）。"""
import numpy as np
import librosa
from pathlib import Path

HERE = Path(__file__).parent
D = HERE / "stems/htdemucs_ft/tol_original"
names = "C C# D Eb E F F# G Ab A Bb B".split()

y, sr = librosa.load(D / "no_vocals.wav", sr=22050, mono=True)
for sb in (80, 120):
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=sb)
    bt = librosa.frames_to_time(beats, sr=sr)
    print("start_bpm", sb, "->", round(60 / float(np.median(np.diff(bt))), 2), "BPM, first beats", np.round(bt[:4], 2))
np.save(HERE / "beats.npy", bt)

maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ch = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y), sr=sr).mean(1)
sc = [(np.corrcoef(np.roll(maj, k), ch)[0, 1], names[k] + " major") for k in range(12)]
sc += [(np.corrcoef(np.roll(mnr, k), ch)[0, 1], names[k] + " minor") for k in range(12)]
print("key", [(round(a, 3), b) for a, b in sorted(sc, reverse=True)[:3]])

v, _ = librosa.load(D / "vocals.wav", sr=22050, mono=True)
e = np.array([np.sqrt(np.mean(v[i * sr:(i + 1) * sr] ** 2)) for i in range(len(v) // sr)])
act = e > e.max() * 0.08
segs, s = [], None
for i, a in enumerate(act):
    if a and s is None:
        s = i
    if not a and s is not None:
        segs.append((s, i))
        s = None
if s is not None:
    segs.append((s, len(act)))
print("vocal segments (s):", [x for x in segs if x[1] - x[0] >= 2])
r = librosa.feature.rms(y=y, frame_length=sr, hop_length=sr)[0]
print("instrumental rms / 10 s:", " ".join(f"{r[i:i + 10].mean():.2f}" for i in range(0, len(r), 10)))

v16, _ = librosa.load(D / "vocals.wav", sr=16000, mono=True)
hop = 256
f0, vf, vp = librosa.pyin(v16, fmin=80, fmax=800, sr=16000, hop_length=hop)
f0[vp < 0.5] = np.nan
np.savez(HERE / "f0.npz", f0=f0, hop=hop / 16000)
print("f0 frames", len(f0), "voiced", int(np.isfinite(f0).sum()))
