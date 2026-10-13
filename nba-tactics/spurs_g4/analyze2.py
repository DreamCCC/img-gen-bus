#!/usr/bin/env python3
"""G4 补充：分半场球员数据、阵容在场、暂停、犯规、得分荒。"""
import json
import re
from collections import defaultdict

pbp = sorted(json.load(open("data/pbp.json")), key=lambda r: int(r["order_number"]))


def secs(period, clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    left = int(m.group(1)) * 60 + float(m.group(2))
    return (int(period) - 1) * 720 + 720 - left


def gc(r):
    m = re.match(r"PT(\d+)M([\d.]+)S", r["clock"])
    return f"Q{r['period']} {int(m.group(1)):02d}:{float(m.group(2)):04.1f}"


rows = [r for r in pbp if r.get("clock")]

print("== 分半场：主要球员 ==")
KEY = ["V. Wembanyama", "D. Fox", "D. Harper", "D. Vassell", "S. Castle", "J. Champagnie",
       "J. Brunson", "O. Anunoby", "K. Towns", "J. Alvarado"]
agg = defaultdict(lambda: defaultdict(int))
for r in rows:
    n = r.get("player_name_i")
    if n not in KEY:
        continue
    h = "1H" if int(r["period"]) <= 2 else "2H"
    a = agg[(n, h)]
    at = r.get("action_type")
    if at in ("2pt", "3pt"):
        a["fga"] += 1
        a["3pa"] += at == "3pt"
        if r.get("shot_result") == "Made":
            a["fgm"] += 1
            a["3pm"] += at == "3pt"
            a["pts"] += 3 if at == "3pt" else 2
    elif at == "freethrow":
        a["fta"] += 1
        if r.get("shot_result") == "Made":
            a["ftm"] += 1
            a["pts"] += 1
    elif at == "turnover":
        a["tov"] += 1
for n in KEY:
    for h in ("1H", "2H"):
        a = agg[(n, h)]
        print(f"  {n:15s} {h} pts {a['pts']:2d}  FG {a['fgm']}/{a['fga']}  3P {a['3pm']}/{a['3pa']}  "
              f"FT {a['ftm']}/{a['fta']}  TOV {a['tov']}")

print("\n== 暂停、恶意犯规、技术犯规、录像回放 ==")
for r in rows:
    d = r.get("description", "")
    if r.get("action_type") in ("timeout", "instantreplay") or "FLAGRANT" in d.upper() or "T.FOUL" in d:
        print(f"  {gc(r)}  {r.get('score_away')}-{r.get('score_home')}  {r.get('team_tricode','')} {d}")

print("\n== 马刺运动战得分荒（两次投篮命中间隔 >= 4 分钟） ==")
last = (0, None)
for r in rows:
    if r.get("team_tricode") == "SAS" and r.get("action_type") in ("2pt", "3pt") and r.get("shot_result") == "Made":
        t = secs(r["period"], r["clock"])
        if last[1] and t - last[0] >= 240:
            print(f"  {gc(last[1])} -> {gc(r)}  {(t-last[0])/60:.1f} 分钟  "
                  f"比分 {last[1]['score_away']}-{last[1]['score_home']} -> 进球前 ")
            mid = [x for x in rows if last[0] < secs(x['period'], x['clock']) < t and x.get('team_tricode') == 'SAS'
                   and x.get('action_type') in ('2pt', '3pt', 'turnover')]
            miss = sum(1 for x in mid if x['action_type'] in ('2pt', '3pt'))
            tov = sum(1 for x in mid if x['action_type'] == 'turnover')
            print(f"     期间马刺投丢 {miss} 次、失误 {tov} 次")
        last = (t, r)

print("\n== 在场阵容（换人推算），翻盘关键时段 ==")
starters = {"SAS": set(), "NYK": set()}
pbs = json.load(open("data/pbs.json"))
for p in pbs:
    e = json.loads(p["extend_info"]) if p["extend_info"] else {}
    if str(e.get("starter")) == "1":
        first, last = p["player_name"].split(" ", 1)
        starters[p["team_abbreviation"]].add(f"{first[0]}. {last}")
print("  首发", starters)
on = {k: set(v) for k, v in starters.items()}
marks = {secs(3, "PT09M40.00S"), secs(3, "PT04M35.00S"), secs(4, "PT09M33.00S"), secs(4, "PT04M11.00S"),
         secs(4, "PT02M21.00S"), secs(4, "PT00M05.70S")}
seen = set()
for r in rows:
    t = secs(r["period"], r["clock"])
    for m in sorted(marks):
        if t > m and m not in seen:
            seen.add(m)
            print(f"  t={m//60:.0f}min  SAS {sorted(on['SAS'])}")
    if r.get("action_type") == "substitution":
        team = r["team_tricode"]
        name = r["player_name"]
        if r["sub_type"] == "out":
            on[team].discard(name)
        else:
            on[team].add(name)
print(f"  终场  SAS {sorted(on['SAS'])}   NYK {sorted(on['NYK'])}")

print("\n== 文班亚马下场时段 ==")
off_t = None
for r in rows:
    if r.get("action_type") == "substitution" and r.get("player_name") == "V. Wembanyama":
        if r["sub_type"] == "out":
            off_t = r
        elif off_t:
            print(f"  {gc(off_t)} {off_t['score_away']}-{off_t['score_home']}  ->  {gc(r)} {r['score_away']}-{r['score_home']}")
            off_t = None
