#!/usr/bin/env python3
"""G4 尼克斯 107-106 马刺：从 data/*.json 打印赛况分析。"""
import json
import re
from collections import defaultdict

D = "data/"
tbs = json.load(open(D + "tbs.json"))
pbs = json.load(open(D + "pbs.json"))
pbp = sorted(json.load(open(D + "pbp.json")), key=lambda r: int(r["order_number"]))


def secs(period, clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    left = int(m.group(1)) * 60 + float(m.group(2))
    p = int(period)
    return (p - 1) * 720 + 720 - left if p <= 4 else 2880 + (p - 5) * 300 + 300 - left


def gclock(period, clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    return f"Q{period} {int(m.group(1)):02d}:{float(m.group(2)):04.1f}"


home = pbs[0]["home_team_id"]
print("home_team_id", home)

print("\n== 球队整体 ==")
keys = ["points", "fieldGoalsMade", "fieldGoalsAttempted", "threePointersMade", "threePointersAttempted",
        "freeThrowsMade", "freeThrowsAttempted", "reboundsOffensive", "reboundsDefensive", "assists",
        "turnoversTotal", "steals", "blocks", "foulsPersonal", "pointsFromTurnovers", "pointsInThePaint",
        "pointsSecondChance", "pointsFastBreak", "benchPoints", "biggestLead", "biggestScoringRun",
        "leadChanges", "timesTied"]
st = {}
for t in tbs:
    st[t["team_abbreviation"]] = json.loads(t["extend_info"])["statistics"]
for k in keys:
    print(f"  {k:24s} SAS {st['SAS'].get(k)!s:>6}   NYK {st['NYK'].get(k)!s:>6}")

print("\n== 球员 ==")
for team in ["SAS", "NYK"]:
    rows = [r for r in pbs if r["team_abbreviation"] == team and r["min"]]
    rows.sort(key=lambda r: -float(r["min"] or 0))
    for r in rows:
        e = json.loads(r["extend_info"]) if r["extend_info"] else {}
        print(f"  {team} {r['player_name_cn'] or '':8s} {r['player_name']:22s} #{e.get('jerseyNum','')!s:3s} "
              f"st{e.get('starter','')} min {float(r['min']):5.1f} pts {r['pts']:>3} "
              f"fg {r['fgm']}/{r['fga']} 3p {r['fg3m']}/{r['fg3a']} ft {r['ftm']}/{r['fta']} "
              f"reb {r['reb']} ast {r['ast']} tov {r['tov']} pf {r['pf']} +/- {r['plus_minus']}")

# 分差时间线（马刺视角）
ev = []
for r in pbp:
    if r.get("score_home") in (None, "") or not r.get("clock"):
        continue
    t = secs(r["period"], r["clock"])
    h, a = int(r["score_home"]), int(r["score_away"])
    sas, nyk = (h, a) if str(home) == "1610612759" else (a, h)
    ev.append((t, sas, nyk, r))
print("\nSAS is home?", str(home) == "1610612759")

print("\n== 分节比分 ==")
q = defaultdict(lambda: [0, 0])
prev = (0, 0)
for t, s, n, r in ev:
    p = int(r["period"])
    q[p][0] += s - prev[0]
    q[p][1] += n - prev[1]
    prev = (s, n)
for p in sorted(q):
    print(f"  Q{p}: SAS {q[p][0]}  NYK {q[p][1]}")

print("\n== 每 3 分钟分差采样 ==")
for mark in range(0, 2881, 180):
    last = [e for e in ev if e[0] <= mark]
    s, n = (last[-1][1], last[-1][2]) if last else (0, 0)
    print(f"  {mark//60:3d}min  SAS {s:3d} NYK {n:3d}  diff {s-n:+d}")

peak = max(ev, key=lambda e: e[1] - e[2])

print("\n== 最大领先之后的每次得分 ==")
prev = (peak[1], peak[2])
for t, s, n, r in ev:
    if t < peak[0] or (s, n) == prev:
        continue
    prev = (s, n)
    print(f"  {gclock(r['period'], r['clock'])}  SAS {s:3d}-{n:<3d} NYK  {s-n:+3d}  {r.get('team_tricode','')} {r.get('description','')}")

print("\n== 第四节最后 4 分钟全部事件 ==")
for r in pbp:
    if r.get("clock") and int(r["period"]) == 4 and secs(r["period"], r["clock"]) >= 2880 - 240 \
            and r.get("action_type") != "substitution":
        print(f"  {gclock(r['period'], r['clock'])}  {r.get('score_away')}-{r.get('score_home')}  "
              f"{r.get('team_tricode','')} {r.get('action_type')} {r.get('description','')}")

print("\n马刺最大领先:", gclock(peak[3]["period"], peak[3]["clock"]), peak[1], peak[2])


def phase_stats(t0, t1, label):
    agg = {k: defaultdict(int) for k in ["SAS", "NYK"]}
    for r in pbp:
        if not r.get("clock") or r.get("team_tricode") not in agg:
            continue
        t = secs(r["period"], r["clock"])
        if not (t0 < t <= t1):
            continue
        a = agg[r["team_tricode"]]
        at = r["action_type"]
        if at in ("2pt", "3pt"):
            a["fga"] += 1
            a["3pa"] += at == "3pt"
            if r["shot_result"] == "Made":
                a["fgm"] += 1
                a["3pm"] += at == "3pt"
        elif at == "freethrow":
            a["fta"] += 1
            a["ftm"] += r["shot_result"] == "Made"
        elif at == "turnover":
            a["tov"] += 1
        elif at == "rebound" and r["sub_type"] == "offensive":
            a["oreb"] += 1
        elif at == "foul":
            a["pf"] += 1
    s0 = [e for e in ev if e[0] <= t0]
    s1 = [e for e in ev if e[0] <= t1]
    b0 = (s0[-1][1], s0[-1][2]) if s0 else (0, 0)
    b1 = (s1[-1][1], s1[-1][2])
    print(f"\n-- {label}: 比分 {b0[0]}-{b0[1]} -> {b1[0]}-{b1[1]}  (SAS {b1[0]-b0[0]} NYK {b1[1]-b0[1]})")
    for k, a in agg.items():
        print(f"   {k} FG {a['fgm']}/{a['fga']} 3P {a['3pm']}/{a['3pa']} FT {a['ftm']}/{a['fta']} "
              f"TOV {a['tov']} OREB {a['oreb']} PF {a['pf']}")


phase_stats(0, peak[0], "开场到马刺最大领先")
phase_stats(peak[0], 1440, "最大领先到半场")
phase_stats(1440, 2160, "第三节")
phase_stats(2160, 2880, "第四节")
phase_stats(2880 - 300, 2880, "最后 5 分钟")
json.dump([{"t": e[0], "sas": e[1], "nyk": e[2]} for e in ev], open(D + "timeline.json", "w"))
