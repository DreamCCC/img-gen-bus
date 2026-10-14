"""竖屏版时间线（文稿_竖屏5min_v2.md，约 6 分钟）：写 scenes/film_vt.json 和抽帧清单 clips_vt.json。

排点规则同 timeline_full.py（旁白一句接一句；进球 / 出手那一帧落在旁白关键词上，或落在镜头结尾前 tail 秒），区别：
- 每个镜头带竖版版式 lay：crop = 比赛画面 4:5 跟拍（路径由 tools/track_vt.py 算，cx 固定的不跟）；quote = 发布会人物，抽帧时直接裁成 4:5；
  panel = 战术拆解 16:9 整幅；没有 lay 的是竖版图卡（film.html 的 SHV）。
- 字幕每行不超过 MAXC 个字。
- 战术拆解用竖版重渲的 work/bd/eXXX_vt（旁白换成 audio/vo_vt，见 ../eXXX_vt_edl.json）。
- 抽帧名字统一加 v_ 前缀，不碰横版的 scenes/clips。
用法：python tools/timeline_vt.py
"""
import json
import re
from pathlib import Path

import librosa

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT.parent
VOD = ROOT / "audio/vo_vt"
LINES = {l["id"]: l for l in json.loads((ROOT / "audio/vo_vt.json").read_text())}
DUR = json.loads((VOD / "durations.json").read_text())
QUOTES = {q["id"]: q for q in json.loads((ROOT / "audio/quotes.json").read_text())}
SBEV = json.loads((BASE / "research/sb_db/_events.json").read_text())
GAP = 0.3
MAXC = 15


# ---------------- 字幕分段 ----------------
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


def size(s):
    return len(re.sub(r"[\s，。？！；、]", "", s))


