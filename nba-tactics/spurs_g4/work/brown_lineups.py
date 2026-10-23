"""G4 下半场：尼克斯阵容 vs 马刺出手、对位、分节三分。
阵容：pbs 首发 + pbp 换人推算；出手质量：shot_detail（event_id = action_number）。"""
import json
import re
from collections import Counter, defaultdict

pbp = sorted(json.load(open("data/pbp.json", encoding="utf-8")), key=lambda r: int(r["order_number"]))
pbs = json.load(open("data/pbs.json", encoding="utf-8"))
sd = {int(s["event_id"]): s for s in json.load(open("data/shot_detail.json", encoding="utf-8"))}
pid_name = {int(p["player_id"]): p["player_name"] for p in pbs}


def short(n):
    f, l = n.split(" ", 1)
    return f"{f[0]}. {l}"


def secs(r):
    m = re.match(r"PT(\d+)M([\d.]+)S", r["clock"])
    return (int(r["period"]) - 1) * 720 + 720 - (int(m.group(1)) * 60 + float(m.group(2)))


def gc(r):
    m = re.match(r"PT(\d+)M([\d.]+)S", r["clock"])
    return f"Q{r['period']} {int(m.group(1)):02d}:{float(m.group(2)):04.1f}"


on = {"SAS": set(), "NYK": set()}
for p in pbs:
    e = json.loads(p["extend_info"]) if p["extend_info"] else {}
    if str(e.get("starter")) == "1":
        on[p["team_abbreviation"]].add(short(p["player_name"]))
print("首发", {k: sorted(v) for k, v in on.items()})

stints, cur, cur_t = [], None, 0
shots = []
for r in pbp:
    if not r.get("clock"):
        continue
    if r.get("action_type") == "substitution":
        (on[r["team_tricode"]].discard if r["sub_type"] == "out" else on[r["team_tricode"]].add)(r["player_name_i"] if r.get("player_name_i") else r["player_name"])
        continue
    if r.get("action_type") == "period" and r.get("sub_type") == "start" and int(r["period"]) == 3:
        pass
    nyk = tuple(sorted(on["NYK"]))
    sas = tuple(sorted(on["SAS"]))
    if r.get("action_type") in ("2pt", "3pt"):
        s = sd.get(int(r["action_number"]))
        hand = float(s["joint_ball_distance"]) / 12 if s and s["joint_ball_distance"] else None
        dfd = pid_name.get(int(s["joint_defenderid"]), "?").split(" ", 1)[-1] if s and s["joint_defenderid"] else "?"
        xfg = float(s["expected_fg"]) if s and s["expected_fg"] else None
        shots.append(dict(r=r, q=int(r["period"]), team=r["team_tricode"], three=r["action_type"] == "3pt",
                          made=r.get("shot_result") == "Made", hand=hand, dfd=dfd, xfg=xfg, nyk=nyk, sas=sas,
                          who=r.get("player_name_i"), dist=r.get("shot_distance")))

print("\n== 马刺每节：FG、三分、预期 vs 实得、平均手离球（英尺，追踪覆盖的出手）==")
for q in (1, 2, 3, 4):
    r = [x for x in shots if x["team"] == "SAS" and x["q"] == q]
    pts = sum((3 if x["three"] else 2) * x["made"] for x in r)
    xr = [x for x in r if x["xfg"] is not None]
    xp = sum((3 if x["three"] else 2) * x["xfg"] for x in xr)
    hr = [x["hand"] for x in r if x["hand"] is not None]
    print(f"  Q{q}: FG {sum(x['made'] for x in r)}/{len(r)}  3P {sum(x['made'] for x in r if x['three'])}/{sum(x['three'] for x in r)}"
          f"  实得 {pts} / 预期 {xp:.1f}（覆盖 {len(xr)}/{len(r)}）  手离球 {sum(hr) / max(1, len(hr)):.2f}")

print("\n== 下半场尼克斯阵容 → 马刺对它的出手 ==")
g = defaultdict(list)
for x in shots:
    if x["team"] == "SAS" and x["q"] >= 3:
        g[x["nyk"]].append(x)
for k, r in sorted(g.items(), key=lambda kv: -len(kv[1])):
    pts = sum((3 if x["three"] else 2) * x["made"] for x in r)
    hr = [x["hand"] for x in r if x["hand"] is not None]
    print(f"  {len(r):2d} 投 {sum(x['made'] for x in r):2d} 中 {pts:2d} 分  3P {sum(x['made'] for x in r if x['three'])}/{sum(x['three'] for x in r)}"
          f"  手离球 {sum(hr)/max(1,len(hr)):.2f}  | {', '.join(k)}")

print("\n== 下半场谁在防马刺的出手（追踪最近防守人）==")
c = Counter(x["dfd"] for x in shots if x["team"] == "SAS" and x["q"] >= 3)
for k, v in c.most_common(10):
    r = [x for x in shots if x["team"] == "SAS" and x["q"] >= 3 and x["dfd"] == k]
    hr = [x["hand"] for x in r if x["hand"] is not None]
    print(f"  {k:14s} {v:2d} 次  被投进 {sum(x['made'] for x in r)}  手离球 {sum(hr)/max(1,len(hr)):.2f}")

print("\n== 下半场文班亚马的出手 ==")
for x in shots:
    if x["team"] == "SAS" and x["q"] >= 3 and x["who"] == "V. Wembanyama":
        print(f"  {gc(x['r'])}  {x['dist']}ft  {'中' if x['made'] else '丢'}  防守 {x['dfd']:12s} 手离球 {x['hand'] or 0:.1f}")

print("\n== 第四节尼克斯出手：谁在防 ==")
for x in shots:
    if x["team"] == "NYK" and x["q"] == 4:
        print(f"  {gc(x['r'])}  {x['who']:14s} {x['dist']}ft {'3P' if x['three'] else '2P'} {'中' if x['made'] else '丢'}"
              f"  防守 {x['dfd']:12s} xFG {x['xfg'] if x['xfg'] is not None else '-'}")

print("\n== 尼克斯球员 ==")
for p in sorted(pbs, key=lambda p: -float(p["min"] or 0)):
    if float(p["min"] or 0) > 0 and p["team_abbreviation"] == "NYK":
        e = json.loads(p["extend_info"]) if p["extend_info"] else {}
        print(f"  {p['player_name']:22s} {float(p['min']):5.1f} min  {p['pts']:>2} pts  reb {p['reb']}  +/- {p['plus_minus']}  "
              f"{'首发' if str(e.get('starter')) == '1' else ''}")
