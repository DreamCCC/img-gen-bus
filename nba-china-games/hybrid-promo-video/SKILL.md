---
name: hybrid-promo-video
description: 制作"真人影像 + 代码动画 + AI 生图"有机混合的宣传片、历史回顾片、赛事或品牌短片，同时出横版（约 3 分钟）和竖版（约 60 秒）。全流程在本地自动化：查证写稿、网上找官方素材、百炼 TTS 旁白、可商用配乐按拍点卡画面、Canvas 逐帧渲染、Python 合成音效与混音、ffmpeg 交付。Use when the user asks to 做宣传片、品牌片、回顾片、纪录短片、混剪、卡点视频、带旁白和配乐的视频，或提到横版加竖版、TTS 配音、片头片尾包装、素材二次加工。
---

# 混合影像宣传片（横版 + 竖版）

参考实现：NBA 中国赛 47 年回顾片，横版 3:17、竖版 62 秒，用户已验收。
- [scripts/](scripts/)：可直接使用的工具。
- [templates/](templates/)：参考实现，新项目照着改。
- [references/](references/)：各环节的细节文档，做到哪一步再读对应的那一篇。

本 skill 不依赖特定 agent。只要能执行 shell 命令、读写文件、看图片，就能按下面的流程做。

## 铁律

**音乐决定时间轴，一张事件表驱动画面和声音；人物只用真实影像；每个事实都要有出处；先做样片，再做成片。**

## 五条核心原则

1. **音乐驱动时间轴。** 先选曲、测拍点，再从拍点推出所有锚点（幕切换、重音、硬停、爆点）。画面去卡音乐，不要让音乐迁就画面。
2. **一张事件表管所有同步。** `timeline_*.py` 生成 JSON，里面有场景区间、旁白起点、事件时间和音乐剪接点。画面（film.html）和音效（mix_film.py）读同一份数据，音画天然对齐。
3. **分工明确，人物用真实影像。** 代码画的人、AI 生成的人都显得呆和假，用户试过几轮后明确否定了。
   - 真人影像：所有人物和动作。
   - 代码动画：数据、文字、地图、标尺、计分牌、翻页、转场、包装。
   - AI 生图：只补没有影像的环境画面（老街景、空房间、静物），不能出现可辨认的人脸。
4. **只用可核实的事实和有授权的素材。** 旁白的每个说法都要有出处，查不到就删。画面只用官方账号发布的素材，配乐只用 CC BY 或 CC0。每条素材都要记进 CREDITS.md。
5. **用户确认后再往下做。** 以下几处要停下来等用户点头：样片风格、旁白音色、配乐曲目、删除文件。

## 环境与约束

- **运行环境**：macOS 或 Linux，需要 Python 3.10 以上、Node 18 以上、ffmpeg、Google Chrome。补帧用的 venhance（RIFE）只能在 Apple Silicon 上用 MPS 加速，其他平台见 `templates/project/requirements.txt` 里的说明。
- **密钥**：只放在项目根目录的 `.env` 里（`DASHSCOPE_API_KEY` 必需，`TIKHUB_API_KEY` 用于检索抖音、B 站、YouTube），并加入 gitignore。绝不在对话或日志里打印密钥。项目结束后提醒用户轮换密钥。
- **TTS 和生图**：只用阿里云百炼。不能克隆真实人声，AI 不能生成真实人物的面孔。
- **素材来源**：只用官方账号。第三方媒体只用来核对事实，不能进成片。
- **远程操作**：不用 scp，只用 ssh 加 git。
- **有沙箱的 agent**：启动 Chrome（puppeteer）、跑 venhance、访问外网下载，通常都要在沙箱外执行，或申请完整的网络和系统权限。报 SSL 错误、Chrome 起不来、MPS 不可用时，先怀疑沙箱。
- 删除文件时用明确的路径列表，不要写 `cd 某目录 && rm -rf *`。

## 开新项目

```bash
bash <skill目录>/scripts/init_project.sh <项目目录> --install   # 建目录、复制脚本和模板，可选：建 venv、装依赖
cp <项目目录>/.env.example <项目目录>/.env                       # 由用户自己填入密钥
```

生成的目录结构（所有脚本都假设 `ROOT` 是 `tools/` 的上一级目录）：

