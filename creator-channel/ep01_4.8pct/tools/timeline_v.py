"""竖版 60 秒时间轴：每个镜头取横版的一段（h0 起，1 倍速）重新构图，或是竖版原生画面。
扣篮落在 Five Armies 113.22 秒那记重音上，其余剪点吸附到拍子；灯灭处音乐硬停，回归处接 Heroic Age。
用法：python tools/timeline_v.py   → scenes/film_v.json
"""
import json
from pathlib import Path

import librosa

ROOT = Path(__file__).resolve().parent.parent
H = json.loads((ROOT / "scenes/film_h.json").read_text())
HA_, HEV, HS = H["anchors"], H["ev"], H["scenes"]
y, sr = librosa.load(ROOT / "assets/music/Five_Armies.mp3", sr=22050)
_, FA_BEATS = librosa.beat.beat_track(y=y, sr=sr, units="time")

V_SLAM = 23.4
FA0 = 113.22 - V_SLAM
beats = [round(float(b) - FA0, 3) for b in FA_BEATS if b >= FA0]
snap = lambda t: min(beats, key=lambda b: abs(b - t))

hook = [snap(1.05), snap(2.1), snap(3.45)]
ruler_land = snap(15.5)
stamp = snap(19.1)
p_lebron, p_kobe, p_jordan = snap(33.0), snap(33.75), snap(34.3)
p_2016, p_2017, p_2018, p_2019 = snap(35.6), snap(36.3), snap(37.0), snap(37.7)
v_stop = round(p_2019 + (HA_["stop"] - HA_["lastHit"]), 3)
fl = {f["year"]: f["t"] for f in H["flips"]}

shots = []


def shot(v0, v1, h0=None, layout="zoom", **kw):
    shots.append({"v0": round(v0, 3), "v1": round(v1, 3), "h0": None if h0 is None else round(h0, 3), "layout": layout, **kw})


PANEL = {"zoom": 1.295, "cx": 960, "cy": 540}
shot(0.0, 5.8, 41.6, "zoom", zoom=1.0, cx=900, cy=540, dim=0.55, native="hook")
shot(5.8, 8.3, HS["vhs"][1] - 2.5, "zoom", zoom=1.15, cx=960, cy=540)
shot(8.3, 11.3, 22.6, "zoom", zoom=1.12, cx=960, cy=560, title="1979 · 北京")
shot(11.3, 17.6, HEV["rulerLand"] - (ruler_land - 11.3), "zoom", zoom=1.0, cx=1080, cy=560)
shot(17.6, 19.9, HEV["stamp"] - (stamp - 17.6), "zoom", zoom=1.05, cx=960, cy=560)
shot(19.9, 20.6, HS["yao"][0] + 0.5, "zoom", **PANEL)
shot(20.6, 25.0, HA_["slam"] - (V_SLAM - 20.6), "zoom", **PANEL)
q18 = next(v for v in H["vo"] if v["id"] == "L18")["t"]
shot(25.0, 29.0, q18 - 0.3, "zoom", zoom=0.88, cx=960, cy=520)
shot(29.0, p_lebron, HEV["spanCount"][0] - 1.3, "zoom", zoom=0.9, cx=960, cy=560)
FLIP = {"regions": [[[1060, 190, 640, 700], [240, 230, 600, 656]], [[150, 340, 680, 460], [100, 900, 880, 595]]]}
for (v0, v1, yr) in [(p_lebron, p_kobe, 2007), (p_kobe, p_jordan, 2013), (p_jordan, p_2016, 2015), (p_2016, p_2017, 2016),
                     (p_2017, p_2018, 2017), (p_2018, p_2019, 2018), (p_2019, v_stop, 2019)]:
    shot(v0, v1, fl[yr] + (0.02 if yr != 2019 else 0), "regions", **FLIP)
LIGHTS = {"regions": [[[360, 30, 1200, 320], [0, 330, 1080, 288]], [[150, 340, 680, 460], [100, 760, 880, 595]]]}
v_boom = round(v_stop + 6.4, 3)
shot(v_stop, v_boom - 0.9, HA_["stop"], "regions", native="six", **LIGHTS)
shot(v_boom - 0.9, v_boom + 5.6, HA_["boom"] - 0.9, "zoom", zoom=1.0, cx=960, cy=540)
shot(v_boom + 5.6, v_boom + 10.9, HS["rockets"][0], "zoom", **PANEL, title="火箭 · 2004 → 2026")
v_card = round(v_boom + 10.9, 3)
v_end = round(v_card + 1.9, 3)
DUR = round(v_end + 4.9, 2)
shot(v_card, v_end, None, "native", native="card")
shot(v_end, DUR, None, "native", native="end")

vdur = json.loads((ROOT / "audio/vo_v/durations.json").read_text())
hdur = {v["id"]: v["dur"] for v in H["vo"]}
vtext = {d["id"]: d["text"] for d in json.loads((ROOT / "audio/vo_lines_v.json").read_text())}
htext = {v["id"]: v["text"] for v in H["vo"]}
VO = [("V01", 0.15), ("V02", 5.85), ("V03", 8.45), ("V04", 13.45), ("V05", 17.75), ("L18", 25.3), ("V07", 29.15),
      ("V08", p_lebron + 0.15), ("V09", v_stop + 0.6), ("V10", v_stop + 3.3), ("L27", v_boom + 0.35),
      ("L28", v_boom + 5.9), ("V14", v_end + 0.2)]
vo = []
for i, t in VO:
    is_v = i.startswith("V")
    vo.append({"id": i, "t": round(t, 3), "dur": vdur[i] if is_v else hdur[i], "text": vtext[i] if is_v else htext[i],
               "wav": f"audio/vo_v/{i}.wav" if is_v else f"audio/vo/{i}.wav"})
for a, b in zip(vo, vo[1:]):
    assert a["t"] + a["dur"] <= b["t"] + 0.01, f"VO overlap {a['id']} {b['id']}"
assert vo[-1]["t"] + vo[-1]["dur"] <= DUR

out = {
    "duration": DUR, "fps": 30, "shots": shots, "vo": vo,
    "music": {"fa0": round(FA0, 3), "stop": v_stop, "boom": v_boom, "ha_boom": 54.08},
    "ev": {"hook": hook, "card": [v_card, round(v_card + 0.93, 3)], "endBounces": [round(v_end + 0.9, 3), round(v_end + 1.5, 3), round(v_end + 1.9, 3), round(v_end + 2.2, 3)],
           "six": round(v_stop + 3.3, 3)},
}
(ROOT / "scenes/film_v.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for s in shots:
    print(s["v0"], s["v1"], s["h0"], s.get("native", ""), s["layout"])
print("duration", DUR, "stop", v_stop, "boom", v_boom)
for v in vo:
    print(v["id"], v["t"], round(v["t"] + v["dur"], 2), v["text"])
