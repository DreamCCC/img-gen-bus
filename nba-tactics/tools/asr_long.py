#!/usr/bin/env python3
"""长音频转写：切成定长小段，百炼 qwen3-asr-flash 并行识别，输出带时间码的文本。

用来在发布会、解说里定位原话的时间点（精度 = 段长）。要在沙箱外运行。
key 读 DASHSCOPE_API_KEY（同 vo.py）。

用法:
  python asr_long.py in.mp4 out.txt [--chunk 30] [--lang en] [--from 0] [--to 0]
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope

HERE = Path(__file__).resolve().parent.parent
for env in (HERE / ".env", HERE.parent / "creator-channel/ep01_4.8pct/.env"):
    if env.exists():
        ENV = dict(l.strip().split("=", 1) for l in env.read_text().splitlines() if "=" in l)
        if ENV.get("DASHSCOPE_API_KEY"):
            break
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]


def duration(p: str) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def asr(p: Path, lang: str) -> str:
    for i in range(5):
        r = dashscope.MultiModalConversation.call(
            model="qwen3-asr-flash",
            messages=[{"role": "user", "content": [{"audio": f"file://{p.resolve()}"}]}],
            asr_options={"language": lang, "enable_itn": True})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (i + 1))
    return "[ASR 失败]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--chunk", type=float, default=30)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    t1 = a.t1 or duration(a.src)
    starts = []
    t = a.t0
    while t < t1:
        starts.append(t)
        t += a.chunk
    with tempfile.TemporaryDirectory() as td:
        def job(s: float) -> str:
            wav = Path(td) / f"{s:08.1f}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(min(a.chunk, t1 - s)), "-i", a.src,
                            "-ac", "1", "-ar", "16000", str(wav)], check=True)
            return asr(wav, a.lang)
        with ThreadPoolExecutor(a.workers) as ex:
            texts = list(ex.map(job, starts))
    with open(a.out, "w", encoding="utf-8") as f:
        for s, txt in zip(starts, texts):
            f.write(f"[{int(s // 60):02d}:{s % 60:04.1f}] {txt}\n")
    print(f"{len(starts)} 段 -> {a.out}")


if __name__ == "__main__":
    main()
