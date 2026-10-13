"""把 文稿_全片v1.md 拆成逐句的配音表 audio/vo_lines.json。

每句：id（H 冷开场，A–F 第一到六章）、text（字幕，保留阿拉伯数字）、say（念的，数字转汉字）、cue（这一段开头的画面提示）。
usage: python tools/split_script.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "文稿_全片v1.md"
DST = ROOT / "audio/vo_lines.json"
VOICE = "longsanshu_v3"
SECTIONS = {"冷开场": "H", "第一章": "A", "第二章": "B", "第三章": "C", "第四章": "D", "第五章": "E", "第六章": "F"}
DIG = "零一二三四五六七八九"
MOOD = {"整版已销毁": "quiet", "这期就讲到这儿": "quiet", "叫混沌": "hype", "这回是真走了": "hype"}


def int_zh(n):
    if n == 0:
        return "零"
    if n >= 100000000:
        hi, lo = divmod(n, 100000000)
        return int_zh(hi) + "亿" + (("零" if lo < 10000000 else "") + int_zh(lo) if lo else "")
    if n >= 10000:
        hi, lo = divmod(n, 10000)
        return int_zh(hi) + "万" + (("零" if lo < 1000 else "") + int_zh(lo) if lo else "")
    out, zero = "", False
    for unit, v in ((1000, "千"), (100, "百"), (10, "十")):
        d, n = divmod(n, unit)
        if d:
            if zero:
                out += "零"
            out += ("两" if d == 2 and unit >= 100 else DIG[d]) + v
            zero = False
        elif out:
            zero = True
    if n:
        out += ("零" if zero else "") + DIG[n]
    return out[1:] if out.startswith("一十") else out


def num_zh(s):
    if "." in s:
        a, b = s.split(".")
        return int_zh(int(a)) + "点" + "".join(DIG[int(c)] for c in b)
    return int_zh(int(s))


def say(text):
    s = re.sub(r"(\d{4})\s*年", lambda m: "".join(DIG[int(c)] for c in m.group(1)) + "年", text)
    s = re.sub(r"\d+(?:\.\d+)?", lambda m: num_zh(m.group(0)), s)
    s = s.replace("α", "阿尔法").replace("米塔格-莱弗勒", "米塔格莱弗勒").replace("个0", "个零")
    return re.sub(r"\s+", "", s)


def sentences(par):
    out, buf = [], ""
    for ch in par:
        buf += ch
        if ch in "。？！":
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def main():
    lines, sec, n = [], None, 0
    for raw in SRC.read_text().splitlines():
        if raw.startswith("## "):
            sec = next(v for k, v in SECTIONS.items() if raw[3:].startswith(k))
            n = 0
            continue
        if not sec or not raw.strip() or raw.startswith("#"):
            continue
        cue = "；".join(re.findall(r"【(.*?)】", raw))
        body = re.sub(r"【.*?】", "", raw).strip()
        for i, t in enumerate(sentences(body)):
            n += 1
            ln = {"id": f"{sec}{n:02d}", "voice": VOICE, "text": t}
            sy = say(t)
            if sy != re.sub(r"\s+", "", t):
                ln["say"] = sy
            if i == 0 and cue:
                ln["cue"] = cue
            if i == 0:
                ln["par"] = True
            for k, m in MOOD.items():
                if k in t:
                    ln["mood"] = m
            lines.append(ln)
    DST.write_text(json.dumps(lines, ensure_ascii=False, indent=1))
    print(len(lines), "lines,", sum(len(l["text"]) for l in lines), "chars")
    for ln in lines:
        if "say" in ln:
            print(ln["id"], ln["say"])


if __name__ == "__main__":
    main()
