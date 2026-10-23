"""VO QA: whisper every line in a vo dir (lines.json + <id>.wav), word-match vs script."""
import json
import os
import re
import sys
from pathlib import Path

import torch

os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))

import librosa  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

root = Path(sys.argv[1])
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("-", " ")).split()
dur = json.loads((root / "durations.json").read_text(encoding="utf-8"))
for ln in json.loads((root / "lines.json").read_text(encoding="utf-8")):
    y = librosa.load(str(root / f"{ln['id']}.wav"), sr=16000)[0]
    segs, _ = m.transcribe(y, language="en", beam_size=5)
    heard = " ".join(s.text.strip() for s in segs)
    ok = "OK  " if norm(heard) == norm(ln["text"]) else "DIFF"
    wps = len(norm(ln["text"])) / dur[ln["id"]]
    print(f"{ln['id']} {ok} {dur[ln['id']]:5.2f}s {wps:4.2f} w/s | {heard}")
