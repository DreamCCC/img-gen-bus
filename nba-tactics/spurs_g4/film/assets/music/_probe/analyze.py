"""Batch-measure candidate tracks for narration compatibility.

Per track: tempo, beat grid, downbeat estimate (bar phase with the strongest low-end onset),
band energy shares (sub/low/lowmid/voice 1-4k/presence), spectral flatness, energy curve.
usage: python analyze.py cand/*.mp3  ->  writes features.json + beats/<name>.json
"""
import json
import os
import sys

import librosa
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BANDS = {'sub': (20, 80), 'low': (80, 250), 'lowmid': (250, 1000), 'voice': (1000, 4000), 'hi': (4000, 11000)}
os.makedirs(f'{HERE}/beats', exist_ok=True)
out = {}
for path in sys.argv[1:]:
    name = os.path.splitext(os.path.basename(path))[0]
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=4096)
    tot = S.sum()
    share = {k: float(S[(fr >= a) & (fr < b)].sum() / tot) for k, (a, b) in BANDS.items()}
    flat = float(np.mean(librosa.feature.spectral_flatness(S=S)))

    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=512)
    tempo = float(np.atleast_1d(tempo)[0])
    bt = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    pulse_conf = float(np.mean(oenv[beats]) / (np.mean(oenv) + 1e-9)) if len(beats) else 0.0

    lo = librosa.onset.onset_strength(S=librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, hop_length=512, fmax=200, n_mels=16)), sr=sr)
    downs = []
    if len(beats) >= 8:
        phase = int(np.argmax([lo[beats[p::4]].mean() for p in range(4)]))
        downs = [round(float(t), 3) for t in bt[phase::4]]

    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    bins = np.arange(0, dur, 2.0)
    e = np.array([rms[(t >= b) & (t < b + 2)].mean() for b in bins])
    db = 20 * np.log10(e / e.max() + 1e-6)
    spark = ''.join(' ▁▂▃▄▅▆▇█'[int(v * 8)] for v in e / e.max())
    jumps = [(round(float(b), 1), round(float(db[i] - db[i - 1]), 1))
             for i, b in enumerate(bins) if i and abs(db[i] - db[i - 1]) > 6]

    json.dump({'title': name, 'tempo': round(tempo, 2), 'beats': [round(float(x), 3) for x in bt],
               'downbeats': downs}, open(f'{HERE}/beats/{name}.json', 'w'))
    out[name] = {'dur': round(dur, 1), 'tempo': round(tempo, 1), 'pulse_conf': round(pulse_conf, 2),
                 'n_beats': len(bt), 'first_down': downs[0] if downs else None,
                 'share': {k: round(v, 3) for k, v in share.items()}, 'flat': round(flat, 4),
                 'spark': spark, 'jumps': jumps}
    s = out[name]['share']
    print(f"{name[:30]:30s} {dur:6.1f}s tempo={tempo:6.1f} conf={pulse_conf:4.2f} "
          f"sub={s['sub']:.2f} low={s['low']:.2f} lmid={s['lowmid']:.2f} voice={s['voice']:.3f} hi={s['hi']:.3f}")
    print('   ', spark)
    print('    jumps', jumps[:10])
json.dump(out, open(f'{HERE}/features.json', 'w'), ensure_ascii=False, indent=1)
