"""Print word times + detected pauses for VO lines. usage: python vo_words.py s06 s08 ..."""
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))
from faster_whisper import WhisperModel  # noqa: E402

VO = Path(__file__).resolve().parents[1] / "film/audio/vo_en"
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
for vid in sys.argv[1:]:
    y, sr = sf.read(VO / f"{vid}.wav")
    y = y.mean(1) if y.ndim > 1 else y
    import librosa
    y16 = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000)
    segs, _ = m.transcribe(y16, language="en", word_timestamps=True)
    words = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    print(f"== {vid} dur {len(y) / sr:.2f}s")
    print("  " + "  ".join(f"{w}@{a:.2f}" for w, a, _ in words))
    gaps = [(words[k + 1][1] - words[k][2], words[k + 1][0], words[k + 1][1]) for k in range(len(words) - 1)]
    for g, w, a in sorted(gaps, reverse=True)[:3]:
        print(f"  pause {g:.2f}s before '{w}' @{a:.2f}")
