"""Bailian qwen3-tts synthesis. Key: DASHSCOPE_API_KEY in <项目根目录>/.env.

usage:
  python tools/tts.py one  out.wav  voice  "文本"  ["语气指令"]
  python tools/tts.py lines lines.json out_dir      # [{"id","text","voice","inst"}...], skips existing
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import dashscope

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(l.strip().split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

DEFAULT_INST = "低沉、克制的纪录片旁白，男声，语速稍慢，吐字清楚，句尾自然下沉，不要播音腔，不要夸张。"


def synth(out, voice, text, inst=None, model=None):
    model = model or ("qwen3-tts-instruct-flash" if inst else "qwen3-tts-flash")
    kw = dict(model=model, text=text, voice=voice, language_type="Chinese")
    if inst:
        kw.update(instructions=inst, optimize_instructions=False)
    r = dashscope.MultiModalConversation.call(**kw)
    if r.status_code != 200:
        raise RuntimeError(f"{voice}: {r.code} {r.message}")
    url = r.output["audio"]["url"]
    tmp = Path(out).with_suffix(".src")
    urllib.request.urlretrieve(url, tmp)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]))
    return dur


if __name__ == "__main__":
    if sys.argv[1] == "one":
        inst = sys.argv[5] if len(sys.argv) > 5 else DEFAULT_INST
        print(sys.argv[3], round(synth(sys.argv[2], sys.argv[3], sys.argv[4], inst), 2))
    elif sys.argv[1] == "lines":
        lines = json.loads(Path(sys.argv[2]).read_text())
        out_dir = Path(sys.argv[3]); out_dir.mkdir(parents=True, exist_ok=True)
        durs = {}
        for ln in lines:
            out = out_dir / f'{ln["id"]}.wav'
            if not out.exists():
                synth(out, ln.get("voice", "Ethan"), ln["text"], ln.get("inst", DEFAULT_INST))
            durs[ln["id"]] = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]))
            print(ln["id"], round(durs[ln["id"]], 2), ln["text"])
        (out_dir / "durations.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1))
