"""整片时间线：冷开场（film_h.json 原样）+ 第 1–5 段，写 scenes/film_f.json 和抽帧清单 clips_f.json。

排点规则
- 旁白一句接一句；关键词时刻按字幕分段吸附到停顿（同 timeline_h.py）。
- 比赛镜头按"事件时刻"对齐：进球 / 出手那一帧落在旁白关键词上，或落在镜头结尾前 tail 秒。
  事件时刻来自计分牌识别（research/sb_db、sb_*.json）对上逐回合记录的比赛时钟，素材表见 research/footage_map.md。
- 战术拆解整段嵌入，旁白时刻用拆解清单 work/bd/eXXX.json，底轨用 work/bd/eXXX.wav。
- 原声：audio/quotes.json 按句裁到文稿引用的那几句（QCUT）；巴克利来自 Inside the NBA，词级时间见素材表。
- 配乐：assets/music/bgm_plan.json，第 2 段提速点、第 3 段终止重音、第 5 段强乐句按画面倒推入点。
英文版（--en）：台词 audio/vo_full_en.json（keys 把下面 K() 用的中文关键词映射成英文原文），旁白 audio/vo_full_en，
冷开场 film_h_en.json，拆解用 work/bd/eXXX_en.*，画面上的文字走 tr(中文, 英文)；输出 scenes/film_f_en.json、clips_f_en.json（片段名加 en_ 前缀）。
用法：python tools/timeline_full.py [--en]
"""
import json
import re
import sys
from pathlib import Path

import librosa

import en_vo

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT.parent
EN = "--en" in sys.argv
tr = lambda zh, en: en if EN else zh  # noqa: E731
VOD = ROOT / ("audio/vo_full_en" if EN else "audio/vo_full")
LINES = {l["id"]: l for l in json.loads((ROOT / ("audio/vo_full_en.json" if EN else "audio/vo_full.json")).read_text())}
DUR = json.loads((VOD / "durations.json").read_text())
WORDS = json.loads((VOD / "words.json").read_text()) if EN else {}
COLD = json.loads((ROOT / ("scenes/film_h_en.json" if EN else "scenes/film_h.json")).read_text())
QUOTES = {q["id"]: q for q in json.loads((ROOT / "audio/quotes.json").read_text())}
SBEV = json.loads((BASE / "research/sb_db/_events.json").read_text())
GAP = 0.3


# ---------------- 字幕分段（同 timeline_h.py，旁白目录换成 vo_full） ----------------
def pauses(lid):
    y, sr = librosa.load(VOD / f"{lid}.wav", sr=16000)
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


_chunks = {}


def chunks(lid):
    if lid in _chunks:
        return _chunks[lid]
    text = LINES[lid]["text"]
    if EN:
        _chunks[lid] = en_vo.chunks(text, WORDS[lid], DUR[lid])
        return _chunks[lid]
    parts = [p for p in re.split(r"(?<=[，。？！；])", text) if p.strip()]
    size = lambda s: len(re.sub(r"[\s，。？！；、]", "", s))
    merged = []
    for p in parts:
        if merged and (len(merged[-1]) + len(p) <= 9 or (size(p) <= 3 and len(merged[-1]) + len(p) <= 24)):
            merged[-1] += p
        else:
            merged.append(p)
    # 三个字以内的开头碎片（"你看，""好，"）并进下一行
    out = []
    for p in merged:
        if out and size(out[-1]) <= 3 and len(out[-1]) + len(p) <= 24:
            out[-1] += p
        else:
            out.append(p)
    # 一行超过 24 字，从中间附近的顿号或"的"后面断开（不在数字和单位之间断）
    merged = []
    for p in out:
        cuts = [i for i, ch in enumerate(p[:-1]) if ch in "、的" and not p[i + 1].isdigit()]
        if len(p) > 24 and cuts:
            cut = min(cuts, key=lambda i: abs(i - len(p) / 2))
            merged += [p[:cut + 1], p[cut + 1:]]
        else:
            merged.append(p)
    merged = [p for p in merged if p.strip()]
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
    _chunks[lid] = [{"text": re.sub(r"[，。；、]$", "", p.strip()), "a": round(bounds[i], 3), "b": round(bounds[i + 1], 3)}
                    for i, p in enumerate(merged)]
    return _chunks[lid]


def kw(lid, key):
    """台词里某个词出现的时刻（相对句首）：词在某段字幕开头就取该段起点，否则按字数插值。"""
    if EN:
        return en_vo.key_time(LINES[lid]["text"], WORDS[lid], DUR[lid], LINES[lid]["keys"][key])
    for c in chunks(lid):
        if c["text"].startswith(key):
            return c["a"]
    text = LINES[lid]["text"]
    i = text.index(key)
    return DUR[lid] * len(re.sub(r"\s", "", text[:i])) / len(re.sub(r"\s", "", text))


# ---------------- 时间线容器 ----------------
vo = [dict(v) for v in COLD["vo"]]
shots, ovs, quotes, clips, orig, beds, qaudio, music = [], [], [], {}, [], [], [], []
sfx = [list(x) for x in COLD["sfx"]]
AT = {}


def say(lid, t):
    vo.append({"id": lid, "t": round(t, 3), "dur": DUR[lid], "text": LINES[lid]["text"], "chunks": chunks(lid)})
    AT[lid] = t
    return t + DUR[lid]


