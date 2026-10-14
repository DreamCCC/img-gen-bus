#!/usr/bin/env python3
"""G4 出手质量：按队、按半场/节统计预期命中率、防守距离、进攻时钟、出手分布。数据 data/shot_detail.json。"""
import json
from collections import defaultdict

rows = json.load(open("data/shot_detail.json"))
pbp = {int(r["action_number"]): r for r in json.load(open("data/pbp.json"))}
TEAM = {"1610612759": "SAS", "1610612752": "NYK"}

agg = defaultdict(lambda: defaultdict(float))
for r in rows:
    e = json.loads(r["ext"])
    f = e["features"]
    team = TEAM[str(e["teamId"])]
    p = int(e["period"])
    three = e["ngssEventInfo"]["type"] == "3pt"
    made = bool(e["success"])
    xfg = float(e["expFieldGoalPct"])
    dist = f["shotDistance"]
    for key in (("1H" if p <= 2 else "2H"), f"Q{p}"):
        a = agg[(team, key)]
        a["n"] += 1
        a["made"] += made
        a["pts"] += made * (3 if three else 2)
        a["xpts"] += xfg * (3 if three else 2)
        a["xfg"] += xfg
        a["def"] += f["jointBallDistance"]
        a["clock"] += e.get("shotClockTime") or 0
        a["late"] += (e.get("shotClockTime") or 24) <= 7
        a["rim"] += dist <= 4
        a["three"] += three
        a["open"] += f["jointBallDistance"] >= 6

print(f"{'':10s} {'FGA':>4s} {'FG%':>6s} {'xFG%':>6s} {'实得':>5s} {'预期':>6s} {'防守距':>6s} {'时钟':>5s} {'≤7秒':>5s} {'篮下':>5s} {'三分':>5s} {'空位≥6':>6s}")
for team in ("SAS", "NYK"):
    for key in ("1H", "2H", "Q1", "Q2", "Q3", "Q4"):
        a = agg[(team, key)]
        n = a["n"]
        print(f"{team} {key:6s} {n:4.0f} {a['made']/n:6.1%} {a['xfg']/n:6.1%} {a['pts']:5.0f} {a['xpts']:6.1f} "
              f"{a['def']/n:5.1f}ft {a['clock']/n:5.1f} {a['late']/n:5.0%} {a['rim']/n:5.0%} {a['three']/n:5.0%} {a['open']/n:6.0%}")
