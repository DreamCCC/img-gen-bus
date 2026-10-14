#!/usr/bin/env python3
"""短窗口精转：whisper medium.en beam search + 人名提示，词级时间戳（原片绝对秒），逐词打印。

用法:
  python quotes_wordasr2.py <src.mp4> <out_dir> name:from-to [name:from-to ...]
  人名提示偶尔会被 whisper 原样吐出来（幻觉），这时设 NOPROMPT=1 重跑。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import whisper

PROMPT = ("Postgame press conference, NBA Finals Game 4, Knicks vs Spurs. "
          "Victor Wembanyama, Mike Brown, Mitch Johnson, OG Anunoby, Jalen Brunson, De'Aaron Fox, free throws.")


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
            r = model.transcribe(str(wav), language="en", word_timestamps=True, fp16=False, beam_size=5,
                                 best_of=5, condition_on_previous_text=False,
                                 initial_prompt=None if os.environ.get("NOPROMPT") else PROMPT,
                                 temperature=(0.0, 0.2, 0.4))
        words = [{"w": w["word"], "a": round(w["start"] + t0, 3), "b": round(w["end"] + t0, 3),
                  "p": round(w.get("probability", 0), 3)} for seg in r["segments"] for w in seg.get("words", [])]
        (out / f"{name}.json").write_text(json.dumps({"from": t0, "to": t1, "words": words}, ensure_ascii=False, indent=1))
        print(f"== {name} {t0:.1f}-{t1:.1f}")
        print(" ".join(w["w"].strip() for w in words))
        for w in words:
            print(f"  {w['a']:8.2f} {w['b']:8.2f} {w['p']:.2f} {w['w'].strip()}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
