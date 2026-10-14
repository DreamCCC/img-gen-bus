# G4 引语核对

来源：NBA 官方 YouTube《San Antonio Spurs vs New York Knicks | NBA Finals Game 4 Postgame Media Availability》（qqPT01jE5S0），
音频 `online/qqPT01jE5S0.m4a`，转写 `asr_postgame_media.txt`（百炼 qwen3-asr-flash，30 秒一段，时间码是段起点）。

## 已核对（原声里有）

| 人 | 时间码 | 原话 | 用途 |
| --- | --- | --- | --- |
| 米奇·约翰逊（马刺主帅） | 19:00–19:30 | "We got away from what got us the 76 points in the first half … putting pressure on the rim, rolling after screens, running … We got on our heels and, you know, missed some shots." | 下半场崩盘的主因；和 PBP 下半场 30 分、8/39 对得上 |
| 文班亚马 | 14:30 | 被问福克斯那次上篮："I fell on the floor. I couldn't really see. I don't know. I just saw the block." | 关键回合 |
| 文班亚马 | 37:30 | "It's going to go one of two ways … the bad one would be giving up, the good one would be getting stronger through this." | 结尾 |
| 文班亚马 | 39:00–39:47 | 美联社记者问他两次罚球："What was going through my mind? I mean, same thing as always, it's just a shot. You might work on your form hours and hours, at the end of the day it's just a shot, so you need to shoot it the normal way."（已逐字核对，见下节 q4_1） | 罚球回合 |
| 迈克·布朗 | 31:12 | "Defensively, we just did it harder for longer stretches, and we were really in tune to what we were supposed to be doing."（已逐字核对，见下节 q3_1） | 下半场防守 |
| 文班亚马 | 40:35 | "Of course I'm going to be more — I mean, I'm going to be more careful, but it's not going to change much."（被问恶意犯规复核） | 恶犯 |
| 迈克·布朗（尼克斯主帅） | 23:30 | "I told OG … he's got to be a monster on the offensive glass tonight." | 绝杀补篮的伏笔 |
| 迈克·布朗 | 28:30 | "That has to be the most iconic shot in the history of New York basketball." | 绝杀 |
| 迈克·布朗 | 35:00 | 被问福克斯为何不控球："You never know what a player's thinking … You would have to ask him." | 关键回合 |
| 阿努诺比 | 63:30 | "It feels cool. I mean, everyone's pretty excited. I'm excited too." | 反差点 |
| 布伦森 | 77:00 | "We have a superstar in our locker room."（说阿努诺比） | 尼克斯视角 |

### ESPN《Inside the NBA》赛后节目（qIyBGPb7Xdg，转写 `asr_barkley.txt`，说话人按画面确认）

| 人 | 时间码 | 原话 | 用途 |
| --- | --- | --- | --- |
| 奥尼尔 | 5:15–5:33（特写） | "I am kind of disappointed in Mitch Johnson … Why in a timeout you don't look at your guys: don't shoot no more threes." | 第三节三分 |
| 巴克利 | 5:39–6:00（特写） | "Yo, those threes were great the 1st half. At some point, when you start missing … maybe we should stop shooting threes. That's my criticism. Like, damn, dude, you ain't making them." | 第三节三分 |
| 演播室全景 | 5:36、5:45–5:57 | 四人坐在 MSG 场边 | 冷开场"赛后被骂" |

巴克利紧接着说"never a reason to shoot eight or nine in a row when you got a twenty-point lead"，"连投八九个"这个数没核对，不引用。

## 原声片段逐字核对（film/audio/quotes.json 的 8 条）

做法：每条在 ref ±60 s 内用本地 whisper medium.en 出词级时间戳（`film/tools/quotes_wordasr.py`、`quotes_wordasr2.py`，结果在 `quotes_wordasr/`），
再把成片窗口单独送百炼 qwen3-asr-flash 交叉核对（`film/tools/quotes_xcheck.py`），入出点用音频能量包络校正。
两套 ASR 加 30 秒段粗转写三方比对；文字以三方一致的为准，不一致的在下面单列。
"gonna / going to" 两套 ASR 互相打架，统一按 going to 写，不影响字义。
片段由 `film/tools/cut_quotes.py` 切出，在 `film/assets/footage/quotes/<id>.mp4`；时间是原片秒。

