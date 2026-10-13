"""人声乐句切分 + 逐句识别，输出歌词时间轴 suno/pop_1_lines.json。
用 ep01 的 venv 运行（需要 dashscope）。"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope
import librosa
import numpy as np

HERE = Path(__file__).parent
ROOT = HERE.parents[1] / "ep01_4.8pct"
ENV = dict(l.strip().split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]

VOC = HERE / "stems_suno/htdemucs_ft/pop_1/vocals.wav"
TMP = HERE / "suno/phr"
TMP.mkdir(exist_ok=True)

y, sr = librosa.load(VOC, sr=16000, mono=True)
db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=1024, hop_length=160)[0] + 1e-6)
thr = float(sys.argv[1]) if len(sys.argv) > 1 else 22
act = db > db.max() - thr

segs, s, gap = [], None, 0
for i, a in enumerate(act):
    t = i * 0.01
    if a:
        if s is None:
            s = t
        gap, e = 0, t
    elif s is not None:
        gap += 1
        if gap > 22:
            if e - s > 0.35:
                segs.append([s, e + 0.12])
            s = None
if s is not None:
    segs.append([s, e])

merged = []
for a, b in segs:
    if merged and a - merged[-1][1] < 0.15 and b - merged[-1][0] < 9:
        merged[-1][1] = b
    else:
        merged.append([a, b])


def asr(k):
    a, b = merged[k]
    p = TMP / f"{k:03d}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VOC), "-ss", f"{max(0, a - 0.1):.2f}",
                    "-to", f"{b + 0.1:.2f}", "-ac", "1", "-ar", "16000", str(p)], check=True)
    for attempt in range(4):
        r = dashscope.MultiModalConversation.call(
            model="qwen3-asr-flash",
            messages=[{"role": "user", "content": [{"audio": f"file://{p.resolve()}"}]}],
            asr_options={"enable_itn": False})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (attempt + 1))
    return ""


with ThreadPoolExecutor(6) as ex:
    texts = list(ex.map(asr, range(len(merged))))

lines = [{"t0": round(a, 2), "t1": round(b, 2), "asr": t} for (a, b), t in zip(merged, texts)]
(HERE / "suno/pop_1_lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1))
for ln in lines:
    print(f"{ln['t0']:7.2f}–{ln['t1']:7.2f}  {ln['asr']}")
