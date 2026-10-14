"""时间轴：旁白排点、字幕分段、画面场景、事件（花字 / 音效）全部写进 scenes/film_h.json。

字幕分段：按标点把一句拆成几段，在旁白音频里找停顿，把分段边界吸附到最近的停顿上。
用法：python tools/timeline_h.py
"""
import json
import re
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
VO = ROOT / "audio/vo"
LINES = {l["id"]: l for l in json.loads((ROOT / "audio/vo_cold.json").read_text())}
DUR = json.loads((VO / "durations.json").read_text())


def pauses(lid):
    """返回旁白内部的停顿中点（秒）。"""
    y, sr = librosa.load(VO / f"{lid}.wav", sr=16000)
    hop = 160
    e = librosa.feature.rms(y=y, frame_length=480, hop_length=hop)[0]
    quiet = e < max(e.max() * 0.06, 1e-4)
    out, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * hop / sr >= 0.09 and k > 0 and j < len(quiet):
                out.append((k + j) / 2 * hop / sr)
            k = j
        else:
            k += 1
    return out


def chunks(lid, max_len=18):
    text = LINES[lid]["text"]
    parts = [p for p in re.split(r"(?<=[，。？！])", text) if p.strip()]
    merged = []
    for p in parts:
        if merged and len(merged[-1]) + len(p) <= 9:
            merged[-1] += p
        else:
            merged.append(p)
    weight = [len(re.sub(r"\s", "", p)) for p in merged]
    total, dur = sum(weight), DUR[lid]
    ps = pauses(lid)
    bounds, acc = [0.0], 0
    for w in weight[:-1]:
        acc += w
        est = dur * acc / total
        near = min(ps, key=lambda x: abs(x - est)) if ps else est
        bounds.append(near if abs(near - est) < 0.8 else est)
    bounds.append(dur)
    return [{"text": re.sub(r"[，。]$", "", p.strip()), "a": round(bounds[i], 3), "b": round(bounds[i + 1], 3)}
            for i, p in enumerate(merged)]


def find(lid, key):
    """台词里某个词出现的时刻：是某个字幕分段的开头就用分段起点（来自停顿），否则按字数比例估。"""
    for c in chunks(lid):
        if c["text"].startswith(key):
            return c["a"]
    text = LINES[lid]["text"]
    i = text.index(key)
    return DUR[lid] * len(re.sub(r"\s", "", text[:i])) / len(re.sub(r"\s", "", text))


# ---------------- 排点 ----------------
T = {}
T["live0"] = 0.0
T["freeze"] = 2.47            # tip_live 结束 = 出手后定格
vo = []


def put(lid, t):
    vo.append({"id": lid, "t": round(t, 3), "dur": DUR[lid], "text": LINES[lid]["text"], "chunks": chunks(lid)})
    return t + DUR[lid]


end = put("c01", T["freeze"] + 0.35)
T["resume"] = end + 0.35
T["tip_rest_end"] = T["resume"] + 3.33
T["tipin"] = T["resume"] + (6.25 - 4.07)        # 原片 6.25 秒补进
T["crowd"] = T["tip_rest_end"]
T["crowd_end"] = T["crowd"] + 2.53
T["board"] = T["crowd_end"] + 0.25
c02 = T["board"] + 0.6
end = put("c02", c02)
T["flip"] = c02 + find("c02", "输了")
c03 = end + 0.45
end = put("c03", c03)
T["record"] = c03 + 0.2
T["record24"] = c03 + find("c03", "之前")
T["inside"] = end + 0.35
c04 = T["inside"] + 0.15
end = put("c04", c04)
T["luan"] = c04 + find("c04", "乱投")
T["beng"] = c04 + find("c04", "心态")
T["stat"] = end + 0.3
c05 = T["stat"] + 0.2
end = put("c05", c05)
T["duibushang"] = c05 + find("c05", "发现")
T["row_x"] = c05 + find("c05", "马刺下半场")
T["row_real"] = c05 + find("c05", "进球却")
T["title_bg"] = end + 0.3
c06 = T["title_bg"] + 0.2
end = put("c06", c06)
T["title"] = end + 0.15
duration = T["title"] + 3.2

scenes = {
    "live": [0, T["freeze"]],
    "freeze": [T["freeze"], T["resume"]],
    "rest": [T["resume"], T["tip_rest_end"]],
    "crowd": [T["crowd"], T["crowd_end"]],
    "board": [T["crowd_end"], T["inside"]],
    "inside": [T["inside"], T["stat"]],
    "stat": [T["stat"], T["title_bg"]],
    "title": [T["title_bg"], duration],
}

# 音效：名字对应 mix_film.py 里的合成函数
sfx = [
    ["freeze", T["freeze"]], ["unfreeze", T["resume"] - 0.25],
    ["boom", T["tipin"]],
    ["whoosh", T["board"] - 0.1], ["flip", T["flip"]], ["swish", T["record"] - 0.05], ["hit", T["record"] + 0.12],
    ["tick", T["record24"]], ["swish", T["inside"] - 0.15], ["swish", T["luan"] - 0.05], ["swish", T["beng"] - 0.05],
    ["whoosh", T["stat"] - 0.1], ["stamp", T["duibushang"] + 0.1], ["tick", T["row_x"]], ["hit", T["row_real"]],
    ["riser", T["title"] - 2.0], ["impact", T["title"]],
]

# 原声：[源文件, 源起点, 成片起点, 时长, 增益dB]
orig = [
    ["../raw/2606111142181002.mp4", 1.6, 0, 2.47, -4],
    ["../raw/2606111142181002.mp4", 4.07, T["resume"], 3.33, -2],
    ["../online/sOQKRjP3ZJk.mp4", 15.25, T["crowd"], 2.53, 0],
    ["../online/qIyBGPb7Xdg.mp4", 340.4, T["inside"], T["stat"] - T["inside"], -18],
]

# 配乐：定格起暗色铺底一路鼓起来，片名重击那一下掐断；计分牌翻盘和"心态崩了"两处推一把
music = [{"src": "assets/music/Lightless_Dawn.mp3", "s0": 0.0, "t": T["freeze"], "dur": round(T["title"] - T["freeze"] + 0.05, 3),
          "db": -13, "fin": 2.5, "fout": 0.05,
          "push": [[T["flip"] - 0.3, T["record24"] + 1.5, 3], [T["stat"], T["title"], 4]]}]

out = {"duration": round(duration, 3), "fps": 30, "T": {k: round(v, 3) for k, v in T.items()},
       "scenes": {k: [round(a, 3), round(b, 3)] for k, (a, b) in scenes.items()},
       "vo": vo, "sfx": [[n, round(t, 3)] for n, t in sfx], "orig": orig, "music": music}
(ROOT / "scenes/film_h.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"duration {duration:.2f}s")
for v in vo:
    print(v["id"], v["t"], [(c["text"], c["a"], c["b"]) for c in v["chunks"]])
