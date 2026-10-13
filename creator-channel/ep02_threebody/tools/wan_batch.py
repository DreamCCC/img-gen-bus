"""并行提交一批万相镜头：python tools/wan_batch.py assets/wan/shots.json [W01 W02 ...] [--res 1080P] [--tag v1]
输出 assets/wan/<id>_<tag>.mp4；已存在的跳过。首帧路径相对 shots.json 所在目录。"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT.parent / "tools/wan_video.py"
PY = ROOT.parent / "ep01_4.8pct/.venv/bin/python"

args = sys.argv[1:]
res = args[args.index("--res") + 1] if "--res" in args else "1080P"
tag = args[args.index("--tag") + 1] if "--tag" in args else "v1"
args = [a for i, a in enumerate(args) if a not in ("--res", "--tag") and (i == 0 or args[i - 1] not in ("--res", "--tag"))]
spec = ROOT / args[0]
want = set(args[1:])
shots = [s for s in json.loads(spec.read_text()) if not want or s["id"] in want]


def run(s):
    out = spec.parent / f"{s['id']}_{tag}.mp4"
    if out.exists():
        return s["id"], "exists"
    cmd = [str(PY), str(TOOL), str(out), s["prompt"], "--dur", str(s["dur"]), "--res", res]
    for k in ("first", "last"):
        if s.get(k):
            cmd += [f"--{k}", str(spec.parent / s[k])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return s["id"], (r.stdout.strip().splitlines() or [""])[-1] + r.stderr.strip()[-300:]


with ThreadPoolExecutor(len(shots)) as ex:
    for sid, msg in ex.map(run, shots):
        print(sid, msg, flush=True)