def K(lid, key):
    return AT[lid] + kw(lid, key)


def end(lid):
    return AT[lid] + DUR[lid]


LIVE = {"contrast": 1.08, "sat": 1.0, "bloom": 0.1}


def add_clip(name, src, t0, dur, rate=1.0, **spec):
    t0 = max(0.0, t0)
    s = {"name": tr(name, "en_" + name), "src": src, "t0": round(t0, 3), "t1": round(t0 + dur * rate, 3), "size": [1920, 1080], "dur": round(dur, 3),
         "grade": LIVE, "sharpen": 0.3, **spec}
    if rate != 1.0:
        s["map"] = [[0, 0], [round(dur, 3), round(dur * rate, 3)]]
        s["rife"] = 4 if rate <= 0.6 else 0
    clips[name] = s
    return s


def shot(name, src, a, b, *, ev=None, at=None, tail=0.8, t0=None, rate=1.0, gain=0.0, mute=False, clipkw=None, **opts):
    """比赛镜头。ev = 事件在素材里的秒数，at = 事件落在成片的时刻（默认镜头结尾前 tail 秒）；或直接给 t0。rate < 1 为慢放。"""
    if t0 is None:
        at = b - tail if at is None else at
        t0 = ev - (at - a) * rate
    s = add_clip(name, src, t0, b - a, rate, **(clipkw or {}))
    shots.append({"a": round(a, 3), "b": round(b, 3), "sc": "clip", "clip": name, **opts})
    if not mute and rate == 1.0:
        orig.append({"src": src, "s0": s["t0"], "t": round(a, 3), "dur": round(b - a, 3), "db": gain, "clip": name})
    return s


def gfx(sc, a, b, whoosh=True, **opts):
    shots.append({"a": round(a, 3), "b": round(b, 3), "sc": sc, **opts})
    if whoosh:
        sfx.append(["whoosh", round(a - 0.1, 3)])


def ov(type_, a, b, **opts):
    ovs.append({"type": type_, "a": round(a, 3), "b": round(b, 3), **opts})
    if type_ == "score":
        for k in opts["keys"][1:]:
            if k[1:3] != opts["keys"][opts["keys"].index(k) - 1][1:3]:
                sfx.append(["flip", round(k[0], 3)])
    elif type_ == "run":
        for ts, _ in opts["steps"][1:]:
            sfx.append(["tick", round(ts, 3)])
    elif type_ == "huazi":
        sfx.append(["stamp" if opts.get("anim") == "slam" else "swish", round(a, 3)])
    elif type_ == "chapter":
        sfx.append(["hit", round(a, 3)])


DB = lambda cid: f"../raw/{cid}.mp4"
EV = lambda cid: SBEV[cid]["tclock"]
DCF8 = "../online/dcf8UW7cMOI.mp4"
JGNC = "../online/JGnCsKF1JLQ.mp4"
Q3R = "../raw/2606111112248401.mp4"
Q4R = "../raw/2606111151336101.mp4"
BLK = "../raw/2606111142193902.mp4"


def montage(items, bounds, tail=0.7, **opts):
    """一串进球：items = [(名字, 片段 id), ...]，bounds 为镜头分界（len = len(items)+1），进球落在每个镜头结尾前 tail 秒。"""
    for (name, cid), a, b in zip(items, bounds, bounds[1:]):
        shot(name, DB(cid), a, b, ev=EV(cid), tail=tail, **opts)


# 原声按句裁剪 [首句, 末句]（含），出点在末句结束后 0.25 秒
QCUT = {"q2_1": (0, 1), "q3_1": (0, 0), "q3_2": (0, 0), "q4_1": (0, 1), "q4_2": (2, 4), "q4_3": (1, 2), "q4_4": (0, 1), "q5_1": (0, 5)}
ROLE = {"文班": tr(("文班亚马", "马刺 · 中锋"), ("Victor Wembanyama", "Spurs · Center")),
        "迈克·布朗": tr(("迈克·布朗", "尼克斯 · 主教练"), ("Mike Brown", "Knicks · Head Coach")),
        "米奇·约翰逊": tr(("米奇·约翰逊", "马刺 · 主教练"), ("Mitch Johnson", "Spurs · Head Coach"))}
# NBA 官方发布会里布朗那路麦克风丢包（每 0.1–0.3 s 断一下），声音改用 SNY 录的同一场发布会（93iEr0LWF8U）；
# 值 = quotes/<qid>.mp4 第 0 秒在 SNY 音频里的位置（互相关对齐，前后半段偏差 < 0.03 s）
ALT_AUDIO = {"q3_1": 501.625, "q4_2": 738.970, "q4_4": 54.910}
SNY = "assets/footage/quotes/sny_93iEr0LWF8U.webm"


def put_quote(name, src, s0, s1, cs, t, who, role, **opts):
    add_clip(name, src, s0, s1 - s0, **{"grade": {"contrast": 1.04, "sat": 1.0, "bloom": 0.05}, "sharpen": 0.4, **opts.pop("clipkw", {})})
    shots.append({"a": round(t, 3), "b": round(t + s1 - s0, 3), "sc": "quote", "clip": name, "who": who, "role": role, "kb": [1.0, 1.02], **opts})
    quotes.append({"id": name, "t": round(t - s0, 3), "chunks": cs})
    qaudio.append({"src": src, "s0": round(s0, 3), "t": round(t, 3), "dur": round(s1 - s0, 3)})
    sfx.append(["swish", round(t - 0.12, 3)])
    return t + s1 - s0


