"""B 站封面合成：底图 + 大字标题，输出 16:9（1920×1080）和单独排版的 4:3（1440×1080）。

用法：python cover.py spec.json
spec.json:
{
  "bg": "底图.png",                 相对 spec.json
  "out": "out/cover/cover",         输出前缀 → cover_16x9.jpg、cover_4x3.jpg
  "focus_x": 0.5,                   4:3 裁切时保留的水平中心（0–1）
  "shade": [0.55, 0.92],            从画面高度的 55% 开始往下压暗，最深 92%
  "top_shade": 0,                   顶部压暗高度（比例），给顶部文字垫底
  "lines": [                         从上往下；y 是文字中心的高度（比例）
    {"text": "三体问题", "y": 0.66, "size": 180, "font": "bold", "fill": "#FFFFFF",
     "stroke": 10, "glow": "#FF4FA3", "box": "#FFD23F", "spans": [["无解", "#FFD23F"]]}
  ]
}
size 是 16:9 版的字号；文字宽度超过安全区时自动缩小。4:3 版沿用同样的比例位置。
文字都排在中间 4:3 安全区内，B 站在 4:3 位置自动裁切时也不会切到字。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {
    "bold": "/Users/mmeng/mgs-code/mgsOwn/img-gen-bus/creator-channel/ep01_4.8pct/assets/fonts/NotoSansSC-Bold.otf",
    "hiragino": "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "futura": "/System/Library/Fonts/Supplemental/Futura.ttc",
}


def font(name, size):
    return ImageFont.truetype(FONTS.get(name, name), size)


def fit_bg(img, W, H, focus_x):
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x0 = min(max(round(img.width * focus_x - W / 2), 0), img.width - W)
    y0 = (img.height - H) // 2
    return img.crop((x0, y0, x0 + W, y0 + H))


def shade(img, y0, a1, top):
    W, H = img.size
    m = Image.new("L", (1, H))
    for y in range(H):
        f = y / H
        a = 0.0
        if f > y0:
            a = a1 * min(1.0, (f - y0) / 0.18)
        if top and f < top:
            a = max(a, 0.75 * (1 - f / top))
        m.putpixel((0, y), int(255 * a))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(dark, img, m.resize((W, H)))


def segments(text, spans, fill):
    """把一行按 spans 切成 [(片段, 颜色)]。"""
    segs = [(text, fill)]
    for word, color in spans or []:
        out = []
        for s, c in segs:
            if c != fill or word not in s:
                out.append((s, c))
                continue
            a, b = s.split(word, 1)
            out += [x for x in [(a, c), (word, color), (b, c)] if x[0]]
        segs = out
    return segs


def draw_line(img, ln, W, H, safe_w, scale):
    size = round(ln["size"] * scale)
    stroke = round(ln.get("stroke", 0) * scale)
    segs = segments(ln["text"], ln.get("spans"), ln.get("fill", "#FFFFFF"))
    while True:
        f = font(ln.get("font", "bold"), size)
        widths = [f.getlength(s) for s, _ in segs]
        total = sum(widths) + 2 * stroke
        pad = round(size * 0.35) if ln.get("box") else 0
        if total + 2 * pad <= safe_w or size < 20:
            break
        size = int(size * 0.96)
        stroke = max(1, int(stroke * 0.96)) if stroke else 0
    asc, desc = f.getmetrics()
    cy = round(ln["y"] * H)
    x = round((W - total) / 2) + stroke
    top = cy - (asc + desc) // 2

    if ln.get("box"):
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x - stroke - pad, top - round(size * 0.12), x - stroke + total + pad, top + asc + desc + round(size * 0.02)],
                            radius=round(size * 0.18), fill=ln["box"])

    if ln.get("glow"):
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        xx = x
        for (s, _), w in zip(segs, widths):
            gd.text((xx, top), s, font=f, fill=ln["glow"], stroke_width=stroke + round(size * 0.06), stroke_fill=ln["glow"])
            xx += w
        g = g.filter(ImageFilter.GaussianBlur(size * 0.18))
        img.alpha_composite(g)
        img.alpha_composite(g)

    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    off = max(2, round(size * 0.04))
    xx = x
    for (s, _), w in zip(segs, widths):
        sd.text((xx + off, top + off), s, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        xx += w
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(off)))

    d = ImageDraw.Draw(img)
    xx = x
    for (s, c), w in zip(segs, widths):
        d.text((xx, top), s, font=f, fill=c, stroke_width=stroke, stroke_fill=ln.get("stroke_fill", "#000000"))
        xx += w


def render(spec, base, W, H, safe_w, scale):
    bg = Image.open(base / spec["bg"]).convert("RGB")
    img = fit_bg(bg, W, H, spec.get("focus_x", 0.5) if W < 1920 else 0.5)
    y0, a1 = spec.get("shade", [0.55, 0.9])
    img = shade(img, y0, a1, spec.get("top_shade", 0)).convert("RGBA")
    for ln in spec["lines"]:
        draw_line(img, ln, W, H, safe_w, scale)
    return img.convert("RGB")


def main():
    p = Path(sys.argv[1])
    spec = json.loads(p.read_text())
    base = p.parent
    out = base / spec["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    render(spec, base, 1920, 1080, 1440 - 120, 1.0).save(f"{out}_16x9.jpg", quality=95)
    render(spec, base, 1440, 1080, 1440 - 100, 1.0).save(f"{out}_4x3.jpg", quality=95)
    print(f"{out}_16x9.jpg", f"{out}_4x3.jpg")


if __name__ == "__main__":
    main()
