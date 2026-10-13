# 配乐与时间轴

## 目录
1. 选曲
2. 测拍点与能量
3. 剪接与硬停
4. 横版时间轴 JSON
5. 竖版时间轴

## 1. 选曲

- 只用能商用的曲库：incompetech（Kevin MacLeod，CC BY 4.0）、Free Music Archive 的 CC BY / CC0 曲目等。CC BY 要在片尾和发布简介里署名。
- 常见组合是两首：
  - 一首铺垫推进曲，负责前 2/3。本项目用的是 "Five Armies"。
  - 一首爆发曲，负责回归段。本项目用的是 "Heroic Age"。
  - 两首中间的静默段用代码合成：低频 drone、钢琴单音、空场馆拍球声。
- 下载后放进 `assets/music/`，把曲名、作者、许可证写进 `CREDITS.md`。
- 选曲要让用户确认。把候选曲目的高潮段各剪 20 秒，拼成对比文件给用户听。

## 2. 测拍点与能量

```bash
.venv/bin/python tools/music_probe.py assets/music/a.mp3 assets/music/b.mp3
```

输出每首曲子的速度（BPM）、按 2 秒分桶的能量曲线，以及突然变安静（break）和突然变响（surge）的位置。用它来找三个关键点：
- 硬停点：选在能量最高的段落里一个重拍的位置。
- 爆点：曲 2 里第一个大重拍。
- 剪接点：两段同相位的小节起点，用来把曲子剪短。

## 3. 剪接与硬停

- 剪接只在同相位小节之间做。例如从第 k 拍跳到第 k+32 拍，中间用 30 ms 交叉淡化。
- 硬停用 25 ms 淡出，听起来就是"啪"一下断掉。
- 曲 2 提前 1–1.5 秒带一点前奏进入，让爆点正好落在画面的爆发帧上。
- 全片最后 2.5 秒淡出。

## 4. 横版时间轴 JSON

`tools/timeline_h.py` 生成 `scenes/film_h.json`。画面、音效和字幕都只从这一份数据读时间，参考实现见 `templates/timeline_h.py`。

```json
{
  "duration": 196.78, "fps": 30,
  "anchors": {"act1": 14.28, "slam": 96.339, "stop": 130.829, "boom": 157.259},
  "scenes":  {"open": [0, 14.28], "map": [14.28, 22.0]},
  "vo":      [{"id": "L01", "t": 4.0, "dur": 1.36, "text": "…"}],
  "ev":      {"openBounces": [0.62, 1.42], "rimOut": 90.279, "rosterCuts": [175.391]},
  "flips":   [{"year": 2007, "home": "魔术", "away": "骑士", "city": "上海 · 澳门", "clip": "f2007", "beats": 4, "t": 111.363}],
  "music":   {"fa_cut_out": 38.522, "fa_cut_in": 55.38, "fa_end": 147.71, "ha_in": 50.85, "ha_at": 154.029}
}
```

写法：

```python
_, BEATS = librosa.beat.beat_track(y=y, sr=sr, units="time")
CUT_OUT, CUT_IN = BEATS[73], BEATS[105]                        # 相差 32 拍，同相位剪接
fa = lambda x: x if x < CUT_OUT else x - (CUT_IN - CUT_OUT)    # 曲 1 的时间 → 成片时间
STOP = fa(147.47 + 0.24)                                       # 硬停点
HA_AT = STOP + 23.2                                            # 静默段时长，之后接曲 2
ha = lambda x: HA_AT + (x - 50.85)                             # 曲 2 的时间 → 成片时间
durs = json.load(open("audio/vo/durations.json"))              # 旁白时长由 TTS 实测
vo = [{"id": i, "t": t, "dur": durs[i], ...} for i, t in VO]
for a, b in zip(vo, vo[1:]):
    assert a["t"] + a["dur"] <= b["t"] + 0.01, f"VO overlap {a['id']} {b['id']}"
```

- 所有锚点都从拍点推导，不要手写秒数。
- 蒙太奇每页时长取整拍数（2 拍或 4 拍）。倒推起点：`起点 = 最后一击的时间 − Σ拍数 × 拍长`，这样最后一页正好落在重音上。
- 旁白放不下时，延长页数或插入过渡场景，不要压缩旁白。
- 换了旁白（换音色、重合成）之后，一定要重跑 timeline，断言能抓到重叠。

## 5. 竖版时间轴

`tools/timeline_v.py` 从横版画面里选镜头，生成 `scenes/film_v.json`：

```json
{"duration": 61.97, "fps": 30,
 "shots": [{"v0": 0, "v1": 5.8, "h0": 41.6, "layout": "zoom", "zoom": 1.15, "cx": 960, "cy": 540, "native": "hook", "title": "…"},
           {"v0": 32.9, "v1": 33.97, "h0": 111.38, "layout": "regions", "regions": [[[1060,190,640,700],[240,230,600,656]]]},
           {"v0": 55.17, "v1": 57.07, "h0": null, "layout": "native", "native": "card"}],
 "vo": [{"id": "V01", "t": 0.15, "dur": 5.52, "text": "…", "wav": "audio/vo_v/V01.wav"}],
 "music": {"fa0": 89.82, "stop": 37.874, "boom": 44.274, "ha_boom": 54.08},
 "ev": {"hook": [0.784, 1.852, 3.431], "card": [55.174, 56.104], "endBounces": [], "six": 41.174}}
```

- `h0` 指这个镜头取自横版的哪个时刻，`null` 表示竖版原生画面。
- 先定竖版的音乐起点：`FA0 = 横版重音在曲子里的时间 − 竖版重音的时间`。再用 `snap()` 把所有镜头的起点对齐到最近的拍点。
- 竖版可以复用横版的旁白句（例如 L18、L27、L28），这时两边的时间槽都要满足，选版本时取较小的那个。