| id | 人 | 原片 in–out | 最终原话（逐字） | 和 quotes.json 原文比 |
| --- | --- | --- | --- | --- |
| q2_1 | 文班 | 2435.58–2441.45（40:35） | Of course I'm going to be more — I mean, I'm going to be more careful, but it's not going to change much. | 原文漏了中间的口误重说 "be more — I mean"，这是原声里连着说的，没法剪掉，保留 |
| q3_1 | 迈克·布朗 | 1871.90–1881.17（31:12） | Defensively, we just did it harder for longer stretches, and we were really in tune to what we were supposed to be doing. | 原文那句确认是原话；片段补上了后半句，让句子收在句号上 |
| q3_2 | 米奇·约翰逊 | 1150.80–1176.17（19:11） | We got away from what got us the 76 points in the first half, just in terms of putting pressure on the rim, rolling after screens, running, continuing to find the paint, whether it's for ourselves or for a teammate. We got on our heels and, you know, missed some shots, and then, you know, you don't get as many free throws and high, high-percentage looks when you play on your heels like that. | 原文用 … 省掉的中间约 9 s 整段保留（见下） |
| q4_1 | 文班 | 2373.89–2386.76（39:34） | What was going through my mind? I mean, same thing as always, it's just a shot. You might work on your form hours and hours, at the end of the day it's just a shot, so you need to shoot it the normal way. | 原文 "At the end of the day, it's just a shot." 是原话，但只是这一句的中间一段（见下） |
| q4_2 | 迈克·布朗 | 2109.25–2122.52（35:09） | You know, again, on that action, you never know what a player's thinking, you know. Maybe he was going to drive and wanted to keep the dribble to run out the clock. I don't know. You would have to ask him. | 前面补了 "you never know what a player's thinking"；"run out the clock" 的 out 存疑（见下） |
| q4_3 | 文班 | 883.15–890.05（14:43） | I fell on the floor. I couldn't really see. I don't know. I just saw the block. | 原文只有最后一句（1 秒不到），补成完整回答 |
| q4_4 | 迈克·布朗 | 1425.20–1434.47（23:45） | I told OG, as big, as strong, as athletic as he is, he's got to be a monster on the offensive glass tonight. | 一致；开头两个词含糊（见下） |
| q5_1 | 文班 | 2258.92–2273.59（37:38） | What's going through my mind right now? I think it's going to go one of two ways. One of two ways, and a bad one and a good one. And I know the bad one would be giving up, the good one would be getting stronger through this, getting more together. And I know this is what we're going to do. | 原文 … 省掉的部分只有约 4 s，整段保留 |

### 重点条目

- **q3_1（布朗 31:00）：确认是原话。** whisper 两遍、qwen 两遍都是 "Defensively, we just did it harder for longer stretches, and we were really in tune to what we were supposed to be doing."
  前面是 "Really, we didn't change much. We basically kept the same game plan."（1864.5–1870.0），想要更完整的上下文可以把入点提前到 1864.3。
  "Defensively" 前约 0.8 s 有个语气词（单独送识别出 "Uh." / "Hmm."），片段从 Defensively 前起点，没带它。
- **q4_1（文班 39:30）：原话确认，但原文不是一个独立句子。** 他完整的回答是 "What was going through my mind? I mean, same thing as always, it's just a shot. You might work on your form hours and hours, at the end of the day it's just a shot, so you need to shoot it the normal way."
  "at the end of the day" 前面的 "hours," 和它之间只隔 0.14 s，单切这一句会切到前一个词，所以整段回答保留（12.9 s）。
  39:00 那段 whisper 第一遍转出的"法语提问"是幻觉，qwen 核对后那里只是主持人点名和冷场。
- **q3_2：** 原文 … 省掉的中间部分（冲击篮筐、挡拆顺下、快攻、打禁区）只有约 9 s，而且是战术内容；
  "teammate." 和 "We got on our heels" 之间没有停顿，"missed some shots" 后面紧接 "and then"，拆成两段都切不干净，所以整段保留到 "like that."（25.4 s）。
  字幕块按词级时间分好了，后期要剪短可以按块边界下刀。

### 存疑的词

- **q4_2 "run out the clock"：** qwen 短窗口听成 "run out the clock"，30 秒段里是 "run out to clock"；whisper 两遍是 "run off that / the clock"（off 置信度 0.26）。两种说法意思一样（把时间耗完），按习惯说法写 out，中文不受影响。
- **q4_4 "I told OG"：** 开头发音含糊，转写结果有 "I told OG" / "A total OG" / "The OG is big" 几种。连上前一句（"…OG was one of the guys I challenged."）一起送 qwen 时得到 "I told OG"，语义也通，按这个写。
  "offensive glass tonight"：qwen 两次一致；whisper 听成 "offensive last night"，不通，不采用。
- **q5_1：** "And I know the bad one" 的 And 只有 qwen 听到，whisper 没有；按 qwen 写。

### 其它

- 14:30 和 36:30 是直播流里重复的同一段文班问答（问题、回答、画面都一样），q4_3 按 ref 取 14:43 那处。
- 原片是 1280x720 AV1，片段用 lanczos 等比放大到 1920x1080、30fps，H.264 crf 14，AAC 48 kHz 立体声 256k，音量没动（只在首尾各加了 30–50 ms 防爆音淡入淡出）。
- 画面下方有原片自带的 ABC/NBA 比分字条（"KNICKS DEFEAT SPURS 107-106 | NYK LEADS 3-1" + 人名数据），没处理，时间线上字幕要放在字条上方，或者遮掉。

## 未核对（不能用）

- 福克斯 "I just thought I'd be able to outrun him."：aihubmix 搜索给出，这个发布会视频里没有福克斯出场。要找到马刺官方或 NBA 官方的福克斯采访原声才能用。
- YouTube 上 DangerousAI 频道的"福克斯/文班赛后采访"是 AI 伪造的恶搞视频，禁止使用。