```
<项目>/
  .env  .gitignore  requirements.txt  package.json  clips_h.json
  render.mjs  render_par.sh  rerender_part.sh  deliver.sh
  tools/    prep_clip.py fx.py sheet.py montage.py music_probe.py genimg.py
            tikhub.py bili.py yt_search.py tts.py tts_audition*.py vo_takes.py timeline_h.py timeline_v.py
  audio/    sfxlib.py mix_film.py mix_film_v.py vo_lines.json vo_lines_v.json vo/ vo_v/
  scenes/   film.html film_h.json film_v.json clips/
  assets/   footage/ music/ gen/ CREDITS.md
  out/      静帧、接触表、样片、母版、交付文件
```

`templates/` 里的文件是 NBA 项目的完整实现。新项目照着改场景、台词、时间轴，不要从零写。

## 架构

```
查证与脚本 ─► timeline_h.py（librosa 测拍点）─► scenes/film_h.json ◄─ timeline_v.py ─► film_v.json
                                                  │ 场景 / 旁白 / 事件 / 音乐剪接点
素材下载 ─► sheet.py 挑镜头 ─► clips_h.json ─► prep_clip.py ─► scenes/clips/<名字>/%05d.jpg
                                                  │
                      scenes/film.html：window.renderFrame(t)（Canvas 2D，逐帧确定性绘制）
                                                  │
               render.mjs（puppeteer 截帧送 ffmpeg）◄─ render_par.sh 分段并行 / rerender_part.sh 局部重渲
vo_takes.py 旁白 ─┐
配乐 mp3 ─────────┼─► mix_film.py（合成音效 + 固定增益混音）─► mix.wav ─► deliver.sh ─► 交付 mp4
事件表 ───────────┘
```

## 工作流清单

复制这张清单，逐项打勾：

```
- [ ] 0  需求：问清问题表里的每一项，尤其是旁白腔调 → references/brief-and-script.md
- [ ] 1  查证与脚本：分幕结构，每句标出处，镜头表（每句对应真人 / 代码 / AI）
- [ ] 2  配乐：找可商用曲目，用 music_probe.py 看能量曲线，定剪接点和硬停点 → references/music-and-timeline.md
         ⏸ 把候选曲目交给用户试听确认
- [ ] 3  旁白：第一轮试音（tts_audition.py），必要时第二轮（tts_audition2.py） → references/voiceover.md
         ⏸ 用户选定音色后，用 vo_takes.py 正式合成
- [ ] 4  时间轴：timeline_h.py 从拍点推出锚点，断言旁白不重叠
- [ ] 5  素材：只搜官方账号，下载，用 sheet.py 挑镜头，写 clips_h.json，跑 prep_clip.py → references/footage-and-images.md
         找不到的画面如实告诉用户，并给替代方案
- [ ] 6  AI 生图：genimg.py，只出空镜和背影
- [ ] 7  页面：在 film.html 里按场景写 sc_xxx(t, f) → references/canvas-render.md
- [ ] 8  静帧自检：render.mjs --stills 加 montage.py，每个场景至少看 2 帧
- [ ] 9  样片：先渲染 10–20 秒并混好音
         ⏸ 用户认可风格后再铺全片
- [ ] 10 混音：mix_film.py，每句旁白在人声频段比背景高 1 dB 以上 → references/sound-and-delivery.md
- [ ] 11 横版：render_par.sh h 4，接触表复查，有问题用 rerender_part.sh 局部重渲
- [ ] 12 竖版：timeline_v.py 选镜头，film.html?v=1 重新构图，mix_film_v.py，渲染
- [ ] 13 交付：deliver.sh 压制，复测响度，补齐 CREDITS.md，过质检清单 → references/troubleshooting-and-qa.md
- [ ] 14 最终报告
- [ ] 15 用户说告一段落时，清理中间文件（先列清单，用户同意后再删）
```

## 常用命令

