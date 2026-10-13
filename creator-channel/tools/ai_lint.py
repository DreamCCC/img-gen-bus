"""口播文稿 AI 味机检。规则见 creator-channel/文稿去AI味清单.md。

用法: python creator-channel/tools/ai_lint.py 文稿.md
只检查正文：【】里的剪辑提示、"## 改了什么"/"## 本稿新增"之后的附录都会跳过。
"""
import re
import statistics as st
import sys

PATTERNS = {
    "不是X而是Y": r"不是[^。]{0,20}[，,]\s*(而是|是因为)",
    "讲义路标": r"首先|其次|最后，|值得注意|值得一提|需要指出|综上|总的来说|由此可见|不难发现|众所周知|与此同时|不仅如此|归根结底",
    "自问自答": r"[^。]{2,25}？\s*(其实|答案|当然|没错|是的)",
    "铺垫": r"那么问题来了|这是什么概念|话不多说|接下来我们|先说一个",
    "宏大升华": r"标志着|里程碑|奠定|深远|彰显|体现了|折射|缩影|新篇章",
    "黑话": r"赋能|底层逻辑|闭环|抓手|颗粒度",
    "假口语": r"好家伙|说白了|实打实|绝了|家人们|划重点|敲黑板|说实话|讲真",
    "万能互动": r"扣1|扣个|点赞|三连|评论区说说|你觉得呢",
    "三段式": r"三件事|三个方面|第一[，,].{0,40}第二",
    "破折号": r"——",
    "逗号造势短句": r"(?m)^[^\n，。]{1,8}，[^\n，。]{1,8}。$",
}


def main(path):
    text = open(path, encoding="utf-8").read()
    text = re.split(r"\n## (改了什么|本稿新增)", text)[0]
    body = re.sub(r"【[^】]*】", "", text)
    hits = 0
    for name, pat in PATTERNS.items():
        found = [m.group(0) for m in re.finditer(pat, body)]
        if found:
            hits += len(found)
            print(f"{name}: {len(found)}  {found[:5]}")
    flat = re.sub(r"[#\s]", "", body)
    lens = [len(s) for s in re.split(r"[。？！]", flat) if s]
    chars = len(re.sub(r"[\s，。？！、：；“”\"（）《》…%—·#]", "", body))
    print(f"命中 {hits} 处；句数 {len(lens)}，平均句长 {st.mean(lens):.1f}，"
          f"标准差 {st.pstdev(lens):.1f}（低于 12 说明节奏太匀）")
    print(f"字数 {chars}，按每秒 4.4 字约 {chars / 4.4 / 60:.1f} 分钟")


if __name__ == "__main__":
    main(sys.argv[1])
