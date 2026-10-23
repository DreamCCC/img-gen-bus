"""Which Spurs shots have a single-play DB clip: data/item_info.json x data/pbp.json x data/shot_detail.json."""
import json

L = lambda p: json.load(open(p, encoding="utf-8"))
items, pbp, sd = L("data/item_info.json"), L("data/pbp.json"), L("data/shot_detail.json")
by_ev = {}
for c in items:
    if str(c.get("event_id") or "") and str(c.get("game") or "") == "0042500404":
        by_ev.setdefault(str(c["event_id"]), []).append(c)
xf = {str(r["event_id"]): r for r in sd}
rows = []
for s in pbp:
    if s["is_field_goal"] != 1 or s["team_tricode"] != "SAS":
        continue
    ev = str(s["action_number"])
    c = sorted(by_ev.get(ev, []), key=lambda c: str(c["id"]))
    x = xf.get(ev, {})
    three = "3PT" in s["description"]
    rows.append(dict(ev=int(ev), p=s["period"], clock=s["clock"], who=s["player_name"], res=s["shot_result"], three=three,
                     xfg=x.get("expected_fg"), hand_ft=round(x["joint_ball_distance"] / 12, 2) if x.get("joint_ball_distance") else None,
                     clip=str(c[-1]["id"]) if c else None, dur=c[-1].get("duration") if c else None, desc=s["description"]))
json.dump(rows, open("work/full_footage.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"items with event_id: {sum(len(v) for v in by_ev.values())}; Spurs FGA {len(rows)}, with clip {sum(1 for r in rows if r['clip'])}")
for r in rows:
    if (r["p"] <= 2 and r["three"]) or r["p"] >= 3:
        print(r["ev"], r["p"], r["clock"][2:], r["who"], r["res"], "3" if r["three"] else "2", r["xfg"], r["hand_ft"], r["clip"], r["dur"])
