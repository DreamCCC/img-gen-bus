import json
import sys

wa, ba = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("9001", "9011")
f0, f1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (140, 285)
a = json.load(open(f"work/e676w/sam_{wa}.json"))
b = json.load(open(f"work/e676w/sam_{ba}.json"))
for f in range(f0, f1 + 1, 3):
    bb = b.get(str(f))
    print(f, "WB", a.get(str(f)), " BR", bb, "h", bb[3] - bb[1] if bb else None)
