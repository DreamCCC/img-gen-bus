#!/usr/bin/env python3
"""发布会原声词级转写：按窗口切音频，本地 whisper medium.en 出词级时间戳（原片绝对秒）。

用法:
  python quotes_wordasr.py <src.mp4> <out_dir> name:from-to [name:from-to ...]
  from/to 可写秒或 mm:ss，例如 q4_3:13:50-15:30
输出 <out_dir>/<name>.json（words 列表）和 <name>.txt（人读版，每段一行带时间）。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import whisper


def sec(s: str) -> float:
    if ":" in s:
        m, x = s.split(":")
        return int(m) * 60 + float(x)
    return float(s)


def main() -> None:
    src, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("medium.en", device="cpu")
    for spec in sys.argv[3:]:
        name, rng = spec.split(":", 1)
        a, b = rng.split("-")
        t0, t1 = sec(a), sec(b)
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "a.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", src,
                            "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            r = model.transcribe(str(wav), language="en", word_timestamps=True, fp16=False,
                                 condition_on_previous_text=False, temperature=0.0)
        words, lines = [], []
        for seg in r["segments"]:
            ws = [{"w": w["word"], "a": round(w["start"] + t0, 3), "b": round(w["end"] + t0, 3),
                   "p": round(w.get("probability", 0), 3)} for w in seg.get("words", [])]
            words += ws
            lines.append(f"[{seg['start'] + t0:8.2f}-{seg['end'] + t0:8.2f}] {seg['text'].strip()}")
        (out / f"{name}.json").write_text(json.dumps({"from": t0, "to": t1, "words": words}, ensure_ascii=False, indent=1))
        (out / f"{name}.txt").write_text("\n".join(lines) + "\n")
        print(f"== {name} {t0:.1f}-{t1:.1f}", flush=True)
        print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
