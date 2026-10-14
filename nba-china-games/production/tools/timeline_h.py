"""横版成片总时间轴：音乐剪接、旁白、场景、音效全部从这里生成 scenes/film_h.json。
时间单位：成片秒。音乐里的时间点用 fa()/ha() 换算成成片时间，保证画面卡在音乐的拍点上。
用法：python tools/timeline_h.py [en]   # en：英文版，读 vo_lines_en.json / vo_en，写 scenes/film_h_en.json
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SUF = "_en" if sys.argv[1:] == ["en"] else ""
y, sr = librosa.load(ROOT / "assets/music/Five_Armies.mp3", sr=22050)
_, FA_BEATS = librosa.beat.beat_track(y=y, sr=sr, units="time")

FA_CUT_OUT = float(FA_BEATS[73])            # 38.52：从这里跳走
FA_CUT_IN = float(FA_BEATS[105])            # 8 小节之后，同一拍相位
OFF = FA_CUT_IN - FA_CUT_OUT
FA_END = 147.47 + 0.24                      # 最后一记重音之后硬停
HA_IN, HA_AT = 50.85, None                  # Heroic Age 从 50.85 进入


def fa(x):
    return x if x < FA_CUT_OUT else x - OFF


STOP = fa(FA_END)
ACT3 = 23.2
HA_AT = round(STOP + ACT3, 3)


def ha(x):
    return HA_AT + (x - HA_IN)


DUR = round(ha(89.0) + 4.6, 2)

fa_beats_film = [round(fa(b), 3) for b in FA_BEATS if (b < FA_CUT_OUT or b >= FA_CUT_IN) and b <= FA_END]
ha_beats_film = [round(ha(HA_IN + k * 0.46440), 3) for k in range(int((89.5 - HA_IN) / 0.4644) + 1)]


def snap(t, grid):
    return min(grid, key=lambda b: abs(b - t))


A = {
    "act1": 14.28,
    "cut": round(FA_CUT_OUT, 3),
    "stern": round(fa(57.98), 3),
    "act2": round(fa(75.36), 3),
    "slam": round(fa(113.22), 3),
    "lastHit": round(fa(147.47), 3),
    "stop": round(STOP, 3),
    "act4": HA_AT,
    "boom": round(ha(54.08), 3),
    "haEnd": round(ha(89.0), 3),
}

# 翻页蒙太奇：有旁白或真人画面的年份 4 拍，其余 2 拍；2019 落在最后一记重音上
FLIP = [
    (2007, "魔术", "骑士", "上海 · 澳门", "cg2007", 4),
    (2008, "雄鹿", "勇士", "广州 · 北京", None, 2),
    (2009, "掘金", "步行者", "北京", None, 2),
    (2010, "火箭", "篮网", "北京 · 广州", None, 2),
    (2012, "热火", "快船", "北京 · 上海", "cg2012", 4),
    (2013, "湖人", "勇士", "北京 · 上海", "cg2013", 4),
    (2014, "篮网", "国王", "上海 · 北京", None, 2),
    (2015, "黄蜂", "快船", "深圳 · 上海", "cg2015", 4),
    (2016, "火箭", "鹈鹕", "上海 · 北京", "cg2016", 4),
    (2017, "勇士", "森林狼", "上海 · 深圳", "cg2017", 4),
    (2018, "76人", "独行侠", "深圳 · 上海", "cg2018", 4),
    (2019, "湖人", "篮网", "上海 · 深圳", None, 0),
]
BEAT = 0.53406
flip_start = round(A["lastHit"] - sum(f[5] for f in FLIP) * BEAT, 3)
flips, t_ = [], flip_start
for y_, h, a, c, clip, nb in FLIP:
    flips.append({"year": y_, "home": h, "away": a, "city": c, "clip": clip, "t": round(t_, 3), "beats": nb})
    t_ += nb * BEAT
ftime = {f["year"]: f["t"] for f in flips}

VO = [
    ("L01", 4.0), ("L02", 5.6), ("L03", 9.7),
    ("L04", 14.6), ("L05", 16.9), ("L06", 19.4),
    ("L07", 22.6), ("L08", 28.8), ("L09", 32.2),
    ("L10", A["stern"] + 0.7), ("L11", A["stern"] + 7.5), ("L12", A["stern"] + 10.3),
    ("L13", A["act2"] + 0.8), ("L14", A["act2"] + 8.0),
    ("L15", A["act2"] + 15.2), ("L16", A["act2"] + 19.2),
    ("L18", A["slam"] + 3.3),
    ("L19", A["slam"] + 8.2), ("L20", A["slam"] + 10.3),
    ("L21a", ftime[2007] + 0.15), ("L21b", ftime[2013] + 0.15), ("L22", ftime[2015] + 0.15),
    ("L23", A["stop"] + 0.6), ("L24", A["stop"] + 9.9), ("L25", A["stop"] + 17.3),
    ("L26", A["act4"] + 0.3), ("L27", A["boom"] + 0.35),
    ("L28", A["act4"] + 15.3), ("L29", A["act4"] + 18.7),
    ("L30", A["haEnd"] - 4.6),
]
lines = {d["id"]: d for d in json.loads((ROOT / f"audio/vo_lines{SUF}.json").read_text())}
durs = json.loads((ROOT / f"audio/vo{SUF}/durations.json").read_text())
vo = [{"id": i, "t": round(t, 3), "dur": durs[i], "text": lines[i]["text"]} for i, t in VO]
for a, b in zip(vo, vo[1:]):
    assert a["t"] + a["dur"] <= b["t"] + 0.01, f"VO overlap {a['id']} {b['id']}"

S = {}
S["open"] = [0.0, A["act1"]]
S["map"] = [A["act1"], 22.0]
S["bj1979"] = [22.0, 28.5]
S["ruler"] = [28.5, 36.0]
S["paper"] = [36.0, A["stern"]]
S["room"] = [A["stern"], A["stern"] + 9.9]
S["vhs"] = [A["stern"] + 9.9, A["act2"]]
S["tvwall"] = [A["act2"], A["act2"] + 7.6]
S["yao"] = [A["act2"] + 7.6, A["act2"] + 14.8]
S["ticket"] = [A["act2"] + 14.8, A["act2"] + 23.4]
S["crowd"] = [A["act2"] + 23.4, A["act2"] + 28.0]
S["board"] = [A["act2"] + 28.0, round(A["slam"] - 2.81, 3)]
S["dunk"] = [round(A["slam"] - 2.81, 3), round(A["slam"] + 1.59, 3)]
S["score"] = [round(A["slam"] + 1.59, 3), A["slam"] + 7.9]
S["span"] = [A["slam"] + 7.9, flip_start]
S["flip"] = [flip_start, A["stop"]]
S["lightsout"] = [A["stop"], A["stop"] + 6.0]
S["counter"] = [A["stop"] + 6.0, A["stop"] + 13.0]
S["cold"] = [A["stop"] + 13.0, A["act4"]]
S["macau"] = [A["act4"], A["act4"] + 9.0]
S["macau2"] = [A["act4"] + 9.0, A["act4"] + 15.0]
S["rockets"] = [A["act4"] + 15.0, A["act4"] + 21.5]
S["roster"] = [A["act4"] + 21.5, A["haEnd"] - 4.8]
S["finale"] = [A["haEnd"] - 4.8, A["haEnd"]]
S["end"] = [A["haEnd"], DUR]
S = {k: [round(a, 3), round(b, 3)] for k, (a, b) in S.items()}

fb = lambda t: round(snap(t, fa_beats_film), 3)
hb = lambda t: round(snap(t, ha_beats_film), 3)
sl = A["slam"]
board0 = S["board"][0]

# 第三幕心跳：间隔从 1.1 秒收紧到 0.3 秒，最后一下落在第四幕的第一拍
hearts, t_, gap = [], A["act4"], 0.3
while t_ > S["cold"][0] + 0.4:
    hearts.append(round(t_, 3))
    t_ -= gap
    gap = min(1.1, gap * 1.13)
hearts = sorted(hearts)[:-1]

roster0 = S["roster"][0]
roster_cuts = [hb(roster0 + k * 2 * 0.4644) for k in range(13)]

EV = {
    "openBounces": [0.62, 1.42, 1.98, 2.38, 2.64, 2.84],
    "rewind": [9.8, A["act1"]],
    "arc": [17.6, 21.0],
    "rulerLand": fb(32.55),
    "typing": [36.5, 39.8],
    "clockTicks": [round(41.6 + k * 1.0, 3) for k in range(9)],
    "tapeIn": 56.9,
    "yaoRuler": fb(68.4),
    "yaoRoar": round(S["yao"][0] + 3.9, 3),
    "stamp": fb(77.25),
    "chant": [fb(82.3 + k * 1.068) for k in range(4)],
    "shot": round(board0 + 3.0, 3), "rimOut": round(board0 + 3.8, 3), "putback": round(board0 + 4.4, 3),
    "boardZoom": [round(board0 + 5.4, 3), S["board"][1]],
    "dunk": {"suck": round(sl - 0.25, 3), "riser": [round(sl - 2.3, 3), round(sl - 0.25, 3)]},
    "flapLand": round(sl + 2.55, 3),
    "spanCount": [107.7, 109.5],
    "lightsRows": [round(131.45 + k * 0.29, 3) for k in range(8)],
    "counter": [137.2, 141.85],
    "hearts": hearts,
    "rosterCuts": roster_cuts,
    "endBounces": [hb(A["haEnd"] - 1.4), hb(A["haEnd"] - 0.46), A["haEnd"] + 0.4, A["haEnd"] + 0.95, A["haEnd"] + 1.3],
}

out = {
    "duration": DUR,
    "ev": EV,
    "fps": 30,
    "music": {"fa_cut_out": FA_CUT_OUT, "fa_cut_in": FA_CUT_IN, "fa_end": FA_END, "ha_in": HA_IN, "ha_at": HA_AT},
    "anchors": A,
    "scenes": S,
    "vo": vo,
    "vo_dir": f"audio/vo{SUF}",
    "flips": flips,
    "faBeats": fa_beats_film,
    "haBeats": ha_beats_film,
}
(ROOT / f"scenes/film_h{SUF}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"duration": DUR, "anchors": A, "scenes": S}, ensure_ascii=False, indent=1))
