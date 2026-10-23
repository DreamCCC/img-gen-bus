"""C6 foul-to-give facts, derived from spurs_g4/data/pbp.json + pbs.json.

Prints the SAS Q4 team-foul log, the NYK five on the floor for the 0:05.7 inbound
(tracked through every substitution of the game), and each player's 3PT line in
this game *before* the final play (pbp shots up to and including 0:05.7).
"""
import json
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"
pbp = json.loads((DATA / "pbp.json").read_text(encoding="utf-8"))
pbs = json.loads((DATA / "pbs.json").read_text(encoding="utf-8"))
pbp.sort(key=lambda r: int(r["order_number"]))


def secs(clock):
    m = re.match(r"PT(\d+)M([\d.]+)S", clock)
    return int(m.group(1)) * 60 + float(m.group(2))


def fmt(clock):
    s = secs(clock)
    return f"{int(s // 60)}:{s % 60:04.1f}" if s < 60 else f"{int(s // 60)}:{int(s % 60):02d}"


players = {}
for r in pbs:
    e = json.loads(r["extend_info"])
    players[e["nameI"]] = {"name": r["player_name"], "team": r["team_abbreviation"], "jersey": e["jerseyNum"],
                           "starter": e["starter"] == "1", "pos": e["position"], "box_3pm": r["fg3m"], "box_3pa": r["fg3a"]}

out = {"game_id": "0042500404"}

# --- SAS Q4 team fouls
fouls = []
for r in pbp:
    if r["period"] == "4" and r.get("action_type") == "foul" and r.get("team_tricode") == "SAS":
        fouls.append({"event": r["action_number"], "clock": fmt(r["clock"]), "desc": r["description"],
                      "qualifiers": r.get("qualifiers", ""), "score": f"SAS {r['score_away']} NYK {r['score_home']}"})
out["sas_q4_fouls"] = fouls

# --- NYK lineup tracking through the whole game
on = {p for p, v in players.items() if v["team"] == "NYK" and v["starter"]}
assert len(on) == 5
lineup_at = None
for r in pbp:
    if r.get("action_type") == "substitution" and r.get("team_tricode") == "NYK":
        who = r["player_name_i"]
        if r["sub_type"] == "out":
            assert who in on, (r["action_number"], who, on)
            on.discard(who)
        else:
            on.add(who)
    if r["action_number"] == 724:
        lineup_at = sorted(on)
    if r["action_number"] == 725:
        assert len(on) == 5
        out["nyk_on_floor_at_725"] = sorted(on)
out["nyk_on_floor_0_05_7"] = lineup_at
out["nyk_on_floor_final"] = sorted(on)

# --- 3PT lines up to the inbound (exclude event 725 Brunson miss and later)
three = {p: [0, 0] for p in lineup_at}
for r in pbp:
    if int(r["action_number"]) >= 725 and r["period"] == "4":
        break
    if r.get("action_type") == "3pt" and r.get("player_name_i") in three:
        three[r["player_name_i"]][1] += 1
        if r.get("shot_result") == "Made":
            three[r["player_name_i"]][0] += 1
out["nyk_3pt_before_final_play"] = {
    p: {"name": players[p]["name"], "jersey": players[p]["jersey"], "3pm": m, "3pa": a,
        "box_final_3pm": players[p]["box_3pm"], "box_final_3pa": players[p]["box_3pa"]}
    for p, (m, a) in three.items()}

# --- context rows
for n in (716, 718, 720, 721, 722, 723, 724, 725, 727):
    r = next(x for x in pbp if x["action_number"] == n and x["period"] == "4")
    out.setdefault("rows", []).append({"event": n, "clock": fmt(r["clock"]), "team": r.get("team_tricode", ""),
                                       "desc": r["description"], "score": f"SAS {r['score_away']} NYK {r['score_home']}"})

print(json.dumps(out, indent=1, ensure_ascii=False))
