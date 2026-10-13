"""用百炼千问改写文稿里的旁白行（以 "> " 开头），其余行由脚本原样保留。

整份文稿发过去当上下文，旁白行标上 [P01] 这样的编号；模型只回编号加新旁白，脚本再按编号填回去。

用法：python qwen_polish.py 文稿.md 输出.md [-m qwen3.8-max] [--brief 额外要求.txt] [--think]
在沙箱里跑时流式返回会被网络代理卡住，要在沙箱外跑。
输出：输出.md；模型的诊断写到 输出.notes.md，思考过程写到 输出.think.txt。
key 读 DASHSCOPE_API_KEY：先找 nba-tactics/.env，找不到用 creator-channel/ep01_4.8pct/.env。
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

SYSTEM = """你是给 B 站篮球区写解说稿的中文编辑，读者是看了很多年 NBA 的中国球迷。
你的任务是把稿子里的旁白改得像一个懂球的中国解说在跟朋友聊这场球，而不是翻译腔或 AI 腔。

稿子里以 "> [P01]" 这种编号开头的是旁白，只改这些。其他行（画面标记、原声、出处备注）是给你看上下文的，不用输出。

硬性要求：
1. 所有事实不能动：数字、比分、时间、人名、出手次数、命中率、引语内容，一个都不能改，也不能新增稿子里没有的事实、数据、典故或评价。
2. 每段旁白的信息量和先后顺序保持不变，篇幅大致相当（总字数上下浮动不超过 10%），因为要卡画面。
3. 用中国球迷熟悉的说法，比如"打铁""砸筐""手感烫""手凉""空切""换防""错位""补防""钉板""绝杀""攻击波"，但要用得自然，不要每句都塞。
4. 句子连着说，用"而、于是、所以、那、就、又"把因果串起来；用观众此刻真会问的问题往下推；多跟"你"说话，用"我们"带路。
5. 不要：排比、三段式、格言式金句、"这是什么概念""那么问题来了"这种空问题、"家人们""说白了""实打实"这种硬塞的口头禅、成语堆砌、逗号造势的短句（如"结果，输了。"）、破折号。
6. 球员称呼保持稿子原样（文班、福克斯、卡斯尔、布伦森、阿努诺比、哈特、唐斯等）。
7. 批评福克斯那一段可以说得更直白，但只能基于稿子里已有的事实。

输出格式：每段旁白一行，写成 "[P01] 改好的旁白"，编号一个不漏、按顺序，不要输出别的行。"""


def load_key():
    for p in (ROOT / "nba-tactics/.env", ROOT / "creator-channel/ep01_4.8pct/.env"):
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("DASHSCOPE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("找不到 DASHSCOPE_API_KEY")


def tag(lines):
    out, ids = [], []
    for i, line in enumerate(lines):
        if line.startswith("> ") and line[2:].strip():
            pid = f"P{len(ids) + 1:02d}"
            ids.append((pid, i))
            out.append(f"> [{pid}] {line[2:].strip()}")
        else:
            out.append(line)
    return "\n".join(out), ids


def chat(system, user, model, think=True):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True,
        "temperature": 0.7,
        "enable_thinking": think,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + load_key(), "Content-Type": "application/json"},
    )
    think_buf, out = [], []
    t0, last = time.time(), 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            choices = json.loads(line[5:]).get("choices") or []
            if not choices:
                continue
            d = choices[0].get("delta", {})
            think_buf.append(d.get("reasoning_content") or "")
            out.append(d.get("content") or "")
            if time.time() - last > 15:
                last = time.time()
                print(f"[{last - t0:4.0f}s] 思考 {sum(map(len, think_buf))} 字，正文 {sum(map(len, out))} 字",
                      file=sys.stderr, flush=True)
    print(f"[{time.time() - t0:4.0f}s] 完成", file=sys.stderr)
    return "".join(think_buf), "".join(out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("-m", "--model", default="qwen3.8-max")
    ap.add_argument("--brief")
    ap.add_argument("--think", action="store_true", help="开深度思考；qwen3.8-max 会先想几分钟")
    a = ap.parse_args()

    lines = pathlib.Path(a.src).read_text().splitlines()
    tagged, ids = tag(lines)
    brief = pathlib.Path(a.brief).read_text() if a.brief else ""
    user = (brief + "\n\n" if brief else "") + "下面是文稿：\n\n" + tagged
    thinking, res = chat(SYSTEM, user, a.model, think=a.think)

    body, _, notes = res.partition("=====诊断=====")
    new = dict(re.findall(r"^\[(P\d+)\]\s*(.+)$", body, flags=re.M))
    missing = [pid for pid, _ in ids if pid not in new]
    for pid, i in ids:
        if pid in new:
            lines[i] = "> " + new[pid].strip()

    dst = pathlib.Path(a.dst)
    dst.write_text("\n".join(lines) + "\n")
    if notes.strip():
        dst.with_suffix(".notes.md").write_text(notes.strip() + "\n")
    if thinking:
        dst.with_suffix(".think.txt").write_text(thinking)
    print("written", dst, f"改了 {len(new)}/{len(ids)} 段", "缺：" + ",".join(missing) if missing else "")


if __name__ == "__main__":
    main()
