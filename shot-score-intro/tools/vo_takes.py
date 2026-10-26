"""Multi-take VO synthesis (CosyVoice system voice) with ASR check, slot fit and automatic take selection.

usage:
  python tools/vo_takes.py audio/vo_lines.json audio/vo [takes=3]
Line fields: id, text (subtitle), say (spoken text, defaults to text; ASR is checked against it), voice, mood (hype|quiet|normal), rate.
Slots come from scenes/film_h.json / film_v.json when they exist; before the timeline is built every line is unconstrained.
Takes go to <out>/takes/<id>_s<seed>.wav; the chosen take is copied to <out>/<id>.wav; picks.json keeps every metric.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import dashscope
import librosa
import numpy as np
from dashscope.audio.tts_v2 import SpeechSynthesizer
from pypinyin import lazy_pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts import ENV, ROOT  # noqa: E402

dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
MODEL = {"_v3": "cosyvoice-v3-flash", "_v2": "cosyvoice-v2"}


def slots():
    s = {}
    for f in ("scenes/film_h.json", "scenes/film_v.json"):
        if not (ROOT / f).exists():
            continue
        d = json.loads((ROOT / f).read_text())
        vo = d["vo"]
        for a, b in zip(vo, vo[1:] + [None]):
            room = (b["t"] if b else d["duration"]) - a["t"]
            s[a["id"]] = min(s.get(a["id"], 99), room)
    return s


def synth(out, ln, seed):
    voice = ln["voice"]
    model = next(m for k, m in MODEL.items() if voice.endswith(k))
    for attempt in range(5):
        try:
            audio = SpeechSynthesizer(model=model, voice=voice, speech_rate=ln.get("rate", 1.0), seed=seed).call(ln.get("say", ln["text"]))
            break
        except Exception as e:  # noqa: BLE001
            if attempt < 4 and ("Throttling" in str(e) or isinstance(e, (TimeoutError, ConnectionError, OSError))):
                time.sleep(4 * (attempt + 1))
                continue
            raise
    tmp = Path(out).with_suffix(".src")
    tmp.write_bytes(audio)
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", trim, "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()


def asr(p):
    for attempt in range(4):
        r = dashscope.MultiModalConversation.call(model="qwen3-asr-flash", messages=[{"role": "user", "content": [{"audio": f"file://{Path(p).resolve()}"}]}],
                                                  asr_options={"language": "zh", "enable_itn": False})
        if r.status_code == 200:
            return r.output.choices[0].message.content[0]["text"]
        time.sleep(3 * (attempt + 1))
    return ""


ALIAS = {"卡塞尔": "卡斯尔"}


def norm(s):
    s = s.upper()
    for k, v in ALIAS.items():
        s = s.replace(k, v)
    s = re.sub(r"[^\u4e00-\u9fffA-Z]", "", s).replace("儿", "").replace("地", "的").replace("得", "的")
    return lazy_pinyin(s)


def errs(heard, ref):
    a, b = norm(heard), norm(ref)
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != "equal")


def metrics(p):
    y, sr = librosa.load(p, sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=55, fmax=400, sr=sr, frame_length=1024)
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0]
    db = 20 * np.log10(rms + 1e-6)
    act = db[db > db.max() - 35]
    S = np.abs(librosa.stft(y, n_fft=1024)) ** 2
    fr = librosa.fft_frequencies(sr=sr, n_fft=1024)
    return {"dur": round(len(y) / sr, 2), "f0": round(float(np.nanmedian(f0[vf])), 1),
            "dyn": round(float(np.percentile(act, 95) - np.percentile(act, 40)), 1),
            "bright": round(float(10 * np.log10(S[(fr > 2000) & (fr < 5000)].sum() / S[(fr > 100) & (fr < 2000)].sum())), 1)}


def take(job):
    ln, seed, d = job
    p = d / "takes" / f"{ln['id']}_s{seed}.wav"
    if not p.exists():
        synth(p, ln, seed)
    cache = p.with_suffix(".asr.txt")
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        heard = cache.read_text()
    else:
        heard = asr(p)
        cache.write_text(heard)
    m = metrics(p)
    e = errs(heard, ln.get("say", ln["text"]))
    m.update(seed=seed, heard=heard, err=e, ok=e == 0)
    return ln["id"], m


def pick(ln, takes, room):
    fit = [t for t in takes if t["ok"] and t["dur"] <= room - 0.1]
    pool = fit or [t for t in takes if t["dur"] <= room - 0.1] or takes
    if not fit:
        least = min(t["err"] for t in pool)
        pool = [t for t in pool if t["err"] == least]
    mood = ln.get("mood", "normal")
    if mood == "hype":
        return max(pool, key=lambda t: t["bright"] + 0.5 * t["dyn"]), bool(fit)
    if mood == "quiet":
        return min(pool, key=lambda t: t["f0"]), bool(fit)
    return sorted(pool, key=lambda t: t["f0"])[len(pool) // 2], bool(fit)


if __name__ == "__main__":
    lines = json.loads(Path(sys.argv[1]).read_text())
    d = ROOT / sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    (d / "takes").mkdir(parents=True, exist_ok=True)
    room = slots()
    res = {}
    with ThreadPoolExecutor(2) as ex:
        for lid, m in ex.map(take, [(ln, s, d) for ln in lines for s in range(1, n + 1)]):
            res.setdefault(lid, []).append(m)
    durs, picks = {}, {}
    for ln in lines:
        lid = ln["id"]
        r = room.get(lid, 99)
        best, clean = pick(ln, res[lid], r)
        shutil.copy(d / "takes" / f"{lid}_s{best['seed']}.wav", d / f"{lid}.wav")
        durs[lid] = best["dur"]
        picks[lid] = {"seed": best["seed"], "room": round(r, 2), "takes": res[lid]}
        flag = "" if clean else "  <-- 无完全正确且放得下的版本"
        print(f"{lid:5s} 选 s{best['seed']}  {best['dur']:.2f}s / 槽 {r:.2f}s  "
              + "  ".join(f"s{t['seed']}:{t['dur']:.2f}{'' if t['ok'] else '✗' + str(t['err'])}" for t in res[lid]) + flag)
        for t in res[lid]:
            if not t["ok"]:
                print(f"       s{t['seed']} 识别为：{t['heard']}")
    (d / "durations.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1))
    (d / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))
