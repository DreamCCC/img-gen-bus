# 素材来源与授权（成片《领先 29 分，马刺是怎么输掉的？》）

## 比赛画面

| 本地文件 | 用在 | 来源 |
|---|---|---|
| `raw/2606110853187102.mp4` 等单回合片段（id 末位 02） | 第 1 段进球串、第 3 段尼克斯追分、拆解①–④的底片 | 腾讯体育 NBA 数据库 |
| `raw/2606111112248401.mp4` / `raw/2606111151336101.mp4` | 第三节、第四节集锦镜头 | 腾讯体育 NBA 数据库（节集锦） |
| `online/dcf8UW7cMOI.mp4` | 第 3–4 段第四节连续转播、结尾全景 | YouTube @NBA《UNREAL GAME 4 ENDING #2 Spurs at #3 Knicks》 |
| `online/sOQKRjP3ZJk.mp4` | 冷开场、阿努诺比补篮回放 | YouTube @NBA《OG Anunoby's INSANE TIP-IN Game 4 vs Spurs》 |
| `online/lL4TMc1sYmQ.mp4` | "只领先 53.8 秒"观众镜头 | YouTube @NBA《Listen to MSG SHAKING During the Knicks HISTORIC 4th QTR Comeback!》 |
| `online/JGnCsKF1JLQ.mp4` | 文班肘击、回放、裁判宣布、唐斯特写 | YouTube @nbaonespn（NBA on ESPN）《Victor Wembanyama's elbow to KAT's head upgraded to flagrant 1》 |
| `assets/footage/inside_barkley*.mp4` | 冷开场、巴克利原声 | YouTube @nbaonespn《Charles Barkley BLASTS Spurs for chucking threes despite 29-point lead \| Inside The NBA》（qIyBGPb7Xdg 5:10–6:11） |
| `assets/footage/wemby_exit.mp4` | 结尾文班背影 | dcf8UW7cMOI 316.50–320.22（第四节 2:42 的死球，不是终场离场；成片已裁掉计分牌） |

## 赛后发布会

`assets/footage/quotes/q*.mp4`，全部来自 YouTube @NBA《San Antonio Spurs vs New York Knicks | NBA Finals Game 4 Postgame Media Availability》（qqPT01jE5S0）。
英文逐字核对见 `research/quotes_verified.md`，中文字幕为自译。原片底部的官方比分条在成片里裁掉了。
布朗的三段（q3_1、q4_2、q4_4）画面仍用 NBA 官方版，声音换成 YouTube @SNY《Mike Brown on Knicks pulling off greatest comeback in NBA Finals history and taking 3-1 series lead》（93iEr0LWF8U）的同场录音：官方版里布朗那路麦克风丢包，每 0.1–0.3 秒断一下。

## 数据

- NBA 逐回合记录（`data/pbp.json`）：比分、时钟、事件。
- NBA 追踪数据（`data/shot_detail.json`）：每次出手的预期命中率、防守人的手离球距离、出手距离。
- 计分牌时钟用视觉模型逐帧识别（`research/sb_*.json`），只用来把事件对到画面，不进成片。

## 配乐

Kevin MacLeod（incompetech.com），CC BY 4.0（https://creativecommons.org/licenses/by/4.0/）：
v3：冷开场 "Lightless Dawn"；第 1–5 段依次为 "Hitman"、"Impact Prelude"、"The Escalation"、"Impact Lento"、"Five Armies"、"Long Road Ahead"。
（v1/v2 用的是 "Montauk Point"、"Invariance"、"The Escalation"、"Stay the Course"、"Calmant"，冷开场没有配乐。）
片尾已署名；B 站简介建议附上：

> Music: "Lightless Dawn", "Hitman", "Impact Prelude", "The Escalation", "Impact Lento", "Five Armies", "Long Road Ahead" by Kevin MacLeod (incompetech.com), licensed under CC BY 4.0

全片音效为代码合成（`audio/sfxlib.py`），无第三方采样。

## 旁白

v1/v2：阿里云百炼 CosyVoice `cosyvoice-v3-flash`，系统音色 `longfei_v3`。没有克隆任何真人声音。

v3（内部试听版）：MiniMax `speech-2.8-hd`，克隆音色 `xjy_internal_test_v1`，用徐静雨的公开音频复刻，仅用于内部效果测试。
**v3 不能公开发布**：正式版要换成已获授权的专人克隆音色，然后重新配音。片尾标注为"AI 合成语音 · 内部效果测试版"。

竖版（`out/vt_*.mp4`，文稿 `../文稿_竖屏5min_v2.md`）：同一个 MiniMax 克隆音色重新配音（`audio/vo_vt`），同样**只限内部测试**；
画面底部常驻"AI 合成配音 · 内部测试版"，片尾同横版标注。素材、配乐都是横版 v3 的子集，没有新增来源。

竖版英文版（`out/领先29分马刺是怎么输掉的_竖屏_英文版.mp4`，文稿 `audio/vo_vt_en.json`）：阿里云百炼 `qwen-audio-3.1-tts-flash`
设计音色"9 号 现场解说"（`…-vd-pbp-…`），由文字描述生成，**没有克隆任何真人声音**，可以公开发布。画面底部常驻"AI-generated narration"，
片尾标"Narration · AI-generated voice"。发布会引语用英文原声 + 英文逐字字幕（`research/quotes_verified.md`）。素材、配乐与中文竖版相同，没有新增来源。

## AI 生成画面

无。全片画面都是真实比赛 / 节目 / 发布会画面，图表和战术拆解为代码绘制。
