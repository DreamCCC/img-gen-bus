"""Transcribe reference videos (first N minutes) for style study.

usage:
  python creator-channel/tools/transcribe_ref.py creator-channel/style_study [minutes=10]
Reads <dir>/audio/*.m4a and <dir>/meta.txt ("id | uploader | title | duration" per line);
writes <dir>/transcripts/<id>.txt with a header line.
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ep01_4.8pct" / "tools"))
from tts import ENV  # noqa: E402

dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
CHUNK = 170


def asr(p):
    for attempt in range(5):
        r = dashscope.MultiModalConversation.call(model="qwen3-asr-flash", messages=[{"role": "user", "content": [{"audio": f"file://{Path(p).resolve()}"}]}],
                                                  asr_options={"language": "zh", "enable_itn": True})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (attempt + 1))
    return ""


def main():
    d = Path(sys.argv[1])
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    meta = {}
    for line in (d / "meta.txt").read_text().splitlines():
        parts = [s.strip() for s in line.split("|")]
        if len(parts) >= 4:
            meta[parts[0]] = parts
    chunks_dir = d / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    (d / "transcripts").mkdir(exist_ok=True)
    jobs = []
    for src in sorted((d / "audio").glob("*.m4a")):
        vid = src.stem
        dur = min(float(meta.get(vid, [0, 0, 0, 1e9])[3]), minutes * 60)
        n = int(dur // CHUNK) + (1 if dur % CHUNK > 5 else 0)
        for i in range(n):
            out = chunks_dir / f"{vid}_{i:02d}.mp3"
            if not out.exists():
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(i * CHUNK), "-t", str(CHUNK), "-i", str(src),
                                "-ac", "1", "-ar", "16000", "-b:a", "48k", str(out)], check=True)
            jobs.append((vid, i, out))
    with ThreadPoolExecutor(8) as ex:
        texts = list(ex.map(lambda j: asr(j[2]), jobs))
    by_vid = {}
    for (vid, i, _), t in zip(jobs, texts):
        by_vid.setdefault(vid, []).append((i, t))
    for vid, parts in by_vid.items():
        m = meta.get(vid, [vid, "?", "?", "?"])
        body = "\n\n".join(t for _, t in sorted(parts))
        (d / "transcripts" / f"{vid}.txt").write_text(f"# {m[1]} · {m[2]}（前 {minutes:g} 分钟）\n\n{body}\n")
        print(vid, m[1], len(body), "字")


if __name__ == "__main__":
    main()
