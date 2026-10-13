#!/usr/bin/env python3
"""标签重叠检查：不出画面，只跑 render_play 的 UI 布局，逐帧量出名牌和字幕、面板、重点球员的冲突。

错误（要改）:
  名牌重叠     两个名牌或距离标签互相压住
  压字幕       名牌压住当前字幕
  压面板       名牌压住战术板、角标、信息卡
提醒（看一眼预览再决定）:
  压身体       名牌压住主角或第二主角（gold/orange）的身体框
  引线过长     名牌被推离球员超过 --leader 像素

同一问题在相邻帧连续出现时合并成一段，给出最严重的那一帧，直接拿去 --preview。
输出: 终端报告 + <work>/qa/labels.json；有错误时退出码为 1。

用法: python check_labels.py kd_macau/e453_edl.json [--step 1] [--workers 8] [--leader 220]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render_play  # noqa: E402

MIN_ALPHA = 0.5   # 正在淡入淡出、还看不清的不算
MIN_PX = 3        # 交叠宽高都超过这么多像素才算压住

_R = None


def _init(path):
    global _R
    _R = render_play.Renderer(Path(path))


def _job(i):
    return _R.layout(i)


def inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return (w, h) if w > MIN_PX and h > MIN_PX else None


def issues(lay, leader):
    out = []
    pills = [p for p in lay["pills"] if p["a"] >= MIN_ALPHA]
    for k, p in enumerate(pills):
        for q in pills[k + 1:]:
            o = inter(p["rect"], q["rect"])
            if o:
                out.append(("错误", "名牌重叠", f"{p['text']} × {q['text']}", o[0] * o[1]))
        for s in lay["subs"]:
            o = s["a"] >= MIN_ALPHA and inter(p["rect"], s["rect"])
            if o:
                out.append(("错误", "压字幕", f"{p['text']} × 字幕「{s['text']}」", o[0] * o[1]))
        for pn in lay["panels"]:
            o = pn["a"] >= MIN_ALPHA and inter(p["rect"], pn["rect"])
            if o:
                out.append(("错误", "压面板", f"{p['text']} × {pn['name']}", o[0] * o[1]))
        for key, b in lay["bodies"].items():
            if key == p["owner"]:
                continue
            o = inter(p["rect"], [float(v) for v in b])
            if o:
                out.append(("提醒", "压身体", f"{p['text']} × {key} 的身体", o[0] * o[1]))
        if p["moved"] > leader:
            out.append(("提醒", "引线过长", f"{p['text']} 被推开 {p['moved']:.0f}px", p["moved"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--step", type=int, default=1, help="每隔几帧查一次")
    ap.add_argument("--workers", type=int, default=8, help="1 = 单进程（沙箱里也能跑）")
    ap.add_argument("--leader", type=float, default=220)
    a = ap.parse_args()
    edl = Path(a.edl).resolve()
    r = render_play.Renderer(edl)
    idx = list(range(0, r.tl.n, a.step))
    if a.workers > 1:
        with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(str(edl),)) as ex:
            lays = list(ex.map(_job, idx, chunksize=8))
    else:
        lays = [r.layout(i) for i in idx]

    runs = {}   # (级别, 类别, 对象) -> 当前这一段
    done = []
    for lay in lays:
        seen = set()
        for lvl, kind, what, sev in issues(lay, a.leader):
            key = (lvl, kind, what)
            if key in seen:
                continue
            seen.add(key)
            cur = runs.get(key)
            if cur and lay["i"] - cur["to"] <= a.step:
                cur["to"] = lay["i"]
                cur["segs"].add(lay["seg"])
                if sev > cur["sev"]:
                    cur["sev"], cur["worst"] = sev, lay["i"]
            else:
                if cur:
                    done.append(cur)
                runs[key] = dict(level=lvl, kind=kind, what=what, frm=lay["i"], to=lay["i"],
                                 segs={lay["seg"]}, sev=sev, worst=lay["i"])
    done += runs.values()
    done.sort(key=lambda d: (d["level"] != "错误", d["frm"]))

    fps = r.tl.fps
    n_err = sum(d["level"] == "错误" for d in done)
    print(f"检查 {len(idx)} 帧（每 {a.step} 帧），{n_err} 段错误，{len(done) - n_err} 段提醒")
    for d in done:
        span = f"帧 {d['frm']}–{d['to']}（{d['frm'] / fps:.2f}–{d['to'] / fps:.2f}s，{'/'.join(sorted(d['segs']))}）"
        print(f"  [{d['level']}] {d['kind']:4s} {d['what']}\n         {span}  最严重 {d['worst']}")
    worst = sorted({d["worst"] for d in done if d["level"] == "错误"})
    if worst:
        print(f"\n看图: python tools/render_play.py {a.edl} --preview {','.join(map(str, worst))}")

    qa = r.work / "qa"
    qa.mkdir(exist_ok=True)
    json.dump([dict(d, segs=sorted(d["segs"])) for d in done], open(qa / "labels.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"报告 -> {qa / 'labels.json'}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
