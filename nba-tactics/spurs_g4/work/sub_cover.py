"""Report ASR speech segments not covered by any caption. usage: python sub_cover.py film.ass asr.json"""
import json
import re
import sys

def ts(s):
    h, m, x = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(x)

caps = []
for line in open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"Dialogue: \d+,([^,]+),([^,]+),Cap,", line)
    if m:
        caps.append((ts(m.group(1)), ts(m.group(2))))
for seg in json.load(open(sys.argv[2], encoding="utf-8")):
    a, b = seg["t"]
    cov = sum(max(0, min(b, y) - max(a, x)) for x, y in caps)
    if cov < 0.6 * (b - a):
        print(f"UNCOVERED {a:7.2f}-{b:7.2f} ({cov:.2f}s covered) {seg['text']}")
print(f"{len(caps)} captions checked")
