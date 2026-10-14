"""真人片段预处理：按规格裁切、可选 RIFE 补帧、按时间映射变速、调色锐化，输出成片帧率的 JPEG 序列。
页面 film.html 按成片时间取第 k 帧绘制，所以这里输出的帧数 = 槽位时长 × 30。

规格（clips_h.json 的一项）：
  name    输出目录 scenes/clips/<name>/
  src     素材路径
  t0, t1  素材入出点（秒）
  crop    [x, y, w, h] 素材像素；省略则整帧
  size    [w, h] 输出尺寸
  dur     槽位时长（秒）
  map     [[成片相对秒, 素材相对秒], ...] 分段线性时间映射；省略则把 t0..t1 均匀拉伸到 dur
  rife    补帧倍数（0 或 4）；慢于 0.5 倍速时建议 4
  grade   fx.grade 参数；mono 为去色比例；false 表示原样输出（已调色的成片，如战术拆解）
  sharpen 锐化强度
用法：python tools/prep_clip.py clips_h.json [名字 ...] [-j并行数]
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

import fx

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
TMP = ROOT / "out/clip_tmp"
TMP.mkdir(parents=True, exist_ok=True)


class Reader:
    """顺序读取并缓存最近的帧，支持按小数帧号做线性混合。"""

    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.buf, self.next = {}, 0

    def get(self, i):
        i = int(np.clip(i, 0, self.n - 1))
        while self.next <= i:
            ok, f = self.cap.read()
            if not ok:
                self.n = self.next
                break
            self.buf[self.next] = f
            self.next += 1
        for k in [k for k in self.buf if k < i - 2]:
            del self.buf[k]
        return self.buf.get(i, self.buf[max(self.buf)])

    def at(self, q):
        i = int(np.floor(q))
        a = q - i
        f0 = self.get(i).astype(np.float32)
        if a < 1e-3:
            return f0 / 255
        return (f0 * (1 - a) + self.get(i + 1).astype(np.float32) * a) / 255


def extract(spec):
    w, h = spec["size"]
    vf = [f"fps={FPS}"]
    if spec.get("crop"):
        x, y, cw, ch = spec["crop"]
        vf.append(f"crop={cw}:{ch}:{x}:{y}")
    vf += [f"scale={w}:{h}:flags=lanczos", f"setpts=N/{FPS}/TB"]
    dst = TMP / f"{spec['name']}_src.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(spec["t0"]), "-to", str(spec["t1"]),
                    "-i", str(ROOT / spec["src"]), "-vf", ",".join(vf), "-r", str(FPS), "-fps_mode", "cfr",
                    "-an", "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", str(dst)], check=True)
    if spec.get("rife"):
        x4 = TMP / f"{spec['name']}_x{spec['rife']}.mp4"
        subprocess.run([str(ROOT / ".venv/bin/venhance"), "interp", str(dst), "-o", str(x4), "--factor", str(spec["rife"]),
                        "--codec", "h264", "--quality", "92", "--scene-threshold", "0"], check=True)
        return x4, FPS * spec["rife"]
    return dst, FPS


def process(spec):
    path, sfps = extract(spec)
    rd = Reader(path)
    n_out = round(spec["dur"] * FPS)
    span = spec["t1"] - spec["t0"]
    km = np.array(spec.get("map") or [[0, 0], [spec["dur"], span]], np.float64)
    g = spec.get("grade", {})
    mono = g.pop("mono", 0) if isinstance(g, dict) else 0
    out = ROOT / "scenes/clips" / spec["name"]
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    for k in range(n_out):
        s = float(np.interp(k / FPS, km[:, 0], km[:, 1]))
        img = rd.at(min(s * sfps, rd.n - 1.001))
        if g is not False:
            sh = spec.get("sharpen", 0.6)
            if sh:
                img = np.clip(img + (img - cv2.GaussianBlur(img, (0, 0), 2.0)) * sh, 0, 1)
            img = fx.grade(img, **{"contrast": 1.22, "sat": 1.05, "bloom": 0.3, **g})
            if mono:
                grey = img.mean(axis=2, keepdims=True)
                img = img * (1 - mono) + grey * mono
        cv2.imwrite(str(out / f"{k:05d}.jpg"), (np.clip(img, 0, 1) * 255).astype(np.uint8),
                    [cv2.IMWRITE_JPEG_QUALITY, 95 if g is False else 93])
    return {"n": n_out, "w": spec["size"][0], "h": spec["size"][1]}


def _run(spec):
    return spec["name"], process(dict(spec))


if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor
    args = [a for a in sys.argv[2:] if not a.startswith("-j")]
    jobs = next((int(a[2:]) for a in sys.argv[2:] if a.startswith("-j")), 1)
    specs = json.loads((ROOT / sys.argv[1]).read_text())
    only = set(args)
    man_path = ROOT / "scenes/clips/manifest.json"
    todo = [s for s in specs if not only or s["name"] in only]
    with ProcessPoolExecutor(jobs) as ex:
        for name, info in ex.map(_run, todo):
            man = json.loads(man_path.read_text()) if man_path.exists() else {}
            man[name] = info
            man_path.write_text(json.dumps(man, indent=1))
            print("clip", name, info, flush=True)
