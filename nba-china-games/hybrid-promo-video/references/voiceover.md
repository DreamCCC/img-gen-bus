# 旁白（阿里云百炼 TTS）

## 目录
1. 百炼上能用的几条线
2. 选音色的流程
3. 台词表写法
4. 多版本合成与自动挑选
5. 时长与时间轴
6. 踩过的坑

## 1. 百炼上能用的几条线

所有调用都用 `.env` 里的 `DASHSCOPE_API_KEY`（北京地域）。

| 模型 | 调用方式 | 能否逐句控制语气 | 适合 |
| --- | --- | --- | --- |
| `qwen3-tts-instruct-flash` | `dashscope.MultiModalConversation.call(model, text, voice, instructions=…, optimize_instructions=False)`，返回音频 URL | 能，用自然语言指令 | 纪录片腔、需要细调语气的场合。男声有 Kai、Ethan、Vincent、Eldric Sage、Moon、Neil、Arthur 等 |
| `qwen3-tts-flash` | 同上，不带 instructions | 不能 | Ryan（戏感强）、Andre 等不支持指令的音色 |
| CosyVoice `cosyvoice-v3-flash` / `cosyvoice-v2` | `dashscope.audio.tts_v2.SpeechSynthesizer(model, voice, speech_rate, seed, instruction).call(text)`，返回音频字节 | 大多数音色不能。少数标杆音色（如 `longanyang`）只接受固定格式的指令，例如"你正在进行比赛解说，你说话的情感是surprised。" | 龙飞 `longfei_v3`（热血磁性男，本项目最终选用）、龙三叔、龙天、龙小诚 `longxiaocheng_v2`、龙安冲 `longanchong`（激情推销男） |
| Qwen-Audio-TTS `qwen-audio-3.0-tts-plus` | 同 CosyVoice 的 SpeechSynthesizer | 能，任意指令 | 系统音色很少（`longanlufeng` 明亮男声），另有 500 多个基础音色 |
| MiniMax `MiniMax/speech-2.8-hd`（百炼托管） | HTTP POST `…/services/aigc/multimodal-generation/generation`，`voice_setting`（`voice_id`、`emotion`）、`voice_modify.intensity`（越低越有力量感） | 只能选情绪类别 | `presenter_male`、`male-qn-jingying`、`male-qn-badao`、`audiobook_male_2` 等 |
| 声音设计：Qwen `qwen3-tts-vd-2026-01-26` / CosyVoice `cosyvoice-v3.5-plus` | POST `…/services/audio/tts/customization`，model 分别是 `qwen-voice-design`、`voice-enrollment`，传入 `voice_prompt` | 设计出来的音色基本不能逐句控制语气 | 系统音色里找不到想要的风格时，按文字描述生成一个新音色。不是克隆 |

- 不同模型的音色不能混用：v3 的音色要配 v3 模型，否则会报 `InvalidParameter … Engine return error code: 4`。
- CosyVoice 的指令参数叫 `instruction`，Qwen-TTS 的叫 `instructions`，不要写错。
- 声音设计的描述只写音色特征（性别、年龄、音调、语速、情绪、质感、用途），不要写"像某某人"。
- 语音识别核对读音用 `qwen3-asr-flash`。

## 2. 选音色的流程

1. 先问清腔调（见 brief-and-script.md）。
2. 第一轮，大范围比：

```bash
.venv/bin/python tools/tts_audition.py out/tts_audition [config.json]        # config 可带 designs，声音设计音色一起比
.venv/bin/python tools/audition_report.py out/tts_audition config.json Q C   # 读音准确率、音高、起伏、语速、安静句与高潮句的响度差
```

   - 纪录片腔看什么：音高中低（男声 100–140 Hz），起伏适中（10–17 个半音），语速偏慢（每秒 3.6–4.6 字），安静句比高潮句轻。
   - 广告腔看什么：起伏大、重音对比大、穿透力高。

   - 一次比十几个音色，覆盖 qwen3-tts、CosyVoice、MiniMax 三条线，用同样的 4 句台词：一句平叙、一句升温、一句高潮、一句压低。
   - 生成每个候选的拼接文件和 `ALL.wav`。再用女声给每个候选报编号，拼成带编号的对比文件，方便用户边听边记。
   - 客观指标，供推荐时参考：
     - 基频中位数：偏低显得沉稳，偏高（男声 200 Hz 以上）说明在"喊"。
     - 音高起伏（10%–90% 分位跨了多少半音）：越大越有表现力。
     - 重音对比（95% 分位与 40% 分位的响度差）：越大越"铿锵"。
     - 穿透力（2–5 kHz 能量占 100–2000 Hz 的比例）：越高声音越亮、越往前冲。
     - 高潮句比安静句响多少：如果高潮句反而更轻，说明这个音色调动不了情绪。本项目的 Kai 就是这样，L21 排比句比耳语句还轻 1.8 dB。
   - 用语音识别逐句核对读音，排除念错字的候选。
