"""Hart (#3) is not detected at f30 (far baseline, legs behind a Spurs player). Adds a hand-read box as track 9103
for f29-31 to work/e676w/tracks.json (original YOLO tracks are in tracks_yolo.json)."""
import json

p = "work/e676w/tracks.json"
T = json.load(open(p))
for f in (29, 30, 31):
    T["frames"][f] = [d for d in T["frames"][f] if d["id"] != 9103]
    T["frames"][f].append({"id": 9103, "box": [1100.0, 262.0, 1162.0, 384.0], "conf": 1.0, "team": "NYK"})
json.dump(T, open(p, "w"))
print("ok")