def quote(qid, t):
    q = QUOTES[qid]
    i, j = QCUT[qid]
    cs = q["chunks"][i:j + 1]
    s0, s1 = max(0.0, cs[0]["a"] - 0.2), min(q["dur"], cs[-1]["b"] + 0.25)
    who, role = ROLE[q["who"]]
    # 发布会画面底部 79% 以下是官方比分条，会压住双语字幕，裁掉后放大
    t_end = put_quote(f"q_{qid}", f"assets/footage/quotes/{qid}.mp4", s0, s1,
                      [{"zh": c["zh"], "en": c["en"], "a": c["a"], "b": c["b"]} for c in cs], t, who, role,
                      clipkw={"crop": [231, 0, 1458, 820]})
    if qid in ALT_AUDIO:
        qaudio[-1].update(src=SNY, s0=round(ALT_AUDIO[qid] + s0, 3))
    return t_end


FRZ = []  # 战术拆解里的定格段（成片时间），配乐在这里压低让分析听清


def breakdown(eid, t):
    bid = tr(eid, f"{eid}_en")
    m = json.loads((ROOT / f"work/bd/{bid}.json").read_text())
    BD[eid] = {sg["id"]: (t + sg["start"], t + sg["end"]) for sg in m["segments"]}
    FRZ.extend((t + sg["start"], t + sg["end"]) for sg in m["segments"] if sg["kind"] == "freeze")
    name = f"bd_{eid}"
    add_clip(name, f"work/bd/{bid}.mp4", 0, m["duration"], grade=False, sharpen=0)
    shots.append({"a": round(t, 3), "b": round(t + m["duration"], 3), "sc": "clip", "clip": name, "kb": [1, 1], "vig": 0})
    for v in m["vo"]:
        say(v["id"], t + v["t"])
    beds.append({"src": f"work/bd/{bid}.wav", "t": round(t, 3), "dur": round(m["duration"], 3)})
    return t + m["duration"]


def chapter(t, num, title, kicker, hold=2.8):
    ov("chapter", t, t + hold, num=num, title=title, kicker=kicker)


BD = {}


def bgm(file, s0, t, db, fin=1.5, fout=2.0):
    """s0 < 0 时把入点往后挪，让曲子从第 0 秒在 t - s0 进来。"""
    if s0 < 0:
        t, s0 = t - s0, 0.0
    music.append({"src": f"assets/music/{file}", "s0": round(s0, 3), "t": round(t, 3), "dur": 0, "db": db, "fin": fin, "fout": fout,
                  "push": [], "dips": []})
    return music[-1]


cold_end = COLD["duration"]

# =====================================================================
# 第 1 段：29 分是怎么来的
# =====================================================================
seg1 = cold_end + 0.2
chapter(seg1 + 0.3, "01", tr("29 分是怎么来的", "HOW THEY GOT TO 29"), "CHAPTER 1 · FIRST HALF")
e = say("s1_01", seg1 + 0.4)
e = say("s1_02", e + GAP)
e = say("s1_03", e + GAP)
montage([("s1_v13", "2606110853187102")], [seg1, AT["s1_02"]])
montage([("s1_c70", "2606110908507902"), ("s1_w88", "2606110908252902"), ("s1_h332", "2606110959367102")],
        [AT["s1_02"], K("s1_02", "客队"), K("s1_02", "第二节"), AT["s1_03"]])
montage([("s1_v305", "2606110954312502"), ("s1_h325", "2606110959171102"), ("s1_h373", "2606111004560502"), ("s1_f203", "2606110935173402")],
        [AT["s1_03"], K("s1_03", "替补"), K("s1_03", "全队"), K("s1_03", "1997"), e + 0.35])
ov("mcorner", seg1 + 0.5, e + 0.3, segs=[[seg1 + 0.7, K("s1_02", "客队"), 0, 720], [K("s1_02", "客队"), K("s1_02", "71"), 720, 1254],
                                         [K("s1_02", "71"), e - 0.3, 1254, 1440]])

a = e + 0.35
e = say("s1_04", a + 0.45)
e = say("s1_05", e + 0.25)
gfx("fgcard", a, e + 0.5, fg=a + 0.5, fg3=a + 1.5, note=AT["s1_05"] + 0.4)

a = e + 0.5
e = say("s1_06", a + 0.2)
k1, k2 = K("s1_06", "比如"), K("s1_06", "被人扑")
shot("s1_h224", DB("2606110939208402"), a, k1, ev=EV("2606110939208402"), tail=0.9)
shot("s1_v74", DB("2606110908494702"), k1, k2, ev=EV("2606110908494702"), tail=0.4)
shot("s1_f111", DB("2606110913193002"), k2, e + 0.35, ev=EV("2606110913193002"), tail=0.6)
ov("shotcard", a + 0.5, k1 - 0.1, who=tr("哈珀", "Harper"), what=tr("三分", "3PT"), hand=3.1, xfg=37)
ov("shotcard", k1 + 0.2, k2 - 0.1, who=tr("瓦塞尔", "Vassell"), what=tr("三分 · 空位", "3PT · OPEN"), hand=10.2, xfg=42)
ov("shotcard", k2 + 0.2, e + 0.3, who=tr("福克斯", "Fox"), what=tr("三分 · 被扑", "3PT · CONTESTED"), hand=2.2, xfg=33, hot=True)

