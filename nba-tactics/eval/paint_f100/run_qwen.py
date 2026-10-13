#!/usr/bin/env python3
"""评测题：第 100 帧真实画面，定位禁区四角。

参考答案（人工 5 倍放大读点，投影核对：限制区弧贴合约 2px，四角处偏差 ≤5px）:
  FT_FAR  罚球线远端 (19,-8) -> (656,610)
  FT_NEAR 罚球线近端 (19,+8) -> (816,814)
  BL_FAR  底线远端   (0,-8)  -> (1280,543)
  BL_NEAR 底线近端   (0,+8)  -> (1530,738)
用法: python run_qwen.py <model> [<model> ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import dashscope
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "kyrie_macau" / "work" / "e7"))
import vlm  # noqa: E402,F401  加载 api key

FRAME = HERE.parents[1] / "kyrie_macau" / "work" / "e7" / "fr" / "orig" / "0100.jpg"
G = np.load(HERE / "G_f100.npy")
TRUTH = {"FT_FAR": (656, 610), "FT_NEAR": (816, 814), "BL_FAR": (1280, 543), "BL_NEAR": (1530, 738)}
VIEWS = {"full": (0, 0, 1920, 1080), "crop": (500, 400, 1700, 900)}
RUNS = 3

PROMPT = """这是一帧 NBA 转播画面。画面中间有一块红色的禁区（油漆区），它在地板上是一个矩形，透视后看起来是四边形：
- 左边那条白线是罚球线；
- 右边那条白线是底线（篮筐在它上方），底线把禁区和场外的红色区域分开；
- 上下两条边是禁区的两条边线，"上"是离镜头远的一边，"下"是离镜头近的一边。
请定位禁区四个角（白线交点的中心）：
FT_FAR = 罚球线和远侧边线的交点；FT_NEAR = 罚球线和近侧边线的交点；
BL_FAR = 底线和远侧边线的交点；BL_NEAR = 底线和近侧边线的交点（可能被球员挡住，按两条线延长求交）。
以 JSON 输出：[{"label":"FT_FAR","point_2d":[x,y]}, ...]。只输出 JSON。"""


def ask(model: str, img: Path) -> str:
    rsp = dashscope.MultiModalConversation.call(
        model=model, messages=[{"role": "user", "content": [{"image": f"file://{img}"}, {"text": PROMPT}]}])
    if getattr(rsp, "status_code", 200) != 200:
        raise RuntimeError(f"HTTP {rsp.status_code}")
    c = rsp.output.choices[0].message.content
    return "".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else str(c)


def to_court(x: float, y: float) -> np.ndarray:
    return cv2.perspectiveTransform(np.float32([[[x, y]]]), G)[0, 0]


def score(pts: dict, view) -> tuple[dict, float, float]:
    x1, y1, x2, y2 = view
    w, h = x2 - x1, y2 - y1
    per = {}
    for k, (tx, ty) in TRUTH.items():
        if k not in pts:
            per[k] = (None, None)
            continue
        px, py = pts[k]
        gx, gy = px / 1000 * w + x1, py / 1000 * h + y1
        e_px = float(np.hypot(gx - tx, gy - ty))
        e_ft = float(np.linalg.norm(to_court(gx, gy) - to_court(tx, ty)))
        per[k] = (e_px, e_ft)
    ok = [v for v in per.values() if v[0] is not None]
    return per, float(np.mean([v[0] for v in ok])), float(np.mean([v[1] for v in ok]))


def main() -> None:
    img = cv2.imread(str(FRAME))
    paths = {}
    for name, (x1, y1, x2, y2) in VIEWS.items():
        p = HERE / f"q_{name}.jpg"
        cv2.imwrite(str(p), img[y1:y2, x1:x2], [cv2.IMWRITE_JPEG_QUALITY, 95])
        paths[name] = p
    log = []
    for model in sys.argv[1:]:
        for name, view in VIEWS.items():
            for r in range(RUNS):
                try:
                    txt = ask(model, paths[name])
                    arr = json.loads(re.search(r"\[.*\]", txt, re.S).group(0))
                    pts = {d["label"]: d["point_2d"] for d in arr}
                except Exception as e:  # noqa: BLE001
                    print(f"{model:<18} {name:<5} #{r}  失败 {str(e)[:60]}")
                    continue
                per, mpx, mft = score(pts, view)
                detail = " ".join(f"{k}={v[0]:.0f}px" if v[0] is not None else f"{k}=缺" for k, v in per.items())
                print(f"{model:<18} {name:<5} #{r}  平均 {mpx:6.1f}px / {mft:5.2f}ft   {detail}", flush=True)
                log.append({"model": model, "view": name, "run": r, "raw": pts, "mean_px": mpx, "mean_ft": mft})
    (HERE / "qwen_results.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
