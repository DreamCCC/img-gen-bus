"""旁白时长驱动的时间轴：data/analysis.json + audio/vo/durations.json → scenes/film.json

每一拍 = 一段源视频播放（src a→b，rate 为每个成片帧推进几个源帧）+ 定格到旁白读完。
源视频 116.62fps，成片 30fps：rate=1 即约 0.26 倍慢放且没有重复帧，rate=3.887 为原速。
英文版：python tools/timeline.py en → audio/vo_lines_en.json + audio/vo_en/ → scenes/film_en.json
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
EN = len(sys.argv) > 1 and sys.argv[1] == "en"
SUF = "_en" if EN else ""
A = json.loads((ROOT / "data/analysis.json").read_text())
DUR = json.loads((ROOT / f"audio/vo{SUF}/durations.json").read_text())
LINES = {l["id"]: l for l in json.loads((ROOT / f"audio/vo_lines{SUF}.json").read_text())}
PRE_WORD = {"下蹲": "dip", "肘角": "elbow"} if EN else {}
SRC_FPS = A["fps"]
REAL = SRC_FPS / FPS
N = A["n_frames"]

shot = A["shots"][0]
M = A["shot_metrics"][0]
DET = M["details"]
DIP, REL, FIN = shot["dip_frame"], M["release_frame"], M["finish_frame"]
MAKE = A["make_frames"][0]
KNEE_MIN = min((e for e in shot["data"] if e["frame"] <= REL and e["knee_angle"]), key=lambda e: e["knee_angle"])["frame"]
PEAK = max((e for e in shot["data"] if e["frame"] <= REL and e["speed"] is not None), key=lambda e: e["speed"])["frame"]
WRIST_PEAK = max((e for e in shot["data"] if e["frame"] <= REL and e["wrist_load_angle"]), key=lambda e: e["wrist_load_angle"])["frame"]
LAND = REL + round(DET["torso"]["landing_time"] * SRC_FPS)

def rew(a, b, sec):
    return (a, b, -abs(a - b) / (sec * FPS))


# 拍：(id, 旁白, 播放段 (a, b, rate), 镜头, 旁白相对拍头的延迟, 尾部留白, 播放前先定格多久)
# pre 可写成旁白里的词：念到这个词前 0.2 秒开始播放
BEATS = [
    ("open", None, (0, MAKE, REAL), "wide", 0, 0, 0),
    ("make", "L01", (MAKE, N - 1, 1.0), "wide", 0.25, 0.45, 0),
    ("rewind", "L02", rew(N - 1, 60, 0.9), "wide", 0.15, 0.35, 0),
    ("detect", "L03", (60, DIP, 1.0), "wide", 0.1, 0.45, 0),
    ("phases", "L04", (DIP, FIN, 1.2), "tight", 0.35, 0.3, "下蹲"),
    ("rew2", None, rew(FIN, DIP, 0.5), "tight", 0, 0, 0),
    ("dip", "L05", (DIP, KNEE_MIN, 1.0), "tight", 0.1, 0.45, 0),
    ("ext", "L06", (KNEE_MIN, PEAK, 1.0), "tight", 0.1, 0.45, 0),
    ("release", "L07", (PEAK, REL, 1.0), "tight", 0.1, 0.45, 0),
    ("rew3", None, rew(REL, DIP, 0.4), "tight", 0, 0, 0),
    ("quick", "L08", (DIP, REL, 1.0), "tight", 0.1, 0.45, 0),
    ("follow", "L09", (REL, FIN, 1.0), "tight", 0.1, 0.45, "肘角"),
    ("others", "L10", (FIN, FIN, 1.0), "tight", 0.1, 0.45, 0),
    ("makeAgain", "L11", (FIN, MAKE + 6, 2.0), "wide", 0.6, 0.5, 0),
    ("card", "L12", (MAKE + 6, MAKE + 6, 1.0), "wide", 0.3, 0.9, 0),
    ("outro", "L13", (MAKE + 6, MAKE + 6, 1.0), "wide", 0.1, 3.2, 0),
]


def chunks(text, dur):
    parts = [p for p in re.split(r"(?<=[，。、；])", text) if p.strip()]
    # 合并过短的片段，字幕一屏不超过约 18 字
    out = []
    for p in parts:
        if out and len(re.sub(r"\s", "", out[-1] + p)) <= 18 and len(re.sub(r"\s", "", p)) <= 6:
            out[-1] += p
        else:
            out.append(p)
    w = [len(re.sub(r"[\s，。、；]", "", p)) + 1.5 for p in out]
    tot = sum(w)
    res, acc = [], 0.0
    for p, x in zip(out, w):
        a = acc / tot * dur
        acc += x
        res.append({"text": re.sub(r"[，。；]$", "", p).strip(), "a": round(a, 3), "b": round(acc / tot * dur, 3)})
    return res


def split_long(p, limit):
    """超长句在靠近中间的词间断开，优先断在连词/介词前。"""
    if len(p) <= limit:
        return [p]
    cut = min((i for i, ch in enumerate(p) if ch == " "),
              key=lambda i: abs(i - len(p) / 2) - (8 if re.match(r" (and|so|to|from|on|back|are|of)\b", p[i:]) else 0))
    return split_long(p[:cut], limit) + split_long(p[cut + 1:], limit)


def chunks_en(text, dur, limit=50):
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        cur = []
        for p in re.split(r"(?<=,)\s+", sent):
            if cur and (len(cur[-1]) < 16 or len(cur[-1]) + 1 + len(p) <= limit):
                cur[-1] += " " + p
            else:
                cur.append(p)
        out += [q for p in cur for q in split_long(p, limit)]
    w = [len(p) + 6 for p in out]
    tot = sum(w)
    res, acc = [], 0.0
    for p, x in zip(out, w):
        a = acc / tot * dur
        acc += x
        res.append({"text": re.sub(r",$", "", p), "a": round(a, 3), "b": round(acc / tot * dur, 3)})
    return res


def plain_en(s):
    return re.sub(r"[\s,.;:!?]", "", s).lower()


def word_frac(line, word):
    if EN:
        plain = plain_en(LINES[line]["text"])
        return plain.index(plain_en(PRE_WORD.get(word, word))) / len(plain)
    plain = re.sub(r"[\s，。、；]", "", LINES[line]["text"])
    return plain.index(word) / len(plain)


beats, vo, t = [], [], 0.0
for bid, line, (a, b, rate), cam, delay, tail, pre in BEATS:
    play = abs(b - a) / abs(rate) / FPS
    vd = DUR[line] if line else 0.0
    if isinstance(pre, str):
        pre = max(0.0, delay + word_frac(line, pre) * vd - 0.2)
    dur = max(pre + play, delay + vd + tail) if line else pre + play
    beats.append({"id": bid, "t0": round(t, 4), "t1": round(t + dur, 4), "a": a, "b": b, "rate": rate, "cam": cam,
                  "pre": round(pre, 4), "play": round(play, 4)})
    if line:
        vo.append({"id": line, "t": round(t + delay, 4), "dur": vd, "chunks": (chunks_en if EN else chunks)(LINES[line]["text"], vd)})
    t += dur
duration = round(t, 3)

# 篮球飞行：只用连续可靠的检测点（上升段、下落进框段），中间飞出画面的部分用抛物线拟合
ball = {int(k): v for k, v in A["ball"].items()}
good = [f for f in range(REL - 4, MAKE + 4) if f in ball and not (abs(ball[f][0] - 1786) < 30 and abs(ball[f][1] - 1553) < 30)]
seq = [f for f in good if f <= REL + 22 or (MAKE - 45 <= f <= MAKE - 25)]
fs = np.array(seq, float)
px = np.polyfit(fs, [ball[f][0] for f in seq], 1)
py = np.polyfit(fs, [ball[f][1] for f in seq], 2)
fit_err = float(np.max(np.hypot(np.polyval(px, fs) - [ball[f][0] for f in seq], np.polyval(py, fs) - [ball[f][1] for f in seq])))

# 逐帧数据：右侧肩肘腕、髋膝踝、脚跟、食指（MediaPipe 下标），3 帧居中平滑只用于画线
IDX = {"sh": 12, "el": 14, "wr": 16, "ix": 20, "hip": 24, "kn": 26, "an": 28, "heel": 30, "toe": 32, "nose": 0}
pose = A["pose"]
frames = []
for i in range(N):
    rec = {}
    for k, j in IDX.items():
        pts = [pose[f][j] for f in range(max(0, i - 1), min(N, i + 2)) if pose[f]]
        if pose[i] and pts:
            rec[k] = [round(float(np.mean([p[0] for p in pts])), 1), round(float(np.mean([p[1] for p in pts])), 1)]
    fh = A["frame_history"][i]
    rec["elbow"] = fh["elbow_angle"]
    rec["knee"] = fh["knee_angle"]
    rec["wrist"] = fh["wrist_load_angle"]
    rec["torso"] = fh["torso_angle"]
    rec["heelY"] = fh["heel_y"]
    if i in ball and i <= DIP and pose[i]:
        wr = pose[i][16]
        if np.hypot(ball[i][0] - wr[0], ball[i][1] - wr[1]) < 260:
            rec["ball"] = ball[i]
            rec["box"] = A["ball_box"].get(str(i))
    frames.append(rec)
speed = {e["frame"]: e["speed"] for e in shot["data"] if e["speed"] is not None}
for f, v in speed.items():
    frames[f]["speed"] = v

DIMS = [
    ("release_form", "出手姿势", "RELEASE FORM", 0.25, f"出手肘角 {DET['release']['median_angle']:.0f}°  理想 160°"),
    ("extension_speed", "伸展速度", "EXTENSION SPEED", 0.15, f"伸肘角速度峰值 {DET['extension']['max_speed']:.0f}°/s"),
    ("follow_through", "随手动作", "FOLLOW-THROUGH", 0.10, f"随手肘角中位 {DET['follow']['median_follow_angle']:.0f}°  波动 {DET['follow']['angle_std']:.0f}°"),
    ("lower_body", "下肢加载", "LOWER-BODY LOAD", 0.10, f"最小膝角 {DET['lower_body']['min_knee_angle']:.0f}°  脚跟抬离 {DET['lower_body']['max_heel_lift_px']:.0f}px"),
    ("wrist_loading", "手腕加载", "WRIST LOADING", 0.10, f"肘-腕-指夹角峰值 {DET['wrist']['peak_wrist_angle']:.0f}°"),
    ("quick_release", "快速出手", "QUICK RELEASE", 0.10, f"下蹲→出手 {DET['quick_release']['time']:.2f}s"),
    ("kinetic_chain", "发力顺序", "KINETIC CHAIN", 0.08, f"膝盖早于出手伸直 {DET['kinetic_chain']['sequence_frames']} 帧"),
    ("torso_control", "躯干控制", "TORSO CONTROL", 0.05, f"躯干偏移 {DET['torso']['mean_deviation']:.0f}°"),
    ("make_result", "命中结果", "MAKE", 0.05, "命中" if DET["make"]["made"] else "未中"),
    ("forward_sway", "落地前移", "FORWARD SWAY", 0.02, f"落地前移 {DET['sway']['sway']:.0f}px"),
]
dims = [{"key": k, "zh": zh, "en": en, "w": w, "score": round(M[k], 2), "note": note} for k, zh, en, w, note in DIMS]
total = sum(d["w"] * d["score"] for d in dims)
assert abs(total - M["total_score"]) < 0.01, (total, M["total_score"])

film = {
    "duration": duration, "fps": FPS, "srcFps": SRC_FPS, "n": N, "w": A["width"], "h": A["height"],
    "beats": beats, "vo": vo,
    "keys": {"dip": DIP, "kneeMin": KNEE_MIN, "peak": PEAK, "wristPeak": WRIST_PEAK, "kneeExt": DET["kinetic_chain"]["knee_extension_frame"],
             "release": REL, "finish": FIN, "land": LAND, "make": MAKE},
    "hoop": A["config"]["hoop_roi"], "groundHeel": shot["ground_heel_y"], "torsoBase": shot["torso_baseline"],
    "ballFit": {"px": px.tolist(), "py": py.tolist(), "from": REL, "to": MAKE - 8},
    "dims": dims, "total": round(total, 2), "score": A["score"], "details": DET,
    "frames": frames,
}
(ROOT / f"scenes/film{SUF}.json").write_text(json.dumps(film, ensure_ascii=False))
print(f"duration {duration:.2f}s  total {total:.2f}  ball fit max err {fit_err:.1f}px  keys {film['keys']}")
for b in beats:
    print(f"  {b['id']:10s} {b['t0']:6.2f}-{b['t1']:6.2f}  src {b['a']}->{b['b']}  cam {b['cam']}")