a = e + 0.35
e = say("s1_07", a + 0.3)
gfx("xbars", a, e + 0.6, n=1, e1=K("s1_07", "正常") + 0.2, r1=K("s1_07", "他们实际"), d1=K("s1_07", "多出来"))

a = e + 0.6
e = say("s1_08", a + 0.2)
shot("s1_h373s", DB("2606111004560502"), a, e + 0.6, ev=EV("2606111004560502"), tail=1.6, rate=0.5, mute=True,
     clipkw={"grade": dict(LIVE, mono=0.5)}, kb=[1.02, 1.1], fout=0.5)
# Hitman 前 28 秒最冲，压在上半场那串数据上；28–90 秒的收薄段从"打成这样"开始，接后面的分析
m1 = bgm("Hitman.mp3", 28.0 - (AT["s1_04"] - seg1), seg1, -15, fin=0.8)
m1["dur"] = round(e + 0.6 - m1["t"], 3)

# =====================================================================
# 第 2 段：第三节 13 比 0
# =====================================================================
seg2 = e + 0.6
e = say("s2_01", seg2 + 0.5)
e = say("s2_02", e + 0.2)
e3 = say("s2_03", e + GAP)
add_clip("bg_jgnc", JGNC, 8.0, 1 / 30)
gfx("board", seg2, K("s2_03", "文班"), delay=2.7, bg="bg_jgnc", head=tr("第三节 9:27", "Q3 9:27"), sas=81, nyk=52, lead=tr("马刺领先 29", "SPURS LEAD BY 29"), leadT=K("s2_03", "还领先"),
    leadK="SPURS +29")
chapter(seg2 + 0.2, "02", tr("第三节：13 比 0", "Q3: THE 13-0 RUN"), "CHAPTER 2 · THIRD QUARTER", hold=2.6)
shot("s2_elbow", JGNC, K("s2_03", "文班"), K("s2_03", "裁判"), ev=13.2, at=K("s2_03", "唐斯") + 0.4, gain=-2)
shot("s2_ref", JGNC, K("s2_03", "裁判"), e3 + 0.3, t0=60.5, gain=-8)
a = e3 + 0.3
e = say("s2_04", a + 0.1)
shot("s2_down", JGNC, a, K("s2_04", "文班"), t0=23.5, gain=-8)
shot("s2_rep", JGNC, K("s2_04", "文班"), e + 0.3, t0=40.0, gain=-8)
ov("fpts", a + 0.3, e + 0.3, keys=[[K("s2_04", "3 个"), 3]], tnote=K("s2_04", "再来"))
a = e + 0.3
e = say("s2_05", a + 0.1)
shot("s2_spurs", JGNC, a, e + 0.25, t0=72.0, gain=-10)
e = quote("q2_1", e + 0.25)
a = e
e = say("s2_06", a + 0.2)
shot("s2_kat", JGNC, a, e + 0.4, t0=50.5, gain=-8)
ov("run", a + 0.3, e + 0.4, label=tr("尼克斯一波", "KNICKS RUN"), steps=[[a, 0], [K("s2_06", "两个罚球") + 0.3, 2]])

e = breakdown("e428", e + 0.4)
ov("run", e - 6.0, e, label=tr("尼克斯一波", "KNICKS RUN"), steps=[[e - 6.0, 2], [e - 4.5, 4]])

a = e
e = say("s2_10", a + 0.8)
b1, b2 = K("s2_10", "阿努诺比") + 0.5, K("s2_10", "哈特") + 0.6
montage([("s2_b432", "2606111033176002"), ("s2_o448", "2606111038291302"), ("s2_h470", "2606111043178802")], [a, b1, b2, e + 1.1], tail=0.6)
a = e + 1.1
e = say("s2_11", a + 0.1)
kz = K("s2_11", "整整")
shot("s2_fox940", Q3R, a, kz, ev=39.6, tail=0.9, gain=-6)
shot("s2_dry", Q3R, kz, e + 0.3, t0=74.0, gain=-8)
ov("run", AT["s2_10"] - 0.6, e + 0.3, label=tr("尼克斯一波", "KNICKS RUN"),
   steps=[[AT["s2_10"] - 0.6, 4], [b1 - 0.6, 7], [b2 - 0.6, 10], [AT["s2_11"] - 0.6, 13]])

a = e + 0.3
e = say("s2_12", a + 0.1)
shot("s2_inside", "assets/footage/inside_barkley.mp4", a, e + 0.3, t0=31.0, gain=-14)
BARK = [{"zh": "我就批评这一点，老兄，你们根本投不进啊", "en": "That's my criticism. Like, damn, dude, you ain't making them.", "a": 0.2, "b": 3.4},
        {"zh": "领先 20 分，根本没理由连着投八九个三分", "en": "There's never a reason to shoot eight or nine in a row when you got a 20-point lead.", "a": 4.3, "b": 7.9}]
e = put_quote("q_barkley", "assets/footage/inside_barkley_ext.mp4", 51.6, 59.8, BARK, e + 0.3, tr("巴克利", "Charles Barkley"), tr("TNT 评论员 · 名人堂球员", "TNT Analyst · Hall of Famer"),
              kicker=tr("INSIDE THE NBA · 赛后节目", "INSIDE THE NBA · POSTGAME"), clipkw={"crop": [1020, 40, 900, 506], "sharpen": 0.5})
