#!/usr/bin/env python3
"""旁白合成：百炼 CosyVoice 系统音色，多 take + ASR 核对，自动挑一条。

key 读 DASHSCOPE_API_KEY：先找 nba-tactics/.env，找不到用 creator-channel/ep01_4.8pct/.env。
行字段: id, text（字幕）, say（念的文本，默认同 text）, voice, rate, mood(hype|normal),
        alias（ASR 对人名的同音误识 → 正字，如 {"神经": "申京"}，只用于核对，不改念法）,
        pick（人工指定 take 的 seed；核对会忽略标点，停顿错位要靠人听或看识别断句）
用法: python vo.py kd_macau/e464_vo.json kd_macau/audio/e464 [takes=3]
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope
import librosa
import numpy as np
from dashscope.audio.tts_v2 import SpeechSynthesizer

HERE = Path(__file__).resolve().parent.parent
for env in (HERE / ".env", HERE.parent / "creator-channel/ep01_4.8pct/.env"):
    if env.exists():
        ENV = dict(l.strip().split("=", 1) for l in env.read_text().splitlines() if "=" in l)
        if ENV.get("DASHSCOPE_API_KEY"):
            break
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
MODEL = {"_v3": "cosyvoice-v3-flash", "_v2": "cosyvoice-v2"}


def synth(out: Path, ln: dict, seed: int) -> None:
    voice = ln.get("voice", "longfei_v3")
    model = next(m for k, m in MODEL.items() if voice.endswith(k))
    for attempt in range(5):
        try:
            audio = SpeechSynthesizer(model=model, voice=voice, speech_rate=ln.get("rate", 1.25),
                                      seed=seed).call(ln.get("say", ln["text"]))
            break
        except Exception as e:  # noqa: BLE001
            if "Throttling" in str(e) and attempt < 4:
                time.sleep(4 * (attempt + 1))
                continue
            raise
    tmp = out.with_suffix(".src")
    tmp.write_bytes(audio)
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", trim, "-ar", "48000", "-ac", "1", str(out)],
                   check=True)
    tmp.unlink()


def asr(p: Path) -> str:
    for attempt in range(4):
        r = dashscope.MultiModalConversation.call(
            model="qwen3-asr-flash", messages=[{"role": "user", "content": [{"audio": f"file://{p.resolve()}"}]}],
            asr_options={"language": "zh", "enable_itn": False})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (attempt + 1))
    return ""


def norm(s: str) -> str:
    s = s.upper().replace("他", "它").replace("她", "它")
    return re.sub(r"[^\u4e00-\u9fffA-Z0-9]", "", s)


def metrics(p: Path) -> dict:
    y, sr = librosa.load(p, sr=16000)
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0]
    db = 20 * np.log10(rms + 1e-6)
    act = db[db > db.max() - 35]
    S = np.abs(librosa.stft(y, n_fft=1024)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=1024)
    return {"dur": round(len(y) / sr, 2),
            "dyn": round(float(np.percentile(act, 95) - np.percentile(act, 40)), 1),
            "bright": round(float(10 * np.log10(S[(fr > 2000) & (fr < 5000)].sum() / S[(fr > 100) & (fr < 2000)].sum())), 1)}


def take(job):
    ln, seed, d = job
    p = d / "takes" / f"{ln['id']}_s{seed}.wav"
    if not p.exists():
        synth(p, ln, seed)
    heard = asr(p)
    fixed = heard
    for wrong, right in ln.get("alias", {}).items():
        fixed = fixed.replace(wrong, right)
    m = metrics(p)
    m.update(seed=seed, heard=heard, ok=norm(fixed) == norm(ln.get("say", ln["text"])))
    return ln["id"], m


def main() -> None:
    lines = json.loads(Path(sys.argv[1]).read_text())
    d = Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    (d / "takes").mkdir(parents=True, exist_ok=True)
    res: dict[str, list] = {}
    with ThreadPoolExecutor(3) as ex:
        for lid, m in ex.map(take, [(ln, s, d) for ln in lines for s in range(1, n + 1)]):
            res.setdefault(lid, []).append(m)
    durs, picks = {}, {}
    for ln in lines:
        lid = ln["id"]
        pool = [t for t in res[lid] if t["ok"]] or res[lid]
        best = max(pool, key=lambda t: t["bright"] + 0.5 * t["dyn"]) if ln.get("mood") == "hype" \
            else sorted(pool, key=lambda t: t["dur"])[len(pool) // 2]
        if "pick" in ln:
            best = next(t for t in res[lid] if t["seed"] == ln["pick"])
        shutil.copy(d / "takes" / f"{lid}_s{best['seed']}.wav", d / f"{lid}.wav")
        durs[lid] = best["dur"]
        picks[lid] = {"seed": best["seed"], "takes": res[lid]}
        bad = [t for t in res[lid] if not t["ok"]]
        print(f"{lid}: s{best['seed']} {best['dur']:.2f}s {'OK' if best['ok'] else '✗ ' + best['heard']}  "
              f"({len(bad)}/{len(res[lid])} 条识别不一致)")
    (d / "durations.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1))
    (d / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
