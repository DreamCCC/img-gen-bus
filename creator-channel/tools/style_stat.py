"""Compare a script's spoken-style markers with the reference UP transcripts.

usage:
  python creator-channel/tools/style_stat.py [script.md ...]
Without arguments only the references are printed. Per-1000-character rates; 句均长 counts Chinese characters per sentence.
Lines starting with # and 【...】 cues are ignored; a "## 改了什么" section and everything after it is dropped.
"""
import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
MARKERS = {
    "问句": r"[？?]", "呢": "呢", "吧": "吧", "啊呀嘛": "[啊呀嘛]", "哎": "哎", "对吧": "对吧|对不对|是吧|是不是",
    "你": "你", "我们": "我们|咱们", "我": "我(?!们)", "那": "(?:^|[，。？\n])那", "所以": "所以", "就": "就",
    "比如": "比如|举个例子", "就是说": "也就是说|就是说|换句话说|简单来说",
}
TARGET = {"句均长": 28, "问句": 3, "呢": 3, "你": 4, "我们": 3, "就": 9, "比如": 1}


def clean(t):
    t = t.split("## 改了什么")[0]
    t = re.sub(r"^#.*$", "", t, flags=re.M)
    return re.sub(r"【[^】]*】", "", t)


def stats(t):
    zh = len(re.findall(r"[\u4e00-\u9fff]", t)) or 1
    lens = sorted(n for s in re.split(r"[。！？?!\n]", t) if (n := len(re.findall(r"[\u4e00-\u9fff]", s))) > 1)
    d = {"字": zh, "句均长": round(sum(lens) / len(lens), 1)}
    d.update({k: round(len(re.findall(p, t)) * 1000 / zh, 1) for k, p in MARKERS.items()})
    return d


def main():
    rows = []
    for p in sorted(glob.glob(str(HERE / "style_study/transcripts/*.txt"))):
        rows.append((Path(p).read_text().splitlines()[0][2:12], stats(clean(Path(p).read_text()))))
    for p in sys.argv[1:]:
        rows.append(("> " + Path(p).stem[:10], stats(clean(Path(p).read_text()))))
    keys = list(rows[0][1])
    print("".ljust(12), *[k[:4].rjust(5) for k in keys])
    for n, d in rows:
        print(n.ljust(12), *[str(d[k]).rjust(5) for k in keys])
    for n, d in rows:
        if n.startswith(">"):
            low = [f"{k} {d[k]} < {v}" for k, v in TARGET.items() if d[k] < v]
            print(n, "低于参考下限：" + ("；".join(low) if low else "无"))


if __name__ == "__main__":
    main()