a = e
e = say("s2_13", a + 0.15)
shot("s2_inside2", "assets/footage/inside_barkley.mp4", a, e + 0.3, t0=44.0, gain=-14)

a = e + 0.3
e = say("s2_14", a + 0.3)
e15 = say("s2_15", e + GAP)
gfx("shotmix", a, K("s2_15", "尼克斯"), q="Q3", bar=a + 0.3, three=K("s2_14", "12"), result=K("s2_14", "就进了"))
shot("s2_run", Q3R, K("s2_15", "尼克斯"), K("s2_15", "一节打完"), ev=185.6, tail=0.4, gain=-4)
q3end = e15 + 0.5
shot("s2_q3end", Q3R, K("s2_15", "一节打完"), q3end, t0=225.8 - (q3end - K("s2_15", "一节打完")), gain=-4)
ov("score", K("s2_15", "一节打完") - 0.2, q3end, keys=[[0, 90, 75, tr("第三节结束", "END Q3")]])
e = e15
seg3 = q3end
# Impact Prelude 一路往上堆，第 100 秒进最满的段落，对上三分雨
m2 = bgm("Impact_Prelude.mp3", 100.0 - (AT["s2_10"] - seg2), seg2, -16)
m2["dur"] = round(seg3 - m2["t"], 3)
m2["push"].append([AT["s2_10"] - 0.5, end("s2_11"), 2])

# =====================================================================
# 第 3 段：第四节往里打，还是不进
# =====================================================================
chapter(seg3 + 0.2, "03", tr("第四节：往里打，还是不进", "Q4: ATTACKING, STILL MISSING"), "CHAPTER 3 · FOURTH QUARTER")
e = say("s3_01", seg3 + 0.4)
shot("s3_drive", Q4R, seg3, e + 0.3, t0=35.6, gain=-4)

a = e + 0.3
e = say("s3_02", a + 0.3)
gfx("shotmix", a, e + 0.5, q="Q4", bar=a + 0.6, hls=[["three", K("s3_02", "三分只有")], ["rim", K("s3_02", "篮下")]], result=K("s3_02", "19 投"))
a = e + 0.5
e = say("s3_03", a + 0.1)
e4 = say("s3_04", e + GAP)
kd = K("s3_04", "防守人")
shot("s3_contest", Q4R, a, kd, ev=3.6, tail=0.5, gain=-4)
e5 = say("s3_05", e4 + GAP)
gfx("defdist", kd, e5 + 0.5, r3=kd + 0.4, r4=AT["s3_05"], m80=K("s3_05", "也就是"), open=K("s3_05", "19 次"))
a = e5 + 0.5
e = say("s3_06", a + 0.1)
shot("s3_oop", Q4R, a, e + 0.25, ev=56.2, at=a + 3.6, gain=-4)
e = quote("q3_1", e + 0.25)
a = e
e = say("s3_07", a + 0.1)
shot("s3_mitch", DCF8, a, e + 0.25, t0=202.2, gain=-10)
e = quote("q3_2", e + 0.25)
a = e
e = say("s3_08", a + 0.1)
kx = K("s3_08", "到了下半场")
shot("s3_h322", DB("2606110959198002"), a, kx, ev=EV("2606110959198002"), tail=0.6, gain=-4)
shot("s3_back", DCF8, kx, e + 0.3, t0=104.5, gain=-4)

a = e + 0.3
e = say("s3_09", a + 0.2)
e10 = say("s3_10", e + GAP)
bb = [a, K("s3_09", "马刺还领先") + 0.3, K("s3_09", "5 分钟"), AT["s3_10"] + 0.2, K("s3_10", "马刺那"), e10 + 0.4]
montage([("s3_a598", "2606111112208502"), ("s3_b606", "2606111112181502"), ("s3_t622", "2606111117300602"), ("s3_o632", "2606111117394102"),
         ("s3_o658", "2606111127259502")], bb, tail=0.55)
ov("score", a + 0.2, e10 + 0.4, keys=[[0, 95, 75, tr("第四节 9:33", "Q4 9:33")], [bb[1] - 0.55, 95, 78, "9:16"], [bb[2] - 0.55, 95, 80, "8:44"],
                                      [bb[3] - 0.55, 95, 83, "7:28"], [bb[4] - 0.55, 97, 86, "7:03"], [bb[5] - 0.55, 99, 95, "4:34"]])

a = e10 + 0.4
e = say("s3_11", a + 0.3)
e = say("s3_12", e + GAP)
e = say("s3_13", e + GAP)
gfx("xbars", a, e + 0.4, n=2, e1=a + 0.2, r1=a + 0.4, d1=a + 0.9, e2=K("s3_12", "按难度"), r2=K("s3_12", "结果只拿了"), d2=K("s3_12", "差了"))
a = e + 0.4
e = say("s3_14", a + 0.2)
e15 = say("s3_15", e + GAP)
seg4 = e15 + 0.9
gfx("mfull", a, seg4, segs=[[a + 0.3, AT["s3_15"] + 0.6, 0, 2669]],
    mark={"t": K("s3_15", "马刺手里"), "g": 2669, "v": 7, "text": tr("还剩 3:31 · 马刺 +7", "3:31 LEFT · SPURS +7"), "sub": "104 : 97"})
