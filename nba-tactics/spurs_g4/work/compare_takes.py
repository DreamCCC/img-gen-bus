"""Compare Charon takes per line: speech length, words/sec, pitch range (semitones), loudness swing (dB), ASR text."""
import os
import re
import sys
from pathlib import Path

import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))

import librosa
import numpy as np
from faster_whisper import WhisperModel

sys.path.insert(0, "film/tools")
from tts_aihubmix import LINES  # noqa: E402

A = Path("film/out/audition_en")
TAKES = {"v1": A / "g_Charon", "v2b": A / "v2b/charon_b", "v2c": A / "v2c/charon_c"}
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
tot = {k: 0.0 for k in TAKES}
for lid, text, _ in LINES:
    print(f"== {lid}  {text}")
    for k, d in TAKES.items():
        y, sr = librosa.load(str(d / f"{lid}.wav"), sr=16000)
        idx = np.flatnonzero(np.abs(y) > 0.02)
        sp = (idx[-1] - idx[0]) / sr
        tot[k] += sp
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr)
        f0 = f0[vf & ~np.isnan(f0)]
        st = 12 * np.log2(np.percentile(f0, 95) / np.percentile(f0, 5)) if len(f0) > 5 else 0
        rms = librosa.feature.rms(y=y)[0]
        rms = rms[rms > 0.01]
        swing = 20 * np.log10(np.percentile(rms, 95) / np.percentile(rms, 20)) if len(rms) > 5 else 0
        heard = " ".join(s.text.strip() for s in m.transcribe(y, language="en", beam_size=5)[0])
        words = len(re.findall(r"[A-Za-z'-]+", text))
        print(f"  {k:4s} speech {sp:4.2f}s  {words / sp:4.2f} w/s  pitch range {st:4.1f} st  loud swing {swing:4.1f} dB | {heard}")
print("total speech:", {k: round(v, 2) for k, v in tot.items()})
