import json
import sys

fr = json.load(open("work/e676w/tracks.json"))["frames"]
ymin = 450
args = sys.argv[1:]
if args and args[0].startswith("y"):
    ymin, args = int(args[0][1:]), args[1:]
for f in [int(x) for x in args]:
    print(f, [(d["id"], [round(v) for v in d["box"]]) for d in fr[f] if d["box"][3] > ymin])
