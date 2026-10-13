"""并行提交万相镜头：python batch.py shots.json [ID ...] [--res 1080P]

shots.json: [{"id", "prompt", "dur", "first": 相对 baby_citypop, "sing": 歌曲起点秒（有则用人声分轨对口型）, "model"}]
输出 wan/<id>.mp4；已存在的跳过。对口型镜头的驱动音频从人声分轨按 sing..sing+dur 切出。
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
TOOL = ROOT.parents[1] / "tools/wan_video.py"
PY = ROOT.parents[1] / "ep01_4.8pct/.venv/bin/python"
VOCALS = ROOT / "stems_suno/htdemucs_ft/pop_1/vocals.wav"
STYLE = "全程保持1980年代后期日本OVA动画电影的手绘赛璐璐画风，人物外貌、发型、服装与首帧完全一致，画面中没有任何文字变化。"

args = sys.argv[1:]
res = args[args.index("--res") + 1] if "--res" in args else "1080P"
args = [a for i, a in enumerate(args) if a != "--res" and (i == 0 or args[i - 1] != "--res")]
spec = HERE / args[0]
want = set(args[1:])
shots = [s for s in json.loads(spec.read_text()) if not want or s["id"] in want]


def run(s):
    out = HERE / f"{s['id']}.mp4"
    if out.exists():
        return s["id"], "exists"
    model = s.get("model") or ("wan2.7-i2v-2026-04-25" if "sing" in s else "wan3.0-video")
    cmd = [str(PY), str(TOOL), str(out), s["prompt"] + STYLE, "--dur", str(s["dur"]), "--res", res, "--model", model,
           "--first", str(ROOT / s["first"])]
    if "sing" in s:
        aud = HERE / "audio" / f"{s['id']}.wav"
        aud.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["sing"]), "-t", str(s["dur"]), "-i", str(VOCALS),
                        "-ac", "1", "-ar", "44100", str(aud)], check=True)
        cmd += ["--audio", str(aud)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return s["id"], (r.stdout.strip().splitlines() or [""])[-1] + r.stderr.strip()[-300:]


with ThreadPoolExecutor(min(4, len(shots))) as ex:
    for sid, msg in ex.map(run, shots):
        print(sid, msg, flush=True)
