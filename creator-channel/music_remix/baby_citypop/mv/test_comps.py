"""每个代码组件出一帧，拼成 out/comps_sheet.jpg 检查。"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import comps  # noqa: E402

beats = json.loads((ROOT / "suno/pop_1_timeline.json").read_text())["beats"]


def ctx(T, t, d):
    return SimpleNamespace(T=T, t=t, d=d, beats=beats, env=lambda x: 0.8, seed=int(T * 30))


bg = comps.rgb(Image.open(ROOT / "look/src/anime_ginza.png").resize((1920, 1080)))
cover = str(ROOT / "look/src/cover_night.png")
tex = [np.asarray(Image.open(ROOT / p).convert("RGB").resize((480, 480)), np.float32) / 255
       for p in ("look/src/anime_ginza.png", "look/src/anime_pool.png", "mina/frames/P1_fan.png")]


def ov(lay, base=bg):
    a = lay[..., 3:]
    return base * (1 - a) + lay[..., :3] * a


items = [
    ("snow+osd", ov(comps.overlay_osd(ctx(1.2, 1.2, 3.7)), comps.scene_snow(ctx(1.2, 1.2, 3.7)) * 0.3)),
    ("skyline", comps.scene_skyline(ctx(7.0, 3.3, 3.7))),
    ("title", comps.scene_title(ctx(16.5, 1.8, 3.0), cover)),
    ("yen", ov(comps.overlay_yen(ctx(22.5, 0.8, 1.6)))),
    ("prop", ov(comps.overlay_prop(ctx(26.0, 0.8, 2.5)))),
    ("mirrorball", comps.scene_mirrorball(ctx(37.0, 0.8, 3.6))),
    ("clock", ov(comps.overlay_clock(ctx(41.5, 1.1, 3.2)))),
    ("bigtext", comps.scene_bigtext(ctx(47.9, 0.6, 1.2), "みんなで歌って!", "大家一起唱")),
    ("hearts", ov(comps.overlay_hearts(ctx(49.0, 0.5, 3), times=(48.7, 48.9)))),
    ("board", comps.scene_board(ctx(79.5, 1.5, 3.6))),
    ("ledger", comps.scene_ledger(ctx(84.0, 3.1, 3.7))),
    ("nikkei", comps.scene_nikkei(ctx(88.0, 3.4, 3.7))),
    ("card_bags", ov(comps.overlay_card_bags(ctx(91.0, 2.8, 3.7)))),
    ("money", ov(comps.overlay_money(ctx(100.0, 1.2, 4.1)))),
    ("rank", ov(comps.overlay_rank(ctx(109.0, 1.9, 6.0)))),
    ("bubbles", comps.scene_bubbles(ctx(138.0, 1.7, 3.8), tex)),
    ("boombox", comps.scene_boombox(ctx(156.0, 2.6, 5.5))),
    ("confetti", ov(comps.overlay_confetti(ctx(208.0, 1.5, 3)))),
    ("countdown", ov(comps.overlay_countdown(ctx(178.5, 0, 0), t_end=180.22), comps.scene_grid_wall(ctx(0, 0, 0)))),
    ("cover+credits", comps.scene_cover(ctx(234.0, 6.5, 14.0), cover, credits=["■原曲", "Baby", "Justin Bieber feat. Ludacris", "■歌唱・編曲", "Suno AI"] * 3)),
]
tw, th = 480, 270
cols = 4
sheet = Image.new("RGB", (cols * tw, ((len(items) + cols - 1) // cols) * (th + 30)), (20, 20, 28))
d = ImageDraw.Draw(sheet)
for k, (name, img) in enumerate(items):
    x, y = (k % cols) * tw, (k // cols) * (th + 30)
    sheet.paste(Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((tw, th)), (x, y + 30))
    d.text((x + 6, y + 4), name, font=comps.font("futura", 22), fill=(255, 255, 255))
(ROOT / "out").mkdir(exist_ok=True)
sheet.save(ROOT / "out/comps_sheet.jpg", quality=85)
print("ok")
