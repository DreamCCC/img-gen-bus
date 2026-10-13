"""pop_1.wav（日语版）的段落与逐句时间轴 → suno/pop_1_timeline.json
锚点来自 paraformer 词时间戳，其余按 2 小节一句插值，最后吸附到实测拍点。"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
BEATS = np.load(HERE / "suno/pop_1_beats.npy")
LINE = 8 * 0.46005


def snap(t):
    return float(BEATS[np.argmin(np.abs(BEATS - t))])


def run(start, anchors, n):
    """从 start 起每 2 小节一句，anchors={序号: 实测时间} 覆盖插值。"""
    return [anchors.get(k, start + k * LINE) for k in range(n)]


CHORUS_JA = ["Baby, baby, baby, oh", "Like baby, baby, baby, no", "Like baby, baby, baby, oh", "帰りたくない",
             "Baby, baby, baby, oh", "Like baby, baby, baby, no", "Like baby, baby, baby, oh", "パーティーは終わらない"]
CHORUS_ZH = ["", "", "", "不想回家", "", "", "", "派对不会结束"]

SECTIONS = [
    ("intro", 0.0, [], []),
    ("verse1", 17.72,
     ["銀座のネオン きらめく夜", "万札振って タクシー止める", "肩パッドに ショルダーフォン", "東京中が 乾杯してる"],
     ["银座的霓虹 闪烁的夜", "挥着万元大钞 拦下出租车", "垫肩西装 配上肩背电话", "整个东京 都在干杯"]),
    ("pre1", 32.68,
     ["扇子が揺れる ディスコの夜", "ミラーボール 回れ朝まで", "残業なんて 明日でいいの", "今夜の東京 わたしたちのもの", "みんなで歌って"],
     ["扇子摇摆 迪斯科之夜", "镜球啊 一直转到天亮", "加班什么的 明天再说", "今夜的东京 属于我们", "大家一起唱"]),
    ("chorus1", 48.5, CHORUS_JA, CHORUS_ZH),
    ("verse2", 77.18,
     ["週末は苗場 新幹線で", "イヴのホテルは 一年待ち", "株価は天まで 明日も上がる", "カード一枚で 春を買うの",
      "残業明けでも カラオケへ", "24時間 笑顔で戦える", "札が舞う 舞う 舞う 舞う", "こんな毎日 永遠に続くよ"],
     ["周末去苗场 搭新干线", "平安夜的酒店 要排一年", "股价冲上天 明天还会涨", "一张信用卡 买下整个春天",
      "加完班 照样去唱卡拉OK", "二十四小时 笑着战斗", "钞票在飞 飞 飞 飞", "这样的日子 会永远继续"]),
    ("chorus2", 107.1, CHORUS_JA, CHORUS_ZH),
    ("bridge", 136.34,
     ["シャボン玉 大きく 高く飛んで", "みんなの夢が 雲の上を走る", "街中のネオン 微笑みかける", "ミラーボールは まだ回ってる",
      "悩みは紙ヒコーキ 飛ばしちゃえ", "青春のボリューム 最大にして", "みんな 準備はいい?", "一緒に歌おう baby"],
     ["肥皂泡 飞得又大又高", "大家的梦 在云上奔跑", "满街的霓虹 对我们微笑", "镜球 还在旋转",
      "烦恼折成纸飞机 飞走吧", "青春的音量 开到最大", "大家 准备好了吗", "一起唱吧 baby"]),
    ("build", 164.7, [], []),
    ("final", 180.22, CHORUS_JA, CHORUS_ZH),
    ("outro", 209.52,
     ["シャボン玉 (yeah, yeah, yeah)", "シャボン玉 (yeah, yeah, yeah)", "シャボン玉 (yeah, yeah, yeah)", "あの頃の東京 (ずっと輝いてる)"],
     ["肥皂泡", "肥皂泡", "肥皂泡", "那时的东京 永远闪耀"]),
    ("tail", 227.5, [], []),
]

ANCHORS = {
    "verse1": {0: 17.72, 2: 25.38},
    "pre1": {0: 32.68, 2: 40.20, 4: 47.30},
    "chorus1": {3: 59.04, 7: 73.86},
    "verse2": {0: 77.18, 5: 94.08, 6: 98.96},
    "chorus2": {3: 118.26, 7: 132.62},
    "bridge": {0: 136.34, 1: 140.08, 3: 146.02, 5: 153.36, 6: 159.04, 7: 162.52},
    "final": {3: 191.64, 7: 206.06},
    "outro": {0: 209.52, 3: 220.86},
}

out = {"audio": "suno/pop_1.wav", "duration": 242.0, "bpm": 130.42, "beats": [round(float(b), 3) for b in BEATS],
       "sections": []}
for i, (name, t0, ja, zh) in enumerate(SECTIONS):
    t1 = SECTIONS[i + 1][1] if i + 1 < len(SECTIONS) else 242.0
    rel = {k: v - t0 for k, v in ANCHORS.get(name, {}).items()}
    starts = [t0 + r for r in run(0.0, rel, len(ja))]
    lines = []
    for k, (a, b) in enumerate(zip(ja, zh)):
        s = snap(starts[k]) if k else starts[k]
        e = starts[k + 1] if k + 1 < len(ja) else t1
        lines.append({"t0": round(s, 2), "t1": round(e, 2), "ja": a, "zh": b})
    out["sections"].append({"name": name, "t0": t0, "t1": t1, "lines": lines})

(HERE / "suno/pop_1_timeline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for s in out["sections"]:
    print(f"[{s['name']}] {s['t0']:.1f}–{s['t1']:.1f}")
    for ln in s["lines"]:
        print(f"   {ln['t0']:6.2f}  {ln['ja']}")
