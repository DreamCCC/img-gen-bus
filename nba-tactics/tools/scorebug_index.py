"""转播视频的记分牌索引：每隔 N 秒裁一次记分牌，百炼 qwen-vl-ocr 读出节次、时钟、比分。

usage: python scorebug_index.py in.mp4 out.json [--every 2] [--crop 440,945,1040,120] [--workers 4]
输出 [{"t": 秒, "period": 4, "clock": "2:52", "sa": 104, "ny": 100} 或 {"t": 秒, "none": true}]
密钥：DASHSCOPE_API_KEY，依次找 nba-tactics/.env、spurs_g4/film/.env。
"""
import argparse
import base64
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope

HERE = Path(__file__).resolve().parent
for p in (HERE.parent / ".env", HERE.parent / "spurs_g4/film/.env"):
    if p.exists():
        env = dict(l.strip().split("=", 1) for l in p.read_text().splitlines() if "=" in l)
        if "DASHSCOPE_API_KEY" in env:
            dashscope.api_key = env["DASHSCOPE_API_KEY"]
            break

MODEL = "qwen3-vl-plus"
PROMPT = ("这是 ESPN 篮球转播底部的记分牌，从左到右依次是：ESPN 台标、SA、SA 的分数、NY、NY 的分数、"
          "节次（如 4TH）、比赛时钟（如 6:24 或 19.6）、最右边一个小数字是进攻时钟。"
          '只输出一行 JSON：{"period": 节次数字, "clock": "比赛时钟原样", "shot": 进攻时钟数字, "sa": SA 分数, "ny": NY 分数}。'
          "看不到记分牌就输出 {\"none\": true}。")


def grab(src, t, crop):
    x, y, w, h = crop
    return subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                           "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "image2", "-c:v", "png", "-"],
                          capture_output=True, check=True).stdout


def ocr(png):
    b64 = "data:image/png;base64," + base64.b64encode(png).decode()
    for k in range(4):
        r = dashscope.MultiModalConversation.call(model=MODEL, messages=[
            {"role": "user", "content": [{"image": b64}, {"text": PROMPT}]}])
        if r.status_code == 200:
            txt = r.output.choices[0].message.content[0]["text"]
            m = re.search(r"\{.*\}", txt, re.S)
            try:
                return json.loads(m.group(0)) if m else {"none": True}
            except json.JSONDecodeError:
                return {"raw": txt}
        time.sleep(2 * (k + 1))
    return {"err": r.message}


def norm(d):
    if "period" in d:
        p = re.sub(r"\D", "", str(d["period"]))
        d["period"] = int(p) if p else None
    for k in ("sa", "ny"):
        if k in d:
            try:
                d[k] = int(d[k])
            except (TypeError, ValueError):
                d[k] = None
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--crop", default="440,945,1040,120")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    crop = [int(v) for v in a.crop.split(",")]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src]))
    ts = [round(i * a.every, 2) for i in range(int(dur / a.every))]

    def job(t):
        return {"t": t, **norm(ocr(grab(a.src, t, crop)))}

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(job, ts))
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=0))
    ok = [r for r in res if "clock" in r]
    print(f"{a.src}: {len(ok)}/{len(res)} frames with scorebug")
