"""YouTube 搜索（经 TikHub）：python tools/yt_search.py "关键词" [...]，列出 视频ID | 频道 | 时长 | 标题。"""
import sys
import urllib.parse

from tikhub import call


def walk(o, key):
    if isinstance(o, dict):
        if key in o:
            yield o[key]
        for v in o.values():
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, key)


def txt(x):
    if not x:
        return ""
    return x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs", []))


for q in sys.argv[1:]:
    d = call("/api/v1/youtube/web_v2/get_general_search?search_query=" + urllib.parse.quote(q))
    print("==", q)
    for v in walk(d, "videoRenderer"):
        print(v.get("videoId"), "|", txt(v.get("ownerText")), "|", txt(v.get("lengthText")), "|", txt(v.get("title"))[:100])
