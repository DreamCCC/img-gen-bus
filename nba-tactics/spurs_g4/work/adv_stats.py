"""G4 高阶指标：分节预期 vs 实得（双方）、防守压迫分、出手时进攻时钟、关键回合的追踪特征。"""
import json
import re

pbp = {int(r["action_number"]): r for r in json.load(open("data/pbp.json", encoding="utf-8"))}
sd = json.load(open("data/shot_detail.json", encoding="utf-8"))
SAS = 1610612759

rows = []
for s in sd:
    e = json.loads(s["ext"])
    f = e.get("features") or {}
    r = pbp.get(int(s["event_id"]))
    three = bool(r and r.get("action_type") == "3pt")
    rows.append(dict(ev=int(s["event_id"]), q=int(e["period"]), sas=int(s["team_id"]) == SAS, made=bool(s["success"]),
                     xfg=float(s["expected_fg"] or 0), three=three, hand=float(s["joint_ball_distance"] or 0) / 12,
                     press=f.get("pressureScore"), sc=e.get("shotClockTime"), def_speed=f.get("defSpeed"),
                     dist=f.get("shotDistance"), desc=(r or {}).get("description", "")))

print("== 分节：预期得分 vs 实得（只算投篮）| 平均压迫分 | 平均手离球 ==")
for team in (True, False):
    for q in (1, 2, 3, 4):
        r = [x for x in rows if x["sas"] == team and x["q"] == q]
        pts = sum((3 if x["three"] else 2) * x["made"] for x in r)
        xp = sum((3 if x["three"] else 2) * x["xfg"] for x in r)
        pr = [x["press"] for x in r if x["press"] is not None]
        print(f"  {'SAS' if team else 'NYK'} Q{q}: {pts:2d} vs x{xp:5.1f} ({pts - xp:+5.1f})  "
              f"press {sum(pr) / max(1, len(pr)):.3f}  hand {sum(x['hand'] for x in r) / max(1, len(r)):.2f}  n={len(r)}")

print("\n== 马刺三分：按节，以及第三节连续投丢 ==")
seq = sorted([x for x in rows if x["sas"] and x["three"] and x["q"] == 3], key=lambda x: x["ev"])
print("  Q3 3PT:", "".join("O" if x["made"] else "x" for x in seq))

print("\n== 关键回合追踪特征 ==")
for ev in (428, 667, 676, 687, 714, 715, 725, 727):
    for x in rows:
        if x["ev"] == ev:
            print(f"  e{ev} {x['desc'][:60]:60s} xFG {x['xfg']:.3f}  hand {x['hand']:.2f}ft  press {x['press']}  "
                  f"shotclock {x['sc']}  dist {x['dist']}")