m3 = bgm("The_Escalation.mp3", 321.9 - (seg4 - seg3), seg3, -15, fout=0.4)
m3["dur"] = round(seg4 - m3["t"] + 0.3, 3)
m3["push"] += [[AT["s3_09"], e10 + 0.4, 2], [AT["s3_15"], seg4, 3]]

# =====================================================================
# 第 4 段：最后 3 分 31 秒
# =====================================================================
chapter(seg4 + 0.2, "04", tr("最后 3 分 31 秒", "THE FINAL 3:31"), "CHAPTER 4 · CLUTCH")
e = say("s4_01", seg4 + 0.4)
e = say("s4_02", e + GAP)
e = say("s4_03", e + GAP)
kw_ = K("s4_02", "文班") + 0.9
shot("s4_wem", DCF8, seg4, e + 0.3, ev=262.0, at=kw_, gain=-2)
ov("score", AT["s4_02"] - 0.3, e + 0.3, keys=[[0, 102, 97, tr("第四节 3:31", "Q4 3:31")], [kw_, 104, 97, "3:31"]])
a = e + 0.3
e = say("s4_04", a + 0.1)
shot("s4_alv", DCF8, a, K("s4_04", "福克斯"), ev=286.6, at=K("s4_04", "104"), gain=-2)
shot("s4_foxmiss", DCF8, K("s4_04", "福克斯"), e + 0.4, ev=308.6, at=K("s4_04", "没进"), gain=-2)
ov("score", a + 0.2, e + 0.4, keys=[[0, 104, 97, "3:07"], [K("s4_04", "104"), 104, 100, "3:07"]])

e = breakdown("e676", e + 0.4)

a = e
e = say("s4_09", a + 0.3)
shot("s4_steal", DCF8, a, e + 0.4, t0=371.0, gain=-2)
a = e + 0.4
e = say("s4_10", a + 0.4)
shot("s4_ft1", DCF8, a, e + 0.9, t0=386.0, gain=-2)
ov("huazi", K("s4_10", "两罚"), e + 0.8, text=tr("两罚全丢", "0 FOR 2 AT THE LINE"), x=1820, y=340, size=80, bg="red", align="right", kicker=tr("1:47 · 马刺领先 1 分", "1:47 · Spurs up 1"))
a = e + 0.9
e = say("s4_11", a + 0.1)
shot("s4_ft2", DCF8, a, e + 0.25, t0=397.6, gain=-6)
e = quote("q4_1", e + 0.25)
a = e
e = say("s4_12", a + 0.3)
kf = K("s4_12", "一个抛投") + 0.7
shot("s4_float", DCF8, a, e + 0.4, ev=426.6, at=kf, gain=-2)
ov("score", a + 0.3, e + 0.4, keys=[[0, 104, 103, "1:22"], [kf, 104, 105, "1:22"]])
ov("huazi", K("s4_12", "这是他们"), e + 0.3, text=tr("尼克斯全场第一次领先", "KNICKS' FIRST LEAD OF THE NIGHT"), x=1820, y=340, size=64, bg="blue", align="right", kicker="Knicks lead 105-104")
a = e + 0.4
e = say("s4_13", a + 0.1)
shot("s4_castle", DCF8, a, K("s4_13", "好在"), ev=452.5, at=K("s4_13", "出界"), gain=-2)
shot("s4_viol", DCF8, K("s4_13", "好在"), e + 0.4, ev=482.2, at=K("s4_13", "24 秒") + 0.6, gain=-2)
a = e + 0.4
e = say("s4_14", a + 0.1)
shot("s4_foxmid", DCF8, a, K("s4_14", "两罚"), ev=499.6, at=K("s4_14", "没进"), gain=-2)
shot("s4_castleft", DCF8, K("s4_14", "两罚"), e + 0.5, ev=526.0, at=K("s4_14", "马刺 106"), gain=-2)
ov("score", a + 0.2, e + 0.5, keys=[[0, 104, 105, "0:32"], [K("s4_14", "两罚") + 0.8, 105, 105, "0:30.3"], [K("s4_14", "马刺 106"), 106, 105, "0:30.3"]])

bd3 = e + 0.5
e = breakdown("e715", bd3)
# Impact Lento 第 122 秒起大爆发：落在福克斯时停里先被压住，"拿住球冲筐"时放开
m4 = bgm("Impact_Lento.mp3", 122.0 - (BD["e715"]["A"][1] - seg4), seg4, -15)
ov("dual", K("s4_17", "比赛还剩") - 0.2, AT["s4_18"] - 0.1, tl=K("s4_17", "比赛还剩"), tr=K("s4_17", "进攻时间"), tgt=K("s4_17", "比整场"),
   tno=K("s4_17", "进攻超时"))
ov("flow", AT["s4_18"], end("s4_19") + 0.4,
   nodes=tr([["把球攥住", "什么都不用做"], ["尼克斯只能犯规", "送马刺上罚球线"], ["两罚都进", "领先 3 分"], ["对面最多三分", "也只能追平"]],
            [["HOLD THE BALL", "Do nothing else"], ["KNICKS MUST FOUL", "Spurs go to the line"], ["MAKE BOTH", "Up 3"], ["BEST CASE FOR NYK", "A three only ties it"]]),
   keys=[K("s4_19", "把球攥"), K("s4_19", "尼克斯只能"), K("s4_19", "两罚都进"), K("s4_19", "对面最多")])
for k in ("比赛还剩", "进攻时间"):
    sfx.append(["tick", round(K("s4_17", k), 3)])
