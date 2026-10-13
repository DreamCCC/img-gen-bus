#!/usr/bin/env python3
"""联网检索：经 AIHubMix 调用带搜索的模型（默认 gemini-3.1-pro-preview-search），返回回答和引用链接。

key 读 AIHUBMIX_API_KEY：先找 nba-tactics/.env，找不到用 creator-channel/ep01_4.8pct/.env。不打印 key。
要在沙箱外运行（aihubmix.com 不在网络白名单里）。

用法:
  python web_search.py "问题" [-m 模型] [-o out.json]
代码里:
  from web_search import search; text, urls = search("问题")
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for env in (HERE / ".env", HERE.parent / "creator-channel/ep01_4.8pct/.env"):
    if env.exists():
        ENV = dict(l.strip().split("=", 1) for l in env.read_text().splitlines() if "=" in l)
        if ENV.get("AIHUBMIX_API_KEY"):
            break
KEY = ENV["AIHUBMIX_API_KEY"]
ENDPOINT = "https://aihubmix.com/v1/chat/completions"


def search(question: str, model: str = "gemini-3.1-pro-preview-search", timeout: int = 180) -> tuple[str, list[str]]:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": question}]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    msg = d["choices"][0]["message"]
    text = msg.get("content") or ""
    urls = [a.get("url_citation", {}).get("url") for a in msg.get("annotations") or [] if a.get("type") == "url_citation"]
    urls += re.findall(r"https?://[^\s)\]>\"']+", text)
    return text, list(dict.fromkeys(u for u in urls if u))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("-m", "--model", default="gemini-3.1-pro-preview-search")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    text, urls = search(a.question, a.model)
    print(text)
    print("\n== 链接 ==")
    for u in urls:
        print(u)
    if a.out:
        Path(a.out).write_text(json.dumps({"q": a.question, "model": a.model, "text": text, "urls": urls},
                                          ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
