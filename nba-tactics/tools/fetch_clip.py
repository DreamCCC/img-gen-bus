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


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
        return r.read()


def local_hls(url: str, dest: Path) -> None:
    """Static ffmpeg builds can segfault resolving https hosts; download the playlist ourselves and mux from disk."""
    tmp = dest.with_suffix(".hls")
    tmp.mkdir(exist_ok=True)
    text = get(url).decode()
    if "#EXT-X-STREAM-INF" in text:
        url = urllib.parse.urljoin(url, [ln for ln in text.splitlines() if ln and not ln.startswith("#")][-1])
        text = get(url).decode()
    out, n = [], 0
    for ln in text.splitlines():
        if ln.startswith("#EXT-X-KEY") and 'URI="' in ln:
            uri = ln.split('URI="')[1].split('"')[0]
            (tmp / "key.bin").write_bytes(get(urllib.parse.urljoin(url, uri)))
            ln = ln.replace(uri, "key.bin")
        elif ln and not ln.startswith("#"):
            name = f"{n:04d}.ts"
            (tmp / name).write_bytes(get(urllib.parse.urljoin(url, ln)))
            ln, n = name, n + 1
        out.append(ln)
    (tmp / "list.m3u8").write_text("\n".join(out) + "\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-protocol_whitelist", "file,crypto", "-allowed_extensions", "ALL",
                    "-i", str(tmp / "list.m3u8"), "-c", "copy", "-bsf:a", "aac_adtstoasc", str(dest)], check=True)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def fetch(news_id: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    hdr = "".join(f"{k}: {v}\r\n" for k, v in HEADERS.items())
    url = play_url(news_id)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-headers", hdr, "-i", url,
                        "-c", "copy", "-bsf:a", "aac_adtstoasc", str(dest)])
    if r.returncode != 0:
        dest.unlink(missing_ok=True)
        local_hls(url, dest)
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