for k in ("把球攥", "尼克斯只能", "两罚都进", "对面最多"):
    sfx.append(["tick", round(K("s4_19", k), 3)])

a = e
e = say("s4_23", a + 0.2)
shot("s4_blkrep", BLK, a, e + 0.3, ev=6.6, at=a + 3.0, rate=0.5, mute=True, clipkw={"grade": dict(LIVE, mono=0.3)})
e = quote("q4_2", e + 0.3)
a = e
e = say("s4_24", a + 0.4)
BUG = {"crop": [1206, 926, 260, 104], "size": [600, 240], "sharpen": 0.6}
add_clip("st_fox130", BLK, 174 / 30, 1 / 30)
add_clip("st_fox125", BLK, 190 / 30, 1 / 30)
add_clip("bug_fox130", BLK, 174 / 30, 1 / 30, **BUG)
add_clip("bug_fox125", BLK, 190 / 30, 1 / 30, **BUG)
gfx("tl13", a, e + 0.5, st1="st_fox130", st2="st_fox125", bug1="bug_fox130", bug2="bug_fox125", t2=K("s4_24", "起跳"), t3=K("s4_24", "前后不到"))
sfx.append(["stamp", round(K("s4_24", "前后不到") + 0.15, 3)])
a = e + 0.5
e = say("s4_25", a + 0.1)
shot("s4_floor", BLK, a, e + 0.25, t0=7.4, gain=-8)
e = quote("q4_3", e + 0.25)
a = e
e = say("s4_26", a + 0.2)
shot("s4_blkslow", BLK, a, e + 0.4, ev=6.67, at=e - 0.4, rate=0.35, mute=True, clipkw={"grade": dict(LIVE, mono=0.8)}, kb=[1.08, 1.16])
sfx.append(["boom", round(e - 0.4, 3)])
a = e + 0.4
e = say("s4_27", a + 0.2)
shot("s4_foul", DCF8, a, e + 0.4, ev=554.1, at=K("s4_27", "5.7") + 0.6, gain=-2)
ov("huazi", K("s4_27", "这是他们"), e + 0.3, text=tr("第四节第 2 次犯规 · 不用罚球", "2ND TEAM FOUL OF Q4 · NO FREE THROWS"), x=1820, y=340, size=56, bg="red", align="right",
   kicker="0:05.7 · Spurs 106-105")

e = breakdown("e727", e + 0.4)
a = e
e = say("s4_33", a + 0.2)
shot("s4_og", DCF8, a, e + 0.25, t0=571.8, gain=-4)
e = quote("q4_4", e + 0.25)
a = e
e = say("s4_35", a + 0.2)
shot("s4_og2", "../online/sOQKRjP3ZJk.mp4", a, e + 0.3, t0=19.6, gain=-6)
a = e + 0.3
e = say("s4_36", a + 0.2)
shot("s4_last", DCF8, a, e + 0.3, ev=593.6, at=K("s4_36", "碰掉") + 0.4, gain=-2)
a = e + 0.3
e = say("s4_37", a + 0.2)
seg5 = e + 1.6
shot("s4_msg", "../online/lL4TMc1sYmQ.mp4", a, seg5, t0=256.4, gain=-4)
ov("huazi", K("s4_37", "53.8"), seg5 - 0.2, text=tr("尼克斯全场只领先了 53.8 秒", "KNICKS LED FOR JUST 53.8 SECONDS"), y=330, size=84, bg="blue", kicker="Knicks led for 53.8 seconds")
# Five Armies 从犯规那句接进来，一路堆到 147 秒收尾，收尾落在"比赛结束"；补进那一下正好在高能段
fa_end = end("s4_36") + 0.3
m4b = bgm("Five_Armies.mp3", 147.0 - (fa_end - AT["s4_27"]), AT["s4_27"], -15, fin=3.0, fout=1.5)
m4b["dur"] = round(fa_end + 2.5 - m4b["t"], 3)
m4b["push"].append([AT["s4_32"] - 0.2, AT["s4_32"] + 4.0, 3])
m4["dur"] = round(m4b["t"] + 3.0 - m4["t"], 3)
m4["fout"] = 3.0
sfx += [["impact", round(AT["s4_32"] - 0.05, 3)], ["impact", round(AT["s4_22"] - 0.05, 3)]]

# =====================================================================
# 第 5 段：回到开头那个问题
# =====================================================================
e = say("s5_01", seg5 + 0.6)
e = say("s5_02", e + GAP)
e = say("s5_03", e + GAP)
e4 = say("s5_04", e + 0.4)
gfx("summary", seg5, e4 + 0.4, t=[K("s5_02", "上半场"), K("s5_02", "下半场"), K("s5_02", "第三节"), K("s5_03", "最后")],
    rows=tr([["1", "上半场", "手感比预期多进 21 分"], ["2", "下半场", "同样的出手，少进 20 分"], ["3", "第三节", "12 个三分进 2 个，被打了 13 比 0"],
             ["4", "最后 3 分半", "2 次失误、2 次罚球不中、1 次不该出手的上篮"]],
            [["1", "FIRST HALF", "21 points above expectation"], ["2", "SECOND HALF", "Same looks, 20 points below"],
             ["3", "THIRD QUARTER", "2 of 12 from three, a 13-0 run against"],
             ["4", "FINAL 3:30", "2 turnovers, 2 missed FTs, 1 shot they didn't need"]]))
