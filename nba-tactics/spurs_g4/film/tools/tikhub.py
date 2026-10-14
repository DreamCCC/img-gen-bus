"""TikHub 抖音检索 / 下载小工具。key 从 <项目根目录>/.env 的 TIKHUB_API_KEY 读取。
用法：
  python tikhub.py users  关键词              # 搜账号（看认证信息，找官方号）
  python tikhub.py videos 关键词 [页数]       # 搜视频，列出作者、认证、时长、点赞
  python tikhub.py posts  sec_uid [页数]      # 某账号的作品列表
  python tikhub.py get    aweme_id 输出.mp4   # 下载最高画质
"""
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(l.strip().split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)
BASE = "https://api.tikhub.io"
HDR = {"Authorization": "Bearer " + ENV["TIKHUB_API_KEY"], "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def call(path, params=None, body=None, retries=3):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=HDR, method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:600]
            if attempt == retries - 1:
                sys.exit(f"HTTP {e.code} {path}: {msg}")
            time.sleep(2 + attempt * 3)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == retries - 1:
                sys.exit(f"network error {path}: {e}")
            time.sleep(2 + attempt * 3)


def walk(o, key):
    """在任意嵌套结构里找出所有名为 key 的字段值。"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, key)


OFFICIAL = {"MS4wLjABAAAAGT6rLfDddeLe43Sb9VzfouQjHWZ20BWn16m1h5Zz0ZA": "NBA官方"}


def describe(aw):
    a = aw.get("author", {})
    tag = "★" + OFFICIAL[a.get("sec_uid")] if a.get("sec_uid") in OFFICIAL else "  "
    verify = a.get("custom_verify") or a.get("enterprise_verify_reason") or ""
    st = aw.get("statistics", {})
    dur = aw.get("duration") or aw.get("video", {}).get("duration") or 0
    return f'{tag} {aw.get("aweme_id")} | {a.get("nickname")} [{verify}] | {dur / 1000:.0f}s | 赞{st.get("digg_count")} | {aw.get("desc", "")[:60]}'


def main():
    cmd = sys.argv[1]
    if cmd == "raw":
        # python tikhub.py raw 路径 '{"json":"body"}'  → 原始响应写到 out/tk_raw.json
        d = call(sys.argv[2], body=json.loads(sys.argv[3])) if len(sys.argv) > 3 else call(sys.argv[2])
        (ROOT / "out/tk_raw.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(json.dumps(d, ensure_ascii=False)[:1500])
    elif cmd == "users":
        d = call("/api/v1/douyin/search/fetch_user_search_v2", body={"keyword": sys.argv[2], "cursor": 0})
        for u in d.get("data", {}).get("data", {}).get("user_list", []):
            extra = {k: v for k, v in u.items() if "verif" in k or "auth" in k}
            print(f'{u.get("nick_name")} | 粉丝{u.get("fans_cnt")} | 作品{u.get("publish_cnt")} | {extra} | sec_uid={u.get("user_id")}')
    elif cmd == "videos":
        pages = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        body = {"keyword": sys.argv[2], "cursor": 0, "sort_type": "1", "content_type": "1"}
        seen = set()
        for _ in range(pages):
            d = call("/api/v1/douyin/search/fetch_video_search_v2", body=body)
            for aw in walk(d, "aweme_info"):
                if isinstance(aw, dict) and aw.get("aweme_id") not in seen:
                    seen.add(aw.get("aweme_id"))
                    print(describe(aw))
            nxt = d.get("data", {})
            body.update(cursor=nxt.get("cursor", 0), search_id=str(next(walk(d, "search_id"), "")), backtrace=nxt.get("backtrace", ""))
    elif cmd == "posts":
        pages = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        cur = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        for _ in range(pages):
            d = call("/api/v1/douyin/app/v3/fetch_user_post_videos", params={"sec_user_id": sys.argv[2], "max_cursor": cur, "count": 20})
            for aw in d.get("data", {}).get("aweme_list", []):
                print(describe(aw), flush=True)
            cur = d.get("data", {}).get("max_cursor", 0)
            print("#cursor", cur, flush=True)
            if not d.get("data", {}).get("has_more"):
                break
    elif cmd == "get":
        d = call("/api/v1/douyin/app/v3/fetch_video_high_quality_play_url", params={"aweme_id": sys.argv[2]})
        urls = [u for u in walk(d, "original_video_url")] + [u for u in walk(d, "url") if isinstance(u, str) and u.startswith("http")]
        if not urls:
            print(json.dumps(d, ensure_ascii=False)[:800])
            sys.exit(1)
        part = sys.argv[3] + ".part"
        for attempt in range(5):
            rc = subprocess.call(["curl", "-sSL", "-C", "-", "--retry", "3", "--max-time", "900",
                                  "-A", "Mozilla/5.0", "-e", "https://www.douyin.com/", "-o", part, urls[0]])
            if rc == 0:
                Path(part).rename(sys.argv[3])
                print("saved", sys.argv[3])
                return
        sys.exit(f"download failed: {sys.argv[3]}")


if __name__ == "__main__":
    main()
