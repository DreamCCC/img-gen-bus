"""Word timestamps for VO lines: asr_words.py vo_dir id [id ...] -> prints and writes vo_dir/words.json."""
import json
import os
import sys
from pathlib import Path

import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))

import librosa  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

root = Path(sys.argv[1])
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
out_p = root / "words.json"
out = json.loads(out_p.read_text(encoding="utf-8")) if out_p.exists() else {}
for lid in sys.argv[2:]:
    segs, _ = m.transcribe(librosa.load(str(root / f"{lid}.wav"), sr=16000)[0], language="en", word_timestamps=True)
    out[lid] = [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for s in segs for w in s.words]
    print(lid, " ".join(f"{w}@{a:.2f}" for w, a, _ in out[lid]))
out_p.write_text(json.dumps(out, indent=1), encoding="utf-8")