for k in ("上半场", "下半场", "第三节"):
    sfx.append(["tick", round(K("s5_02", k), 3)])
sfx.append(["tick", round(K("s5_03", "最后"), 3)])
e = quote("q5_1", e4 + 0.4)
a = e
e = say("s5_05", a + 0.3)
tail_end = e + 0.8
x_end = min(a + 7.2, tail_end - 1.0)
shot("s5_exit", "assets/footage/wemby_exit.mp4", a, x_end, t0=0.05, rate=0.5, mute=True, kb=[1.0, 1.05],
     clipkw={"crop": [150, 0, 1600, 900], "grade": dict(LIVE, mono=0.35)})
shot("s5_arena", DCF8, x_end, tail_end, t0=598.0, gain=-10, fout=0.7)
endcard = [
    ["比赛画面", "腾讯体育 NBA 数据库 · NBA 官方 · NBA on ESPN"],
    ["赛后发布会", "NBA 官方 Postgame Media Availability"],
    ["数据", "NBA 逐回合记录 · NBA 追踪数据"],
    ["音乐", "Kevin MacLeod (incompetech.com) · CC BY 4.0"],
    ["", "Lightless Dawn · Hitman · Impact Prelude · The Escalation"],
    ["", "Impact Lento · Five Armies · Long Road Ahead"],
    ["解说配音", "AI 合成语音 · 内部效果测试版"],
]
if EN:
    endcard = [
        ["Game footage", "Tencent Sports NBA archive · NBA · NBA on ESPN"],
        ["Press conferences", "NBA Postgame Media Availability · SNY"],
        ["Data", "NBA play-by-play · NBA tracking data"],
        ["Music", "Kevin MacLeod (incompetech.com) · CC BY 4.0"],
        ["", "Lightless Dawn · Hitman · Impact Prelude · The Escalation"],
        ["", "Impact Lento · Five Armies · Long Road Ahead"],
        ["Narration", "AI-generated voice (Qwen TTS voice design)"],
    ]
shots.append({"a": round(tail_end, 3), "b": round(tail_end + 7.0, 3), "sc": "end", "lines": endcard})
duration = tail_end + 7.0
# Long Road Ahead 前 100 秒低沉，第 100 秒整段推满，对上"尼克斯拿到了……总冠军"，一直铺到片尾
m5 = bgm("Long_Road_Ahead.mp3", 100.0 - (K("s5_05", "尼克斯") - seg5), seg5, -15, fin=2.5, fout=2.5)
m5["dur"] = round(duration - m5["t"], 3)

for mu in music:
    for a, b in FRZ:
        if mu["t"] < a and b < mu["t"] + mu["dur"]:
            mu["dips"].append([round(a + 0.15, 3), round(b, 3), -5, 500])

# ---------------- 输出 ----------------
shots.sort(key=lambda s: s["a"])
for s0, s1 in zip(shots, shots[1:]):
    if 0 < s1["a"] - s0["b"] < 0.5 or s1["a"] < s0["b"]:
        s0["b"] = s1["a"]
for s in shots:
    if s.get("clip") in clips and s["sc"] in ("clip", "quote"):
        c = clips[s["clip"]]
        need = round(s["b"] - s["a"], 3)
        if abs(need - c["dur"]) > 1e-3:
            rate = (c["t1"] - c["t0"]) / c["dur"]
            c["dur"] = need
            c["t1"] = round(c["t0"] + need * rate, 3)
            if "map" in c:
                c["map"] = [[0, 0], [need, round(need * rate, 3)]]
for o in orig:
    o["dur"] = clips[o["clip"]]["dur"]

out = {
    "duration": round(duration, 3), "fps": 30, "cold_end": cold_end,
    "T": COLD["T"], "scenes": COLD["scenes"],
    "vo": vo, "shots": shots, "ov": ovs, "quotes": quotes, "sfx": sorted(sfx, key=lambda x: x[1]),
    "orig_cold": COLD["orig"], "orig": orig, "beds": beds, "qaudio": qaudio, "music": music,
    "segs": {"seg1": round(seg1, 3), "seg2": round(seg2, 3), "seg3": round(seg3, 3), "seg4": round(seg4, 3), "seg5": round(seg5, 3)},
}
(ROOT / tr("scenes/film_f.json", "scenes/film_f_en.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1))
(ROOT / tr("clips_f.json", "clips_f_en.json")).write_text(json.dumps(list(clips.values()), ensure_ascii=False, indent=1))
print(f"duration {duration:.2f}s = {int(duration // 60)}:{duration % 60:04.1f}")
for k, v in out["segs"].items():
    print(f"  {k} {v:7.2f}  ({int(v // 60)}:{v % 60:04.1f})")
print(f"shots {len(shots)}  clips {len(clips)}  overlays {len(ovs)}  quotes {len(quotes)}  sfx {len(sfx)}")
gaps = [(round(s0["b"], 2), round(s1["a"], 2)) for s0, s1 in zip(shots, shots[1:]) if s1["a"] - s0["b"] > 0.01]
print("镜头空档：", gaps or "无")
if shots[0]["a"] > cold_end + 0.01:
    print("冷开场后到第一个镜头的空档：", cold_end, shots[0]["a"])
for c in clips.values():
    if c["t0"] <= 0.0 and not c["src"].startswith(("work/", "assets/")):
        print("入点被夹到 0：", c["name"])
