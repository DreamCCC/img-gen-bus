#!/usr/bin/env python3
"""发布会原声切片 + 中英字幕块对齐 + 回写 audio/quotes.json + 审看预览 / 联系表。

入出点（原片秒）是按词级 ASR（research/quotes_wordasr/）和音频能量包络人工定的：
入点 = 第一个词起声前约 0.2 s，出点 = 最后一个词收声后约 0.3 s。字幕块 a/b 由词级时间对齐，相对片段起点。

usage:
  python tools/cut_quotes.py            切片 + 回写 quotes.json
  python tools/cut_quotes.py --preview  另外出 out/原声_审看v1.mp4 和 out/原声_联系表.jpg
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FILM = Path(__file__).resolve().parent.parent
PROJ = FILM.parent
SRC = "online/presser/qqPT01jE5S0.mp4"
ASR = PROJ / "research/quotes_wordasr"
OUT = FILM / "assets/footage/quotes"
FPS = 30

# speech = 能量包络测得的第一个词起声 / 最后一个词收声（原片秒）
Q = {
    "q2_1": {
        "in": 2435.58, "out": 2441.45, "speech": (2435.78, 2441.15), "asr": "fine_np/q2_1.json",
        "chunks": [
            ("Of course I'm going to be more — I mean, I'm going to be more careful,", "当然，我会更注意一点，"),
            ("but it's not going to change much.", "但不会有太大改变。"),
        ]},
    "q3_1": {
        "in": 1871.90, "out": 1881.18, "speech": (1872.00, 1880.88), "asr": "fine/q3_1.json",
        "chunks": [
            ("Defensively, we just did it harder for longer stretches,", "防守上，我们就是做得更狠、坚持得更久，"),
            ("and we were really in tune to what we were supposed to be doing.", "而且大家都很清楚自己该干什么。"),
        ]},
    "q3_2": {
        "in": 1150.80, "out": 1176.15, "speech": (1151.00, 1175.85), "asr": "fine_np/q3_2.json",
        "chunks": [
            ("We got away from what got us the 76 points in the first half,", "上半场拿76分靠的那套东西，我们丢了，"),
            ("just in terms of putting pressure on the rim, rolling after screens,", "就是冲击篮筐、挡拆后顺下，"),
            ("running, continuing to find the paint,", "打快攻，一直往禁区里打，"),
            ("whether it's for ourselves or for a teammate.", "不管是自己打，还是给队友做机会。"),
            ("We got on our heels and, you know, missed some shots,", "后来我们打得畏手畏脚，也丢了些球，"),
            ("and then, you know, you don't get as many free throws", "这样一来，罚球就少了，"),
            ("and high, high-percentage looks when you play on your heels like that.", "好的出手机会也少了。打得这么被动，就会这样。"),
        ]},
    "q4_1": {
        "in": 2373.89, "out": 2386.75, "speech": (2374.09, 2386.45), "asr": "fine/q4_1b.json",
        "chunks": [
            ("What was going through my mind?", "我当时在想什么？"),
            ("I mean, same thing as always, it's just a shot.", "跟平时一样，就是一次投篮而已。"),
            ("You might work on your form hours and hours,", "投篮动作你可以练上无数个小时，"),
            ("at the end of the day it's just a shot,", "但说到底，也就是一次投篮，"),
            ("so you need to shoot it the normal way.", "所以就该照平常那样投。"),
        ]},
    "q4_2": {
        "in": 2109.25, "out": 2122.50, "speech": (2109.45, 2122.20), "asr": "fine_np/q4_2.json",
        "chunks": [
            ("You know, again, on that action,", "那个回合嘛，"),
            ("you never know what a player's thinking, you know.", "你永远不知道球员当时在想什么。"),
            ("Maybe he was going to drive", "可能他是想突破，"),
            ("and wanted to keep the dribble to run out the clock.", "想一直运着球，把时间耗完。"),
            ("I don't know. You would have to ask him.", "我不知道，你们得去问他。"),
        ]},
    "q4_3": {
        "in": 883.15, "out": 890.05, "speech": (883.35, 889.75), "asr": "fine_np/q4_3.json",
        "chunks": [
            ("I fell on the floor.", "我当时摔在地上了，"),
            ("I couldn't really see. I don't know.", "没怎么看清，我也说不好。"),
            ("I just saw the block.", "就只看到那记封盖。"),
        ]},
    "q4_4": {
        "in": 1425.20, "out": 1434.45, "speech": (1425.40, 1434.15), "asr": "fine_np/q4_4.json",
        "chunks": [
            ("I told OG, as big, as strong, as athletic as he is,", "我跟阿努诺比说，你块头这么大、\n这么壮、运动能力这么好，"),
            ("he's got to be a monster on the offensive glass tonight.", "今晚的前场篮板，你得给我抢疯了。"),
        ]},
    "q5_1": {
        "in": 2258.92, "out": 2273.60, "speech": (2259.12, 2273.30), "asr": "fine/q5_1.json",
        "chunks": [
            ("What's going through my mind right now?", "我现在在想什么？"),
            ("I think it's going to go one of two ways.", "我觉得接下来只有两条路。"),
            ("One of two ways, and a bad one and a good one.", "两条路，一条坏的，一条好的。"),
            ("And I know the bad one would be giving up,", "坏的那条，是就此放弃；"),
            ("the good one would be getting stronger through this, getting more together.", "好的那条，是经历这一场，\n变得更强、更抱团。"),
            ("And I know this is what we're going to do.", "我知道，我们会走好的那条路。"),
        ]},
}

ROLE = {"文班": "文班 · 马刺", "迈克·布朗": "迈克·布朗 · 尼克斯主帅", "米奇·约翰逊": "米奇·约翰逊 · 马刺主帅"}


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def tokens(s: str) -> list[str]:
    return [t for t in (norm(x) for x in re.split(r"[\s\-—]+", s)) if t]


def align(cfg: dict) -> list[dict]:
    """把每个字幕块的英文对到词级 ASR 上，返回原片绝对时间 a/b。"""
    words = json.loads((ASR / cfg["asr"]).read_text())["words"]
    for w in words:
        if w["b"] - w["a"] > 0.8:  # whisper 会把停顿算进停顿后第一个词
            w["a"] = w["b"] - 0.4
    asr_t = [norm(w["w"]) for w in words]
    canon, owner = [], []
    for i, (en, _) in enumerate(cfg["chunks"]):
        for t in tokens(en):
            canon.append(t)
            owner.append(i)
    m = {}
    for blk in difflib.SequenceMatcher(None, canon, asr_t, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k
    on, off = cfg["speech"]
    out = []
    for i, (en, zh) in enumerate(cfg["chunks"]):
        idx = [j for j in range(len(canon)) if owner[j] == i and j in m]
        a = words[m[idx[0]]]["a"]
        b = words[m[idx[-1]]]["b"]
        out.append({"zh": zh, "en": en, "a": a, "b": b})
    out[0]["a"] = on
    out[-1]["b"] = off
    for x, y in zip(out, out[1:]):  # 块之间不重叠
        if x["b"] > y["a"]:
            x["b"] = y["a"]
    return out


def cut(qid: str, t0: float, t1: float) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{qid}.mp4"
    dur = t1 - t0
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(PROJ / SRC), "-t", f"{dur:.3f}",
        "-vf", f"scale=1920:1080:flags=lanczos,fps={FPS},format=yuv420p",
        "-af", f"aresample=48000,afade=t=in:d=0.03,afade=t=out:st={dur - 0.05:.3f}:d=0.05",
        "-frames:v", str(round(dur * FPS)), "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(dst)], check=True)
    return dst


def build() -> list[dict]:
    path = FILM / "audio/quotes.json"
    quotes = json.loads(path.read_text())
    for q in quotes:
        cfg = Q[q["id"]]
        t0 = cfg["in"]
        t1 = round(t0 + round((cfg["out"] - t0) * FPS) / FPS, 3)
        chunks = align(cfg)
        dst = cut(q["id"], t0, t1)
        q["en"] = " ".join(en for en, _ in cfg["chunks"])
        q.update({
            "src": SRC, "in": t0, "out": t1, "dur": round(t1 - t0, 3),
            "file": str(dst.relative_to(FILM)),
            "zh": "".join(z.replace("\n", "") for _, z in cfg["chunks"]),
            "chunks": [{"zh": c["zh"].replace("\n", ""), "en": c["en"],
                        "a": round(c["a"] - t0, 2), "b": round(c["b"] - t0, 2)} for c in chunks],
        })
        print(q["id"], f"{t0:.2f}-{t1:.2f} ({t1 - t0:.2f}s)", dst.name)
        for c in q["chunks"]:
            print(f"   {c['a']:6.2f}-{c['b']:6.2f}  {c['zh']}  |  {c['en']}")
    path.write_text(json.dumps(quotes, ensure_ascii=False, indent=1) + "\n")
    return quotes


def ass_time(t: float) -> str:
    h, r = divmod(max(t, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def preview(quotes: list[dict]) -> None:
    out_dir = FILM / "out"
    gap = 0.5
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for q in quotes:
            dur = q["dur"]
            zh_by_chunk = {c[0]: c[1] for c in Q[q["id"]]["chunks"]}
            ev = []
            ch = q["chunks"]
            for i, c in enumerate(ch):
                end = ch[i + 1]["a"] if i + 1 < len(ch) else dur
                end = min(end, c["b"] + 0.6) if i + 1 < len(ch) else dur
                zh = zh_by_chunk[c["en"]].replace("\n", "\\N")
                ev.append(f"Dialogue: 0,{ass_time(c['a'] + gap)},{ass_time(end + gap)},ZH,,0,0,0,,{zh}")
                ev.append(f"Dialogue: 0,{ass_time(c['a'] + gap)},{ass_time(end + gap)},EN,,0,0,0,,{c['en']}")
            ev.append(f"Dialogue: 1,{ass_time(gap)},{ass_time(dur + gap)},NAME,,0,0,0,,{ROLE.get(q['who'], q['who'])}")
            ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(dur + gap)},TAG,,0,0,0,,{q['id']}  "
                      f"{q['in']:.2f}–{q['out']:.2f}  {dur:.2f}s")
            ass = Path(td) / f"{q['id']}.ass"
            ass.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ZH,Hiragino Sans GB,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,1,2,80,80,300,1
Style: EN,Helvetica Neue,36,&H00D8F0FF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,250,1
Style: NAME,Hiragino Sans GB,44,&H00FFFFFF,&H00FFFFFF,&H00C06A1A,&H00C06A1A,1,0,0,0,100,100,0,0,3,14,0,7,60,60,56,1
Style: TAG,Menlo,26,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,6,0,9,40,40,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
            part = Path(td) / f"{q['id']}.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(FILM / q["file"]),
                "-vf", f"tpad=start_duration={gap}:color=black,ass={ass}:fontsdir=/System/Library/Fonts",
                "-af", f"adelay={int(gap * 1000)}:all=1",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(part)], check=True)
            parts.append(part)
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(out_dir / "原声_审看v1.mp4")], check=True)
        sheet(quotes, Path(td))


def sheet(quotes: list[dict], td: Path) -> None:
    fz = "/System/Library/Fonts/Hiragino Sans GB.ttc"
    f_title, f_txt, f_small = ImageFont.truetype(fz, 30), ImageFont.truetype(fz, 24), ImageFont.truetype(fz, 20)
    tw, th = 384, 216
    W = 3 * tw + 40 + 1100
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    texts = [(wrap(q["zh"], f_txt, 1080, d), wrap(q["en"], f_small, 1080, d)) for q in quotes]
    heights = [max(th, 44 + 32 * len(zl) + 26 * len(el)) + 24 for zl, el in texts]
    im = Image.new("RGB", (W, sum(heights) + 20), (18, 18, 22))
    d = ImageDraw.Draw(im)
    y = 10
    for q, (zl, el), h in zip(quotes, texts, heights):
        for k, t in enumerate((0.05, q["dur"] / 2, q["dur"] - 0.05)):
            fr = td / f"{q['id']}_{k}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(FILM / q["file"]),
                            "-frames:v", "1", "-vf", f"scale={tw}:{th}", str(fr)], check=True)
            im.paste(Image.open(fr), (10 + k * (tw + 5), y))
            d.text((16 + k * (tw + 5), y + 4), f"{t:.2f}s", font=f_small, fill=(255, 230, 80))
        x = 3 * tw + 40
        d.text((x, y), f"{q['id']}  {q['who']}   in {q['in']:.2f}  out {q['out']:.2f}  dur {q['dur']:.2f}s  "
                        f"（插在 {q['after']} 后）", font=f_title, fill=(255, 200, 90))
        yy = y + 44
        for ln in zl:
            d.text((x, yy), ln, font=f_txt, fill=(240, 240, 240))
            yy += 32
        for ln in el:
            d.text((x, yy), ln, font=f_small, fill=(170, 200, 230))
            yy += 26
        y += h
    im.save(FILM / "out/原声_联系表.jpg", quality=90)


def wrap(s: str, font, width: int, d) -> list[str]:
    out, cur = [], ""
    unit = list(s) if re.search(r"[\u4e00-\u9fff]", s) else re.split(r"(?<= )", s)
    for u in unit:
        if d.textlength(cur + u, font=font) > width:
            out.append(cur)
            cur = u
        else:
            cur += u
    return out + [cur] if cur else out


if __name__ == "__main__":
    qs = build()
    if "--preview" in sys.argv:
        preview(qs)
