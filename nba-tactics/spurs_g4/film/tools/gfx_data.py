"""代码画面用的数据：分差曲线、上半场投篮、应得/实得分，全部从 data/ 现算，写进 scenes/gfx_data.json。

口径
- 分差：pbp 每次比分变化记一点，横轴比赛秒数（0–2880），纵轴马刺领先分（客队 away − 主队 home）。
- 投篮：pbp is_field_goal=1 的出手，三分按 actionType=3pt。
- 应得分：shot_detail 每次出手 ext.expFieldGoalPct × 分值（2/3）之和；实得分：命中 × 分值（不含罚球）。
用法：python tools/gfx_data.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT.parent / "data"
SAS, NYK = 1610612759, 1610612752

pbp = sorted(json.loads((DATA / "pbp.json").read_text()), key=lambda r: int(r["order_number"]))
shots = [json.loads(r["ext"]) | {"event_id": int(r["event_id"])} for r in json.loads((DATA / "shot_detail.json").read_text())]
tbs = {r["team_name_cn"]: r for r in json.loads((DATA / "tbs.json").read_text())}


def gsec(period, clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    return (int(period) - 1) * 720 + 720 - (int(m[1]) * 60 + float(m[2]))


def clock_cn(period, clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    s = float(m[2])
    return f"第{'一二三四'[int(period) - 1]}节 {int(m[1])}:{int(s):02d}"


# ---------- 分差 ----------
margin, prev = [[0, 0, 0]], (0, 0)
for r in pbp:
    if r["score_away"] == "":
        continue
    sc = (int(r["score_away"]), int(r["score_home"]))
    if sc != prev:
        margin.append([round(gsec(r["period"], r["clock"]), 1), *sc])
        prev = sc
margin.append([2880, *prev])
top = max(a - h for _, a, h in margin)
peaks = []
for r in pbp:
    if r["score_away"] and int(r["score_away"]) - int(r["score_home"]) == top:
        g = round(gsec(r["period"], r["clock"]), 1)
        if not peaks or peaks[-1]["sas"] != int(r["score_away"]):
            peaks.append({"g": g, "sas": int(r["score_away"]), "nyk": int(r["score_home"]), "label": clock_cn(r["period"], r["clock"])})
at = lambda g: next(m for m in reversed(margin) if m[0] <= g)
half, final = at(1440), margin[-1]

# ---------- 投篮（pbp） ----------
fg = {}
for key, ps in (("1H", "12"), ("2H", "34")):
    rows = [r for r in pbp if r["is_field_goal"] == "1" and r["team_tricode"] == "SAS" and r["period"] in ps]
    seq = [[int(json.loads(r["extend_info"])["actionType"] == "3pt"), int(r["shot_result"] == "Made")] for r in rows]
    fg[key] = {
        "fgm": sum(m for _, m in seq), "fga": len(seq),
        "fg3m": sum(m for t, m in seq if t), "fg3a": sum(t for t, _ in seq),
        "seq": seq,
    }

# ---------- 应得 / 实得 ----------
fg_ids = {int(r["action_number"]) for r in pbp if r["is_field_goal"] == "1" and r["team_tricode"] == "SAS"}
xp = {}
for key, ps in (("1H", (1, 2)), ("2H", (3, 4)), ("Q3", (3,)), ("Q4", (4,))):
    ss = [s for s in shots if s["teamId"] == SAS and int(s["period"]) in ps]
    val = lambda s: 3 if s["ngssEventInfo"]["type"] == "3pt" else 2
    xp[key] = {
        "xpts": round(sum(float(s["expFieldGoalPct"]) * val(s) for s in ss), 2),
        "pts": sum(val(s) * bool(s["success"]) for s in ss),
        "n": len(ss),
        "n_pbp": sum(1 for r in pbp if r["is_field_goal"] == "1" and r["team_tricode"] == "SAS" and int(r["period"]) in ps),
    }

# ---------- 第三 / 四节：出手构成、防守人手离球距离（口径同 shot_quality.py） ----------
# 篮下 = 出手距离 ≤ 4 英尺；手离球 = features.jointBallDistance（英尺）
quarters = {}
for q in (3, 4):
    ss = sorted([s for s in shots if s["teamId"] == SAS and int(s["period"]) == q], key=lambda s: s["shotUTCTime"])
    kinds = [["three" if s["ngssEventInfo"]["type"] == "3pt" else "rim" if s["features"]["shotDistance"] <= 4 else "mid",
              int(bool(s["success"]))] for s in ss]
    jd = [float(s["features"]["jointBallDistance"]) for s in ss]
    quarters[f"Q{q}"] = {
        "fga": len(kinds), "fgm": sum(m for _, m in kinds),
        "three": sum(k == "three" for k, _ in kinds), "three_m": sum(m for k, m in kinds if k == "three"),
        "rim": sum(k == "rim" for k, _ in kinds), "mid": sum(k == "mid" for k, _ in kinds),
        "seq": kinds,
        "def_avg": round(sum(jd) / len(jd), 3), "def_n": len(jd),
        "open6": sum(d >= 6 for d in jd), "open6_pct": round(sum(d >= 6 for d in jd) / len(jd) * 100, 1),
        "def_seq": [round(d, 2) for d in jd],
    }

untracked = sorted(fg_ids - {s["event_id"] for s in shots})
untracked = [{"action": a, **{k: r[k] for k in ("period", "clock", "description")}} for r in pbp for a in untracked if int(r["action_number"]) == a]

out = {
    "margin": margin,
    "marks": {"peaks": peaks, "half": half, "final": final, "top": top},
    "fg": fg,
    "xpts": xp,
    "quarters": quarters,
    "untracked": untracked,
    "box": {k: {f: v[f] for f in ("pts", "fgm", "fga", "fg3m", "fg3a")} for k, v in tbs.items()},
}
(ROOT / "scenes/gfx_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

print(f"分差点 {len(margin)}，最大领先 +{top}：", [(p['label'], f"{p['sas']}:{p['nyk']}") for p in peaks])
print(f"半场 {half[1]}:{half[2]} ({half[1] - half[2]:+d})，终场 {final[1]}:{final[2]} ({final[1] - final[2]:+d})")
for k, v in fg.items():
    print(f"马刺{k} 投篮 {v['fgm']}/{v['fga']}  三分 {v['fg3m']}/{v['fg3a']}  投篮得分 {v['fgm'] * 2 + v['fg3m']}")
for k, v in xp.items():
    print(f"马刺{k} 应得 {v['xpts']:.1f}  实得 {v['pts']}  差 {v['pts'] - v['xpts']:+.1f}  （追踪 {v['n']} 次 / pbp {v['n_pbp']} 次）")
for k, v in quarters.items():
    print(f"马刺{k} {v['fgm']}/{v['fga']}  三分 {v['three_m']}/{v['three']} ({v['three'] / v['fga']:.0%})  篮下 {v['rim']} ({v['rim'] / v['fga']:.0%})  "
          f"中距离 {v['mid']}  手离球 {v['def_avg']:.1f}ft  ≥6ft {v['open6']}/{v['def_n']} ({v['open6_pct']}%)")
print("追踪数据缺失的马刺出手：", untracked)
print("全场 box：", out["box"])
