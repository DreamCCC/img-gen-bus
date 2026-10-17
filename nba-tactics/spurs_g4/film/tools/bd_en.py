"""竖版战术拆解的英文 EDL：由 ../eXXX_vt_edl.json 生成 ../eXXX_vt_en_edl.json。

换英文旁白（audio/vo_vt_en）、英文角标 / 标注 / 球员名；图层里挂在中文旁白某个词上的时刻（"b5+2.7" 这种），
按 REMAP 换成英文旁白里对应词的位置（words.json 词级时间，见 tools/en_vo.py）。
用法：python tools/bd_en.py
"""
import json
from pathlib import Path

import en_vo

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT.parent
LINES = {l["id"]: l for l in json.loads((ROOT / "audio/vo_vt_en.json").read_text())}
VOD = ROOT / "audio/vo_vt_en"
DUR = json.loads((VOD / "durations.json").read_text())
WORDS = json.loads((VOD / "words.json").read_text())

BADGE = {"时停": "FREEZE", "倒回": "REWIND", "原速": "REAL TIME", "子弹时间": "BULLET TIME"}
TEXT = {"中路没人": "WIDE-OPEN LANE", "单手扣进！": "ONE-HAND SLAM!", "从身后追到": "CHASE-DOWN FROM BEHIND",
        "31 英尺出手": "31-FT HEAVE", "没人管": "NOBODY ON HIM"}
NAMES = {"OG": "ANUNOBY", "HA": "HART", "KT": "TOWNS", "BR": "BRUNSON", "MB": "BRIDGES", "WB": "WEMBANYAMA", "KJ": "JOHNSON",
         "FX": "FOX", "VS": "VASSELL", "JC": "CHAMPAGNIE", "CA": "CASTLE", "HP": "HARPER", "JA": "ALVARADO", "DH": "HARPER"}
# 中文时刻 -> (台词, keys 里的中文关键词, 额外偏移秒)
REMAP = {"b5+0.8": ("b5", "四个人", 0.0), "b5+2.0": ("b5", "各盯各的", 0.0), "b5+2.7": ("b5", "中路", 0.0), "b5+3.5": ("b5", "中路", 0.8),
         "d16b+0.8": ("d16b", "没人去管", -0.1), "d16b+0.9": ("d16b", "没人去管", 0.0), "d16b+1.5": ("d16b", "没人去管", 0.6)}


def ref(v):
    if not isinstance(v, str) or "+" not in v or v.split("+")[0] not in LINES:
        return v
    lid, key, off = REMAP[v]
    t = en_vo.key_time(LINES[lid]["text"], WORDS[lid], DUR[lid], LINES[lid]["keys"][key]) + off
    return f"{lid}+{max(0.0, t):.2f}"


def badge(s):
    if s.startswith("慢放"):
        return s.replace("慢放", "SLOW-MO")
    return BADGE.get(s, s)


for eid in ("e428", "e715", "e727"):
    e = json.loads((BASE / f"{eid}_vt_edl.json").read_text())
    e["_note"] = f"{eid} 竖版拆解英文版：由 {eid}_vt_edl.json 经 film/tools/bd_en.py 生成，别手改。"
    e.update(lang="en", vo={"lines": "film/audio/vo_vt_en.json", "dir": "film/audio/vo_vt_en"}, out=f"film/work/bd/{eid}_vt_en.mp4")
    e["fonts"] = {**e.get("fonts", {}),
                  "numw": ["~/Library/Fonts/Action NBA-Bold.otf", None],
                  "ko": ["/Library/Fonts/Managed/Knockout-67FullBantamwt_348560848.otf", None]}
    players = json.loads((BASE / e["work"] / "players.json").read_text())
    e["names"] = {k: NAMES[k] for k in players}
    for sg in e["segments"]:
        if "badge" in sg:
            sg["badge"] = badge(sg["badge"])
    for ly in e["layers"]:
        for k in ("on", "off"):
            if k in ly:
                ly[k] = ref(ly[k])
        if "anim" in ly:
            ly["anim"] = [ref(x) for x in ly["anim"]]
        for k in ("text", "label"):
            if isinstance(ly.get(k), str):
                ly[k] = TEXT.get(ly[k], ly[k])
    (BASE / f"{eid}_vt_en_edl.json").write_text(json.dumps(e, ensure_ascii=False, indent=1))
    print(eid, [ly.get("on") for ly in e["layers"] if isinstance(ly.get("on"), str) and ly["on"][:1] in "bd"])
