"""英文旁白试音：几个百炼 qwen3-tts 男声念同样 4 句，英文 ASR 核对，拼成带编号报幕的对比文件。

usage: python tools/tts_audition_en.py out/tts_audition_en
       python tools/tts_audition_en.py out/tts_audition_en_native native   # 母语英文男声一轮
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import dashscope
import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts import ENV  # noqa: E402

dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

BASE = "Epic NBA trailer narrator. Confident, resonant male voice in clear American English, punchy on key words."
LINES = [
    ("normal", "That ball first touched a court in China forty-seven years ago.", ""),
    ("hype", "The first NBA game ever played in China!", " Big and energetic, build to the end."),
    ("quiet", "Then, the lights went out.", " Slow down and pull back, almost hushed."),
    ("normal", "Forty-seven years. And the ball keeps bouncing.", " Warm, final, let it land."),
]
CANDS = [
    ("A", "Ethan", False), ("B", "Ryan", False), ("C", "Neil", False), ("D", "Arthur", False),
    ("E", "Vincent", False), ("F", "Eldric Sage", False), ("G", "longanlufeng", True), ("H", "longfei_v3", False),
]
COSY = {"longanlufeng": "qwen-audio-3.0-tts-plus", "longfei_v3": "cosyvoice-v3-flash",
        "loongandy_v3": "cosyvoice-v3-flash", "loongeric_v3": "cosyvoice-v3-flash", "loongluca_v3": "cosyvoice-v3-flash", "loongandy_v2": "cosyvoice-v2"}
# 第二轮：母语英文男声（A–H 都有中式口音被否）
NATIVE = [("1", "loongandy_v3", False), ("2", "loongeric_v3", False), ("3", "loongluca_v3", False),
          ("4", "loongandy_v2", False), ("5", "Aiden", False), ("6", "Kai", False)]
if sys.argv[2:] == ["native"]:
    CANDS = NATIVE


def synth(out, voice, text, inst):
    tmp = Path(out).with_suffix(".src")
    if voice in COSY:
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        kw = dict(model=COSY[voice], voice=voice)
        if inst:
            kw["instruction"] = inst
        tmp.write_bytes(SpeechSynthesizer(**kw).call(text))
    else:
        for attempt in range(5):
            r = dashscope.MultiModalConversation.call(model="qwen3-tts-flash", text=text, voice=voice, language_type="English")
            if r.status_code == 200:
                break
            if attempt == 4:
                raise RuntimeError(f"{voice}: {r.code} {r.message}")
            time.sleep(4 * (attempt + 1))
        urllib.request.urlretrieve(r.output["audio"]["url"], tmp)
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", trim, "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()


def asr(p):
    for attempt in range(4):
        r = dashscope.MultiModalConversation.call(model="qwen3-asr-flash", messages=[{"role": "user", "content": [{"audio": f"file://{Path(p).resolve()}"}]}],
                                                  asr_options={"language": "en", "enable_itn": False})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (attempt + 1))
    return ""


def words(s):
    return re.sub(r"[^a-z ]", " ", s.lower().replace("-", " ")).split()


def metrics(p):
    y, sr = librosa.load(p, sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=55, fmax=400, sr=sr, frame_length=1024)
    v = f0[vf]
    rms = 20 * np.log10(librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0] + 1e-6)
    act = rms[rms > rms.max() - 35]
    return dict(dur=round(len(y) / sr, 2), f0=round(float(np.nanmedian(v)), 1),
                range=round(float(12 * np.log2(np.nanpercentile(v, 90) / np.nanpercentile(v, 10))), 1),
                dyn=round(float(np.percentile(act, 95) - np.percentile(act, 40)), 1), loud=round(float(np.percentile(act, 90)), 1))


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rep = {}
    for tag, voice, inst in CANDS:
        files = []
        for i, (mood, text, extra) in enumerate(LINES):
            p = out / f"{tag}_{voice}_{i + 1}.wav"
            if not p.exists():
                synth(p, voice, text, BASE + extra if inst else None)
            heard = asr(p)
            m = metrics(p)
            miss = [w for w in words(text) if w not in words(heard)]
            m.update(mood=mood, heard=heard, miss=miss)
            rep.setdefault(f"{tag} {voice}", []).append(m)
            files.append(p)
        ann = out / f"_ann_{tag}.wav"
        if not ann.exists():
            synth(ann, "Cherry", f"Voice {tag}.", None)
        lst = out / f"_{tag}.txt"
        sil = out / "_sil.wav"
        if not sil.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.7", str(sil)], check=True)
        lst.write_text("".join(f"file '{f.name}'\nfile '_sil.wav'\n" for f in [ann] + files))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out / f"{tag}_{voice}.wav")], check=True)
        print(tag, voice, "  ".join(f"{m['dur']}s f0 {m['f0']} 起伏 {m['range']} 重音 {m['dyn']} 响 {m['loud']}{' 漏:' + ','.join(m['miss']) if m['miss'] else ''}" for m in rep[f"{tag} {voice}"]), flush=True)
    allst = out / "_all.txt"
    allst.write_text("".join(f"file '{t}_{v}.wav'\nfile '_sil.wav'\n" for t, v, _ in CANDS))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(allst), "-c", "copy", str(out / "ALL_对比.wav")], check=True)
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
