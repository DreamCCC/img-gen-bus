import librosa, numpy as np
d = "baby_citypop/stems/htdemucs_ft/baby_original/"
y, sr = librosa.load(d + "no_vocals.wav", sr=22050, mono=True)
_, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=130)
bt = librosa.frames_to_time(beats, sr=sr)
C = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y), sr=sr, hop_length=512)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=512)
names = "C C# D Eb E F F# G Ab A Bb B".split()
tmpl = {}
for r in range(12):
    tmpl[names[r]] = np.roll([1,0,0,0,1,0,0,1,0,0,0,0], r)
    tmpl[names[r] + "m"] = np.roll([1,0,0,1,0,0,0,1,0,0,0,0], r)
out = []
for i in range(0, len(bt) - 2, 2):
    m = C[:, (ct >= bt[i]) & (ct < bt[i + 2])].mean(axis=1)
    best = max(tmpl, key=lambda k: np.dot(tmpl[k], m) / np.linalg.norm(m))
    out.append((round(bt[i], 2), best))
print(len(bt), "beats; ibi", round(float(np.median(np.diff(bt))), 4))
line = ""
for t, c in out:
    line += f"{c:>3}"
print(" ".join(f"{t:.1f}" for t, _ in out[::16]))
for k in range(0, len(out), 16):
    print(f"{out[k][0]:6.1f}s", " ".join(f"{c:>3}" for _, c in out[k:k + 16]))
