"""80 年代日本风格的日中双语字幕（逐字变色）+ 歌名字幕卡。

样式：
  telop   —— 歌番組テロップ：80 年代电视音乐节目的歌词字幕，白字粗黑边 + 投影，唱到的字变黄
  karaoke —— レーザーカラオケ：80 年代镭射卡拉 OK，白字蓝边，唱到的字变粉红；日文靠左、中文靠右错开
字幕放在 16:9 画面中间 4:3 的安全区里（当年电视字幕只敢放在这个范围）。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_JA = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"
FONT_ZH = next(Path("/System/Library/AssetsV2").glob("com_apple_MobileAsset_Font*/*/AssetData/Yuanti.ttc"))
W, H = 1920, 1080
SAFE_L, SAFE_R = (W - H * 4 // 3) // 2 + 60, W - (W - H * 4 // 3) // 2 - 60

STYLES = {
    "telop": dict(ja_size=72, zh_size=44, base=(255, 255, 255), sung=(255, 226, 64), edge=(16, 16, 24),
                  edge_w=6, zh_fill=(255, 255, 255), zh_edge=(16, 16, 24), zh_edge_w=4, shadow=(5, 5),
                  layout="center", bottom=86),
    "karaoke": dict(ja_size=70, zh_size=44, base=(255, 255, 255), sung=(255, 92, 168), edge=(24, 48, 170),
                    edge_w=5, zh_fill=(255, 255, 255), zh_edge=(24, 48, 170), zh_edge_w=4, shadow=(0, 0),
                    layout="stagger", bottom=70),
}


def _text_layer(text, font, fill, edge, edge_w, xy):
    """丸ゴ只有常规字重，先用描边画出粗外框，再用同色细描边把字身加粗。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text(xy, text, font=font, fill=edge, stroke_width=edge_w + 2, stroke_fill=edge)
    d.text(xy, text, font=font, fill=fill, stroke_width=2, stroke_fill=fill)
    return lay


def broadcast(lay):
    """字幕叠在调色后的画面上，只做轻微柔化，模拟当年电视字幕机的边缘。"""
    return lay.filter(ImageFilter.GaussianBlur(0.9))


def _shadow(lay, off):
    if not any(off):
        return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = lay.split()[3].filter(ImageFilter.GaussianBlur(3))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 170), (off[0], off[1]), a)
    return sh


def line_layers(ja, zh, style="telop"):
    """一句字幕的两张整帧图层：未唱（含阴影和中文）与已唱，以及日文每个字右边缘的 x 坐标。"""
    s = STYLES[style]
    fj, fz = ImageFont.truetype(FONT_JA, s["ja_size"]), ImageFont.truetype(str(FONT_ZH), s["zh_size"])
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    jw = d.textlength(ja, font=fj)
    zw = d.textlength(zh, font=fz) if zh else 0
    zy = H - s["bottom"] - s["zh_size"]
    jy = zy - s["ja_size"] - 22
    if s["layout"] == "center":
        jx, zx = (W - jw) / 2, (W - zw) / 2
    else:
        jx, zx = SAFE_L, SAFE_R - zw
    base = _text_layer(ja, fj, s["base"], s["edge"], s["edge_w"], (jx, jy))
    sung = _text_layer(ja, fj, s["sung"], s["edge"], s["edge_w"], (jx, jy))
    under = _shadow(base, s["shadow"])
    if zh:
        zl = _text_layer(zh, fz, s["zh_fill"], s["zh_edge"], s["zh_edge_w"], (zx, zy))
        under = Image.alpha_composite(Image.alpha_composite(under, _shadow(zl, s["shadow"])), zl)
    edges = [jx + d.textlength(ja[:k + 1], font=fj) for k in range(len(ja))]
    return Image.alpha_composite(under, base), Image.alpha_composite(under, sung), jx - s["edge_w"] - 2, edges


def subtitle(ja, zh, progress, style="telop"):
    """progress: 0–1，日文行已唱到的比例（逐字变色）。返回 RGBA 叠加层。"""
    base, sung, x0, edges = line_layers(ja, zh, style)
    cut = int(x0 + (edges[-1] + STYLES[style]["edge_w"] + 2 - x0) * progress)
    mask = Image.new("L", (W, H), 0)
    mask.paste(255, (0, 0, max(0, cut), H))
    return Image.composite(sung, base, mask)


def title_card(title="BABY", artist="MINA", credits=("原曲　J.Bieber 他", "編曲・歌唱　Suno AI")):
    """80 年代音乐节目开唱时左下角的歌名字幕卡。"""
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    x, y = SAFE_L, H - 330
    ft = ImageFont.truetype(FONT_JA, 96)
    fa = ImageFont.truetype(FONT_JA, 52)
    fc = ImageFont.truetype(FONT_JA, 30)
    d.text((x, y), "♪", font=fa, fill=(255, 226, 64), stroke_width=5, stroke_fill=(16, 16, 24))
    d.text((x + 60, y - 30), title, font=ft, fill=(255, 255, 255), stroke_width=7, stroke_fill=(16, 16, 24))
    d.text((x + 64, y + 92), artist, font=fa, fill=(255, 226, 64), stroke_width=5, stroke_fill=(16, 16, 24))
    for k, c in enumerate(credits):
        d.text((x + 66, y + 168 + k * 40), c, font=fc, fill=(255, 255, 255), stroke_width=4, stroke_fill=(16, 16, 24))
    sh = _shadow(out, (5, 5))
    return Image.alpha_composite(sh, out)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from grade import grade

    here = Path(__file__).parent
    bg = Image.open(here / "src/anime_ginza.png").convert("RGB").resize((W, H), Image.LANCZOS)
    bg2 = Image.open(here / "src/anime_pool.png").convert("RGB").resize((W, H), Image.LANCZOS)
    jobs = {
        "sub_telop": (bg, subtitle("万札振って タクシー止める", "挥着万元大钞 拦下出租车", 0.55, "telop")),
        "sub_karaoke": (bg, subtitle("万札振って タクシー止める", "挥着万元大钞 拦下出租车", 0.55, "karaoke")),
        "title_card": (bg2, title_card()),
    }
    for name, (b, lay) in jobs.items():
        g = grade(np.asarray(b, np.float32) / 255, "film89", seed=3)
        pic = Image.fromarray((g * 255).astype(np.uint8)).convert("RGBA")
        Image.alpha_composite(pic, broadcast(lay)).convert("RGB").save(here / f"{name}_v2.jpg", quality=92)
    print("ok")
