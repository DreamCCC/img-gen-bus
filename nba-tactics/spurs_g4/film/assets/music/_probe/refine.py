"""Beat grid for the picked tracks, seeded with the catalog BPM (librosa alone octave-errs on slow pieces).

usage: python refine.py  ->  ../beats/<file>.json + refine.json (per-track summary)
"""
import json
import os

import librosa
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.dirname(HERE)
os.makedirs(f'{MUSIC}/beats', exist_ok=True)

# file, catalog bpm (None = arhythmic pad), meter
PICKS = [
    ('Long_Note_Three.mp3', None, 4),
    ('Ominous_Intro.mp3', 70, 4),
    ('Montauk_Point.mp3', 118, 4),
    ('Loopster.mp3', 108, 4),
    ('Invariance.mp3', 108, 4),
    ('Industrial_Cinematic.mp3', 110, 4),
    ('The_Escalation.mp3', 96, 4),
    ('Constance.mp3', 83, 4),
    ('Stay_the_Course.mp3', 60, 4),
    ('Enter_the_Maze.mp3', 93, 4),
    ('Calmant.mp3', 58, 4),
    ('Danse_Morialta.mp3', 70, 4),
]
# tracks whose tempo changes: track each span separately, (start_s, end_s, seed_bpm)
SEGMENTS = {
    'Invariance.mp3': [(0, 114.5, 108), (116.0, 216.8, 129)],
    'The_Escalation.mp3': [(0, 200, -96), (200, 250, 129), (250, 327.3, 144)],
}
HOP = 512


def track(y, sr, seed, meter, t0=0.0):
    """seed < 0 pins the tempo to |seed| (autocorrelation peak is at half of it and the tracker octave-jumps)."""
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    kw = {'bpm': -seed} if seed < 0 else {'start_bpm': seed}
    _, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=HOP, tightness=300, **kw)
    bt = librosa.frames_to_time(beats, sr=sr, hop_length=HOP)
    lo = librosa.onset.onset_strength(S=librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, hop_length=HOP, fmax=200, n_mels=16)), sr=sr)
    phase = int(np.argmax([lo[beats[p::meter]].mean() if len(beats[p::meter]) else 0 for p in range(meter)]))
    return bt + t0, bt[phase::meter] + t0


summary = {}
for fn, bpm, meter in PICKS:
    y, sr = librosa.load(f'{MUSIC}/{fn}', sr=22050, mono=True)
    dur = len(y) / sr
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=2048)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=4096)
    st = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=2048)
    voice = S[(fr >= 1000) & (fr < 4000)].sum(0) / (S.sum(0) + 1e-12)
    loud = S.sum(0) > np.percentile(S.sum(0), 20)
    win = [(round(float(b), 0), float(voice[(st >= b) & (st < b + 4) & loud].mean()))
           for b in np.arange(0, dur - 4, 4) if ((st >= b) & (st < b + 4) & loud).any()]
    worst = sorted(win, key=lambda x: -x[1])[:3]

    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP)
    db = 20 * np.log10(rms / rms.max() + 1e-6)

    rec = {'file': fn, 'duration': round(dur, 2), 'catalog_bpm': bpm}
    if bpm:
        spans = SEGMENTS.get(fn, [(0, dur, bpm)])
        parts = [track(y[int(a * sr):int(b * sr)], sr, seed, meter, a) for a, b, seed in spans]
        bt = np.concatenate([p[0] for p in parts])
        downs = np.concatenate([p[1] for p in parts])
        ibi = np.diff(bt)
        measured = 60 / np.median(ibi[ibi > 0])
        segs = []
        for a in np.arange(0, dur, 30):
            m = (bt[:-1] >= a) & (bt[:-1] < a + 30)
            if m.sum() > 4:
                segs.append([int(a), round(float(60 / np.median(ibi[m])), 1)])
        if len(spans) > 1:
            per = []
            for (a, b, _), (pb, _) in zip(spans, parts):
                d = np.diff(pb)
                per.append([a, b, round(float(60 / np.median(d)), 1) if len(d) > 4 else None])
            rec['bpm_by_span'] = per
        rec.update({'bpm_measured': round(float(measured), 1), 'bpm_by_30s': segs, 'meter': meter,
                    'beats': [round(float(x), 3) for x in bt], 'downbeats': [round(float(x), 3) for x in downs],
                    'bar_sec': round(float(60 / measured * meter), 3)})
    else:
        on = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP, units='time', backtrack=True)
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
        strength = oenv[librosa.time_to_frames(on, sr=sr, hop_length=HOP)]
        keep = on[strength > np.percentile(strength, 90)] if len(on) else on
        rec.update({'bpm_measured': None, 'cue_points': [round(float(x), 3) for x in keep],
                    'note': 'arhythmic pad: no beat grid, cue_points = strongest onsets'})
    json.dump(rec, open(f'{MUSIC}/beats/{os.path.splitext(fn)[0]}.json', 'w'), indent=1)
    summary[fn] = {k: v for k, v in rec.items() if k not in ('beats', 'downbeats', 'cue_points')}
    summary[fn]['voice_share_worst4s'] = [[t, round(v, 3)] for t, v in worst]
    summary[fn]['voice_share_median'] = round(float(np.median([v for _, v in win])), 3)
    summary[fn]['first_downbeats'] = rec.get('downbeats', rec.get('cue_points', []))[:6]
    print(fn, json.dumps(summary[fn], ensure_ascii=False))
json.dump(summary, open(f'{HERE}/refine.json', 'w'), indent=1, ensure_ascii=False)
