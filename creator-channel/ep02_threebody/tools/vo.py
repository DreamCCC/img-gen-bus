"""全片配音：每句合成多个版本，识别校对，自动挑一版；同时保存逐字时间戳。

usage: python tools/vo.py [audio/vo_lines.json] [audio/vo] [takes=3]
版本存在 <out>/takes/<id>_s<seed>_r<rate>.wav，旁边的 .json 是逐字时间戳（已减掉切掉的开头静音）。
选中的版本复制成 <out>/<id>.wav 和 <out>/<id>.json；picks.json 记录所有指标。
缓存按 id + seed + 语速命名，不看文字：改了某句的文字，要先删掉它的 takes。
"""
import json
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope
import numpy as np
import soundfile as sf
from dashscope.audio.tts_v2 import ResultCallback, SpeechSynthesizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "ep01_4.8pct/tools"))
from tts import ENV  # noqa: E402
from vo_takes import asr, metrics, norm, pick  # noqa: E402

dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
MODEL = {"_v3": "cosyvoice-v3-flash", "_v2": "cosyvoice-v2"}
RATE = 1.25
SR = 48000
HEAD, TAIL = 0.05, 0.08


class Collect(ResultCallback):
    def __init__(self):
        self.audio, self.sent, self.err = bytearray(), {}, None
        self.done = threading.Event()

    def on_data(self, data):
        self.audio.extend(data)

    def on_event(self, message):
        out = json.loads(message)["payload"].get("output", {})
        s = out.get("sentence") or {}
        if s.get("words"):
            self.sent[s["index"]] = s["words"]

    def on_complete(self):
        self.done.set()

    def on_error(self, message):
        self.err = str(message)
        self.done.set()

    def on_close(self):
        self.done.set()


def rate(ln):
    return ln.get("rate", RATE)


def take_path(d, ln, seed):
    return d / "takes" / f"{ln['id']}_s{seed}_r{rate(ln):g}.wav"


def chars_from(sent):
    out, off, last = [], 0.0, 0.0
    for k in sorted(sent):
        ws = sent[k]
        if out and ws[0]["begin_time"] / 1000 < last - 0.05:
            off = last
        for w in ws:
            out.append({"ch": w["text"], "t0": w["begin_time"] / 1000 + off, "t1": w["end_time"] / 1000 + off})
        last = out[-1]["t1"]
    return out


def synth(out, ln, seed):
    voice = ln["voice"]
    model = next(m for k, m in MODEL.items() if voice.endswith(k))
    for attempt in range(6):
        cb = Collect()
        try:
            s = SpeechSynthesizer(model=model, voice=voice, speech_rate=rate(ln), seed=seed, callback=cb,
                                  additional_params={"word_timestamp_enabled": True})
            s.streaming_call(ln.get("say", ln["text"]))
            s.streaming_complete()
            cb.done.wait(120)
        except Exception as e:  # noqa: BLE001
            cb.err = str(e)
        if not cb.err and cb.audio:
            break
        time.sleep(4 * (attempt + 1))
    else:
        raise RuntimeError(f"{ln['id']} s{seed}: {cb.err}")
    src = Path(out).with_suffix(".src")
    src.write_bytes(bytes(cb.audio))
    raw = Path(out).with_suffix(".raw.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", str(SR), "-ac", "1", str(raw)], check=True)
    y, _ = sf.read(raw)
    src.unlink()
    raw.unlink()
    loud = np.nonzero(np.abs(y) > 10 ** (-50 / 20))[0]
    a = max(0, loud[0] - int(HEAD * SR))
    b = min(len(y), loud[-1] + int(TAIL * SR))
    sf.write(out, y[a:b], SR, subtype="PCM_16")
    shift = a / SR
    chars = [{"ch": c["ch"], "t0": round(max(0.0, c["t0"] - shift), 3), "t1": round(max(0.0, c["t1"] - shift), 3)}
             for c in chars_from(cb.sent)]
    Path(out).with_suffix(".json").write_text(json.dumps(chars, ensure_ascii=False))


def take(job):
    ln, seed, d = job
    p = take_path(d, ln, seed)
    if not p.exists() or not p.with_suffix(".json").exists():
        synth(p, ln, seed)
    heard = asr(p)
    m = metrics(p)
    m.update(seed=seed, heard=heard, ok=norm(heard) == norm(ln.get("say", ln["text"])))
    return ln["id"], m


def main():
    lines = json.loads((ROOT / (sys.argv[1] if len(sys.argv) > 1 else "audio/vo_lines.json")).read_text())
    d = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "audio/vo")
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    (d / "takes").mkdir(parents=True, exist_ok=True)
    res = {}
    with ThreadPoolExecutor(3) as ex:
        for lid, m in ex.map(take, [(ln, s, d) for ln in lines for s in range(1, n + 1)]):
            res.setdefault(lid, []).append(m)
            print(lid, f"s{m['seed']}", m["dur"], "ok" if m["ok"] else "✗", flush=True)
    durs, picks, bad = {}, {}, []
    for ln in lines:
        lid = ln["id"]
        best, clean = pick(ln, res[lid], 99)
        src = take_path(d, ln, best["seed"])
        shutil.copy(src, d / f"{lid}.wav")
        shutil.copy(src.with_suffix(".json"), d / f"{lid}.json")
        durs[lid] = best["dur"]
        picks[lid] = {"seed": best["seed"], "takes": res[lid]}
        if not clean:
            bad.append(lid)
            for t in res[lid]:
                print(f"  {lid} s{t['seed']} 识别为：{t['heard']}")
    (d / "durations.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1))
    (d / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))
    print(f"总时长 {sum(durs.values()):.1f}s，{len(lines)} 句，没有完全正确版本的：{bad}")


if __name__ == "__main__":
    main()
