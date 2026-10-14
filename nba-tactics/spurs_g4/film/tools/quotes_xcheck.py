#!/usr/bin/env python3
"""引语交叉核对：把指定窗口送百炼 qwen3-asr-flash 转一遍，和 whisper 词级结果对照。要在沙箱外运行。

key 读 film/.env 的 DASHSCOPE_API_KEY（不打印）。
用法:
  python quotes_xcheck.py <src.mp4> name:from-to [name:from-to ...]
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import dashscope

ENV = Path(__file__).resolve().parent.parent / ".env"
dashscope.api_key = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)["DASHSCOPE_API_KEY"]


def asr(p: Path) -> str:
    for i in range(5):
        try:
            r = dashscope.MultiModalConversation.call(
                model="qwen3-asr-flash",
                messages=[{"role": "user", "content": [{"audio": f"file://{p.resolve()}"}]}],
                asr_options={"language": "en", "enable_itn": True})
            if r.status_code == 200:
                return r.output.choices[0].message.content[0]["text"]
        except Exception:
            pass
        time.sleep(3 * (i + 1))
    return "[ASR 失败]"


def main() -> None:
    src = sys.argv[1]
    with tempfile.TemporaryDirectory() as td:
        for spec in sys.argv[2:]:
            name, rng = spec.split(":", 1)
            a, b = (float(x) for x in rng.split("-"))
            wav = Path(td) / f"{name}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src,
                            "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            print(f"== {name} {a:.2f}-{b:.2f}: {asr(wav)}", flush=True)


if __name__ == "__main__":
    main()
