"""下载 YouTube 视频（经 TikHub 取直链）：python tools/yt_get.py 视频ID 输出.mp4 [最高分辨率=1080]"""
import subprocess
import sys
import tempfile
from pathlib import Path

from tikhub import call


def walk(o):
    if isinstance(o, dict):
        if "url" in o and "mime_type" in o:
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


vid, dst = sys.argv[1], Path(sys.argv[2])
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
d = call(f"/api/v1/youtube/web_v2/get_video_streams?video_id={vid}")
fs = list(walk(d))
print(d["data"].get("author"), "|", d["data"].get("title"))
vids = sorted((f for f in fs if f["mime_type"] == "video/mp4" and f.get("height") and f["height"] <= cap), key=lambda f: (f["height"], f["bitrate"]))
auds = [f for f in fs if f["mime_type"] == "audio/mp4"]
if not vids or not auds:
    sys.exit("no mp4 streams")
tmp = Path(tempfile.mkdtemp(dir=dst.parent))
v, a = tmp / "v.mp4", tmp / "a.m4a"
for f, p in [(vids[-1], v), (auds[0], a)]:
    subprocess.check_call(["curl", "-sSL", "--retry", "3", "--max-time", "1800", "-A", "Mozilla/5.0", "-o", str(p), f["url"]])
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(v), "-i", str(a), "-c", "copy", str(dst)])
v.unlink(); a.unlink(); tmp.rmdir()
print("saved", dst, f'{vids[-1]["height"]}p')
