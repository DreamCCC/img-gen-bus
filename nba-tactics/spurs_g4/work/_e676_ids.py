import json

fr = json.load(open("work/e676w/tracks.json"))["frames"]
ids = sorted({d["id"] for f in range(0, 286) for d in fr[f] if d["box"][3] > 300})
print(",".join(map(str, ids)))
