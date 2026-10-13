"""整首歌的字幕轨：按 suno/pop_1_timeline.json 逐句显示，日文逐字变色。

样式分工：テロップ为主；从「みんな 準備はいい?」起到最后副歌结束用レーザーカラオケ；
歌名卡放在前奏 MINA 回头那一段。

逐字变色：识别器的词时间戳是平均切的，不能用。这里在每句时间内，
用人声分轨的起音强度累积量和线性时间各占一半推进变色，再按每个字的音节数分配宽度。

  python subtrack.py            # 生成 out/subs_preview.mp4（字幕 + 调色背景 + 歌，带时间码，供核对）
其他程序用 SubTrack(...).frame(t) 取某一时刻的 RGBA 字幕层（numpy，H×W×4，0–1）。
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from subs import H, STYLES, W, broadcast, line_layers, title_card  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "suno/pop_1_timeline.json"
VOCALS = ROOT / "stems_suno/htdemucs_ft/pop_1/vocals.wav"
LEAD = 0.35
HOLD = 0.8
KARAOKE = (158.9, 209.4)
TITLE = (11.0, 14.6)
BAND = 720

SMALL = set("ゃゅょぁぃぅぇぉャュョァィゥェォ")
PUNCT = set(" 　,.!?()、。・（）")


def char_weight(c):
    """大致的音节数：汉字约 2 拍，假名 1 拍，拗音小字并入前一拍，英文字母约 1/3 拍。"""
    if c in PUNCT:
        return 0.0
    if c in SMALL:
        return 0.15
    if "\u4e00" <= c <= "\u9fff":
        return 1.8
    if c.isascii():
        return 0.35
    return 1.0


def onset_env():
    import librosa
    y, sr = librosa.load(VOCALS, sr=22050, mono=True)
    hop = 256
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    return env, hop / sr


class SubTrack:
    def __init__(self):
        tl = json.loads(TIMELINE.read_text())
        self.lines = [l for s in tl["sections"] for l in s["lines"]]
        self.env, self.dt = onset_env()
        self.cache = {}
        t = title_card()
        self.title = np.asarray(broadcast(t), np.float32) / 255

    def style_at(self, t):
        return "karaoke" if KARAOKE[0] <= t < KARAOKE[1] else "telop"

    def window(self, i):
        l = self.lines[i]
        show = l["t0"] - LEAD
        nxt = self.lines[i + 1]["t0"] - LEAD if i + 1 < len(self.lines) else 1e9
        hide = min(nxt, l["t1"] + HOLD)
        return show, hide

    def layers(self, i, style):
        key = (i, style)
        if key not in self.cache:
            l = self.lines[i]
            base, sung, x0, edges = line_layers(l["ja"], l["zh"], style)
            band = lambda im: np.asarray(broadcast(im), np.float32)[BAND:] / 255
            w = np.array([char_weight(c) for c in l["ja"]])
            mora = np.concatenate([[0], np.cumsum(w)]) / max(w.sum(), 1e-6)
            xs = np.concatenate([[x0], edges])
            xs[-1] += STYLES[style]["edge_w"] + 2
            a, b = l["t0"], max(l["t1"] - 0.15, l["t0"] + 0.5)
            k0, k1 = int(a / self.dt), int(b / self.dt) + 1
            e = self.env[k0:k1] + 0.2 * self.env[k0:k1].mean()
            cum = np.concatenate([[0], np.cumsum(e)]) / e.sum()
            self.cache[key] = (band(base), band(sung), mora, xs, a, b, cum)
        return self.cache[key]

    def cut_x(self, t, mora, xs, a, b, cum):
        if t <= a:
            return xs[0]
        if t >= b:
            return W
        lin = (t - a) / (b - a)
        oc = np.interp(lin, np.linspace(0, 1, len(cum)), cum)
        p = 0.5 * lin + 0.5 * oc
        return float(np.interp(p, mora, xs))

    def patches(self, t):
        """t 时刻要叠的图层，[(起始行 y, RGBA 数组)]。"""
        out = []
        if TITLE[0] <= t < TITLE[1]:
            out.append((0, self.title))
        for i in range(len(self.lines)):
            show, hide = self.window(i)
            if show <= t < hide:
                base, sung, *rest = self.layers(i, self.style_at(self.lines[i]["t0"]))
                cut = max(0, int(round(self.cut_x(t, *rest))))
                band = base.copy()
                band[:, :cut] = sung[:, :cut]
                out.append((BAND, band))
                break
        return out

    def frame(self, t):
        out = np.zeros((H, W, 4), np.float32)
        for y0, p in self.patches(t):
            out[y0:] = p
        return out


def over(img, patches):
    for y0, p in patches:
        a = p[..., 3:]
        img[y0:] = img[y0:] * (1 - a) + p[..., :3] * a
    return img


def section_at(tl, t):
    for s in tl["sections"]:
        if s["t0"] <= t < s["t1"]:
            return s["name"]
    return ""


def preview(fps=30):
    from grade import grade
    here = Path(__file__).parent
    tl = json.loads(TIMELINE.read_text())
    bgs = {}
    for name in ("anime_ginza", "anime_pool"):
        im = Image.open(here / f"src/{name}.png").convert("RGB").resize((W, H), Image.LANCZOS)
        bgs[name] = grade(np.asarray(im, np.float32) / 255, "film89", seed=3).astype(np.float32)
    day = {"verse2", "chorus2"}
    track = SubTrack()
    fmono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 26)
    out = ROOT / "out/subs_preview.mp4"
    out.parent.mkdir(exist_ok=True)
    dur = tl["duration"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-i", str(ROOT / tl["audio"]),
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(int(dur * fps)):
        t = n / fps
        sec = section_at(tl, t)
        bg = bgs["anime_pool" if sec in day else "anime_ginza"]
        img = over(bg.copy(), track.patches(t))
        frame = Image.fromarray((img * 255).astype(np.uint8))
        ImageDraw.Draw(frame).text((24, 20), f"{int(t // 60)}:{t % 60:05.2f}  {sec}  {track.style_at(t)}",
                                   font=fmono, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print(out)


if __name__ == "__main__":
    preview()
