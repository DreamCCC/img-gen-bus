"""G4 下半场尼克斯每段阵容的时长与得失分（尼克斯主队：score_home=NYK）。"""
import json
import re

pbp = sorted(json.load(open("data/pbp.json", encoding="utf-8")), key=lambda r: int(r["order_number"]))
pbs = json.load(open("data/pbs.json", encoding="utf-8"))


def secs(r):
    m = re.match(r"PT(\d+)M([\d.]+)S", r["clock"])
    return (int(r["period"]) - 1) * 720 + 720 - (int(m.group(1)) * 60 + float(m.group(2)))


def clk(t):
    q, s = int(t // 720) + 1, 720 - t % 720
    return f"Q{q} {int(s // 60):02d}:{s % 60:04.1f}"


on = set()
for p in pbs:
    e = json.loads(p["extend_info"]) if p["extend_info"] else {}
    if p["team_abbreviation"] == "NYK" and str(e.get("starter")) == "1":
        f, l = p["player_name"].split(" ", 1)
        on.add(f"{f[0]}. {l}")

stints, start, s0, last = [], 0.0, (0, 0), (0, 0)
for r in pbp:
    if not r.get("clock"):
        continue
    t = secs(r)
    if start < 1440 <= t:
        stints.append((start, 1440.0, tuple(sorted(on)), s0, last))
        start, s0 = 1440.0, last
    if r.get("score_home") not in (None, ""):
        last = (int(r["score_home"]), int(r["score_away"]))
    if r.get("action_type") == "substitution" and r["team_tricode"] == "NYK":
        if t > start:
            stints.append((start, t, tuple(sorted(on)), s0, last))
            start, s0 = t, last
        (on.discard if r["sub_type"] == "out" else on.add)(r["player_name_i"] or r["player_name"])
stints.append((start, 2880.0, tuple(sorted(on)), s0, last))

print("== 尼克斯下半场每段阵容（时段 | 时长 | 尼克斯-马刺 分段比分 | 阵容）==")
agg = {}
for a, b, five, (h0, a0), (h1, a1) in stints:
    if b <= 1440:
        continue
    a = max(a, 1440)
    dn, ds = h1 - h0, a1 - a0
    print(f"  {clk(a)} → {clk(b)}  {(b - a) / 60:4.1f}min  {dn:2d}-{ds:2d}  ({dn - ds:+d})  {', '.join(five)}")
    k = agg.setdefault(five, [0, 0, 0])
    k[0] += b - a; k[1] += dn; k[2] += ds
h_half = next(s for s in stints if s[0] >= 1440)[3]
print(f"\n中场 尼克斯 {h_half[0]} - 马刺 {h_half[1]}；终场 尼克斯 {last[0]} - 马刺 {last[1]}；"
      f"下半场 {last[0] - h_half[0]} - {last[1] - h_half[1]}")
print("\n== 汇总（下半场，按时长）==")
for five, (d, n, s) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {d / 60:4.1f}min  {n:2d}-{s:2d} ({n - s:+d})  {', '.join(five)}")
