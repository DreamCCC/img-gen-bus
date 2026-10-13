---
name: nba-play-breakdown
description: 把 NBA 转播里的单个回合做成战术拆解短视频：从数据库按逐回合记录（PBP）找片段并下载，球场标定与镜头补偿、球员检测跟踪、人形蒙版、4 倍插帧慢放，再用一张 EDL 驱动时停、倒带、子弹时间、地板战术线（被球员身体遮挡）、球员圈与名牌、小战术板、百炼旁白和原声音效混音，最后多球合成成片。Use when the user asks for 战术解析、战术拆解、回合复盘、进球分析、画战术线、时停、子弹时间、战术板、球员标注，或要分析某个球员某场比赛的进球、助攻、防守视频。
---

# NBA 回合战术拆解视频

参考实现：`kd_macau/`。2026 中国赛澳门站火箭对独行侠，杜兰特两记进球：第 464 号事件是 25 英尺三分，用户确认了风格；第 453 号事件是 12 英尺急停。两球合成成片 `kd_macau/out/kd_macau_breakdown_full.mp4`，时长 1 分 34 秒，用户已验收。特效版（时停发光、流光传球、冲击波、视线锥、空间控制图、突破残影、进球特效）的 EDL 是 `e453_fx_edl.json`、`e464_fx_edl.json`，合成 `kd_macau/out/kd_macau_breakdown_fx.mp4`。新项目在 `nba-tactics/<项目名>/` 下照着 `kd_macau` 的文件改，不要从零写。

本仓库的通用铁律（先样片后成片、亲眼看过、不做闪避、不用 scp、事实有出处）见 `img-gen-bus-skills/SKILL.md`，这里不重复。

## 目标

观众看完要能说出"这球是怎么来的"。即使没有成套战术，也要让人一眼看清：谁吸引了防守，谁漏了人，空位有多大，出手时防守人有多近。每个画面加工都为这个目的服务，不为炫技。

## 本项目的铁律

1. **数字以数据库为准，画面只做佐证。** 时间、比分、出手距离、助攻人、本场第几分、第几次助攻都来自 `kb_pbp` 和 `kb_pbs`。画面追踪算出的距离只是估算，要先和 PBP 的 `shot_distance` 对一下（误差在 1 英尺以内才可信），片尾注明"球员位置：画面追踪估算"。
2. **球员身份要有两个证据。** 号码看原图裁切，名单看 `kb_pbs`；看不清号码时，用换人记录反推当时在场的五个人。认不出就用"弱侧协防人"这类泛称，不要猜名字。
3. **线画在地板上，并且被人挡住。** 跑位、传球、测距线都在球场坐标里算，再投回画面，用人形蒙版把重点球员压在线上面。不要在屏幕空间里画浮动的线。
4. **只用真实画面。** 不用代码画人。小战术板上的球员用圆点表示，这种示意可以接受。
5. **旁白决定时停长度。** 每次时停持续多久，由那句旁白的长度决定（EDL 自动排）。不要手填时长再让旁白去凑。
6. **默认不加背景音乐。** 只用旁白、原声和音效。原声通常是英文解说：原速段低音量垫底，进球后没有旁白的空档恢复原始音量。

## 环境

- `nba-tactics/.venv`（uv 建的）：ultralytics、opencv、torch（Apple Silicon 用 MPS）、numpy、pillow、dashscope、librosa。YOLO 权重（`yolo11x.pt`、`yolo11x-seg.pt`）首次运行自动下载。
- 百炼密钥 `DASHSCOPE_API_KEY`：`vo.py` 先读 `nba-tactics/.env`，没有就读 `creator-channel/ep01_4.8pct/.env`。不要打印密钥。
- **以下命令要在沙箱外运行**（申请 `all` 权限）：`render_play.py` 全片或联系表（多进程信号量）、`seg.py`、`ball.py`、`track.py`（MPS），以及 SSH 查库。
- 字体在 `assets/fonts/`：Noto Sans SC（中文）、Barlow Condensed（数字）。

## 目录结构

```
nba-tactics/
  tools/      nba_sql.py fetch_clip.py track.py calib.py camera.py traj.py seg.py ball.py gridsheet.py vo.py render_play.py court.py
              check_shot.py（出手距离和画面数字对账） check_labels.py（标签重叠检查）
  assets/fonts/
  <项目>/
    data/            PBP 等查询结果 JSON
    raw/             下载的片段 eNNN_xxx.mp4（NNN = PBP action_number）
    eNNN_players.json  跟踪 ID → 球员
    eNNN_vo.json       旁白台词
    eNNN_edl.json      剪辑表（时间轴 + 图层）
    work/eNNN/       tracks.json cam.json players.json masks/ fr/orig fr/slow ids/ preview/
    work/calib/      GNNN_<帧>.npy 和核对图
    audio/eNNN/      旁白 wav、durations.json、picks.json
    qa/              联系表、转场条
    out/             eNNN_v1.mp4、成片
```

## 工作流清单

复制这张清单，逐项打勾。命令都在项目目录（如 `kd_macau/`）下用 `../.venv/bin/python ../tools/...` 运行。

