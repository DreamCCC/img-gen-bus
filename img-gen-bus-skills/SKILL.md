---
name: img-gen-bus-skills
description: img-gen-bus 仓库的根经验库：AI 视频与音乐内容（宣传片、NBA 战术拆解、B 站科普口播、AI 翻唱、MV）的通用铁律、项目地图，以及"识别错误 → 定位原因 → 修正 → 复查"的方法和错误目录。Use when starting or continuing any sub-project in img-gen-bus（nba-china-games、nba-tactics、creator-channel 下各期、music_remix），when rendering, mixing or delivering video/audio, when generating with 百炼/万相/通义万相/qwen-image/Suno, when downloading footage, or when the user reports 卡顿、画面有问题、对不上、不好听、AI 味、看不懂 等问题。
---

# img-gen-bus 根经验库

本仓库做"代码画面 + AI 生成 + 真实素材"混合的视频和音乐。各子项目流程不同，但犯过的错高度重复。开工前读完本文件；碰到问题时按"识别与修正"一节走，并查 [references/error-catalog.md](references/error-catalog.md)。

## 铁律（每个子项目都适用）

1. **先样片后成片。** 风格、音色、字幕、定妆照这类决定，先出 10–20 秒样片或一张图，用户点头再铺开。
2. **所有改动都要亲眼看过。** 渲染出来抽帧看，不凭代码推断"应该没问题"。你听不到声音：可以报指标，好不好听要请用户试听。
3. **数据驱动时间轴。** 音乐拍点和一张事件表（JSON）驱动画面、字幕、音效，音画天然对齐。不要手填时间。
4. **人物分工。** 真实人物只用真实影像；AI 不生成可辨认的真人面孔，不克隆真人声音（包括歌手）。虚拟角色可以用 AI 生成，但要在发布时标注 AI。
5. **事实要有出处。** 查不到就删，不让用户替你核实；要核实就自己上网查。
6. **安全。** 密钥只放 `.env`（已 gitignore），绝不打印。远程只用 ssh 加 git，**不用 scp**。不看远程服务器上的环境变量和密钥。
7. **混音不做闪避。** 人声出来时不压低音乐，用户明确否定过两次。用固定 EQ 凹口、段落固定音量和固定增益。
8. **删除要谨慎。** 只删自己生成的中间文件；用户文件要先列清单征得同意。用明确的路径列表删，不写 `cd 目录 && rm -rf *`。
9. **用户反馈的时间点就是线索。** 用户说"2:44 到 2:50 卡顿"，先把那段逐帧量化，找到真正的原因再改，不要凭猜测重做。

## 项目地图

| 路径 | 内容 |
| --- | --- |
| `nba-china-games/hybrid-promo-video/` | 宣传片 skill（横版 + 竖版，Canvas 逐帧渲染，TTS 旁白，卡点配乐）。做宣传片、回顾片时直接按它走 |
| `nba-tactics/` | NBA 回合战术拆解 skill（`SKILL.md`）：查库找片段、球场标定、球员跟踪、时停与子弹时间、地板战术线、战术板。参考实现 `kd_macau/`（杜兰特澳门两球）。数据库查询 `tools/nba_sql.py` 和片段下载 `tools/fetch_clip.py` 其他 NBA 项目也能用 |
| `creator-channel/口播风格指南.md` | B 站科普口播怎么写（以它为准） |
| `creator-channel/文稿去AI味清单.md` | 去 AI 味规则（与上一份冲突时以风格指南为准） |
| `creator-channel/tools/` | `ai_lint.py`（AI 味机检）、`style_stat.py`（口播指标对比）、`wan_video.py`（万相视频，支持首帧和音频驱动）、`transcribe_ref.py` |
| `creator-channel/ep01_4.8pct/` | 第 1 期（高考），工具最全：`tools/` 下有 tts、vo_takes、bili、tikhub、yt_search、sheet、montage、prep_clip、genimg；`.env` 和 `.venv`（含 yt-dlp、dashscope）也在这里 |
| `creator-channel/ep02_threebody/` | 第 2 期（三体，已搁置），`tools/qa.sh` 渲染静帧联系表 |
| `creator-channel/music_remix/baby_citypop/` | AI 翻唱 + MV 完整实现（Suno 翻唱、万相对口型、年代调色、日中双语卡拉 OK 字幕），流程见 [references/music-mv.md](references/music-mv.md) |
| `img-gen-bus-skills/scripts/` | 通用体检和修复脚本，见下 |

