"""英文旁白词级时间：whisper medium.en 对每句 wav 出词级时间戳，写 <旁白目录>/words.json（{id: [[词, 起, 止], ...]}）。

时间线用它把字幕分段和关键词时刻对到真正念到的那个词上（英文按字母数比例估会差 0.3 秒以上）。
台词文本当 initial_prompt 传进去，人名拼写更稳。在东京跑（/root/venv_whisper，CPU）：
  python tools/vo_words.py audio/vo_full_en.json audio/vo_full_en [-j8]
已有的条目跳过；台词改了要先删掉 words.json 里对应的 id。
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_model = None


def align(job):
    global _model
    lid, wav, prompt = job
    import torch
    import whisper
    torch.set_num_threads(4)
    if _model is None:
        _model = whisper.load_model("medium.en", device="cpu")
    r = _model.transcribe(str(wav), language="en", word_timestamps=True, fp16=False, initial_prompt=prompt,
                          condition_on_previous_text=False, temperature=0.0)
    words = [[w["word"].strip(), round(w["start"], 3), round(w["end"], 3)] for s in r["segments"] for w in s["words"]]
    return lid, words


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-j")]
    jobs = next((int(a[2:]) for a in sys.argv[1:] if a.startswith("-j")), 6)
    lines = json.loads((ROOT / args[0]).read_text())
    d = ROOT / args[1]
    out = d / "words.json"
    have = json.loads(out.read_text()) if out.exists() else {}
    todo = [(l["id"], d / f"{l['id']}.wav", l.get("say", l["text"])) for l in lines if l["id"] not in have and (d / f"{l['id']}.wav").exists()]
    with ProcessPoolExecutor(jobs) as ex:
        for lid, words in ex.map(align, todo):
            have[lid] = words
            out.write_text(json.dumps(have, ensure_ascii=False, indent=0))
            print(lid, " ".join(w for w, _, _ in words), flush=True)
    print(f"done {len(todo)} lines -> {out}")
