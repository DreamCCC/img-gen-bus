import librosa, numpy as np
d = "baby_citypop/stems/htdemucs_ft/baby_original/"
y, sr = librosa.load(d + "no_vocals.wav", sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
bt = librosa.frames_to_time(beats, sr=sr)
print("tempo", float(np.atleast_1d(tempo)[0]), "first beats", np.round(bt[:6], 2), "median ibi", round(float(np.median(np.diff(bt))), 4))
ch = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
maj = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]); mnr = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
names = "C C# D Eb E F F# G Ab A Bb B".split()
sc = [(np.corrcoef(np.roll(maj, k), ch)[0,1], names[k] + " major") for k in range(12)] + [(np.corrcoef(np.roll(mnr, k), ch)[0,1], names[k] + " minor") for k in range(12)]
print("key", sorted(sc, reverse=True)[:3])
v, _ = librosa.load(d + "vocals.wav", sr=22050, mono=True)
e = np.array([np.sqrt(np.mean(v[i*sr:(i+1)*sr]**2)) for i in range(len(v)//sr)])
act = e > e.max() * 0.08
segs = []; s = None
for i, a in enumerate(act):
    if a and s is None: s = i
    if not a and s is not None:
        segs.append((s, i)); s = None
if s is not None: segs.append((s, len(act)))
print("vocal segments (s):", [x for x in segs if x[1] - x[0] >= 2])
