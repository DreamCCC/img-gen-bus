"""全片时间轴：按配音实际时长排出每句的位置、逐字时间、字幕和段落标记。

usage: python tools/timeline.py  ->  scenes/film.json
画面（scenes/film.html）和混音（audio/mix.py）都只读这份文件；改停顿只改这里。
逐字时间来自配音合成时返回的时间戳（audio/vo/<id>.json），按 say 文本的字符排列。
"""
import json
import re
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
LINES = json.loads((ROOT / "audio/vo_lines.json").read_text())
VO = ROOT / "audio/vo"
FPS = 30

GAP, PAR = 0.3, 0.7
START = 4.0
PRE = {"H05": 0.8, "H09": 1.0, "H11": 0.4, "H12": 0.25, "H15": 0.8, "H19": 1.2, "H21": 0.8, "H24": 0.9, "H27": 0.8,
       "H29": 0.5, "H30": 0.5,
       "A04": 0.8, "A09": 0.9,
       "B04": 0.8, "B06": 0.5, "B08": 0.9, "B13": 1.0, "B15": 0.4,
       "C07": 0.9, "C12": 1.0, "C14": 0.4, "C15": 0.6, "C18": 0.8, "C21": 1.0, "C23": 0.8, "C24": 0.6, "C25": 1.6,
       "D02": 0.3, "D06": 0.9, "D09": 0.5, "D11": 0.6, "D12": 1.0, "D14": 1.0, "D15": 0.4,
       "E05": 0.9, "E07": 2.5, "E08": 0.9, "E09": 1.5,
       "F05": 1.0, "F08": 1.0, "F13": 1.5}
# 句内切开、插入静音：id -> [(say 中的短语, 静音秒数)]
SPLIT = {"C20": [("整版已销毁", 1.0)], "D08": [("得加", 0.6)]}
# 某句之后插入的非旁白段落：(名字, 时长)
AFTER = {"H18": [("B_hold", 1.0)],
         "H30": [("pre_title", 0.6), ("title", 8.0), ("ch1", 2.5)],
         "A11": [("pre_ch2", 0.8), ("ch2", 2.5)],
         "B19": [("pre_ch3", 0.8), ("ch3", 2.5)],
         "C26": [("pre_ch4", 1.0), ("ch4", 2.5)],
         "D15": [("pre_ch5", 1.2), ("ch5", 2.5)],
         "E09": [("pre_ch6", 1.0), ("ch6", 2.5)],
         "F13": [("ending", 5.0), ("credits", 6.0)]}
SUB_MAX = 17


def align(say, chars):
    """把时间戳逐字对到 say 文本上；对不上的字用前后插值。"""
    out, j = [], 0
    for ch in say:
        k = j
        while k < len(chars) and chars[k]["ch"] != ch and k < j + 3:
            k += 1
        if k < len(chars) and chars[k]["ch"] == ch:
            out.append([chars[k]["t0"], chars[k]["t1"]])
            j = k + 1
        else:
            out.append(None)
    for i, v in enumerate(out):
        if v is None:
            prev = next((out[p][1] for p in range(i - 1, -1, -1) if out[p]), 0.0)
            out[i] = [prev, prev]
    return out


def clauses(s):
    return [c for c in re.split(r"(?<=[，。？！：；])", s) if c]


def subs_for(text, say, times, shift):
    tc, sc = clauses(re.sub(r"\s+(?=[\u4e00-\u9fff，。？！：；《》“”])|(?<=[\u4e00-\u9fff，。？！：；《》“”])\s+", "", text)), clauses(say)
    if len(tc) != len(sc):
        tc = sc
    units, pos = [], 0
    for t, s in zip(tc, sc):
        a, b = pos, pos + len(s)
        pos = b
        units.append([t, a, b])
    merged = []
    for u in units:
        if merged and len(merged[-1][0]) + len(u[0]) <= SUB_MAX and not merged[-1][0].endswith(("。", "？", "！")):
            merged[-1][0] += u[0]
            merged[-1][2] = u[2]
        else:
            merged.append(u)
    out = []
    for t, a, b in merged:
        t = t.rstrip("，。：；")
        out.append({"t0": round(shift(times[a][0]), 3), "t1": round(shift(times[b - 1][1]), 3), "text": t})
    return out


def main():
    t = START
    vo, subs, marks = [], [], {"start": 0.0}
    for ln in LINES:
        lid = ln["id"]
        say = ln.get("say", ln["text"])
        chars = json.loads((VO / f"{lid}.json").read_text())
        dur = sf.info(str(VO / f"{lid}.wav")).duration
        t += PRE.get(lid, PAR if ln.get("par") else GAP)
        times = align(say, chars)
        cuts = sorted((say.index(p), gap) for p, gap in SPLIT.get(lid, []))
        segs, src, pad = [], 0.0, 0.0
        bounds = [(max(0.0, times[idx][0] - 0.03), gap) for idx, gap in cuts]
        for at, gap in bounds:
            segs.append([round(src, 3), round(at, 3), round(t + src + pad, 3)])
            src, pad = at, pad + gap
        segs.append([round(src, 3), round(dur, 3), round(t + src + pad, 3)])

        def shift(x, t=t, bounds=bounds):
            return t + x + sum(g for at, g in bounds if x >= at)

        film_chars = [[c, round(shift(a), 3), round(shift(b), 3)] for c, (a, b) in zip(say, times)]
        vo.append({"id": lid, "t": round(t, 3), "dur": round(dur + pad, 3), "text": ln["text"], "say": say,
                   "cue": ln.get("cue", ""), "segs": segs, "chars": film_chars})
        subs += subs_for(ln["text"], say, times, shift)
        t += dur + pad
        for name, d in AFTER.get(lid, []):
            marks[name] = round(t, 3)
            t += d
            marks[name + "_end"] = round(t, 3)
    film = {"fps": FPS, "duration": round(t, 3), "vo": vo, "subs": subs, "marks": marks}
    (ROOT / "scenes/film.json").write_text(json.dumps(film, ensure_ascii=False))
    print(f"duration {t:.1f}s ({t / 60:.1f} min), {len(vo)} lines, {len(subs)} subs")
    for k, v in marks.items():
        if not k.endswith("_end"):
            print(f"  {k:10s} {v:7.2f}  ({int(v // 60)}:{v % 60:04.1f})")


if __name__ == "__main__":
    main()