## 识别与修正：工作循环

每做完一步、每次用户反馈问题，都走一遍：

```
1. 量化  把问题区段变成数字和图：抽帧接触表、逐帧差分、每秒码率、响度、识别文本对比
2. 定位  逐个关掉组件，或分段二分，直到能指着一个文件或一行参数说"就是它"
3. 修正  改根因，不改症状；改动要能复用（写成参数、脚本或规则）
4. 复查  用同一把尺子再量一次，指标回到正常范围才算修好；再抽帧看一眼
5. 沉淀  新坑写进 references/error-catalog.md，被用户打回的做法写进 references/user-feedback.md
```

具体的量化手段和命令见 [references/find-and-fix.md](references/find-and-fix.md)。

## 通用脚本

用任一装了 numpy 的 venv 运行（例如 `creator-channel/music_remix/.venv/bin/python`）。

```bash
# 成片或片段体检：帧数与时长、每秒码率、重复帧、冻结、黑场
python img-gen-bus-skills/scripts/video_qa.py out/成片.mp4
python img-gen-bus-skills/scripts/video_qa.py out/成片.mp4 --from 195 --to 206 --region 0.333,0.333,0.333,0.333
python img-gen-bus-skills/scripts/video_qa.py wan/F2.mp4 --max-mbps 0      # 中间文件不查码率

# AI 视频重复帧修复（删重复帧 + 运动补偿插帧，时间轴不变）
python img-gen-bus-skills/scripts/smooth_dups.py wan/F2.mp4 wan/smooth/F2.mp4

# B 站封面：底图 + 大字，出 16:9 和单独排版的 4:3，文字自动收进 4:3 安全区
python img-gen-bus-skills/scripts/cover.py out/cover/cover.json
```

封面底图用没有烧录字幕的原始素材（万相空镜、首帧图），不要从成片里截帧。封面大字直接写"这期做了什么"，例如"三体问题为什么无解？""把比伯的《Baby》改成1989年东京City Pop"。

## 交付前必查

- [ ] `video_qa.py` 全片通过：帧数等于时长 × 帧率，没有重复帧、冻结、黑场，码率峰值不超过约 50 Mbps（交付编码用 `-crf 18 -maxrate 40M -bufsize 80M`）。
- [ ] 全片接触表从头扫到尾（每 2.5–8 秒一格），用户提过的时间点单独逐帧看。
- [ ] 字幕和歌词、旁白对得上；识别核对过没有念错或唱错的字。
- [ ] 素材出处和 AI 生成声明写进片尾或 CREDITS。
- [ ] 最终报告写清：文件路径、规格、时长；改了什么、为什么；哪些需要用户亲自看或听。

## 参考文档

| 什么时候读 | 文档 |
| --- | --- |
| 出了问题、要自检时 | [references/find-and-fix.md](references/find-and-fix.md)：识别错误的手段和命令 |
| 遇到报错或怪现象 | [references/error-catalog.md](references/error-catalog.md)：现象 → 原因 → 修法 |
| 开工前、写稿前 | [references/user-feedback.md](references/user-feedback.md)：被用户打回过的做法和开工前要问清的事 |
| 做 AI 翻唱、MV、虚拟歌手 | [references/music-mv.md](references/music-mv.md) |
| 做宣传片、回顾片 | `nba-china-games/hybrid-promo-video/SKILL.md` |
| 做战术解析、回合拆解、进球分析，或要查 NBA 数据库、下载比赛片段 | `nba-tactics/SKILL.md` |
