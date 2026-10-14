"""Round-2 audition: ad / trailer style ("铿锵有力"). Designs custom voices once (ids cached in out_dir/voices.json).

usage:
  python tools/tts_audition2.py out_dir [config.json]
config.json (all keys optional, defaults below are the NBA project):
  {"preview": "声音设计试听句", "ad": "广告风格语气指令", "lines": [["A", "台词！"], ...],
   "designs": {"qvd_xxx": ["qwen", "声音描述"], "cvd_xxx": ["cosy", "声音描述"]}}
Voice descriptions must describe timbre / age / energy / use case, never a real person (imitation is not supported and risky).
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts_audition as A  # noqa: E402

PREVIEW = "詹姆斯来了！科比来了！库里来了！连乔丹，也来了！"

LINES = [
    ("A", "二零零二年，那代人里，走出了一个巨人！"),
    ("B", "詹姆斯来了！科比来了！库里来了！"),
    ("C", "连乔丹，也来了！"),
    ("D", "四十七年。它，回来了！"),
]
AD = "激昂有力的篮球广告宣传片旁白，男声，声音洪亮饱满，重音铿锵、一字一顿地砸下去，情绪层层推进，高潮处充满爆发力和号召力，不要播音腔。"

DESIGNS = {
    "qvd_hype": ("qwen", "35岁左右的中国男性，体育宣传片与电影预告片旁白。中低音，音色浑厚有力，胸腔共鸣强，爆发力极强；情绪激昂热血，富有感染力和号召力，重音铿锵，语调起伏大，情绪层层推进，高潮处声音洪亮、几乎呐喊。普通话标准，不要播音腔。"),
    "qvd_ad": ("qwen", "30岁左右的中国男性广告配音员，专门配运动品牌和体育赛事广告。声音明亮洪亮、穿透力强，中音偏低，咬字干脆利落，每个重音都铿锵有力，节奏感极强，语气自信、热血、充满号召力，像在点燃全场。普通话标准。"),
    "cvd_hype": ("cosy", "35岁左右的男性体育宣传片旁白，中低音，音色浑厚有力，胸腔共鸣强，爆发力强，情绪激昂热血、富有感染力，重音铿锵，语调起伏大，适合篮球宣传片和热血预告片。"),
    "cvd_ad": ("cosy", "30岁左右的男性运动品牌广告配音员，声音明亮洪亮、穿透力强，咬字干脆利落，重音铿锵有力，节奏感强，语气自信热血、充满号召力，适合体育赛事广告和宣传片。"),
}


def cands(v):
    designed = [(n, (lambda vid: (lambda o, t: A.qwen_vd(o, vid, t)))(v[n]) if k == "qwen"
                 else (lambda vid: (lambda o, t: A.cosy(o, "cosyvoice-v3.5-plus", vid, t)))(v[n]))
                for n, (k, _) in DESIGNS.items()]
    return [("q_Kai", lambda o, t: A.qwen_synth(o, "Kai", t, AD))] + designed + [
        ("qa_lufeng", lambda o, t: A.cosy(o, "qwen-audio-3.0-tts-plus", "longanlufeng", t, AD)),
        ("c_longfei", lambda o, t: A.cosy(o, "cosyvoice-v3-flash", "longfei_v3", t)),
        ("c_longanchong", lambda o, t: A.cosy(o, "cosyvoice-v2", "longanchong", t)),
        ("c_longanyang", lambda o, t: A.cosy(o, "cosyvoice-v3-flash", "longanyang", t, "你正在进行比赛解说，你说话的情感是surprised。")),
        ("q_Vincent", lambda o, t: A.qwen_synth(o, "Vincent", t, AD)),
        ("q_Ethan", lambda o, t: A.qwen_synth(o, "Ethan", t, AD)),
        ("m_badao", lambda o, t: A.minimax(o, "male-qn-badao", t, intensity=-60)),
        ("m_presenter", lambda o, t: A.minimax(o, "presenter_male", t, intensity=-60, emotion="surprised")),
    ]


def run(job):
    cand, fn, lid, text = job
    out = OUT / cand / f"{lid}.wav"
    if out.exists():
        return cand, lid, "skip"
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            fn(out, text)
            return cand, lid, "ok"
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if ("Throttling" in msg or "429" in msg) and attempt < 4:
                time.sleep(4 * (attempt + 1))
                continue
            return cand, lid, f"ERR {msg[:200]}"


if __name__ == "__main__":
    OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
    A.OUT = str(OUT)
    if len(sys.argv) > 2:
        cfg = json.loads(Path(sys.argv[2]).read_text())
        PREVIEW = cfg.get("preview", PREVIEW)
        AD = cfg.get("ad", AD)
        LINES = [tuple(x) for x in cfg.get("lines", LINES)]
        DESIGNS = {k: tuple(x) for k, x in cfg.get("designs", DESIGNS).items()}
    vf = OUT / "voices.json"
    voices = json.loads(vf.read_text()) if vf.exists() else {}
    for name, (kind, prompt) in DESIGNS.items():
        if name not in voices:
            voices[name] = A.design(name, kind, prompt, PREVIEW)
            vf.write_text(json.dumps(voices, ensure_ascii=False, indent=1))
            print("designed", name, voices[name], flush=True)
    cs = cands(voices)
    jobs = [(c, fn, lid, t) for c, fn in cs for lid, t in LINES]
    with ThreadPoolExecutor(2) as ex:
        for c, lid, st in ex.map(run, jobs):
            if st != "skip":
                print(c, lid, st, flush=True)
    done = []
    for c, _ in cs:
        files = [OUT / c / f"{lid}.wav" for lid, _ in LINES]
        if all(f.exists() for f in files):
            A.join(files, OUT / f"{c}.wav", 0.6)
            done.append(c)
    (OUT / "ALL_order.txt").write_text("\n".join(f"{i+1:02d} {c}" for i, c in enumerate(done)) + "\n")
    print("joined:", " ".join(done))
