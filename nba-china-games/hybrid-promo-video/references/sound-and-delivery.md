# 音效合成、混音与交付

## 目录
1. 代码合成音效（sfxlib）
2. 横版混音
3. 竖版混音
4. 交付压制与响度

## 1. 代码合成音效（sfxlib）

全部音效都由 `audio/sfxlib.py` 用 numpy 合成，不依赖采样包，也就没有版权问题：

| 类别 | 函数 |
| --- | --- |
| 打击 | `tom`、`taiko`、`thump`、`impact`（爆点重击）、`braam`（预告片式低音长号） |
| 过渡 | `whoosh`、`riser`（上扬）、`click`（翻页） |
| 篮球 | `rim_clank`（篮筐）、`dribble_room`（空场馆里的拍球声） |
| 氛围 | `crowd_layer`（人群）、`piano`（钢琴单音） |
| 工具 | `Bus(n).place(sig, t0, gain, pan)`、`load`、`seg`、`ramp`、`room_ir`（混响）、`load_vo`、`vo_gain`、`vocal_pocket`、`section_gain` |

音效的放置时间全部从时间轴 JSON 的 `ev` 里读，画面读的也是同一份数据。

## 2. 横版混音

参考实现 `templates/mix_film.py`，运行 `.venv/bin/python audio/mix_film.py`，输出 `out/film_h_mix.wav` 和 `out/film_h_mix_sfxstem.wav`（音效分轨，供竖版用）。

```
music / vo / sfx / amb 四条 Bus
音乐：曲 1 第一段 + 曲 1 第二段（30 ms 交叉淡化）+ 硬停 → 静默段合成 drone 和钢琴 → 曲 2 从 ha_in 接入
音效：遍历 ev 里的每个事件，放置对应的合成音
旁白：load_vo() 把有声部分统一到 -20 dBFS，再乘 vo_gain(id)（高潮句 +1 dB，安静句 -2.5 dB）
```

**不做闪避（ducking）。** 旁白一出来就把音乐压低，用户听到的是人声和背景"此起彼伏"。给人声留位置只用固定手段：

- `vocal_pocket(music)`：固定 EQ，把音乐的 1–4 kHz 压低约 8 dB，不随旁白起落。
- `section_gain(N, [(t0, t1, -3)])`：按段落固定调音量，相当于人工推推子。只给音乐最响的段落用，进出各用 1.5 秒缓变。
- 总线增益：`G_MUSIC 0.46`、`G_SFX 0.5`、`G_VO 3.3`。不加软削波，最后把峰值归一到 0.93。

脚本会打印每句旁白在 300–4000 Hz 频段比背景高多少 dB。做到 +1 dB 以上就能并排听清；低于 0 dB 时，先拆开看是音乐还是音效盖住了人声，再针对那一段调 `section_gain`。本项目换成龙飞以后，横版最低 +1.7 dB，竖版最低 +1.8 dB。

## 3. 竖版混音

参考实现 `templates/mix_film_v.py`。必须先跑横版混音，因为要用它导出的音效分轨。

- 音效：按每个镜头的 `h0`，从横版音效分轨复制对应片段，两端加 8 ms 淡入淡出。蒙太奇每页太短，复制会切掉起音，这几页改在竖版里重新放音效。
- 竖版原生音效：钩子重击、翻页、对阵卡、片尾拍球。
- 音乐重新剪：曲 1 从 `fa0` 开始播放，到竖版的 `stop` 硬停；曲 2 带约 1.5 秒前奏，让爆点落在竖版的 `boom` 上；最后 2.5 秒淡出。
- 旁白、EQ 凹口、段落音量的做法和横版一样。

## 4. 交付压制与响度

```bash
./deliver.sh out/film_h_master.mp4 out/film_h_mix.wav out/成片_横版.mp4 22M
./deliver.sh out/film_v_master.mp4 out/film_v_mix.wav out/成片_竖版.mp4 16M
```

deliver.sh 做三件事：
1. 用 `ebur128` 测出混音的整体响度 I。
2. 只用固定增益，把响度推到 -16 LUFS：`volume=(-16-I+0.3)dB`。再过采样到 192 kHz 做限幅（`alimiter limit=0.75`）后降回 48 kHz，这样才能压住 AAC 编码后的峰值。
3. 视频用 H.264 crf 19 压制，限制 maxrate（横版 22M，竖版 16M），然后复测响度。

规则：
- 不要用单遍 `loudnorm`。它是动态增益，人声和音乐会忽大忽小，用户能听出来。
- 目标约 -16 LUFS，峰值不超过 -1.5 dBFS。不要硬推到 -14 LUFS：本项目的冲击音效很重，推到 -14 时限幅器要削掉约 9 dB，冲击力明显变弱。
- 压制完复测一遍。本项目最终：横版 -16.1 LUFS、峰值 -1.6 dBFS，竖版 -16.0 LUFS、峰值 -2.3 dBFS。
- 片尾和发布简介里都要有配乐署名。
