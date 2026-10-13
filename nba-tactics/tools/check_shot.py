#!/usr/bin/env python3
"""出手距离自动比对 + 画面数字核对：拿画面追踪的结果和 PBP 记录对账。

1. 出手距离：投篮人起跳那一帧（players 配置里 air 段的起点；没有就用出手帧）的脚底，
   离篮筐多远，和 PBP 的 shot_distance 比。差 ≤1 英尺通过，≤2 提醒，>2 错误
   （多半是标定、认人或脚底点有问题）。同时看位置在不在三分线外，和 2pt/3pt 对不对得上。
2. 画面数字：投篮线标签、+2/+3、卡片的"本场第 N 分""第 N 次助攻"、卡片比分，
   信息卡的出手前比分，旁白里的"N 英尺"，都和 PBP 对一遍。

PBP 默认在 EDL 同级的 data/*.json 里按 action_number 找（文件名 eNNN 里的 NNN），也可以 --pbp 指定。
用法: python check_shot.py kd_macau/e453_edl.json [--pbp kd_macau/data/pbp_440_466.json]
有错误时退出码为 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from court import RIM  # noqa: E402

PASS_FT, WARN_FT = 1.0, 2.0


def find_pbp(base: Path, num: int, path: str | None) -> dict:
    files = [Path(path)] if path else sorted((base / "data").glob("*.json"))
    for f in files:
        rows = json.load(open(f))
        for r in rows if isinstance(rows, list) else []:
            if str(r.get("action_number")) == str(num):
                return r
    raise SystemExit(f"在 {[str(f) for f in files]} 里找不到 action_number={num}")


def uv_at(players: dict, key: str, f: int) -> np.ndarray | None:
    arr = players[key]["uv"]
    got = [arr[k] for k in range(f - 2, f + 3) if 0 <= k < len(arr) and arr[k] is not None]
    return np.median(np.array(got), axis=0) if got else None


CORNER_U = RIM[0] + np.sqrt(23.75 ** 2 - 22 ** 2)   # 底角直线段和弧线的交点，约 14.2 英尺


_lim = np.arcsin(22 / 23.75)
_a = np.linspace(-_lim, _lim, 400)
_us = np.linspace(0, CORNER_U, 100)
THREE = np.r_[np.c_[_us, np.full(100, -22.0)], np.c_[RIM[0] + 23.75 * np.cos(_a), 23.75 * np.sin(_a)],
              np.c_[_us[::-1], np.full(100, 22.0)]]


def beyond_arc(u: float, v: float) -> tuple[bool, float]:
    """在不在三分线外，以及离线最近多远（英尺，正数在外）。"""
    out = abs(v) >= 22 if u <= CORNER_U else np.hypot(u - RIM[0], v - RIM[1]) >= 23.75
    d = float(np.min(np.hypot(THREE[:, 0] - u, THREE[:, 1] - v)))
    return bool(out), d if out else -d


def nums(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--pbp")
    a = ap.parse_args()
    edl_path = Path(a.edl).resolve()
    base = edl_path.parent
    edl = json.load(open(edl_path))
    work = base / edl["work"]
    m = re.search(r"e(\d+)", work.name)
    if not m:
        raise SystemExit(f"从 work 目录名 {work.name} 读不出事件号（应为 eNNN）")
    num = int(m.group(1))
    pbp = find_pbp(base, num, a.pbp)
    players = json.load(open(work / "players.json"))
    cfg_path = base / f"{work.name}_players.json"
    cfg = {p["key"]: p for p in json.load(open(cfg_path))["players"]} if cfg_path.exists() else {}

    layers = edl["layers"]
    shot = next((ly for ly in layers if ly["type"] == "shotline"), None)
    arc = next((ly for ly in layers if ly["type"] == "arc"), None)
    key = (shot or arc or {}).get("key") or next(k for k, v in edl["style"].items() if v == "gold")
    release = arc["at"] if arc else next(int(s["at"]) for s in edl["segments"] if s.get("badge") == "出手")
    takeoff = next((x for x, y in cfg.get(key, {}).get("air", []) if x <= release <= y), None)

    rows = []

    def add(level, item, got, want, note=""):
        rows.append((level, item, got, want, note))

    rec = float(pbp["shot_distance"])
    is3 = pbp.get("action_type") == "3pt" or "3PT" in pbp.get("description", "")
    name = players[key]["name"]
    print(f"事件 {num}：{pbp.get('description')}")
    print(f"投篮人 {key}（{name}），出手帧 {release}，起跳帧 {takeoff if takeoff is not None else '无 air 配置'}")

    for label, f in (("起跳", takeoff), ("出手", release)):
        if f is None:
            continue
        u = uv_at(players, key, f)
        if u is None:
            add("错误", f"{label}帧 {f} 出手距离", "没有轨迹", f"{rec:.1f} 英尺", "这一帧前后都没有脚底点")
            continue
        d = float(np.hypot(*(u - RIM)))
        diff = d - rec
        primary = f == (takeoff if takeoff is not None else release)
        lvl = "通过" if abs(diff) <= PASS_FT else "提醒" if abs(diff) <= WARN_FT or not primary else "错误"
        add(lvl, f"{label}帧 {f} 出手距离", f"{d:.1f} 英尺", f"{rec:.1f} 英尺",
            f"差 {diff:+.1f}；球场坐标 ({u[0]:.1f}, {u[1]:.1f})" + ("" if primary else "；空中插值，仅参考"))
        if primary:
            out, margin = beyond_arc(*u)
            if out != is3:
                lvl = "提醒" if abs(margin) < 1.0 else "错误"
                add(lvl, "三分线内外", "线外" if out else "线内", "3pt" if is3 else "2pt",
                    f"离三分线 {margin:+.1f} 英尺")
            else:
                add("通过", "三分线内外", "线外" if out else "线内", "3pt" if is3 else "2pt", f"离三分线 {margin:+.1f} 英尺")

    if shot and shot.get("label"):
        got = re.findall(r"[\d.]+", shot["label"])
        ok = got and abs(float(got[0]) - round(rec, 1)) < 0.05
        add("通过" if ok else "错误", "投篮线标签", shot["label"], f"{rec:.1f} 英尺")

    pts = 3 if is3 else 2
    for ly in layers:
        if ly["type"] == "pop":
            add("通过" if ly["text"] == f"+{pts}" else "错误", "进球弹字", ly["text"], f"+{pts}")

    card = next((s for s in edl["segments"] if s["kind"] == "card"), None)
    if card:
        for who, what in card.get("rows", []):
            m1 = re.search(r"本场第\s*(\d+)\s*分", what)
            if m1:
                want = int(pbp["points_total"])
                add("通过" if int(m1.group(1)) == want else "错误", f"卡片 {who}", what, f"points_total={want}")
            m2 = re.search(r"第\s*(\d+)\s*次助攻", what)
            if m2:
                want = int(pbp["assist_total"])
                add("通过" if int(m2.group(1)) == want else "错误", f"卡片 {who}", what, f"assist_total={want}")
        post = [int(card["score"][1]), int(card["score"][2])]
        rec_sc = sorted([int(pbp["score_home"]), int(pbp["score_away"])])
        add("通过" if sorted(post) == rec_sc else "错误", "卡片比分", f"{post[0]}:{post[1]}",
            f"home {pbp['score_home']} / away {pbp['score_away']}")
        title = next((ly for ly in layers if ly["type"] == "title"), None)
        if title:
            pre = next((nums(x)[-2:] for x in title["lines"] if re.search(r"\d+\s*-\s*\d+", x)), None)
            if pre:
                d0, d1 = post[0] - pre[0], post[1] - pre[1]
                ok = sorted([d0, d1]) == [0, pts]
                add("通过" if ok else "错误", "信息卡出手前比分", f"{pre[0]}-{pre[1]}",
                    f"卡片 {post[0]}:{post[1]} 减去这球 {pts} 分")

    vo_lines = json.load(open(base / edl["vo"]["lines"]))
    for ln in vo_lines:
        for x in re.findall(r"(\d+(?:\.\d+)?)\s*英尺", ln["text"]):
            ok = abs(float(x) - rec) < 0.6
            add("通过" if ok else "提醒", f"旁白 {ln['id']}", f"{x} 英尺", f"{rec:.1f} 英尺")

    w = max(len(r[1]) for r in rows) + 2
    for lvl, item, got, want, note in rows:
        print(f"  [{lvl}] {item:<{w}} 画面/算出 {got:<12} 记录 {want}" + (f"  {note}" if note else ""))
    n_err = sum(r[0] == "错误" for r in rows)
    n_warn = sum(r[0] == "提醒" for r in rows)
    print(f"{len(rows)} 项：{n_err} 错误，{n_warn} 提醒")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
