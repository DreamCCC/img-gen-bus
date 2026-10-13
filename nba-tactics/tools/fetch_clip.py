#!/usr/bin/env python3
"""news_id -> videoPlay 签名 m3u8 -> mp4。本机直连即可，不需要白名单；接口偶发 403 限流，会退避重试。

用法: python fetch_clip.py <news_id> [<news_id> ...] -d raw/
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://testapi.nba.cn/nba-web/api/web/content/videoPlay"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://testapi.nba.cn/",
}


def play_url(news_id: str, tries: int = 6) -> str:
    req = urllib.request.Request(f"{ENDPOINT}?{urllib.parse.urlencode({'newsId': news_id})}", headers=HEADERS)
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                obj = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code != 403 or i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    if obj.get("code") != 0 or not (obj.get("data") or {}).get("url"):
        raise RuntimeError(f"videoPlay {news_id}: code={obj.get('code')} msg={obj.get('msg')}")
    return obj["data"]["url"]


def fetch(news_id: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    hdr = "".join(f"{k}: {v}\r\n" for k, v in HEADERS.items())
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-headers", hdr, "-i", play_url(news_id),
         "-c", "copy", "-bsf:a", "aac_adtstoasc", str(dest)],
        check=True,
    )
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("news_ids", nargs="+")
    ap.add_argument("-d", "--dir", default=".")
    a = ap.parse_args()
    for nid in a.news_ids:
        p = fetch(nid, Path(a.dir) / f"{nid}.mp4")
        info = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate:format=duration", "-of", "csv=p=0", str(p)],
            capture_output=True, text=True,
        ).stdout.split()
        print(nid, p, " ".join(info))


if __name__ == "__main__":
    main()
