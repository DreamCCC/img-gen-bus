import json
import re
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
segs = d["segments"] if isinstance(d, dict) and "segments" in d else d
pat = re.compile(sys.argv[2], re.I)
for s in segs:
    if pat.search(s["text"]):
        print(f"{s['t'][0]:7.2f}-{s['t'][1]:7.2f} {s['text'].strip()}")
