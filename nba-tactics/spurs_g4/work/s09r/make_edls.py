"""s09r: lead-in at speed 1 (no AR before tracked frames), freeze at release with ring shrink + note,
short half/quarter-speed release, miss at speed 1 + ~0.4 s tail.  run from spurs_g4/"""
import json, shutil
from pathlib import Path

FZ = 1.4
# ev, pre_from, a_from, release, slow_to, slow_speed, c_to, red_on (src frame), ar_end (src frame), note
CFG = {
    "613": dict(pre=78, a=104, rel=123, sto=133, sspd=0.5, cto=164, red=146, end=157, defk="KT", note="HAND 1.7 FT"),
    "554": dict(pre=48, a=66, rel=93, sto=98, sspd=0.25, cto=117, red=99.5, end=113, defk="MR", note="HAND 2.0 FT"),
}

for ev, c in CFG.items():
    src = Path(f"work/q4miss/e{ev}")
    dst = Path(f"work/s09r/e{ev}")
    (dst / "masks").mkdir(parents=True, exist_ok=True)
    for f in ("cam.json", "players.json"):
        shutil.copy2(src / f, dst / f)
    for p in (src / "masks").glob("*.npz"):
        if not (dst / "masks" / p.name).exists():
            shutil.copy2(p, dst / "masks" / p.name)

    e = json.load(open(f"s09_{ev}_edl.json"))
    e["_note"] = (e["_note"] + f" s09r re-time: lead-in f{c['pre']}-{c['rel']} at speed 1 (no AR before f{c['a']}, "
                  f"the first tracked frame used), {FZ}s freeze at release f{c['rel']} with ring shrink + note, "
                  f"f{c['rel']}-{c['sto']} at {c['sspd']}x, miss at 1x to f{c['cto']}.")
    e["work"] = f"work/s09r/e{ev}"
    e["out"] = f"film/out/s09r/s09r_{ev}.mp4"
    e["segments"] = [
        {"id": "pre", "kind": "play", "from": c["pre"], "to": c["a"], "speed": 1, "audio_db": -14},
        {"id": "a", "kind": "play", "from": c["a"], "to": c["rel"], "speed": 1, "audio_db": -14},
        {"id": "fz", "kind": "freeze", "at": c["rel"], "dur": FZ},
        {"id": "b", "kind": "play", "from": c["rel"], "to": c["sto"], "speed": c["sspd"]},
        {"id": "c", "kind": "play", "from": c["sto"], "to": c["cto"], "speed": 1, "audio_db": -14},
    ]
    red = round((c["red"] - c["sto"]) / 30, 3)
    end = round((c["end"] - c["sto"]) / 30, 3)
    ar_off = f"c+{red + 0.1:.3f}"
    e["layers"] = [
        {"type": "tag", "keys": ["WB"], "on": "a", "off": f"c+{end}"},
        {"type": "ring", "keys": [c["defk"]], "r": 2.0, "on": "a+0.05", "off": f"c+{end}"},
        {"type": "ring", "keys": ["WBA"], "r": 6.0, "on": "fz", "off": "fz+0.35"},
        {"type": "ring", "keys": ["WBA"], "r": 4.6, "on": "fz+0.2", "off": "fz+0.55"},
        {"type": "ring", "keys": ["WBA"], "r": 3.4, "on": "fz+0.4", "off": "fz+0.75"},
        {"type": "ring", "keys": ["WBA"], "r": 2.4, "on": "fz+0.6", "off": ar_off},
        {"type": "ring", "keys": ["WBR"], "r": 2.4, "pulse": True, "on": f"c+{red}", "off": f"c+{end}"},
        {"type": "note", "key": "WB", "text": c["note"], "color": "ar", "on": "fz+0.7", "off": ar_off},
        {"type": "note", "key": "WB", "text": c["note"], "color": "red", "on": f"c+{red}", "off": f"c+{end}"},
    ]
    json.dump(e, open(f"s09r_{ev}_edl.json", "w"), indent=1)
    n = [c["a"] - c["pre"], c["rel"] - c["a"], round(FZ * 30), round((c["sto"] - c["rel"]) / c["sspd"]), c["cto"] - c["sto"]]
    print(ev, n, sum(n), f"{sum(n) / 30:.2f}s")
