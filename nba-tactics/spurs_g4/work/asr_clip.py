"""Whisper large-v3 transcript with segment + word times. usage: python asr_clip.py media out.json [start end]"""
import json
import os
import sys
from pathlib import Path

import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))
import librosa  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else None
y, _ = librosa.load(src, sr=16000, mono=True, offset=t0, duration=None if t1 is None else t1 - t0)
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
segs, _ = m.transcribe(y, language="en", word_timestamps=True, vad_filter=True)
res = []
for s in segs:
    res.append({"t": [round(s.start + t0, 2), round(s.end + t0, 2)], "text": s.text.strip(),
                "words": [[w.word.strip(), round(w.start + t0, 2), round(w.end + t0, 2)] for w in s.words]})
    print(f"{s.start + t0:7.2f}-{s.end + t0:7.2f} {s.text.strip()}")
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