def split_long(p):
    """超过 MAXC 字从中间附近断开：优先断在虚词后 / 副词前，数字前后两个字以内不断。"""
    if size(p) <= MAXC:
        return [p]
    n = len(p)

    def ok(i):
        return 1 <= i < n - 2 and not any(c.isdigit() for c in p[max(0, i - 1):i + 3])

    good = [i for i in range(n - 1) if ok(i) and (p[i] in "的了呢啊、着" or p[i + 1] in "就都还是把被在从到给跟和也又才只没")]
    cands = good or [i for i in range(n - 1) if ok(i)] or [n // 2]
    cut = min(cands, key=lambda i: abs(size(p[:i + 1]) - size(p) / 2))
    return split_long(p[:cut + 1]) + split_long(p[cut + 1:])


_chunks = {}


def chunks(lid):
    if lid in _chunks:
        return _chunks[lid]
    text = LINES[lid]["text"]
    parts = [p for p in re.split(r"(?<=[，。？！；])", text) if p.strip()]
    merged = []
    for p in parts:
        if merged and size(merged[-1]) + size(p) <= 8:
            merged[-1] += p
        else:
            merged.append(p)
    out = []
    for p in merged:
        if out and size(out[-1]) <= 3 and size(out[-1]) + size(p) <= MAXC:
            out[-1] += p
        else:
            out.append(p)
    pieces = [x for p in out for x in split_long(p) if x.strip()]
    weight = [size(p) or 1 for p in pieces]
    total, dur = sum(weight), DUR[lid]
    ps = pauses(lid)
    bounds, acc = [0.0], 0
    for w in weight[:-1]:
        acc += w
        est = dur * acc / total
        near = min(ps, key=lambda x: abs(x - est)) if ps else est
        bounds.append(near if abs(near - est) < 0.6 else est)
    bounds.append(dur)
    _chunks[lid] = [{"text": re.sub(r"[，。；、]$", "", p.strip()), "a": round(bounds[i], 3), "b": round(bounds[i + 1], 3)}
                    for i, p in enumerate(pieces)]
    return _chunks[lid]


def kw(lid, key):
    """台词里某个词出现的时刻（相对句首）：词在某段字幕开头就取该段起点，否则按字数插值。"""
    for c in chunks(lid):
        if c["text"].startswith(key):
            return c["a"]
    text = LINES[lid]["text"]
    i = text.index(key)
    return DUR[lid] * len(re.sub(r"\s", "", text[:i])) / len(re.sub(r"\s", "", text))


# ---------------- 时间线容器 ----------------
vo, shots, ovs, quotes, orig, beds, qaudio, music, sfx, chap = ([] for _ in range(10))
clips, AT, BD = {}, {}, {}
FRZ = []


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
    s = {"name": name, "src": src, "t0": round(t0, 3), "t1": round(t0 + dur * rate, 3), "size": [1920, 1080], "dur": round(dur, 3),
         "grade": LIVE, "sharpen": 0.3, **spec}
    if rate != 1.0:
        s["map"] = [[0, 0], [round(dur, 3), round(dur * rate, 3)]]
        s["rife"] = 4 if rate <= 0.6 else 0
    clips[name] = s
    return s


def shot(name, src, a, b, *, ev=None, at=None, tail=0.8, t0=None, rate=1.0, gain=0.0, mute=False, clipkw=None, lay="crop", **opts):
    """比赛镜头。ev = 事件在素材里的秒数，at = 事件落在成片的时刻（默认镜头结尾前 tail 秒）；或直接给 t0。rate < 1 为慢放。"""
    name = "v_" + name
    if t0 is None:
        at = b - tail if at is None else at
        t0 = ev - (at - a) * rate
    s = add_clip(name, src, t0, b - a, rate, **(clipkw or {}))
    shots.append({"a": round(a, 3), "b": round(b, 3), "sc": "clip", "lay": lay, "clip": name, **opts})
    if not mute and rate == 1.0:
        orig.append({"src": src, "s0": s["t0"], "t": round(a, 3), "dur": round(b - a, 3), "db": gain, "clip": name})
    return s


def card(sc, a, b, whoosh=True, **opts):
    shots.append({"a": round(a, 3), "b": round(b, 3), "sc": sc, **opts})
    if whoosh:
        sfx.append(["whoosh", round(a - 0.1, 3)])


def ov(type_, a, b, **opts):
    ovs.append({"type": type_, "a": round(a, 3), "b": round(b, 3), **opts})
    if type_ == "score":
        for i, k in enumerate(opts["keys"][1:], 1):
            if k[1:3] != opts["keys"][i - 1][1:3]:
                sfx.append(["flip", round(k[0], 3)])
    elif type_ == "run":
        for ts, _ in opts["steps"][1:]:
            sfx.append(["tick", round(ts, 3)])
    elif type_ == "huazi":
        sfx.append(["stamp" if opts.get("anim") == "slam" else "swish", round(a, 3)])
    elif type_ == "chapter":
        sfx.append(["hit", round(a, 3)])


def chapter(t, num, title, kicker, hold=2.6):
    ov("chapter", t, t + hold, num=num, title=title, kicker=kicker)
    chap.append([round(t, 3), num, title])


def breakdown(eid, t, **opts):
    m = json.loads((ROOT / f"work/bd/{eid}_vt.json").read_text())
    BD[eid] = {sg["id"]: (t + sg["start"], t + sg["end"]) for sg in m["segments"]}
    FRZ.extend((t + sg["start"], t + sg["end"]) for sg in m["segments"] if sg["kind"] == "freeze")
    name = f"v_bd_{eid}"
    add_clip(name, f"work/bd/{eid}_vt.mp4", 0, m["duration"], grade=False, sharpen=0)
    shots.append({"a": round(t, 3), "b": round(t + m["duration"], 3), "sc": "clip", "lay": "panel", "clip": name, **opts})
    for v in m["vo"]:
        say(v["id"], t + v["t"])
    beds.append({"src": f"work/bd/{eid}_vt.wav", "t": round(t, 3), "dur": round(m["duration"], 3)})
    return t + m["duration"]


def put_quote(name, src, s0, s1, cs, t, who, role, crop, **opts):
    add_clip(name, src, s0, s1 - s0, size=[1080, 1350], crop=crop, grade={"contrast": 1.04, "sat": 1.0, "bloom": 0.05}, sharpen=0.4)
    shots.append({"a": round(t, 3), "b": round(t + s1 - s0, 3), "sc": "clip", "lay": "quote", "clip": name, "who": who, "role": role,
                  "kb": [1.0, 1.02], **opts})
    quotes.append({"id": name, "t": round(t - s0, 3), "chunks": cs})
    qaudio.append({"src": src, "s0": round(s0, 3), "t": round(t, 3), "dur": round(s1 - s0, 3)})
    sfx.append(["swish", round(t - 0.12, 3)])
    return t + s1 - s0


# 原声按句裁剪 [首句, 末句]（含）；发布会画面去掉底部比分条后按人物裁 4:5
QCUT = {"q3_1": (0, 0), "q4_2": (2, 3), "q5_1": (1, 5)}
QCROP = {"q3_1": [632, 0, 656, 820], "q4_2": [632, 0, 656, 820], "q5_1": [682, 0, 656, 820]}
ROLE = {"文班": ("文班亚马", "马刺 · 中锋"), "迈克·布朗": ("迈克·布朗", "尼克斯 · 主教练")}
# 布朗那路麦克风丢包，声音改用 SNY 录的同一场发布会（同 timeline_full.py）
ALT_AUDIO = {"q3_1": 501.625, "q4_2": 738.970}
SNY = "assets/footage/quotes/sny_93iEr0LWF8U.webm"


def quote(qid, t, **opts):
    q = QUOTES[qid]
    i, j = QCUT[qid]
    cs = q["chunks"][i:j + 1]
    s0, s1 = max(0.0, cs[0]["a"] - 0.2), min(q["dur"], cs[-1]["b"] + 0.25)
    who, role = ROLE[q["who"]]
    t_end = put_quote(f"v_q_{qid}", f"assets/footage/quotes/{qid}.mp4", s0, s1,
                      [{"zh": c["zh"], "en": c["en"], "a": c["a"], "b": c["b"]} for c in cs], t, who, role, QCROP[qid], **opts)
    if qid in ALT_AUDIO:
        qaudio[-1].update(src=SNY, s0=round(ALT_AUDIO[qid] + s0, 3))
    return t_end


def bgm(file, s0, t, db, fin=1.5, fout=2.0):
    if s0 < 0:
        t, s0 = t - s0, 0.0
    music.append({"src": f"assets/music/{file}", "s0": round(s0, 3), "t": round(t, 3), "dur": 0, "db": db, "fin": fin, "fout": fout,
                  "push": [], "dips": []})
    return music[-1]


def montage(items, bounds, tail=0.7, **opts):
    for (name, cid, *more), a, b in zip(items, bounds, bounds[1:]):
        kw_ = dict(opts, **(more[0] if more else {}))
        if "t0" not in kw_:
            kw_.update(ev=EV(cid), tail=tail)
        shot(name, DB(cid), a, b, **kw_)


SW = 1080 * 1080 / 1350
CXR = (SW / 2, 1920 - SW / 2)


def follow(rel, xs, mk, xr, *, before=None, after=None):
    """投篮跟球的 cxk。rel / mk = 出手、球到篮筐在镜头内的秒数，xs / xr = 射手、篮筐在原画面的横坐标（取出手、进球那一刻）。
    出手前射手放在远离篮筐的三分之一处，出手后缓入缓出移到篮筐，球到之前 0.2 秒到位；射手和篮筐一个框装得下就不移。
    before / after = 出手前 / 进球后另加的关键帧 [[t, cx], ...]。"""
    clamp = lambda x: round(min(max(x, CXR[0]), CXR[1]))
    sign = 1 if xr > xs else -1
    if abs(xr - xs) <= SW - 200:
        ks = [[rel, clamp((xs + xr) / 2)]]
    else:
        cs, cr = clamp(xs + sign * SW / 6), clamp(xr - sign * SW * 0.1)
        ks = [[rel, cs], [mk - 0.2, cr]]
    ks = (before or []) + ks + (after or [])
    return [[round(t, 2), clamp(x)] for t, x in ks]


DB = lambda cid: f"../raw/{cid}.mp4"
EV = lambda cid: SBEV[cid]["tclock"]
DCF8 = "../online/dcf8UW7cMOI.mp4"
JGNC = "../online/JGnCsKF1JLQ.mp4"
Q3R = "../raw/2606111112248401.mp4"
Q4R = "../raw/2606111151336101.mp4"
BLK = "../raw/2606111142193902.mp4"
TIP = "../raw/2606111142181002.mp4"
MSGV = "../online/sOQKRjP3ZJk.mp4"
INSIDE = "../online/qIyBGPb7Xdg.mp4"
Y_TOP = 285 + 300  # 窗口上部花字的中心线

# =====================================================================
# 开场：补篮 → 结果 → 历史最大逆转 → "没那么简单" → 标题
# =====================================================================
TIPIN = 4.85  # 补篮碰框进网落在成片这一刻（素材 6.45 秒）
shot("tip", TIP, 0, TIPIN + 1.2, ev=6.45, at=TIPIN, gain=-1, flash=TIPIN, shake=TIPIN, kb=[1.0, 1.06],
     cxk=[[0, 740], [1.5, 670], [3.0, 720], [4.3, 1290], [6.05, 1300]])
sfx.append(["impact", round(TIPIN - 0.05, 3)])
e = say("o1", TIPIN - 0.05)
c0 = TIPIN + 1.2
shot("crowd", MSGV, c0, c0 + 2.5, t0=15.25, gain=0, shake=c0 + 0.1, kb=[1.04, 1.1])
ov("huazi", c0 + 0.1, c0 + 2.4, text="绝杀", x=540, y=285 + 520, size=200, anim="slam", kicker="Knicks 107  Spurs 106")
b0 = c0 + 2.5
e2 = say("o2", b0 + 0.3)
e3 = say("o3", e2 + 0.4)
add_clip("v_bg_tip", TIP, 1.6, 1 / 30)
card("board", b0, e3 + 0.4, bg="v_bg_tip", head="第二节 3:06 · 马刺最大领先", head2="终场 FINAL", sas=71, nyk=42, sas2=106, nyk2=107,
     flip=K("o2", "输了"), peak=K("o2", "29"), record=AT["o3"] - 0.1, record24=K("o3", "把这么大"))
sfx += [["flip", round(K("o2", "输了"), 3)], ["stamp", round(AT["o3"] - 0.1, 3)]]
a = e3 + 0.4
e4 = say("o4", a + 0.15)
kb_ = K("o4", "但是啊")
shot("inside", INSIDE, a, kb_, t0=340.4, gain=-18, cx=980)
ov("huazi", K("o4", "乱投"), kb_, text="乱投？", x=1020, y=285 + 330, size=104, bg="white", align="right", kicker="Shot selection")
ov("huazi", K("o4", "心态"), kb_, text="心态崩了？", x=1020, y=285 + 560, size=104, bg="red", align="right", kicker="Mental collapse")
ti = e4 + 0.5
card("mfull", kb_, ti, segs=[[kb_ + 0.2, e4 - 0.2, 0, 2880]],
     huazi={"t": K("o4", "没那么简单"), "text": "没那么简单", "kicker": "It's not that simple"})
sfx.append(["stamp", round(K("o4", "没那么简单"), 3)])
add_clip("v_top_slow", MSGV, 30.3, 4.2)
card("title", ti, ti + 4.2, whoosh=False, clip="v_top_slow", hit=ti + 0.7)
sfx += [["riser", round(ti - 1.4, 3)], ["impact", round(ti + 0.65, 3)]]
seg1 = ti + 4.2
m0 = bgm("Lightless_Dawn.mp3", 0.0, 3.6, -13, fin=2.0, fout=0.6)
m0["push"].append([AT["o4"], ti + 0.7, 3])
m0["dur"] = round(seg1 + 0.4 - m0["t"], 3)

# =====================================================================
# 一 · 借来的领先
# =====================================================================
chapter(seg1 + 0.3, "01", "借来的领先", "CHAPTER 1 · FIRST HALF")
e = say("a1", seg1 + 0.5)
e = say("a2", e + 0.25)
mb = [seg1, seg1 + 2.3] + [seg1 + 2.3 + (e + 0.7 - seg1 - 2.3) * i / 4 for i in (1, 2, 3, 4)]
montage([("s1_v13", "2606110853187102", {"t0": 4.65, "cxk": [[0, 1000], [0.5, 1080], [1.8, 1100], [2.3, 1060]]}),
         ("s1_c70", "2606110908507902", {"t0": 8.21, "cxk": follow(0.1, 200, 1.3, 1230)}),
         ("s1_w88", "2606110908252902", {"t0": 6.84, "cxk": follow(0.1, 170, 1.2, 1290)}),
         ("s1_h325", "2606110959171102", {"t0": 5.26, "cxk": follow(0.1, 590, 1.35, 1249)}),
         ("s1_h373", "2606111004560502", {"t0": 7.80, "cxk": follow(0.15, 1610, 1.2, 1310)})], mb)
ov("score", AT["a2"] - 0.2, K("a2", "半场"), keys=[[0, 41, 22, "第一节结束"]])
ov("huazi", K("a2", "14"), e + 0.6, text="半场 14 记三分", x=540, y=Y_TOP, size=80, kicker="14 3PM · Most in a Finals half")
a = e + 0.7
e = say("a3", a + 0.25)
shot("s1_f111", DB("2606110913193002"), a, e + 0.5, ev=EV("2606110913193002"), tail=0.7,
     cxk=[[0, 960], [1.0, 1000], [1.8, 1200], [2.6, 1260]])
ov("shotcard", a + 0.3, e + 0.45, who="福克斯", what="三分 · 被扑", hand=2.2, xfg=33, hot=True)
a = e + 0.5
e4 = say("a4", a + 0.3)
e5 = say("a5", e4 + 1.2)
kx = K("a5", "手感这玩意儿")
card("xbars", a, kx, n=1, e1=K("a4", "按正常") + 0.2, r1=K("a4", "实际"), d1=AT["a5"] + 0.2)
shot("s1_h373s", DB("2606111004560502"), kx, e5 + 0.8, t0=7.70, rate=0.5, mute=True,
     clipkw={"grade": dict(LIVE, mono=0.5)}, kb=[1.02, 1.1], fout=0.5, cx=1460)
seg2 = e5 + 0.8
m1 = bgm("Hitman.mp3", 28.0 - (AT["a3"] - seg1), seg1, -15, fin=0.8)
m1["dur"] = round(seg2 - m1["t"], 3)

# =====================================================================
# 二 · 第三节
# =====================================================================
chapter(seg2 + 0.2, "02", "第三节：13 比 0", "CHAPTER 2 · THIRD QUARTER")
e = say("b1", seg2 + 0.5)
e2 = say("b2", e + 0.2)
add_clip("v_bg_jgnc", JGNC, 8.0, 1 / 30)
kwb = K("b2", "文班亚马")
card("board", seg2, kwb, delay=2.3, bg="v_bg_jgnc", head="第三节 9:27", sas=81, nyk=52, lead="马刺领先 29", leadT=K("b2", "马刺还领先"),
     leadK="SPURS +29")
shot("s2_elbow", JGNC, kwb, K("b2", "一级"), ev=13.2, at=K("b2", "唐斯") + 0.4, gain=-2, bug=False,
     cxk=[[0, 820], [1.9, 820], [1.95, 1000]])
shot("s2_ref", JGNC, K("b2", "一级"), e2 + 0.3, t0=60.5, gain=-8, bug=False, cx=1060)
a = e2 + 0.3
e = say("b3", a + 0.1)
shot("s2_down", JGNC, a, K("b3", "再来"), t0=23.5, gain=-8, bug=False, cxk=[[0, 930], [1.0, 1000]])
shot("s2_rep", JGNC, K("b3", "再来"), e + 0.4, t0=40.0, gain=-8, bug=False, cx=975)
ov("fpts", a + 0.3, e + 0.4, keys=[[K("b3", "3 个"), 3]], tnote=K("b3", "再来"))
a = e + 0.4
e = say("b4", a + 0.2)
shot("s2_kat", JGNC, a, e + 0.4, t0=50.5, gain=-8, bug=False,
     cxk=[[0, 1010], [1.5, 1000], [2.4, 900], [3.1, 1020], [3.9, 1060]])
ov("run", a + 0.3, e + 0.4, label="尼克斯一波", steps=[[a, 0], [K("b4", "两个罚球") + 0.3, 2]])
bd1 = e + 0.4
e = breakdown("e428", bd1, head="中路没人", kicker="BREAKDOWN · 8:49 Q3")
dunk = BD["e428"]["dunk"][0] + 1.83
ov("run", bd1, e, label="尼克斯一波", steps=[[bd1, 2], [dunk, 4]])
mont0 = e
mb = [mont0, mont0 + 2.5, mont0 + 5.0, mont0 + 7.5]
montage([("s2_b432", "2606111033176002", {"t0": 9.75, "cxk": follow(0.6, 720, 1.5, 1310, before=[[0, 900]])}),
         ("s2_o448", "2606111038291302", {"t0": 3.70, "cxk": follow(0.65, 1520, 1.65, 1320)}),
         ("s2_h470", "2606111043178802", {"t0": 1.60, "cxk": follow(0.95, 260, 2.0, 1310)})], mb)
ov("run", mont0, mb[-1], label="尼克斯一波", steps=[[mont0, 4], [mb[0] + 1.5, 7], [mb[1] + 1.65, 10], [mb[2] + 2.0, 13]])
ov("huazi", mb[2] + 2.05, mb[3], text="13 : 0", x=540, y=Y_TOP, size=110, anim="slam", kicker="Knicks 13-0 run")
a = mb[3]
e = say("b7", a + 0.3)
k_end = K("b7", "一节打完")
card("shotmix", a, k_end, q="Q3", bar=a + 0.3, three=K("b7", "12"), result=K("b7", "就进俩"))
q3end = e + 0.5
shot("s2_q3end", Q3R, k_end, q3end, t0=225.8 - (q3end - k_end), gain=-4,
     cxk=[[0, 1330], [0.4, 1150], [0.8, 1000], [1.2, 850], [1.7, 620], [2.2, 540]])
ov("score", k_end - 0.2, q3end, keys=[[0, 90, 75, "第三节结束"]])
BARK = [{"zh": "我就批评这一点，老兄，你们根本投不进啊", "en": "That's my criticism. Like, damn, dude, you ain't making them.", "a": 0.2, "b": 3.4},
        {"zh": "领先 20 分，根本没理由连着投八九个三分", "en": "There's never a reason to shoot eight or nine in a row when you got a 20-point lead.", "a": 4.3, "b": 7.9}]
e = put_quote("v_q_barkley", "assets/footage/inside_barkley_ext.mp4", 51.6, 59.8, BARK, q3end + 0.1, "巴克利", "TNT 评论员 · 名人堂球员",
              [1264, 60, 512, 640], kicker="INSIDE THE NBA · 赛后节目")
a = e
e = say("b8", a + 0.6)
kz = K("b8", "你领先")
shot("s2_inside2", "assets/footage/inside_barkley.mp4", a, kz, t0=44.0, gain=-14, cx=880, bug=False)
shot("s2_run", Q3R, kz, e + 0.6, ev=185.6, tail=0.6, gain=-6,
     cxk=[[0, 800], [1.0, 1000], [1.6, 1130], [3.5, 1130], [4.5, 1020]])
seg3 = e + 0.6
m2 = bgm("Impact_Prelude.mp3", 100.0 - (mont0 - seg2), seg2, -16)
m2["dur"] = round(seg3 - m2["t"], 3)
m2["push"].append([mont0 - 0.5, mb[-1], 2])

# =====================================================================
# 三 · 第四节
# =====================================================================
chapter(seg3 + 0.2, "03", "第四节：往里打，还是不进", "CHAPTER 3 · FOURTH QUARTER")
e1 = say("c1", seg3 + 0.4)
kr = K("c1", "结果呢")
shot("s3_drive", Q4R, seg3, kr, t0=35.6, gain=-4, cxk=[[0, 720], [0.8, 620], [2.0, 560]])
e2 = say("c2", e1 + 0.5)
kd0, kd = K("c2", "因为"), K("c2", "防守人")
card("shotmix", kr - 0.2, kd0, q="Q4", bar=kr, hls=[["rim", kr + 0.7]], result=K("c1", "19 投"))
shot("s3_contest", Q4R, kd0, kd, ev=3.6, tail=0.5, gain=-4, cxk=[[0, 680], [1.5, 540], [2.8, 480]])
card("defdist", kd, e2 + 2.0, r3=kd + 0.3, r4=K("c2", "平均"), m80=K("c2", "八十"), open=K("c2", "你说"))
e = quote("q3_1", e2 + 2.0)
a = e
bb = [a + i * 2.2 for i in range(6)]
e = say("c3", a + 0.3)
montage([("s3_a598", "2606111112208502", {"cx": 1160}),
         ("s3_b606", "2606111112181502", {"cxk": [[0, 1050], [1.0, 1200], [1.8, 1380]]}),
         ("s3_t622", "2606111117300602", {"cxk": follow(0.3, 430, 1.5, 1400)}),
         ("s3_o632", "2606111117394102", {"cxk": follow(1.05, 830, 1.7, 1300, before=[[0, 1000]])}),
         ("s3_o658", "2606111127259502", {"cxk": follow(0.85, 490, 1.75, 1440, before=[[0, 620]])})], bb, tail=0.55)
ov("score", a + 0.2, bb[-1], keys=[[0, 95, 75, "第四节 9:33"], [bb[1] - 0.55, 95, 78, "9:16"], [bb[2] - 0.55, 95, 80, "8:44"],
                                   [bb[3] - 0.55, 95, 83, "7:28"], [bb[4] - 0.55, 97, 86, "7:03"], [bb[5] - 0.55, 99, 95, "4:34"]])
ov("huazi", bb[5] - 0.5, bb[5], text="5 分钟 20 : 4", x=540, y=Y_TOP, size=84, anim="slam", kicker="Knicks 20-4 run")
a = bb[-1]
e = say("c4", a + 0.3)
card("xbars", a, e + 1.5, n=2, e1=a + 0.2, r1=a + 0.4, d1=a + 0.9, e2=K("c4", "下半场") - 0.5, r2=K("c4", "下半场"), d2=K("c4", "原样"))
a = e + 1.5
e = say("c5", a + 0.2)
seg4 = e + 1.0
card("mfull", a, seg4, segs=[[a + 0.3, AT["c5"] + 1.2, 0, 2669]],
     mark={"t": K("c5", "马刺手里"), "g": 2669, "v": 7, "text": "还剩 3:31 · 马刺 +7", "sub": "104 : 97"},
     huazi={"t": K("c5", "这都能输"), "text": "这都能输？", "kicker": "How?"})
sfx.append(["stamp", round(K("c5", "这都能输"), 3)])
m3 = bgm("The_Escalation.mp3", 321.9 - (seg4 - seg3), seg3, -15, fout=0.4)
m3["dur"] = round(seg4 - m3["t"] + 0.3, 3)
m3["push"] += [[bb[0], bb[-1], 2], [AT["c5"], seg4, 3]]

# =====================================================================
# 四 · 最后 3 分半
# =====================================================================
chapter(seg4 + 0.2, "04", "最后 3 分 31 秒", "CHAPTER 4 · CLUTCH")
e = say("d1", seg4 + 0.5)
kwm = K("d1", "文班亚马") + 0.9
e2 = say("d2", e + 0.3)
shot("s4_wem", DCF8, seg4, e2 + 1.0, ev=259.79, at=kwm, gain=-2,
     cxk=follow(1.2, 1360, 2.3, 500, before=[[0, 1220]],
                after=[[2.7, 600], [3.2, 800], [3.78, 1050], [3.8, 1060], [4.7, 980], [5.2, 1120], [5.7, 1400], [6.2, 1250],
                       [6.48, 1250], [6.5, 560], [8.5, 450]]))
ov("score", AT["d1"] - 0.3, e2 + 1.0, keys=[[0, 102, 97, "第四节 3:31"], [kwm, 104, 97, "3:31"]])
ov("huazi", K("d2", "这是"), e2 + 0.9, text="最后一个运动战进球", x=540, y=Y_TOP, size=66, kicker="Spurs' last field goal")
a = e2 + 1.0
e3 = say("d3", a + 0.3)
e4 = say("d4", e3 + 0.3)
rel = e4 + 0.05
mk27 = rel + (17.33 - 15.87)
e5 = say("d5", mk27 + 0.5)
shot("s4_br27", "../raw/d676.mp4", a, e5 + 1.2, ev=15.87, at=rel, gain=0,
     cxk=follow(rel - a, 840, mk27 - a, 1270, before=[[0, 520], [2.0, 850], [4.0, 1000], [6.0, 780]],
                after=[[mk27 - a + 0.1, 980], [e5 + 1.2 - a, 820]]))
ov("score", a + 0.2, e5 + 1.2, keys=[[0, 104, 100, "2:31"], [mk27, 104, 103, "2:21"]])
ov("huazi", K("d4", "27"), rel + 0.3, text="27 英尺 · 8 米多", x=540, y=Y_TOP, size=66, kicker="27-ft three")
a = e5 + 1.2
e = say("d6", a + 1.76)
shot("s4_ft1", DCF8, a, a + 4.8, t0=386.0, gain=-2, cxk=[[0, 850], [1.98, 850], [2.0, 900]])
ov("huazi", a + 3.0, a + 4.7, text="两罚全丢", x=540, y=Y_TOP, size=80, kicker="1:47 · Spurs lead by 1")
a = a + 4.8
e = say("d7", a + 0.3)
kf = K("d7", "抛投") + 0.7
shot("s4_float", DCF8, a, e + 1.6, ev=425.1, at=kf, gain=-2, cxk=[[0, 1150], [1.5, 1200], [2.4, 1100], [4.0, 900]])
ov("score", a + 0.3, e + 1.6, keys=[[0, 104, 103, "1:22"], [kf, 104, 105, "1:22"]])
ov("huazi", kf + 0.3, e + 1.5, text="尼克斯全场第一次领先", x=540, y=Y_TOP, size=60, bg="blue", kicker="Knicks lead 105-104")
a = e + 1.6
e = say("d8", a + 0.2)
shot("s4_castleft", DCF8, a, e + 1.2, ev=515.0, at=K("d8", "两罚") + 0.6, gain=-2, cx=950)
ov("score", a + 0.2, e + 1.2, keys=[[0, 104, 105, "0:32"], [K("d8", "两罚") + 0.6, 105, 105, "0:30.3"], [K("d8", "马刺 106"), 106, 105, "0:30.3"]])
bd3 = e + 1.2
PY715 = 285 + 150
e = breakdown("e715", bd3, py=PY715)
ov("dual", K("d10", "还剩") - 0.2, AT["d11"] - 0.1, py=PY715, tl=K("d10", "还剩"), tr=K("d10", "进攻时间"), tgt=K("d10", "比比赛"))
ov("flow", AT["d11"], BD["e715"]["A"][1] - 0.05,
   nodes=[["什么都不用做", "把球攥在手里"], ["等尼克斯犯规", "送你上罚球线"], ["两罚都进", "领先 3 分"], ["对面最多投三分", "也只能追平"]],
   keys=[K("d11", "什么都不用"), K("d11", "等对面"), end("d11") - 0.2, end("d11") + 0.5])
for k in ("还剩", "进攻时间"):
    sfx.append(["tick", round(K("d10", k), 3)])
for k in (K("d11", "什么都不用"), K("d11", "等对面"), end("d11") - 0.2, end("d11") + 0.5):
    sfx.append(["tick", round(k, 3)])
sfx.append(["impact", round(AT["d13"] - 0.05, 3)])
e = quote("q4_2", e + 0.3)
a = e
e = say("d14", a + 0.4)
BUGC = {"crop": [1206, 926, 260, 104], "size": [600, 240], "sharpen": 0.6}
add_clip("v_st_fox130", BLK, 174 / 30, 1 / 30)
add_clip("v_st_fox125", BLK, 190 / 30, 1 / 30)
add_clip("v_bug_fox130", BLK, 174 / 30, 1 / 30, **BUGC)
add_clip("v_bug_fox125", BLK, 190 / 30, 1 / 30, **BUGC)
card("tl13", a, e + 0.9, st1="v_st_fox130", st2="v_st_fox125", bug1="v_bug_fox130", bug2="v_bug_fox125", t2=K("d14", "到起跳"),
     t3=K("d14", "前后不到"))
sfx.append(["stamp", round(K("d14", "前后不到") + 0.15, 3)])
a = e + 0.9
e = say("d15", a + 0.2)
shot("s4_blkslow", BLK, a, e + 0.4, ev=6.67, at=e - 0.4, rate=0.35, mute=True, clipkw={"grade": dict(LIVE, mono=0.8)}, kb=[1.08, 1.16],
     cxk=[[0, 980], [1.8, 920], [3.0, 800], [4.2, 690], [5.4, 610], [6.6, 570]])
sfx.append(["boom", round(e - 0.4, 3)])
bd4 = e + 0.4
e = breakdown("e727", bd4, head="最后 5.7 秒", kicker="BREAKDOWN · 0:05.7")
sfx.append(["impact", round(AT["d17"] - 0.05, 3)])
a = e
e = say("d18", a + 0.2)
seg5 = e + 2.2
shot("s4_msg", "../online/lL4TMc1sYmQ.mp4", a, seg5, t0=256.4, gain=-4, bug=False,
     cxk=[[0, 960], [1.2, 1000], [1.7, 1270], [2.5, 1070], [3.3, 1110], [4.4, 960], [5.6, 760], [6.2, 760]])
ov("huazi", K("d18", "53.8"), seg5 - 0.2, text="尼克斯全场只领先 53.8 秒", x=540, y=Y_TOP, size=60, bg="blue", kicker="Knicks led for 53.8 seconds")
m4 = bgm("Impact_Lento.mp3", 122.0 - (BD["e715"]["A"][1] - seg4), seg4, -15)
fa0 = bd4 - 3.0
fa_end = end("d18") + 0.3
m4b = bgm("Five_Armies.mp3", 147.0 - (fa_end - fa0), fa0, -15, fin=3.0, fout=1.5)
m4b["dur"] = round(fa_end + 2.5 - m4b["t"], 3)
m4b["push"].append([AT["d17"] - 0.2, AT["d17"] + 4.0, 3])
m4["dur"] = round(m4b["t"] + 3.0 - m4["t"], 3)
m4["fout"] = 3.0

# =====================================================================
# 收尾
# =====================================================================
e1 = say("e1", seg5 + 0.6)
e2 = say("e2", e1 + GAP)
card("summary", seg5, e2 + 0.5, t=[K("e1", "那 29 分"), K("e1", "下半场"), AT["e2"] + 0.3],
     rows=[["上半场", "手感多给了 21 分"], ["下半场", "同样的出手，少进 20 分"], ["最后 3 分半", "自己丢掉的回合，把比赛送了出去"]])
for k in (K("e1", "那 29 分"), K("e1", "下半场"), AT["e2"] + 0.3):
    sfx.append(["tick", round(k, 3)])
a = e2 + 0.5
e3 = say("e3", a + 0.3)
shot("s5_exit", "assets/footage/wemby_exit.mp4", a, e3 + 0.6, t0=0.05, rate=0.5, mute=True, cx=850, kb=[1.0, 1.05],
     clipkw={"grade": dict(LIVE, mono=0.35)})
e = quote("q5_1", e3 + 0.6)
endcard = [
    ["比赛画面", "腾讯体育 NBA 数据库 · NBA 官方 · NBA on ESPN"],
    ["赛后发布会", "NBA 官方 Postgame Media Availability"],
    ["数据", "NBA 逐回合记录 · NBA 追踪数据"],
    ["音乐", "Kevin MacLeod (incompetech.com) · CC BY 4.0"],
    ["", "Lightless Dawn · Hitman · Impact Prelude"],
    ["", "The Escalation · Impact Lento · Five Armies"],
    ["", "Long Road Ahead"],
    ["解说配音", "AI 合成语音 · 内部效果测试版"],
]
card("end", e + 0.3, e + 7.3, whoosh=False, lines=endcard)
duration = e + 7.3
m5 = bgm("Long_Road_Ahead.mp3", 100.0 - (K("e3", "尼克斯") - seg5), seg5, -15, fin=2.5, fout=2.5)
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
    if s.get("clip") in clips and s["sc"] == "clip":
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

segs = {"seg1": seg1, "seg2": seg2, "seg3": seg3, "seg4": seg4, "seg5": seg5}
out = {
    "duration": round(duration, 3), "fps": 30, "chap": chap,
    "vo": sorted(vo, key=lambda v: v["t"]), "shots": shots, "ov": ovs, "quotes": quotes, "sfx": sorted(sfx, key=lambda x: x[1]),
    "orig": orig, "beds": beds, "qaudio": qaudio, "music": music, "segs": {k: round(v, 3) for k, v in segs.items()},
}
(ROOT / "scenes/film_vt.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
(ROOT / "clips_vt.json").write_text(json.dumps(list(clips.values()), ensure_ascii=False, indent=1))
track = sorted(s["clip"] for s in shots if s.get("lay") == "crop" and "cx" not in s and "cxk" not in s)
(ROOT / "work/vt_track_list.json").write_text(json.dumps(track))
print(f"duration {duration:.2f}s = {int(duration // 60)}:{duration % 60:04.1f}")
for k, v in segs.items():
    print(f"  {k} {v:7.2f}  ({int(v // 60)}:{v % 60:04.1f})")
print(f"shots {len(shots)}  clips {len(clips)}  overlays {len(ovs)}  quotes {len(quotes)}  sfx {len(sfx)}  跟拍 {len(track)}")
gaps = [(round(s0["b"], 2), round(s1["a"], 2)) for s0, s1 in zip(shots, shots[1:]) if s1["a"] - s0["b"] > 0.01]
print("镜头空档：", gaps or "无")
for c in clips.values():
    if c["t0"] <= 0.0 and not c["src"].startswith(("work/", "assets/")):
        print("入点被夹到 0：", c["name"])
long = [(v["id"], c["text"]) for v in vo for c in v["chunks"] if size(c["text"]) > MAXC]
print("超长字幕：", long or "无")
