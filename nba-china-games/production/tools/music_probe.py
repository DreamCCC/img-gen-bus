"""Measure candidate tracks: tempo, energy curve (2 s bins), breaks and surges.

usage: python tools/music_probe.py a.mp3 [b.mp3 ...]
"""
import sys
import librosa
import numpy as np

BARS = ' ▁▂▃▄▅▆▇█'
for path in sys.argv[1:]:
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    bins = np.arange(0, dur, 2.0)
    e = np.array([rms[(t >= b) & (t < b + 2)].mean() for b in bins])
    en = e / e.max()
    spark = ''.join(BARS[int(v * 8)] for v in en)
    db = 20 * np.log10(e / e.max() + 1e-6)
    jumps = [(round(b, 1), round(db[i] - db[i - 1], 1)) for i, b in enumerate(bins) if i and abs(db[i] - db[i - 1]) > 6]
    print(f'\n{path.split("/")[-1]}  {dur:.1f}s  tempo≈{float(np.atleast_1d(tempo)[0]):.1f}')
    print('  energy/2s:', spark)
    print('  jumps(dB):', jumps)