```bash
# 素材
.venv/bin/python tools/tikhub.py videos "关键词" 2               # 抖音，★ 标记的是官方号
.venv/bin/python tools/yt_search.py "关键词"                     # YouTube，下载用 yt-dlp
.venv/bin/python tools/bili.py search "关键词"                   # B 站
.venv/bin/python tools/sheet.py in.mp4 out/sheet.jpg 2 8         # 带时间码的接触表
.venv/bin/python tools/prep_clip.py clips_h.json [名字 ...]      # 按规格处理片段，可只处理指定的几个

# 配乐、旁白、生图
.venv/bin/python tools/music_probe.py assets/music/*.mp3
.venv/bin/python tools/tts_audition.py out/tts_audition
.venv/bin/python tools/vo_takes.py audio/vo_lines.json audio/vo 3
.venv/bin/python tools/genimg.py prompts.json assets/gen

# 时间轴、混音
.venv/bin/python tools/timeline_h.py && .venv/bin/python tools/timeline_v.py
.venv/bin/python audio/mix_film.py && .venv/bin/python audio/mix_film_v.py

# 画面
node render.mjs scenes/film.html out/st --stills 12.5,30,47.2   # 竖版加环境变量 QUERY=v=1
.venv/bin/python tools/montage.py out/st.jpg 3 480 out/st/*.png
./render_par.sh h 4 out/film_h_master.mp4 out/film_h_mix.wav
./render_par.sh v 4 out/film_v_master.mp4 out/film_v_mix.wav

# 交付
./deliver.sh out/film_h_master.mp4 out/film_h_mix.wav out/成片_横版.mp4 22M
./deliver.sh out/film_v_master.mp4 out/film_v_mix.wav out/成片_竖版.mp4 16M
```

## 关键经验（被用户打回过的地方）

| 被打回的做法 | 正确做法 |
| --- | --- |
| 用代码或 AI 画人物 | 人物一律用真实影像 |
| 用纪录片腔的音色，被说"力量感不强""不够激情" | 开工前问清腔调。宣传片多半要铿锵有力的广告腔，本项目选的是 CosyVoice `longfei_v3` |
| 旁白一出来就压低音乐，被说"此起彼伏" | 不做闪避：固定 EQ 凹口 + 段落固定音量 + 固定增益交付 |
| 单遍 loudnorm 交付 | 测出整体响度，算一个固定增益，再过采样限幅 |
| 每句语气指令都写一大串形容词 | 一个基础人设，每句只加一处差异 |
| 画面没有卡在拍点上 | 先定音乐，再从拍点推出画面时间 |
| 直接铺全片 | 先做 10–20 秒样片给用户确认 |

## 禁止事项

- 编造事实、比分、引语。查不到出处的就删掉。
- 用第三方媒体或球迷上传的画面。
- 用 AI 生成真人面孔，或克隆真人声音。
- 不看静帧就交付。所有画面改动都要渲染出来亲眼看过。
- 宣称"听过了"。你听不到声音：可以报指标，但音色和配乐要请用户试听确认。
- 不列清单就删除文件。
- 在对话、日志或提交记录里出现密钥。

## 最终报告

写清楚：交付文件的路径、规格、时长、响度；没找到的素材和替代方案；因为无法核实而删掉的说法；配乐署名要求；需要用户亲自确认的地方（曲目、音色、整片观感）；提醒轮换密钥。详见 [references/troubleshooting-and-qa.md](references/troubleshooting-and-qa.md)。

## 参考文档索引

| 环节 | 文档 |
| --- | --- |
| 需求问题表、查证、分幕结构、镜头表、竖版改写、样片 | [references/brief-and-script.md](references/brief-and-script.md) |
| 选曲、测拍点、剪接与硬停、时间轴 JSON 结构 | [references/music-and-timeline.md](references/music-and-timeline.md) |
| 素材渠道、挑镜头、裁切、prep_clip、AI 生图 | [references/footage-and-images.md](references/footage-and-images.md) |
| 百炼各条 TTS 线、选音色、台词表、多版本挑选 | [references/voiceover.md](references/voiceover.md) |
| film.html 约定、竖版重新构图、渲染、自检 | [references/canvas-render.md](references/canvas-render.md) |
| 合成音效、混音、交付压制与响度 | [references/sound-and-delivery.md](references/sound-and-delivery.md) |
| 踩坑清单、质检、最终报告、收尾清理 | [references/troubleshooting-and-qa.md](references/troubleshooting-and-qa.md) |
