"""Audition QA: whisper each line, word-match vs script, leading/trailing silence, speech length."""
import re
import sys
from pathlib import Path

import os

import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))

import librosa
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

sys.path.insert(0, "film/tools")
from tts_aihubmix import CANDS, LINES  # noqa: E402

root = Path(sys.argv[1] if len(sys.argv) > 1 else "film/out/audition_en")
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("-", " ")).split()

for c, _, _ in CANDS:
    print(f"== {c}")
    for lid, text, _ in LINES:
        p = root / c / f"{lid}.wav"
        a, sr = sf.read(p)
        env = np.abs(a) > 0.02
        idx = np.flatnonzero(env)
        lead, tail = (idx[0] / sr, (len(a) - idx[-1]) / sr) if len(idx) else (0, 0)
        segs, _ = m.transcribe(librosa.load(str(p), sr=16000)[0], language="en", beam_size=5)
        heard = " ".join(s.text.strip() for s in segs)
        want, got = norm(text), norm(heard)
        ok = "OK " if got == want else "DIFF"
        print(f"  {lid} {ok} dur {len(a)/sr:4.1f}s speech {(idx[-1]-idx[0])/sr if len(idx) else 0:4.1f}s "
              f"lead {lead:.2f} tail {tail:.2f} | {heard}")
