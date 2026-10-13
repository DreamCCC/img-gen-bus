"""视频片段 → 成片帧率的 JPEG 序列，供 film.html 按成片时间取帧。
规格 scenes/clips.json：[{name, src, ss, len, out, crop?, grade?}]
  ss/len   素材入点和长度（秒）
  out      输出时长（秒），out > len 即慢放（帧混合补帧）
  crop     ffmpeg crop 参数 "w:h:x:y"
  grade    额外的 ffmpeg 滤镜
python tools/prep_clips.py [名字 ...]
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "scenes/clips.json"
OUT = ROOT / "scenes/clips"


def prep(c):
    d = OUT / c["name"]
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    k = c["out"] / c["len"]
    vf = []
    if c.get("crop"):
        vf.append(f"crop={c['crop']}")
    vf.append("scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080")
    vf.append(f"setpts={k:.6f}*PTS")
    vf.append("minterpolate=fps=30:mi_mode=blend" if k > 1.05 else "fps=30")
    if c.get("grade"):
        vf.append(c["grade"])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(c["ss"]), "-t", str(c["len"]), "-i", str(ROOT / c["src"]),
                    "-vf", ",".join(vf), "-q:v", "3", "-start_number", "0", str(d / "%05d.jpg")], check=True)
    n = len(list(d.glob("*.jpg")))
    print(f"{c['name']:12s} {n} 帧")
    return n


def main():
    spec = json.loads(SPEC.read_text())
    want = set(sys.argv[1:])
    man_p = OUT / "manifest.json"
    man = json.loads(man_p.read_text()) if man_p.exists() else {}
    for c in spec:
        if want and c["name"] not in want:
            continue
        man[c["name"]] = {"n": prep(c)}
    man_p.write_text(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
