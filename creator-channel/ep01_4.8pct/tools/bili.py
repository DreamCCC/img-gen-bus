"""B 站检索（经 TikHub）。
python tools/bili.py search "关键词" [页数]      列出 BV | UP主(mid) | 时长 | 播放 | 标题
python tools/bili.py up 用户mid "关键词"         在某个 UP 主的投稿里按关键词搜
python tools/bili.py get BV号 输出.mp4            下载（DASH 最高画质 + 音频合并）
"""
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

from tikhub import call


def walk(o, key):
    if isinstance(o, dict):
        if key in o:
            yield o
        for v in o.values():
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, key)


def clean(s):
    return re.sub(r"<[^>]+>", "", s or "")


CURL = ["curl", "-sSLf", "--retry", "8", "--retry-all-errors", "--retry-delay", "2", "--max-time", "900",
        "-A", "Mozilla/5.0", "-e", "https://www.bilibili.com/"]
CURL_SEG = ["curl", "-sSLf", "--max-time", "900", "-A", "Mozilla/5.0", "-e", "https://www.bilibili.com/"]


def fetch_ranged(url, dst, parts=16):
    """B 站 CDN 单连接限速，按 Range 分段并行拉取再拼接。"""
    head = subprocess.run(CURL + ["-r", "0-0", "-o", "/dev/null", "-D", "-", url], capture_output=True, text=True)
    m = re.search(r"content-range: bytes 0-0/(\d+)", head.stdout, re.I)
    if not m:
        return False
    size = int(m.group(1))
    step = -(-size // parts)
    rng = [(i * step, min(size, (i + 1) * step) - 1) for i in range(parts)]

    def seg(i):
        a, b = rng[i]
        p = Path(f"{dst}.{i}")
        for _ in range(10):
            have = p.stat().st_size if p.exists() else 0
            if have >= b - a + 1:
                break
            with open(p, "ab") as f:
                subprocess.run(CURL_SEG + ["-r", f"{a + have}-{b}", url], stdout=f)
        return p.exists() and p.stat().st_size == b - a + 1

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(parts) as ex:
        if not all(ex.map(seg, range(parts))):
            return False
    with open(dst, "wb") as out:
        for i in range(parts):
            seg = Path(f"{dst}.{i}")
            out.write(seg.read_bytes())
            seg.unlink()
    return Path(dst).stat().st_size == size


cmd = sys.argv[1]
if cmd == "search":
    q = sys.argv[2]
    for pg in range(1, (int(sys.argv[3]) if len(sys.argv) > 3 else 1) + 1):
        d = call(f"/api/v1/bilibili/web/fetch_general_search?keyword={urllib.parse.quote(q)}&order=totalrank&page={pg}&page_size=42")
        for v in walk(d, "bvid"):
            if v.get("type") not in (None, "video"):
                continue
            print(v["bvid"], "|", v.get("author"), f'({v.get("mid")})', "|", v.get("duration"), "|", v.get("play"), "|", clean(v.get("title"))[:80])
elif cmd == "up":
    d = call(f"/api/v1/bilibili/web/fetch_user_post_videos_v2?uid={sys.argv[2]}&pn=1&ps=30&keyword={urllib.parse.quote(sys.argv[3])}")
    for v in walk(d, "bvid"):
        print(v["bvid"], "|", v.get("length") or v.get("duration"), "|", v.get("play"), "|", clean(v.get("title"))[:90])
elif cmd == "get":
    bv, dst = sys.argv[2], Path(sys.argv[3])
    info = call(f"/api/v1/bilibili/web/fetch_one_video?bv_id={bv}")
    vd = next(walk(info, "cid"))
    print(vd.get("owner", {}).get("name"), "|", vd.get("title"))
    d = call(f"/api/v1/bilibili/web/fetch_video_playurl?bv_id={bv}&cid={vd['cid']}")
    dash = next(walk(d, "dash"))["dash"]
    v = max((x for x in dash["video"] if x.get("codecs", "").startswith("avc")), key=lambda x: (x["height"], x["bandwidth"]))
    a = max(dash["audio"], key=lambda x: x["bandwidth"])
    tmp = Path(tempfile.mkdtemp(dir=dst.parent))
    for x, p in [(v, tmp / "v.m4s"), (a, tmp / "a.m4s")]:
        urls = [x.get("baseUrl") or x["base_url"]] + (x.get("backupUrl") or x.get("backup_url") or [])
        if not any(fetch_ranged(u, p) for u in urls):
            sys.exit(f"download failed: {bv}")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "v.m4s"), "-i", str(tmp / "a.m4s"), "-c", "copy", str(dst)])
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print("saved", dst, f'{v["width"]}x{v["height"]}')
