"""万相 wan3.0 视频生成：提交 → 轮询 → 下载。key 从 ep01_4.8pct/.env 的 DASHSCOPE_API_KEY 读取。

usage:
  python creator-channel/tools/wan_video.py out.mp4 "提示词" [--dur 5] [--res 720P] [--ratio 16:9] [--first 首帧.png] [--last 尾帧.png] [--audio 驱动音频.wav] [--seed N] [--model wan3.0-video]
不给 --audio 时无声输出（audio=false）；关闭水印。WAN_BASE 环境变量可换接口地址（默认北京地域通用地址）。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ep01_4.8pct/tools"))
from tts import ENV  # noqa: E402

BASE = os.environ.get("WAN_BASE", "https://dashscope.aliyuncs.com/api/v1")
KEY = ENV["DASHSCOPE_API_KEY"]


def req(method, path, body=None, extra=None):
    h = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", **(extra or {})}
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            return json.loads(f.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")


def data_url(p):
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[Path(p).suffix.lower()]
    return f"data:{mime};base64," + base64.b64encode(Path(p).read_bytes()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("prompt")
    ap.add_argument("--dur", type=int, default=5)
    ap.add_argument("--res", default="720P")
    ap.add_argument("--ratio", default="16:9")
    ap.add_argument("--first")
    ap.add_argument("--last")
    ap.add_argument("--audio", help="驱动音频（wav/mp3），口型和动作跟着它走；先传到百炼临时存储")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--model", default="wan3.0-video")
    a = ap.parse_args()

    inp = {"prompt": a.prompt}
    media = [{"type": t, "url": data_url(p)} for t, p in (("first_frame", a.first), ("last_frame", a.last)) if p]
    extra = {"X-DashScope-Async": "enable"}
    if a.audio:
        from dashscope.utils.oss_utils import OssUtils
        url = OssUtils.upload(model=a.model, file_path=a.audio, api_key=KEY)
        media.append({"type": "driving_audio", "url": url[0] if isinstance(url, tuple) else url})
        extra["X-DashScope-OssResourceResolve"] = "enable"
    if media:
        inp["media"] = media
    params = {"resolution": a.res, "ratio": "adaptive" if media else a.ratio, "duration": a.dur, "watermark": False, "prompt_extend": True}
    if not a.audio:
        params["audio"] = False
    if a.seed is not None:
        params["seed"] = a.seed
    r = req("POST", "/services/aigc/video-generation/video-synthesis", {"model": a.model, "input": inp, "parameters": params}, extra)
    tid = r["output"]["task_id"]
    print("task", tid, flush=True)
    t0 = time.time()
    while True:
        time.sleep(10)
        o = req("GET", f"/tasks/{tid}")["output"]
        st = o["task_status"]
        if st == "SUCCEEDED":
            break
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            sys.exit(f"{st}: {o.get('code')} {o.get('message')}")
        print(f"  {st} {time.time() - t0:.0f}s", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sSL", "--retry", "3", "-o", a.out, o["video_url"]], check=True)
    Path(a.out).with_suffix(".json").write_text(json.dumps(dict(model=a.model, prompt=a.prompt, params=params, first=a.first, last=a.last,
                                                                 actual_prompt=o.get("actual_prompt"), task_id=tid), ensure_ascii=False, indent=1))
    print("saved", a.out, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
