"""Bailian qwen-image generation (no identifiable people).

usage: python tools/genimg.py prompts.json out_dir [model]
prompts.json: [{"id": "...", "prompt": "...", "size": "1664*928"}]; skips existing files.
"""
import json
import sys
import urllib.request
from pathlib import Path

import dashscope

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(l.strip().split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)
dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

NEG = "清晰可辨认的人脸, 正脸, 名人, 文字, 水印, logo, 商标, 现代手机, 现代汽车, 卡通, 插画, 过度饱和, 畸形"

items = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
model = sys.argv[3] if len(sys.argv) > 3 else "qwen-image-3.0-pro"
for it in items:
    dst = out / f'{it["id"]}.png'
    if dst.exists():
        continue
    r = dashscope.MultiModalConversation.call(
        model=model,
        messages=[{"role": "user", "content": [{"text": it["prompt"]}]}],
        size=it.get("size", "1664*928"), negative_prompt=it.get("neg", NEG),
        prompt_extend=False, watermark=False, n=1)
    if r.status_code != 200:
        print(it["id"], "FAIL", r.code, r.message)
        continue
    url = next(c["image"] for c in r.output["choices"][0]["message"]["content"] if "image" in c)
    urllib.request.urlretrieve(url, dst)
    print(it["id"], "ok")
