"""按 edl.json 渲染 MV：取素材 → 代码叠层 → 调色 → 字幕 → 编码，多进程分段，最后拼接并配歌。

python render.py [--from 秒] [--to 秒] [--jobs N] [--out 文件名] [--nosubs]

edl.json:
  shots:    [{t0, t1, look, src}]，src 之一：
            {"kind": "scene", "name": comps.scene_<name>, "args": {...}}
            {"kind": "video", "path": 相对 baby_citypop, "start": 素材秒（对应 t0）, "speed": 1, "fit": "cover"|"contain", "crop": [x,y,w,h] 比例, "loop": 秒?}
            {"kind": "image", "path": ..., "zoom": [z0, z1], "pan": [x, y]}
            {"kind": "grid", "cells": [9 个 src], "reveal": [9 个歌曲时间，null 为一开始就在], "labels": [9 个字符串]}
  overlays: [{t0, t1, name: comps.overlay_<name>, args}]
"""
import argparse
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "look"))
import comps  # noqa: E402
from comps import H, W  # noqa: E402
from grade import grade  # noqa: E402

FPS = 30


class Reader:
    """顺序读视频帧；请求的帧号只能递增，读到结尾后保持最后一帧。"""

    def __init__(self, path, start=0.0, speed=1.0, fit="cover", crop=None, size=(W, H)):
        self.size = size
        w, h = size
        vf = []
        if crop:
            x, y, cw, ch = crop
            vf.append(f"crop=iw*{cw}:ih*{ch}:iw*{x}:ih*{y}")
        if speed != 1:
            vf.append(f"setpts=PTS/{speed}")
        vf.append(f"fps={FPS}")
        if fit == "cover":
            vf.append(f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=bicubic,crop={w}:{h}")
        else:
            vf.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=bicubic,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-i", str(ROOT / path), "-vf", ",".join(vf),
               "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.idx, self.last = -1, np.zeros((h, w, 3), np.float32)

    def read(self, k):
        n = self.size[0] * self.size[1] * 3
        while self.idx < k:
            buf = self.p.stdout.read(n) if self.p else b""
            if len(buf) < n:
                self.close()
                self.idx = k
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(self.size[1], self.size[0], 3).astype(np.float32) / 255
            self.idx += 1
        return self.last

    def close(self):
        if self.p:
            self.p.kill()
            self.p.wait()
            self.p = None


class Source:
    def __init__(self, src, t0, size=(W, H)):
        self.src, self.t0, self.size, self.reader = src, t0, size, None

    def frame(self, T, ctx):
        s, k = self.src, int(round((T - self.t0) * FPS))
        kind = s["kind"]
        if kind == "video":
            if s.get("loop"):
                k %= max(1, int(s["loop"] * FPS))
                if self.reader is not None and k < self.reader.idx:
                    self.reader.close()
                    self.reader = None
            if self.reader is None:
                self.reader = Reader(s["path"], s.get("start", 0.0), s.get("speed", 1.0), s.get("fit", "cover"), s.get("crop"), self.size)
            return self.reader.read(k)
        if kind == "image":
            img = comps.scene_image(ctx, str(ROOT / s["path"]), tuple(s.get("zoom", (1.0, 1.06))), tuple(s.get("pan", (0, 0))))
            return _resize(img, self.size)
        if kind == "scene":
            args = dict(s.get("args", {}))
            for key in ("path",):
                if key in args:
                    args[key] = str(ROOT / args[key])
            if "textures" in args:
                args["textures"] = [_tex(p) for p in args["textures"]]
            return _resize(getattr(comps, "scene_" + s["name"])(ctx, **args), self.size)
        raise ValueError(kind)

    def close(self):
        if self.reader:
            self.reader.close()


def _resize(img, size):
    if img.shape[1] == size[0] and img.shape[0] == size[1]:
        return img
    from PIL import Image
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize(size, Image.BILINEAR)
    return np.asarray(im, np.float32) / 255


_TEX = {}


def _tex(p):
    if p not in _TEX:
        from PIL import Image
        im = Image.open(ROOT / p).convert("RGB").resize((480, 480), Image.BILINEAR) if not p.endswith(".mp4") else None
        if im is None:
            r = Reader(p, 1.0, size=(480, 480))
            _TEX[p] = r.read(0).copy()
            r.close()
        else:
            _TEX[p] = np.asarray(im, np.float32) / 255
    return _TEX[p]


class Grid:
    CW, CH, GAP = 640, 360, 6

    def __init__(self, src, t0):
        self.cells = [Source(c, t0, (self.CW - 2 * self.GAP, self.CH - 2 * self.GAP)) if c else None for c in src["cells"]]
        self.reveal = src.get("reveal") or [None] * 9
        self.labels = src.get("labels") or [""] * 9

    def frame(self, T, ctx):
        out = comps.scene_grid_wall(ctx)
        for k, c in enumerate(self.cells):
            if c is None:
                continue
            r = self.reveal[k]
            gx, gy = (k % 3) * self.CW + self.GAP, (k // 3) * self.CH + self.GAP
            if r is not None and T < r:
                out[gy:gy + self.CH - 2 * self.GAP, gx:gx + self.CW - 2 * self.GAP] = _snow_cell(self.CW - 2 * self.GAP, self.CH - 2 * self.GAP, k, ctx.seed)
                continue
            img = c.frame(T, ctx)
            p = 1.0 if r is None else comps.ease_out((T - r) / 0.18)
            ch = max(1, int(img.shape[0] * p))
            y0 = gy + (img.shape[0] - ch) // 2
            out[y0:y0 + ch, gx:gx + img.shape[1]] = img[(img.shape[0] - ch) // 2:(img.shape[0] - ch) // 2 + ch]
            if self.labels[k] and p >= 1:
                out[gy:gy + img.shape[0], gx:gx + img.shape[1]] = _label(out[gy:gy + img.shape[0], gx:gx + img.shape[1]], self.labels[k])
            if k == 4:
                out[gy - self.GAP:gy, gx - self.GAP:gx + img.shape[1] + self.GAP] = np.array(comps.PINK) / 255
                out[gy + img.shape[0]:gy + img.shape[0] + self.GAP, gx - self.GAP:gx + img.shape[1] + self.GAP] = np.array(comps.PINK) / 255
                out[gy:gy + img.shape[0], gx - self.GAP:gx] = np.array(comps.PINK) / 255
                out[gy:gy + img.shape[0], gx + img.shape[1]:gx + img.shape[1] + self.GAP] = np.array(comps.PINK) / 255
        return out

    def close(self):
        for c in self.cells:
            if c:
                c.close()


_LBL = {}
_CH = {}


def _snow_cell(w, h, k, seed):
    """没翻开的格子：老电视雪花 + 左上角频道号。"""
    from PIL import Image, ImageDraw
    if k not in _CH:
        lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((18, 14), f"CH {k + 1}", font=comps.font("osd", 34), fill=(60, 255, 110, 255),
                                 stroke_width=3, stroke_fill=(0, 40, 0, 255))
        _CH[k] = np.asarray(lay, np.float32) / 255
    rng = np.random.default_rng(seed * 9 + k)
    n = rng.random((h // 2, w // 2), dtype=np.float32)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)[:h, :w]
    img = np.repeat(n[..., None], 3, 2) * 0.55 + 0.05
    a = _CH[k][..., 3:]
    return img * (1 - a) + _CH[k][..., :3] * a


def _label(cell, text):
    from PIL import Image, ImageDraw
    key = (text, cell.shape[1], cell.shape[0])
    if key not in _LBL:
        lay = Image.new("RGBA", (cell.shape[1], cell.shape[0]), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.text((14, cell.shape[0] - 12), text, font=comps.font("maru", 24), fill=(255, 255, 255, 235), anchor="ld",
               stroke_width=3, stroke_fill=(0, 0, 0, 220))
        _LBL[key] = np.asarray(lay, np.float32) / 255
    a = _LBL[key][..., 3:]
    return cell * (1 - a) + _LBL[key][..., :3] * a


def audio_env():
    import soundfile as sf
    y, sr = sf.read(ROOT / "suno/pop_1.wav", dtype="float32")
    y = y.mean(1) if y.ndim > 1 else y
    hop = sr // FPS
    n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    rms = rms / (np.percentile(rms, 95) + 1e-6)
    return np.clip(rms, 0, 1)


def render_range(job):
    k0, k1, seg, edl, nosubs = job
    import cv2
    cv2.setNumThreads(1)
    env = audio_env()
    shots, ovs = edl["shots"], edl["overlays"]
    track = None
    if not nosubs:
        from subtrack import SubTrack, over
        track = SubTrack()
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "40M", "-bufsize", "80M",
           "-pix_fmt", "yuv420p", str(seg)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    live = {}
    for k in range(k0, k1):
        T = k / FPS
        si = next((i for i, s in enumerate(shots) if s["t0"] <= T < s["t1"]), None)
        for i in [i for i in live if i != si]:
            live.pop(i).close()
        ctx = SimpleNamespace(T=T, beats=edl["beats"], env=lambda t: float(env[min(len(env) - 1, int(t * FPS))]), seed=k)
        if si is None:
            img = np.zeros((H, W, 3), np.float32)
            look = "film89"
        else:
            s = shots[si]
            if si not in live:
                live[si] = Grid(s["src"], s["t0"]) if s["src"]["kind"] == "grid" else Source(s["src"], s["t0"])
            ctx.t, ctx.d = T - s["t0"], s["t1"] - s["t0"]
            img = live[si].frame(T, ctx).copy()
            look = s.get("look", "film89")
        for o in ovs:
            if o["t0"] <= T < o["t1"]:
                octx = SimpleNamespace(**{**vars(ctx), "t": T - o["t0"], "d": o["t1"] - o["t0"]})
                lay = getattr(comps, "overlay_" + o["name"])(octx, **o.get("args", {}))
                a = lay[..., 3:]
                img = img * (1 - a) + lay[..., :3] * a
        img = grade(np.clip(img, 0, 1), look, seed=k)
        if track:
            img = over(img, track.patches(T))
        enc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    for v in live.values():
        v.close()
    enc.stdin.close()
    enc.wait()
    return seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="t_from", type=float, default=0)
    ap.add_argument("--to", dest="t_to", type=float)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default="mv_v1.mp4")
    ap.add_argument("--nosubs", action="store_true")
    a = ap.parse_args()
    edl = json.loads((HERE / "edl.json").read_text())
    t_to = a.t_to if a.t_to is not None else edl["dur"]
    k0, k1 = int(a.t_from * FPS), int(t_to * FPS)
    segdir = HERE / "segs"
    segdir.mkdir(exist_ok=True)
    n = a.jobs
    step = math.ceil((k1 - k0) / n)
    jobs = [(k0 + i * step, min(k1, k0 + (i + 1) * step), segdir / f"seg{i:02d}.mp4", edl, a.nosubs) for i in range(n) if k0 + i * step < k1]
    with Pool(len(jobs)) as pool:
        segs = pool.map(render_range, jobs)
    lst = segdir / "list.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    out = ROOT / "out" / a.out
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                           "-ss", f"{a.t_from:.3f}", "-t", f"{(k1 - k0) / FPS:.3f}", "-i", str(ROOT / "suno/pop_1.wav"),
                           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest",
                           "-movflags", "+faststart", str(out)])
    print(out)


if __name__ == "__main__":
    main()