```
- [ ] 1  选题与数据：找比赛、找目标球员的命中回合、拉前后 PBP、名单和号码 → references/data-and-footage.md
- [ ] 2  找片段并下载：按 game + event_id 对上 PBP，下载，md5 去掉重复的 01/02 版本
- [ ] 3  看懂回合：接触表 → 逐帧裁切放大，写出传球链和关键帧号（接球、分球、出手、进框）
         核对记分牌和 PBP 的时间、比分一致
- [ ] 4  跟踪：track.py，看 ids/ 预览认人，写 eNNN_players.json → references/vision-pipeline.md
- [ ] 5  标定：挑禁区完整的参考帧，读四角，calib.py 求 G，看核对图；camera.py 链到全片段
- [ ] 6  轨迹：traj.py，打印关键帧的距离（出手距离写好 EDL 后由 check_shot.py 自动比对）
- [ ] 7  蒙版和慢放：seg.py（10 名球员）、ffmpeg 4 倍插帧并拆帧（可以和第 8 步并行）
- [ ] 8  旁白：写 eNNN_vo.json，vo.py 合成 3 条并用 ASR 核对 → references/script-and-audio.md
- [ ] 9  EDL：段落 + 图层 → references/edl-and-render.md
- [ ] 10 自检：先跑两个脚本，都要 0 错误
         check_shot.py   出手距离、三分线内外、画面和旁白里的数字 vs PBP
         check_labels.py 名牌重叠、压字幕、压战术板（报出的帧直接 --preview 看）
         再 --sheet 1.0 看节奏，--preview 逐个看每段关键帧的全尺寸图
- [ ] 11 样片：先做一球
         ⏸ 用户确认风格、音色、要不要背景音乐
- [ ] 12 全片：render_play.py --out；测响度；其他球照同样风格做
- [ ] 13 合成：多球按比赛时间排序，画面交叉淡化，音频不交叉淡化；接触表 + 转场条复查
- [ ] 14 最终报告
```

## 常用命令

```bash
# 数据（SSH 到白名单服务器代发，只读）
../.venv/bin/python ../tools/nba_sql.py "SELECT ... FROM nba_game_prod.kb_pbp WHERE game_id='...'" -o data/pbp.json
../.venv/bin/python ../tools/fetch_clip.py <news_id> -d raw/

# 视觉
../.venv/bin/python ../tools/track.py raw/e453_pullup.mp4 work/e453 --end 11.8 --every 15
../.venv/bin/python ../tools/gridsheet.py raw/e453_pullup.mp4 work/calib/grid.jpg 184 --crop 300,400,1500,900
../.venv/bin/python ../tools/calib.py raw/e453_pullup.mp4 184 "390,695=0,8;643,496=0,-8;1155,794=19,8;1340,565=19,-8" work/calib/G453_184.npy
../.venv/bin/python ../tools/camera.py raw/e453_pullup.mp4 work/e453 --ref 184 --G work/calib/G453_184.npy --end 11
../.venv/bin/python ../tools/traj.py work/e453 e453_players.json
../.venv/bin/python ../tools/seg.py raw/e453_pullup.mp4 work/e453 --ids <players.json 里用到的全部跟踪 ID> --start 55 --end 265

# 旁白、自检、渲染
../.venv/bin/python ../tools/vo.py e453_vo.json audio/e453 3
../.venv/bin/python ../tools/check_shot.py e453_edl.json            # 不到 1 秒，沙箱里能跑
../.venv/bin/python ../tools/check_labels.py e453_edl.json          # 约 1 分钟，多进程要在沙箱外；--workers 1 可在沙箱里跑
../.venv/bin/python ../tools/render_play.py e453_edl.json --sheet 1.0
../.venv/bin/python ../tools/render_play.py e453_edl.json --preview 420,770,950
../.venv/bin/python ../tools/render_play.py e453_edl.json --out out/e453_v1.mp4
```

## 叙事模板（每球 40–55 秒）

参考实现两球都用这个结构，用户认可。

| 段 | 画面 | 旁白要点 |
| --- | --- | --- |
| live | 原速播完整回合；左上角比赛信息卡；重点球员金圈 | 先给结论：比分背景，这球最显眼的一点（空位将近 5 米、贴脸还是进了） |
| rew | 倒带回到传球前，角标"倒回" | "这球是怎么打出来的？倒回去看。" |
| A 时停 | 画面变灰，只留 3–4 个相关球员是彩色；第一条传球线 | 谁持球、谁在防谁 |
| 慢放 ×0.25 | 持球人突破路线（橙色），防守人移动路线（蓝色） | 持球人往哪走，谁离开了自己的人 |
| B 时停 | 收缩区域（蓝色包络）或测距线 | 几个人被吸过去，漏了谁，拉开了多远 |
| 子弹时间 ×0.25 | 球带光晕飞出，传球线（金色） | 一句短话："申京马上分球。" |
| C 时停 | 接球人的"最近防守人"范围圈 | 空位有多大，扑防的人从哪来 |
| 慢放 ×0.5 | 接球后的动作，扑防路线 | 出手前的那一步 |
| R 出手定格 | 投篮线 + 距离标签，测距线到封盖人，出手弧线 | 出手距离，封盖多近 |
| 慢放进框 | "命中"压在球进框那一帧，篮下弹出 +2 或 +3 | "12 英尺，命中！" |
| end | 原速、原声欢呼 | 无旁白 |
| card | 背景虚化缓推；比分 + 三行数据 + 完整战术板复盘 | 一句总结，点出规律 |

