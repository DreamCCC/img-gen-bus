"""qwen-image-edit：以参考图为底按提示词改图，保持角色一致。

usage: python edit.py jobs.json out_dir
jobs.json: [{"id": "...", "refs": ["相对 jobs.json 的图片", ...], "prompt": "...", "neg": "...", "size": "1664*928"}]；已存在的跳过。
"""
import base64
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope

ENV_FILE = Path(__file__).resolve().parents[3] / "ep01_4.8pct/.env"
ENV = dict(l.strip().split("=", 1) for l in ENV_FILE.read_text().splitlines() if "=" in l)
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
MODEL = "qwen-image-3.0-pro"


def data_url(p):
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def run(it):
    dst = out / f'{it["id"]}.png'
    if dst.exists():
        return it["id"], "exists"
    content = [{"image": data_url(spec.parent / r)} for r in it["refs"]] + [{"text": it["prompt"]}]
    kw = {k: it[v] for k, v in (("negative_prompt", "neg"), ("size", "size")) if it.get(v)}
    try:
        r = dashscope.MultiModalConversation.call(model=it.get("model", MODEL), messages=[{"role": "user", "content": content}],
                                                  watermark=False, n=1, **kw)
    except Exception as e:
        return it["id"], f"ERROR {type(e).__name__}"
    if r.status_code != 200:
        return it["id"], f"FAIL {r.code} {r.message}"
    url = next(c["image"] for c in r.output["choices"][0]["message"]["content"] if "image" in c)
    urllib.request.urlretrieve(url, dst)
    return it["id"], "ok"


spec = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
with ThreadPoolExecutor(4) as ex:
    for sid, msg in ex.map(run, json.loads(spec.read_text())):
        print(sid, msg, flush=True)
