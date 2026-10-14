"""MiniMax speech-2.8-hd 复刻音色配旁白（内部效果版）：每句多版本 + ASR 核对 + 按情绪挑版本。

usage:
  python tools/vo_minimax.py audio/vo_cold.json audio/vo [takes=2]
  python tools/vo_minimax.py audio/vo_full.json audio/vo_full [takes=2]
音色 id 在 work/xjy/voices.json["minimax"]；MiniMax key 读 nba_auto_video/.env。
情绪：EMO 里没列的句子不传 emotion，由模型按文本自己判断；TAGGED 里的句子用带停顿 / 语气标签的合成文本。
台词 JSON 里也可以直接写 emotion / tag 字段，作用同 EMO / TAGGED（字典优先）。
Takes 写 <out>/takes/<id>_m<k>.wav，选中的复制到 <out>/<id>.wav，另写 durations.json / picks.json。
"""
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts import ROOT  # noqa: E402
from vo_takes import asr, errs, metrics  # noqa: E402

MM_ENV = dict(l.strip().split("=", 1) for l in open(Path.home() / "mgs-code/nba_auto_video/.env")
              if "=" in l and not l.lstrip().startswith("#"))
MM_KEY = MM_ENV["MINIMAX_API_KEY"].strip()
VOICE = json.loads((ROOT / "work/xjy/voices.json").read_text())["minimax"]
SPEED = 1.15

EMO = {
    "c01": "calm",
    "s2_09b": "surprised", "s3_15": "surprised", "s4_03": "surprised", "s4_07": "surprised",
    "s4_20": "surprised", "s4_22": "surprised", "s4_32": "surprised",
    "s4_16": "calm", "s4_18": "calm",
    "s4_26": "sad", "s4_36": "sad", "s5_03": "sad", "s5_05": "sad",
}
HYPE = {"s2_09b", "s4_07", "s4_20", "s4_22", "s4_32"}
# 2.8 的停顿 <#秒#> 和语气标签只进合成文本；ASR 仍按 say/text 核对
TAGGED = {
    "c04": "赛后骂声一片，说来说去就两句：<#0.25#>马刺下半场乱投，心态崩了。",
    "s3_15": "但你别忘了，比赛还剩三分半的时候，马刺手里还握着七分，<#0.35#>这都能输？",
    "s4_19": "很简单，<#0.2#>什么都不用做，把球攥在手里就行，尼克斯只能犯规把你送上罚球线，两罚都进就领先三分，对面最多投个三分追平，这是打过球的人都知道的处理。",
    "s4_20": "可福克斯把球一拿住，脚下没停，<#0.15#>直接冲着篮筐就去了。",
    "s4_22": "(gasps)一巴掌钉在了板上。",
    "s4_24": "可你看计分牌，福克斯拿住球的时候还剩十三秒，起跳的时候还剩十二点五秒，前后不到一秒，<#0.2#>这哪像是要耗时间的样子。",
    "s4_26": "(sighs)就这一球，等于白送了尼克斯一次进攻，而这场比赛最后就输在这一次进攻上。",
    "s4_37": "这场球尼克斯一共只领先了<#0.3#>五十三点八秒。",
    "s5_03": "真正把比赛送出去的，<#0.3#>是最后三分半马刺自己丢掉的那几个回合，最要命的就是福克斯那次根本不用出手的上篮。",
    "s5_05": "三天后回到圣安东尼奥，第五场马刺九十比九十四又输了四分，<#0.35#>尼克斯拿到了一九七三年以后的第一个总冠军。",
}


def synth(out, text, emotion):
    vs = {"voice_id": VOICE, "speed": SPEED, "vol": 1.0, "pitch": 0}
    if emotion:
        vs["emotion"] = emotion
    body = {"model": "speech-2.8-hd", "text": text, "stream": False, "voice_setting": vs, "language_boost": "Chinese",
            "audio_setting": {"sample_rate": 44100, "format": "mp3", "channel": 1}}
    for attempt in range(6):
        try:
            req = urllib.request.Request("https://api.minimax.io/v1/t2a_v2", data=json.dumps(body).encode(),
                                         headers={"Authorization": f"Bearer {MM_KEY}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=180).read())
            if r.get("base_resp", {}).get("status_code") != 0:
                raise RuntimeError(r.get("base_resp"))
            break
        except Exception:  # noqa: BLE001
            if attempt == 5:
                raise
            time.sleep(4 * (attempt + 1))
    tmp = Path(out).with_suffix(".mp3")
    tmp.write_bytes(bytes.fromhex(r["data"]["audio"]))
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", trim, "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()


def take(job):
    ln, k, d = job
    p = d / "takes" / f"{ln['id']}_m{k}.wav"
    if not p.exists():
        synth(p, TAGGED.get(ln["id"], ln.get("tag", ln.get("say", ln["text"]))), EMO.get(ln["id"], ln.get("emotion")))
    cache = p.with_suffix(".asr.txt")
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        heard = cache.read_text()
    else:
        heard = asr(p)
        cache.write_text(heard)
    m = metrics(p)
    e = errs(heard, ln.get("say", ln["text"]))
    m.update(take=k, heard=heard, err=e, ok=e == 0)
    return ln["id"], m


def pick(ln, takes):
    pool = [t for t in takes if t["ok"]] or [min(takes, key=lambda t: t["err"])]
    if ln["id"] in HYPE or ln.get("mood") == "hype":
        return max(pool, key=lambda t: t["bright"] + 0.5 * t["dyn"])
    return max(pool, key=lambda t: t["dyn"])


if __name__ == "__main__":
    lines = json.loads((ROOT / sys.argv[1]).read_text())
    d = ROOT / sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    (d / "takes").mkdir(parents=True, exist_ok=True)
    res = {}
    def ks(lid):
        have = {int(p.stem.rsplit("_m", 1)[1]) for p in (d / "takes").glob(f"{lid}_m*.wav")}
        return sorted(have | set(range(1, n + 1)))
    with ThreadPoolExecutor(3) as ex:
        for lid, m in ex.map(take, [(ln, k, d) for ln in lines for k in ks(ln["id"])]):
            res.setdefault(lid, []).append(m)
    durs, picks, bad = {}, {}, []
    for ln in lines:
        lid = ln["id"]
        best = pick(ln, res[lid])
        shutil.copy(d / "takes" / f"{lid}_m{best['take']}.wav", d / f"{lid}.wav")
        durs[lid] = best["dur"]
        picks[lid] = {"take": best["take"], "emotion": EMO.get(lid, ln.get("emotion")), "takes": res[lid]}
        print(f"{lid:6s} 选 m{best['take']} {best['dur']:.2f}s  " + "  ".join(
            f"m{t['take']}:{t['dur']:.2f}{'' if t['ok'] else '✗' + str(t['err'])}" for t in res[lid]))
        if not best["ok"]:
            bad.append(lid)
            print(f"       识别为：{best['heard']}")
    (d / "durations.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1))
    (d / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))
    print("total", round(sum(durs.values()), 1), "s;  无零错版本:", bad or "无")
