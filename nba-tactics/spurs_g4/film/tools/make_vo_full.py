"""从 文稿_v2.md 第 1–5 段抽旁白，按句拆成台词，生成数字读法。

usage: python tools/make_vo_full.py            → audio/vo_full.json、audio/quotes.json
台词 id：s<段>_<序号>；【原声】按出现顺序记 q<段>_<序号>，并记下它前面那句台词的 id。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "文稿_v2.md"

D = "零一二三四五六七八九"
MEASURE = "次个分秒英尺天罚投人步"
HYPE = {"补进了！", "一巴掌钉在了板上。"}


def cardinal(n):
    if n < 10:
        return D[n]
    if n < 20:
        return "十" + (D[n % 10] if n % 10 else "")
    if n < 100:
        return D[n // 10] + "十" + (D[n % 10] if n % 10 else "")
    if n < 1000:
        h, r = divmod(n, 100)
        if r == 0:
            return D[h] + "百"
        return D[h] + "百" + ("零" + D[r] if r < 10 else cardinal(r) if r >= 20 else "一" + cardinal(r))
    return "".join(D[int(c)] for c in str(n))


def say(text):
    s = re.sub(r"(\d{4})\s*年", lambda m: "".join(D[int(c)] for c in m.group(1)) + "年", text)
    s = re.sub(r"(\d+)%", lambda m: "百分之" + cardinal(int(m.group(1))), s)
    s = re.sub(r"(\d+)\.(\d+)", lambda m: cardinal(int(m.group(1))) + "点" + "".join(D[int(c)] for c in m.group(2)), s)

    def num(m):
        n, after = int(m.group(1)), m.group(2)
        if n == 2 and after and after[0] in MEASURE:
            return "两" + after
        return cardinal(n) + after

    s = re.sub(r"(\d+)\s*(\S?)", num, s)
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)


def sentences(p):
    out = re.findall(r"[^。？！]+[。？！]?", p)
    return [x.strip() for x in out if x.strip()]


lines, quotes = [], []
sec = None
for raw in SRC.read_text().splitlines():
    m = re.match(r"## (\d)\.", raw)
    if m:
        sec = int(m.group(1))
        n = 0
        continue
    if not sec:
        continue
    if raw.startswith("> ") and raw[2:].strip():
        for s in sentences(raw[2:].strip()):
            n += 1
            cue = re.match(r"（(.+?)）", s)
            s = re.sub(r"^（.+?）", "", s)
            ln = {"id": f"s{sec}_{n:02d}", "voice": "longfei_v3", "rate": 1.25,
                  "mood": "hype" if s in HYPE else "normal", "text": s}
            if cue:
                ln["cue"] = cue.group(1)
            sp = say(s)
            if sp != s:
                ln["say"] = sp
            lines.append(ln)
    elif raw.startswith("【原声】"):
        q = re.match(r"【原声】(.+?)：\"(.+)\"（(.+?)）", raw)
        quotes.append({"id": f"q{sec}_{sum(1 for x in quotes if x['id'].startswith(f'q{sec}_')) + 1}",
                       "after": lines[-1]["id"], "who": q.group(1), "en": q.group(2), "ref": q.group(3)})

(ROOT / "audio/vo_full.json").write_text("[\n" + ",\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n]\n")
(ROOT / "audio/quotes.json").write_text(json.dumps(quotes, ensure_ascii=False, indent=1))
print(len(lines), "lines,", len(quotes), "quotes,", round(sum(len(l["text"]) for l in lines) / 5.2 / 60, 1), "min est")
for l in lines:
    print(l["id"], l["text"], ("\n      say: " + l["say"]) if "say" in l else "")
for q in quotes:
    print(q)
