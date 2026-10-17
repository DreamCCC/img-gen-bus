"""英文旁白的字幕分段和关键词时刻，按 words.json（tools/vo_words.py）的词级时间对齐。

台词文本和识别结果先各自规整成小写单词序列（数字展开成英文读法、连字符拆开），用 difflib 对齐；
对不上的词在前后两个对齐点之间按序号插值。
"""
import difflib
import re

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_words(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        h, r = divmod(n, 100)
        return [ONES[h], "hundred"] + (num_words(r) if r else [])
    if 1900 <= n < 2000:
        return num_words(n // 100) + num_words(n % 100)
    th, r = divmod(n, 1000)
    return num_words(th) + ["thousand"] + (num_words(r) if r else [])


def tokens(text):
    out = []
    for raw in re.findall(r"[A-Za-z0-9.'’:-]+", text):
        for part in re.split(r"[-:]", raw):
            part = part.strip(".'’").lower().replace("’", "'")
            if not part:
                continue
            m = re.fullmatch(r"(\d+)\.(\d+)", part)
            if m:
                out += num_words(int(m.group(1))) + ["point"] + [ONES[int(c)] for c in m.group(2)]
            elif part.isdigit():
                out += num_words(int(part))
            else:
                out.append(re.sub(r"[^a-z']", "", part))
    return [t for t in out if t]


def token_times(text, words, dur):
    """台词文本里每个单词的起始时刻（秒）。"""
    ta = tokens(text)
    tb, tt = [], []
    for w, a, b in words:
        for tok in tokens(w):
            tb.append(tok)
            tt.append(a)
    anchors = [(0, 0.0)]
    for blk in difflib.SequenceMatcher(a=ta, b=tb, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            anchors.append((blk.a + k, tt[blk.b + k]))
    anchors.append((len(ta), dur))
    anchors.sort()
    out = []
    j = 0
    for i in range(len(ta)):
        while j + 1 < len(anchors) and anchors[j + 1][0] <= i:
            j += 1
        (i0, t0), (i1, t1) = anchors[j], anchors[min(j + 1, len(anchors) - 1)]
        out.append(t0 if i1 == i0 else t0 + (t1 - t0) * (i - i0) / (i1 - i0))
    return out


def key_time(text, words, dur, key):
    """key（台词里的一段原文）开始念的时刻。"""
    ta, kt = tokens(text), tokens(key)
    for i in range(len(ta) - len(kt) + 1):
        if ta[i:i + len(kt)] == kt:
            return token_times(text, words, dur)[i]
    raise KeyError(f"{key!r} not in {text!r}")


def split_text(text, maxc=44):
    """按句号、问号、逗号等切成字幕行；超长的从中间附近的词间断开。"""
    parts = [p.strip() for p in re.split(r"(?<=[.?!,;:])\s+", text) if p.strip()]
    merged = []
    for p in parts:
        if merged and not re.search(r"[.?!]$", merged[-1]) and len(merged[-1]) + 1 + len(p) <= maxc:
            merged[-1] += " " + p
        elif merged and len(p) <= 12 and len(merged[-1]) + 1 + len(p) <= maxc:
            merged[-1] += " " + p
        else:
            merged.append(p)
    out = []
    for p in merged:
        while len(p) > maxc:
            sp = [m.start() for m in re.finditer(" ", p)]
            cut = min(sp, key=lambda i: abs(i - len(p) / 2))
            out.append(p[:cut])
            p = p[cut + 1:]
        out.append(p)
    return out


def chunks(text, words, dur, maxc=44):
    lines = split_text(text, maxc)
    times = token_times(text, words, dur)
    out, k = [], 0
    for ln in lines:
        out.append({"text": re.sub(r"[,.;:]$", "", ln), "a": round(times[k] if k < len(times) else dur, 3)})
        k += len(tokens(ln))
    out[0]["a"] = 0.0
    for c, nx in zip(out, out[1:] + [None]):
        c["b"] = nx["a"] if nx else round(dur, 3)
    return out