## 被用户认可的做法和踩过的坑

| 情况 | 做法 |
| --- | --- |
| 自动检测球基本都是误检（场边静物） | 传球中的球位、篮筐位置人工读点：`gridsheet.py` 出带像素网格的放大图，写进 EDL 的 `ball` 和 `anchors` |
| 跟踪编号一个回合 100 多个，经常串号 | 不追求全自动：按帧段把编号指给球员（`ids`），串号段用 `manual` 人工补脚底点 |
| 下方数据条挡住球员的脚，框底不等于脚底 | 被挡的那几帧用 `manual` 补点；看到"位置突然偏了"，先查是不是被图形挡住，再怀疑相机 |
| 球员起跳时脚底投影会把人"抬"到场外 | 在 `air` 里写起跳到落地的帧段，用两端位置插值 |
| 名牌互相重叠、压住别的重点球员、压住字幕或战术板 | 渲染器按优先级避让：上推并画引线，横向让开重点球员身体，字幕区算障碍，战术板和信息卡挪到位移最小的一侧。`check_labels.py` 逐帧量，e464 样片里"申京压住战术板 4 秒"就是它查出来的 |
| 战术板上名字被别的圆点或篮筐挡住 | 渲染器依次试右、左、上、下，选第一个不压圆点的位置 |
| 时停是死图，被体检脚本判成冻结，观感也僵 | 每个时停带 1.05–1.16 倍缓推（EDL 的 `zoom`），收尾卡片背景也缓推 |
| ASR 把"申京"听成"神经" | 不是念错。`alias` 里写同音别名，只用于核对 |
| "往里突"被听成"往里吐"，"晚了二十五英尺"断句错 | 改写台词（"往篮下冲"）或拆成两句；自动核对忽略标点，停顿错位要看识别断句，用 `pick` 指定 take |
| 原声只有 -44 dBFS，听不出现场感 | 原速段原声比旁白低约 16 dB；进球后的空档恢复原始音量 |
| 旁白点名里萨谢，画面亮的却是比贝罗维奇（e464 C 时停） | 时停帧选在旁白点名的人**身体可见**的那一帧：第 124 帧里萨谢被申京挡住、没蒙版，挪到 128 帧他冲出来时再停。`spot` 只放旁白说到的人，其他人的名牌在这个时停前收掉 |
| 发光描边包不住人、边缘锯齿（YOLO 蒙版粗，漏掉深色皮肤和球衣） | `glow` 时停帧自动用 SAM2（`work/sam2.1_l.pt`）按跟踪框重抠，存 `masks_hq/`；没跟踪框的人在 EDL `mask_box` 里给框 |
| 想做"转播视角飞到正上方俯视" | 不做。单机位斜拍的远端地板分辨率太低，拉成俯视严重失真；换矢量球场后用户仍觉得一般。用万相等生成模型补过渡也不行：球员位置、人数、号码会变，违背只用真实画面。俯视信息交给右上角战术板 |

## 交付前必查

- [ ] `check_shot.py` 和 `check_labels.py` 都是 0 错误；提醒逐条看过预览图再决定改不改。
- [ ] 每段至少一张全尺寸预览看过：线贴地板并被人挡住，战术板和画面同步，没有抠错人（这些脚本查不了）。
- [ ] 画面上和旁白里的每个数字都能在 PBP 或 `kb_pbs` 里找到，或标明是画面估算（脚本只覆盖出手距离、得分、助攻、比分，其他数字人工核）。
- [ ] 字幕和念出来的一致（ASR 核对通过，或已按实际读音改字幕）。
- [ ] 响度：单球约 -21 LUFS，峰值不超过 -1 dBFS。发平台前问用户要不要提到 -16 LUFS。
- [ ] 合成片：用接触表从头扫到尾，转场条逐帧看；第二球开头的旁白没被淡入吃掉。
- [ ] 最终报告：文件路径、规格、时长、响度；每球讲了什么；改了什么；哪些需要用户亲耳听（人名读音、原声电平）。

## 参考文档

| 什么时候读 | 文档 |
| --- | --- |
| 查库、找片段、下载、核对事实 | [references/data-and-footage.md](references/data-and-footage.md) |
| 跟踪、认人、标定、镜头补偿、蒙版、慢放 | [references/vision-pipeline.md](references/vision-pipeline.md) |
| 写 EDL、图层清单、渲染与自检 | [references/edl-and-render.md](references/edl-and-render.md) |
| 写旁白、合成与核对、混音、合成成片 | [references/script-and-audio.md](references/script-and-audio.md) |
