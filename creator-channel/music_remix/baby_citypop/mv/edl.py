"""按导演脚本生成剪辑表 edl.json。

时间全部来自 suno/pop_1_timeline.json（歌词句起点）和拍点；剪辑点吸附到最近的拍。
影视片段从 footage/picks.json 里按标签取：{"标签": [{"file": "raw/x.mp4", "in": 秒, "label": "作品 (年)", "crop": [...]?}, ...]}，
同一标签按顺序轮流取用。缺素材的槽位先用 MINA 镜头或代码画面顶上。
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
TL = json.loads((ROOT / "suno/pop_1_timeline.json").read_text())
BEATS = TL["beats"]
LINES = {s["name"]: [l["t0"] for l in s["lines"]] for s in TL["sections"]}
SEC = {s["name"]: (s["t0"], s["t1"]) for s in TL["sections"]}
IBI = 60 / TL["bpm"]
PICKS = json.loads((ROOT / "footage/picks.json").read_text()) if (ROOT / "footage/picks.json").exists() else {}
_used = {}

shots, overlays = [], []


def b(t):
    """吸附到最近的拍点。"""
    return min(BEATS, key=lambda x: abs(x - t))


def shot(t0, t1, src, look="film89"):
    shots.append(dict(t0=round(t0, 3), t1=round(t1, 3), look=look, src=src))


def ov(t0, t1, name, **args):
    overlays.append(dict(t0=round(t0, 3), t1=round(t1, 3), name=name, args=args))


def wan(name, take_t0, t0, **kw):
    """万相镜头。take_t0 是这条镜头第 0 秒对应的歌曲时间（对口型镜头 = sing）；None 表示从头放。"""
    start = 0.0 if take_t0 is None else max(0.0, t0 - take_t0)
    sub = "wan/smooth" if (ROOT / f"wan/smooth/{name}.mp4").exists() else "wan"
    return dict(kind="video", path=f"{sub}/{name}.mp4", start=round(start, 3), **kw)


def scene(name, **args):
    return dict(kind="scene", name=name, args=args)


def clip(tag, fallback=None, offset=0.0):
    """从精选库按标签取下一段影视片段。"""
    pool = PICKS.get(tag, [])
    if not pool:
        return fallback or scene("black")
    k = _used.get(tag, 0)
    _used[tag] = k + 1
    p = pool[k % len(pool)]
    s = dict(kind="video", path="footage/" + p["file"], start=p["in"] + offset, fit="cover")
    if p.get("crop"):
        s["crop"] = p["crop"]
    if p.get("speed"):
        s["speed"] = p["speed"]
    s["label"] = p.get("label", "")
    if tag == "grid":
        s["loop"] = 3.0
    return s


def film(t0, t1, tag, fallback=None, look="tv89"):
    shot(t0, t1, clip(tag, fallback), look)


def chorus(sec, takes_mcu, takes_wide, react_tag, kaeri_tag, party_tag, look="film89", day=False):
    """副歌：Baby 各句在近景/全景两条整段演唱之间切换，每句末尾 1 拍插一个当年人物的欢乐反应镜头。"""
    L = LINES[sec]
    end = SEC[sec][1]
    t_mid = L[4]
    for k, t in enumerate(L):
        nxt = L[k + 1] if k + 1 < len(L) else end
        if k in (3, 7):
            continue
        take_m, take_w = takes_mcu if t < t_mid else takes_mcu[2:], takes_wide if t < t_mid else takes_wide[2:]
        mcu, mcu_t0 = take_m[0], take_m[1]
        wide, wide_t0 = take_w[0], take_w[1]
        cut = b(nxt - 2 * IBI)
        if k % 2 == 0:
            shot(t, cut, wan(mcu, mcu_t0, t), look)
        else:
            shot(t, cut, wan(wide, wide_t0, t), look)
        film(cut, nxt, react_tag, fallback=wan(wide if k % 2 == 0 else mcu, wide_t0 if k % 2 == 0 else mcu_t0, cut))
        ov(t, t + 3 * IBI, "hearts", times=[round(t + i * IBI, 3) for i in range(3)], seed=k + (10 if day else 0))
    k3, k7 = L[3], L[7]
    half = b(k3 + (L[4] - k3) / 2)
    film(k3, half, kaeri_tag)
    film(half, L[4], kaeri_tag)
    for i in range(4):
        a, z = b(k7 + i * (end - k7) / 4), b(k7 + (i + 1) * (end - k7) / 4) if i < 3 else end
        film(a, z, party_tag)
    ov(k7, end, "confetti", seed=7 if day else 3)


def build():
    # ---------------- 前奏
    I = SEC["intro"]
    shot(0, 0.9, scene("snow"), "tv89")
    film(0.9, b(3.7), "tokyo_night", fallback=scene("skyline"))
    shot(b(3.7), b(7.4), scene("skyline"), "tv89")
    ov(0.9, b(7.4), "osd", text="▶ PLAY", date="1989.12.29 FRI", clock="PM 11:58")
    shot(b(7.4), b(11.0), wan("I3", None, 0))
    shot(b(11.0), b(14.7), wan("I4", None, 0))
    shot(b(14.7), I[1], scene("title", path="look/src/cover_night.png"))

    # ---------------- 主歌一
    V = LINES["verse1"]
    shot(V[0], b(V[0] + 4 * IBI), wan("V1", 17.4, V[0]))
    film(b(V[0] + 4 * IBI), V[1], "tokyo_night", fallback=wan("V1", 17.4, b(V[0] + 4 * IBI)))
    film(V[1], V[2], "money_taxi", fallback=wan("I3", None, 0))
    ov(V[1] + IBI, V[1] + 5 * IBI, "yen", y=420)
    film(V[2], V[3], "shoulder", fallback=wan("V1", 17.4, V[2]))
    ov(V[2] + IBI, V[3] - IBI / 2, "prop", title="ショルダーフォン", lines=["1985年　登場", "重さ　約3kg"])
    e = SEC["verse1"][1]
    for i in range(3):
        film(b(V[3] + i * (e - V[3]) / 3), b(V[3] + (i + 1) * (e - V[3]) / 3) if i < 2 else e, "toast")

    # ---------------- 预副歌
    P = LINES["pre1"]
    mid = b(P[0] + 4 * IBI)
    film(P[0], mid, "fan", fallback=wan("P1", 32.5, P[0]))
    shot(mid, P[1], wan("P1", 32.5, mid))
    shot(P[1], P[2], scene("mirrorball", speed=1.0))
    film(P[2], P[3], "office", fallback=scene("mirrorball", speed=2.0))
    ov(P[2], P[3], "clock", h0=21.0, h1=29.0)
    shot(P[3], P[4], wan("P4", 43.4, P[3]))
    shot(P[4], SEC["pre1"][1], scene("bigtext", text="みんなで歌って!", sub="大家一起唱"))
    ov(SEC["pre1"][1], SEC["pre1"][1] + 0.3, "flash")

    # ---------------- 副歌一（夜·舞台）
    chorus("chorus1", ("N1", 48.3, "N2", 62.8), ("N3", 48.3, "N4", 62.8), "react", "kaeri", "party")

    # ---------------- 主歌二（泡沫生活图鉴）
    W2 = LINES["verse2"]
    half = b(W2[0] + 4 * IBI)
    film(W2[0], half, "ski", fallback=scene("board"))
    shot(half, W2[1], scene("board"))
    shot(W2[1], W2[2], scene("ledger"))
    shot(W2[2], W2[3], scene("nikkei"))
    film(W2[3], W2[4], "shopping", fallback=scene("black"))
    ov(W2[3], W2[4], "card_bags")
    film(W2[4], W2[5], "karaoke", fallback=wan("P1", 32.5, 32.5))
    film(W2[5], b(W2[5] + 4 * IBI), "regain", fallback=scene("black"))
    film(b(W2[5] + 4 * IBI), W2[6], "salaryman", fallback=scene("black"))
    film(W2[6], b(W2[6] + 4 * IBI), "money_rain", fallback=scene("mirrorball"))
    film(b(W2[6] + 4 * IBI), W2[7], "money_rain", fallback=scene("mirrorball"))
    ov(W2[6], W2[7], "money", n=70)
    shot(W2[7], SEC["verse2"][1], wan("W8", None, 0))

    # ---------------- 副歌二（白天·海边）
    c2 = SEC["chorus2"][0]
    ov(c2, c2 + 6.0, "rank")
    chorus("chorus2", ("D1", 106.8, "D4", 121.3), ("D3", 106.8, "D2", 121.3), "react_day", "sunset", "pool_party", day=True)

    # ---------------- 桥段
    B = LINES["bridge"]
    tex = ["mina/frames/stage_mcu.png", "look/src/anime_pool.png", "mina/frames/P4_roof.png", "mina/frames/D_beach_wide.png",
           "mina/frames/W8_car.png", "look/src/anime_ginza.png", "mina/frames/P1_fan.png"]
    shot(B[0], B[1], scene("bubbles", textures=tex))
    shot(B[1], B[2], wan("B2", None, 0))
    for i in range(4):
        film(b(B[2] + i * (B[3] - B[2]) / 4), b(B[2] + (i + 1) * (B[3] - B[2]) / 4) if i < 3 else B[3], "smile")
    shot(B[3], B[4], scene("mirrorball", speed=0.4, warm=True))
    shot(B[4], B[5], wan("B5", None, 0))
    shot(B[5], B[6], scene("boombox"))
    shot(B[6], B[7], wan("B7", 158.6, B[6]))
    ov(b(B[6] + 4 * IBI), B[7], "bigcue", text="準備OK?", y=200)
    shot(B[7], SEC["bridge"][1], scene("bigtext", text="一緒に歌おう!", sub="一起唱吧"))
    ov(SEC["bridge"][1], SEC["bridge"][1] + 0.3, "flash")

    # ---------------- 推进段：先是萨克斯独奏（全景 → 特写），之后九宫格每拍翻开一格，最后倒数，正中间 MINA 亮起
    b0, b1 = SEC["build"]
    sax_end = b(171.0)
    sax_mid = b(b0 + (sax_end - b0) * 0.55)
    shot(b0, sax_mid, wan("S1", None, b0))
    shot(sax_mid, sax_end, wan("S2", None, sax_mid))
    order = [0, 2, 6, 8, 1, 3, 5, 7]
    cells, reveal, labels = [None] * 9, [None] * 9, [""] * 9
    for i, k in enumerate(order):
        c = clip("grid")
        cells[k], reveal[k], labels[k] = c, round(b(sax_end + i * IBI), 3), c.get("label", "")
    cells[4], reveal[4], labels[4] = wan("F1", 179.9, b1 - 0.6), round(b1 - 0.6, 3), "MINA"
    shot(sax_end, b1, dict(kind="grid", cells=cells, reveal=reveal, labels=labels))
    ov(b1 - 5 * 0.736, b1, "countdown", t_end=b1)

    # ---------------- 最后副歌：九宫格大合唱（中间 MINA，周围当年人物按 2 小节换一批）
    F = LINES["final"]
    fe = SEC["final"][1]
    ov(F[0], F[0] + 2.0, "bigcue", text="みんなで!", y=150)

    def grid_block(a, z):
        t = a
        while t < z - 0.1:
            u = min(z, b(t + 8 * IBI))
            cs = [clip("grid") for _ in range(9)]
            take, tt0 = ("F1", 179.9) if t < 194.5 else ("F2", 194.5)
            cs[4] = wan(take, tt0, t)
            shot(t, u, dict(kind="grid", cells=cs, labels=[c.get("label", "") for c in cs[:4]] + ["MINA"] + [c.get("label", "") for c in cs[5:]]))
            t = u

    grid_block(F[0], F[3])
    for i in range(4):
        film(b(F[3] + i * (F[4] - F[3]) / 4), b(F[3] + (i + 1) * (F[4] - F[3]) / 4) if i < 3 else F[4], "party")
    grid_block(F[4], F[7])
    for i in range(4):
        film(b(F[7] + i * (fe - F[7]) / 4), b(F[7] + (i + 1) * (fe - F[7]) / 4) if i < 3 else fe, "party")
    ov(F[7], fe, "confetti", n=300, seed=11)
    for t in (F[1], F[2], F[5], F[6], F[3], F[7]):
        ov(t - 0.12, t + 0.18, "flash")

    # ---------------- 尾声
    O = LINES["outro"]
    hi = ["mina/frames/F_gold_mcu.png", "mina/frames/D_pool_mcu.png", "mina/frames/W8_car.png", "mina/frames/stage_mcu.png",
          "mina/frames/B2_clouds.png", "mina/frames/P4_roof.png", "look/src/cover_night.png"]
    shot(O[0], O[3], scene("bubbles", textures=hi, n=8, seed=5))
    shot(O[3], b(227.5), wan("O2", None, 0))
    shot(b(227.5), 240.9, scene("cover", path="look/src/cover_night.png", credits=credits()))
    shot(240.9, TL["duration"], scene("black"), "tv89")
    ov(240.9, TL["duration"], "osd", text="■ STOP", date="", clock="", tracking=0)


def credits():
    out = ["■原曲", "Baby", "Justin Bieber feat. Ludacris (2010)",
           "作詞・作曲　J. Bieber / C. Stewart / T. Nash /", "C. Milian / C. Bridges", "",
           "■日本語詞・中国語訳", "（制作者）", "",
           "■歌唱・編曲", "Suno AI（AI 生成）", "",
           "■映像", "万相 Wan / Qwen-Image（AI 生成）", "代码动画", "",
           "■引用映像（各 1–3 秒）"]
    used = {p["file"] for pool in PICKS.values() for p in pool}
    seen = []
    for f in sorted(used):
        meta = ROOT / "footage" / Path(f).with_suffix(".json")
        w = json.loads(meta.read_text())["work"] if meta.exists() else Path(f).stem
        if w not in seen:
            seen.append(w)
    out += seen + ["", "■本作品は AI 生成コンテンツを含みます", "本视频含 AI 生成内容", "", "TOKYO 1989"]
    return out


if __name__ == "__main__":
    build()
    for s in shots:
        s["src"].pop("label", None)
        if s["src"]["kind"] == "grid":
            for c in s["src"]["cells"]:
                if c:
                    c.pop("label", None)
    shots.sort(key=lambda s: s["t0"])
    for a, z in zip(shots, shots[1:]):
        if abs(a["t1"] - z["t0"]) > 0.02:
            print(f"gap/overlap {a['t1']} -> {z['t0']}")
    edl = dict(fps=30, dur=TL["duration"], beats=BEATS, shots=shots, overlays=overlays)
    (HERE / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=0))
    print(len(shots), "shots", len(overlays), "overlays")