3. 用户说"不够激情""不够有力量"时，进第二轮，换成广告风格：

```bash
.venv/bin/python tools/tts_audition2.py out/tts_audition2 [config.json]
```

   - 台词改用感叹号。
   - 加入声音设计的候选，例如"30 岁左右的男性运动品牌广告配音员，声音明亮洪亮、穿透力强，重音铿锵有力"。
   - 支持指令的音色，统一用广告风格的指令。
4. 推荐时把指标和理由一起告诉用户，但说明你听不到声音，最终由用户的耳朵决定。

本项目的经过：Kai（纪录片腔）被评价"情绪调动弱"；第一轮的 16 个候选都"不够激情"；第二轮里用户选了 CosyVoice 龙飞。

## 3. 台词表写法

`audio/vo_lines.json`：

```json
[
 {"id": "L03", "voice": "longfei_v3", "mood": "normal", "text": "而这颗球，第一次落在中国的地板上——是四十七年前。", "say": "而这颗球，第一次落在中国的地板上，是四十七年前。"},
 {"id": "L21a", "voice": "longfei_v3", "mood": "hype", "text": "詹姆斯来了。", "say": "詹姆斯来了！"},
 {"id": "L23", "voice": "longfei_v3", "mood": "quiet", "rate": 0.8, "text": "然后，灯，灭了。"}
]
```

- `text` 是字幕原文。`say` 是实际念的文本，省略时等于 `text`。
- 高潮句在 `say` 里用感叹号。CosyVoice 这类不支持指令的音色，语气主要靠标点来带。
- 破折号在 `say` 里换成逗号。CosyVoice 可能把"——"念成杂音。
- `mood` 取 `hype` / `quiet` / `normal`，用于挑版本和混音增益。
- `rate` 是语速。安静句用 0.8–0.9。
- 用 qwen3-tts-instruct 时，可以加 `inst` 字段写语气指令。所有句子共用一个基础人设，每句只追加一处差异（放慢、收住、加重某个词）。形容词堆得越多（"像在讲秘密""带一点好笑"），语气越怪。

## 4. 多版本合成与自动挑选

```bash
.venv/bin/python tools/vo_takes.py audio/vo_lines.json audio/vo 3
.venv/bin/python tools/vo_takes.py audio/vo_lines_v.json audio/vo_v 3
```

- 每句用随机种子 1、2、3 各出一版，存在 `takes/<id>_s<seed>.wav`，并裁掉首尾静音。
- 每一版都用语音识别核对，同音字（他/它/她）视为一致。
- 时间槽从 `scenes/film_h.json` 和 `film_v.json` 读取，等于"下一句的起点减本句的起点"。横竖版共用的句子取较小的那个。
- 挑选规则：先要求读音正确、放得进时间槽；在这些版本里，高潮句选"穿透力 + 0.5 × 重音对比"最大的，安静句选基频最低的，平叙句选基频居中的。
- 结果写进 `picks.json`。用户点名换某句时，直接把 `takes/` 里的另一版复制过去，不用重新合成。
- 本项目里被排除的念错版本，例如"球馆"念成"酒馆"、"仰起"念成"扬起"、"中国赛"念成"中国再"。所以每句至少出 3 版。
- 换音色前，先备份原来的 `audio/vo/`，例如复制成 `audio/vo_kai/`。

## 5. 时长与时间轴

- 合成完会写出 `durations.json`。timeline 脚本读取它并断言旁白不重叠。
- 换音色或重新合成后，必须按顺序重做：timeline → 混音 → 重渲画面（字幕的显示时长跟着旁白变）→ 交付。
- 龙飞的语速约每秒 4.5–5.5 个字，比 Kai 快。换成快的音色通常不会挤乱时间轴；换成慢的音色，要先检查时间槽。

## 6. 踩过的坑

| 现象 | 原因或解决 |
| --- | --- |
| 被评价"语气不对劲" | 每句的语气指令写法不统一、形容词太多。改成统一人设，每句只加一处差异 |
| 被评价"力量感不强""不够激情" | 音色本身的问题，改指令救不回来。换音色，或者用声音设计 |
| 批量合成时报 `Throttling.RateQuota` 或 HTTP 429 | 并发降到 2，失败后等 4、8、12 秒重试 |
| CosyVoice v3 的音色报 Engine error 4 | 模型写错了，v3 的音色要配 `cosyvoice-v3-flash` |
| 各句音量差 10 dB 以上 | 混音时逐句归一化（`sfxlib.load_vo`），再按 mood 补回轻重（`sfxlib.vo_gain`） |
| 不能克隆真人声音 | 只用系统音色或声音设计 |
