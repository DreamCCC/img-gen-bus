"""Write spurs_g4/s09_{554,593,613}_edl.json from one template (run from spurs_g4/)."""
import json

BASE = json.load(open("s09_613_edl.json", encoding="utf-8"))

CLIPS = {
    "554": dict(
        note="Shot 9 clip B: PBP 554, Q4 11:48 (scorebug 11:49/13 -> 11:48/12), Wembanyama 4' driving layup MISS. "
             "NGSS shot_detail event 554: defensiveInfo.jointBallDistance 23.959 in = 2.00 ft (closest joint lPinky, defender Mitchell Robinson #23). "
             "Release ~f92-94 behind Robinson, ball off the rim ~f100-102. f100 broadcast flash replaced by the f99/f101 average.",
        slow_from=84, rim=[84, 632, 334], hand="HAND 2.0 FT", defender="MR", dname="ROBINSON",
        segs=[(64, 88, 1), (88, 96, 0.5), (96, 112, 1)],
        rings=[(6.0, "a+0.25", "a+0.6"), (4.6, "a+0.45", "a+0.8"), (3.4, "a+0.65", "b+0.2"), (2.4, "b+0.05", "c+0.25")],
        note_on="a+0.6", red_on="c+0.15", gold_off="c+0.25"),
    "593": dict(
        note="Shot 9 clip C: PBP 593, Q4 9:38 (scorebug 9:39 / shot clock 7), Wembanyama 1' driving floater MISS. "
             "NGSS shot_detail event 593: defensiveInfo.jointBallDistance 20.29 in = 1.69 ft (closest joint lPinky, defender Jalen Brunson #11, "
             "not identifiable in frame, so no defender ring). Release ~f90, ball off the rim ~f98-100. f82 broadcast flash replaced by the f81/f83 average.",
        slow_from=84, rim=[80, 647, 275], hand="HAND 1.7 FT", defender=None,
        segs=[(66, 86, 1), (86, 94, 0.5), (94, 110, 1)],
        rings=[(6.0, "a+0.1", "a+0.45"), (4.6, "a+0.3", "a+0.65"), (3.4, "a+0.5", "b+0.15"), (2.4, "b", "c+0.25")],
        note_on="a+0.45", red_on="c+0.12", gold_off="c+0.25"),
    "613": dict(
        note=BASE["_note"],
        slow_from=114, rim=[105, 516, 262], hand="HAND 1.7 FT", defender="KT", dname="TOWNS",
        segs=[(104, 118, 1), (118, 130, 0.5), (130, 156, 1)],
        rings=[(6.0, "a+0.2", "a+0.56"), (4.6, "a+0.38", "a+0.74"), (3.4, "a+0.56", "a+0.92"), (2.4, "a+0.74", "c+0.62")],
        note_on="b", red_on="c+0.5", gold_off="c+0.62"),
}

for ev, c in CLIPS.items():
    e = json.loads(json.dumps(BASE))
    w = f"work/q4miss/e{ev}"
    e["_note"] = c["note"] + " Rings shrink around the shooter in steps (ring layers; their radius is graphic, not a measurement); the only number on screen is the NGSS value. No VO; the s09 concat lays the reel's original audio at -14 dB."
    e.update(work=w, orig=f"{w}/fr/orig", audio_src=f"work/q4miss/e{ev}.wav", out=f"film/out/s09/s09_{ev}.mp4")
    e["slow"] = {"dir": f"{w}/fr/slow", "from": c["slow_from"], "mul": 4}
    e["anchors"] = {"rim": c["rim"]}
    e["style"] = {"WB": "gold", "WBA": "ar", "WBR": "red"}
    e["names"] = {"WB": "WEMBANYAMA", "WBA": "WEMBANYAMA", "WBR": "WEMBANYAMA"}
    if c["defender"]:
        e["style"][c["defender"]] = "def"
        e["names"][c["defender"]] = c["dname"]
    e["segments"] = [
        {"id": i, "kind": "play", "from": a, "to": b, "speed": sp, **({"audio_db": -14} if sp == 1 else {})}
        for i, (a, b, sp) in zip("abc", c["segs"])]
    L = [{"type": "tag", "keys": ["WB"], "on": "a"}]
    if c["defender"]:
        L.append({"type": "ring", "keys": [c["defender"]], "r": 2.0, "on": "a+0.05"})
    L += [{"type": "ring", "keys": ["WBA"], "r": r, "on": on, "off": off} for r, on, off in c["rings"]]
    L += [{"type": "ring", "keys": ["WBR"], "r": 2.4, "pulse": True, "on": c["red_on"]},
          {"type": "note", "key": "WB", "text": c["hand"], "color": "ar", "on": c["note_on"], "off": c["gold_off"]},
          {"type": "note", "key": "WB", "text": c["hand"], "color": "red", "on": c["red_on"]}]
    e["layers"] = L
    open(f"s09_{ev}_edl.json", "w", encoding="utf-8", newline="\n").write(json.dumps(e, ensure_ascii=False, indent=1) + "\n")
    print(ev, "ok")
