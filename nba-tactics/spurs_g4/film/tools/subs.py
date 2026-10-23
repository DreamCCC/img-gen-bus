"""English captions as ASS (burned in with ffmpeg `subtitles=...:fontsdir=assets/fonts`).

build(defs, vo_at, words, out)
  defs   [{"vo": "a2", "w": [0, 14], "text": "The shot clock is *longer than the game*, ..."}, ...]
         "w" = first/last word index in words.json (whole line if omitted); *...* = accent (gold, bold).
         {"at": [t0, t1], "text": ..., "kind": "quote"} places a caption by absolute time (interview soundbites).
  vo_at  {vo id: absolute start time in the cut (s)}
  words  vo_dir/words.json from work/asr_words.py
Timing: start 0.08 s before the first word, end 0.45 s after the last; a gap shorter than HOLD to the next caption is
bridged so lines never blink; minimum on-screen time MIN_DUR. One line up to ~80 characters (horizontal frame).
Look: Inter SemiBold on a blurred dark pill, 0.22 s fade with an 8 px rise; sits above the broadcast score bug
(which occupies y 945-1060), so every code scene keeps y > 860 clear.
"""
import json
import re
from pathlib import Path

from PIL import ImageFont

FONTS = Path(__file__).resolve().parent.parent / "assets/fonts"
SIZE, Y, HOLD, MIN_DUR = 52, 928, 0.7, 1.5
WHITE, GOLD = "&H00F6F4F2&", "&H0045C8FF&"
HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,{SIZE},{WHITE},{WHITE},&H00000000&,&H00000000&,0,0,0,0,100,100,0.4,0,1,0,0,2,0,0,0,1
Style: Box,Inter SemiBold,{SIZE},&H00140A05&,&H00140A05&,&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Who,Inter SemiBold,30,&H00C8C0B8&,&H00C8C0B8&,&H00000000&,&H00000000&,0,0,0,0,100,100,3,0,1,0,0,2,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t: float) -> str:
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def width(text: str) -> float:
    plain = text.replace("*", "")
    f = ImageFont.truetype(str(FONTS / "Inter-SemiBold.ttf"), round(SIZE / 1.21))
    return f.getlength(plain) * 1.03 + 0.4 * len(plain)


def styled(text: str) -> str:
    return re.sub(r"\*(.+?)\*", lambda m: f"{{\\b1\\c{GOLD}}}{m.group(1)}{{\\b0\\c{WHITE}}}", text)


def timed(defs, vo_at, words):
    out = []
    for d in defs:
        if "at" in d:
            out.append([d["at"][0], d["at"][1], d])
            continue
        w = words[d["vo"]]
        i, j = d.get("w", [0, len(w) - 1])
        out.append([vo_at[d["vo"]] + w[i][1] - 0.08, vo_at[d["vo"]] + w[j][2] + 0.45, d])
    out.sort(key=lambda x: x[0])
    for k, c in enumerate(out):
        nxt = out[k + 1][0] if k + 1 < len(out) else None
        c[1] = max(c[1], c[0] + MIN_DUR)
        if nxt is not None:
            if nxt - c[1] < HOLD:
                c[1] = nxt - 0.04
            c[1] = min(c[1], nxt - 0.04)
    return out


def build(defs, vo_at, words, out: Path) -> None:
    ev = []
    for t0, t1, d in timed(defs, vo_at, words):
        w = width(d["text"])
        x0, x1, y0, y1 = 960 - w / 2 - 44, 960 + w / 2 + 44, Y - 64, Y + 14
        fade = r"\fad(220,220)"
        box = (f"{{\\an7\\pos(0,0){fade}\\blur22\\1a&H5A&\\p1}}m {x0:.0f} {y0:.0f} l {x1:.0f} {y0:.0f} {x1:.0f} {y1:.0f} "
               f"{x0:.0f} {y1:.0f}{{\\p0}}")
        ev.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},Box,,0,0,0,,{box}")
        rise = f"\\move(960,{Y + 8},960,{Y},0,260)"
        ev.append(f"Dialogue: 1,{ts(t0)},{ts(t1)},Cap,,0,0,0,,{{{rise}{fade}}}{styled(d['text'])}")
        if d.get("who"):
            ev.append(f"Dialogue: 1,{ts(t0)},{ts(t1)},Who,,0,0,0,,{{\\move(960,{Y - 70},960,{Y - 78},0,260){fade}}}{d['who']}")
    out.write_text(HEAD + "\n".join(ev) + "\n", encoding="utf-8")


def load_words(vo_dir: Path) -> dict:
    return json.loads((vo_dir / "words.json").read_text(encoding="utf-8"))
