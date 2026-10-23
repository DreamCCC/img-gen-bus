# 交接：《HOW DO YOU BLOW 29?》（马刺 @ 尼克斯 总决赛 G4，横屏 2 分钟英文版）

比赛 `0042500404`，尼克斯 107–106，马刺一度领先 29 分。横屏 1920×1080，英文旁白（Gemini TTS 音色 Charon），
NBA 转播风格的战术 AR + 代码动画，Kevin MacLeod 配乐。文稿见 `文稿_横屏2min_en_v3.md`，大纲 `大纲_v1.md`。

下文路径默认相对 `nba-tactics/spurs_g4/`；`film/` 指 `nba-tactics/spurs_g4/film/`。

## 1. 现在的状态

两个版本都已完成，响度 −16 LUFS 左右，片尾有配乐署名。

| 版本 | 时长 | 本地 | 服务器 |
|---|---|---|---|
| 简化版 | 103.1 s | `film/out/final_simple/HOW_DO_YOU_BLOW_29_simple.mp4` | `/root/backup/spurs_g4_film/final_20261024/` |
| 复杂版（带跟踪 AR，重新卡点） | 117.8 s | `film/out/final_complex/HOW_DO_YOU_BLOW_29_complex.mp4` | 同上 |

同目录还有 `.ass`（字幕）和 `.json`（每个镜头的起点、旁白时刻）。

服务器 `root@8.152.222.232` 上的备份：

| 路径 | 内容 |
|---|---|
| `/root/backup/spurs_g4_film/final_20261024/*.mp4/.ass/.json` | 两版成片 |
| `/root/backup/spurs_g4_film/final_20261024/essentials_20261024.tar`（126 MB） | git 不收、又难以复原的小文件：`film/audio/**`（旁白 wav）、`film/assets/**`（字体、配乐）、各 `work/` 目录里的 json（tracks / cam / players / SAM 注入轨迹 / VO 清单）。tar 内路径相对仓库根 `mgs-code-01/` |
| `/root/backup/spurs_g4_film/inter_20261023b.tar`（3.45 GB，10-23 23:26） | 中间件快照：`film/raw`（全部原始片段）、`film/out`、`film/work`、`work`（含蒙版 npz），不含可再生的 `fr/` 帧和 `fxcache`。tar 内路径相对 `spurs_g4/` |
| `/root/backup/mgs-code-01.git` | 代码的 git 备份远端（remote 名 `backup`） |

## 2. 新设备恢复

### 2.1 代码

```powershell
git clone https://github.com/DreamCCC/img-gen-bus.git mgs-code-01      # 或: git clone root@8.152.222.232:/root/backup/mgs-code-01.git mgs-code-01
```

新设备要先配好能登录 `root@8.152.222.232` 的 ssh key（凭据自己迁移，不进仓库）。远程一律 ssh 和 git，不用 scp。

### 2.2 环境

- **Python 3.12：** 在 `nba-tactics/` 下执行 `py -3.12 -m venv .venv`，然后
  `.venv\Scripts\python -m pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cu128`。
  torch 是 cu128 版，需要 NVIDIA 显卡；没有显卡就把 torch / torchvision 换成 CPU 版，跟踪和 SAM 会慢很多。
- **ffmpeg：** 9.x gyan **full** build（需要 libass 烧字幕、rubberband 变速），放进 PATH。
- **node：** 24.x。在 `film/` 下 `npm install`（puppeteer-core）。代码动画要用本机 Chrome，先设好环境变量 `CHROME_PATH`。
- **`.env`：** 把 `film/.env.example` 复制成 `film/.env`，填 `AIHUBMIX_API_KEY`（英文旁白）、`DASHSCOPE_API_KEY`（ASR）、`TIKHUB_API_KEY`（找片）。密钥绝不打印、不提交。
- **模型权重：** `yolo11x.pt`、`yolo11x-seg.pt`、`sam2.1_l.pt` 由 ultralytics 首次运行时自动下载（放在 `spurs_g4/` 和 `spurs_g4/work/` 下）。
- **Windows shell 前缀：** 每个新终端先跑
  `$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"`。

### 2.3 拉资源（推荐：从服务器拉备份）

PowerShell 5 的管道会把二进制流当文本改坏，下载要走 `cmd /c`：

```powershell
cd C:\...\mgs-code-01\nba-tactics\spurs_g4
cmd /c "ssh root@8.152.222.232 ""cat /root/backup/spurs_g4_film/inter_20261023b.tar"" > inter.tar"
tar -xf inter.tar                      # 先解中间件快照（相对 spurs_g4/）
cd ..\..
cmd /c "ssh root@8.152.222.232 ""cat /root/backup/spurs_g4_film/final_20261024/essentials_20261024.tar"" > essentials.tar"
tar -xf essentials.tar                 # 再解精简包（相对仓库根，会用较新的 json 覆盖快照里的旧版本）
```

下完用 `ssh root@8.152.222.232 "sha256sum <文件>"` 和本地 `Get-FileHash` 比对。两个包解完，跟踪、蒙版、旁白都不用重算；没备份的 `fr/` 帧和 `fxcache` 在渲染时会自动重新生成，第一次渲染会慢一些。

### 2.4 备份拿不到时，资源从源头重新获取

**比赛单回合片段**：文件名就是腾讯体育 NBA 数据库的 `news_id`，用 `nba-tactics/tools/fetch_clip.py` 下载：

```powershell
cd nba-tactics\spurs_g4\film
..\..\.venv\Scripts\python ..\..\tools\fetch_clip.py 2606111142181002 2606110853187102 -d raw/
```

境外出口签名接口一律 403，脚本会自动改由白名单服务器 ssh 取签名地址（细节见 `nba-tactics/references/data-and-footage.md`）。

| news_id | 用在 |
|---|---|
| `2606111142181002`（同时要 `.wav`：`ffmpeg -i x.mp4 x.wav`） | 绝杀补篮：s01 冷开场、s16；跟踪目录 `work/e727w` |
| `2606110853187102` | s04 进球串（e13），`work/e13` |
| `2606110908252902` | s04（e88），`work/e88` |
| `2606110908507902` / `2606110959171102` | s04 简化版备选（e70 / e325） |
| `2606111033176002` / `2606111038291302` / `2606111043178802` | s05a（e432 / e448 / e470） |
| `2606111127202702`（同时要 `.wav`） | 布伦森三分：s06、s08，`work/e676w` |
| `2606111142193902`（放在 `spurs_g4/raw/`，同时要 `.wav`） | 福克斯被盖：sampleA，`work/e715` |
| `2606111151336101` | 第四节集锦。s09 的三个片段 `work/q4miss/s09_e554/593/613.mp4` 由 `work/q4miss/assemble.py` 从它裁出（e613 = 74.0–82.0 s） |
| `2606111112248401` | 第三节集锦（备用） |
| `presser/2606111356236401` | fox 镜头（福克斯赛后，竖屏素材） |
| `presser/2606111429332601` | s17：转播集锦里的现场解说，取 606.65–614.2 s |

其余 `raw/` 里的 id 是没进成片的备选。

**比赛数据**（`data/pbp.json`、`pbs.json`、`shot_detail.json`，已在 git 里）：SQL 网关 `tech-api.nbadata.cn` 有 IP 白名单，
只能用 `tools/nba_sql.py` 经服务器代发，表结构见 `references/data-and-footage.md`（kb_tbs、kb_pbs、kb_pbp、nba_shot_detail）。

**旁白**：配置在 `film/audio/vo_en.json`（Gemini TTS，音色 Charon），生成命令：
`python tools/tts_aihubmix.py vo audio/vo_en audio/vo_en.json`（在 `film/` 下；只补缺的 wav）。
TTS 每次结果不同，重配后时长会变，要重新对时间线里的 `vo` 偏移和 `subs` 时间。所以优先用备份里的 wav。

**配乐**：incompetech.com（Kevin MacLeod，CC BY 4.0），用到 Montauk Point、The Escalation、Calmant，
放 `film/assets/music/`；`work/get_music.ps1` 会从 incompetech 下载当时试听的 12 首（改一下脚本里的目标路径）。

**字体**：Barlow Condensed、Inter（Google Fonts），放 `film/assets/fonts/`。

## 3. 目录和管线

```
nba-tactics/tools/        render_play.py（EDL 驱动的跟踪 AR）、track / camera / idsheet / traj / seg（跟踪链）、fetch_clip、nba_sql、asr_long …
nba-tactics/spurs_g4/     各镜头 EDL（*_edl.json）、球员配置（e*_players.json）、文稿、data/
  work/                   跟踪工作目录（每个回合一个）+ 本片的 QA / 渲染脚本
  film/                   成片工程：timeline_*.json、subs_en.json、scenes/（代码动画）、shots/（fxclip 规格）、tools/
    out/                  各镜头成品和成片；s04r/_tools/montage_fz.py 也在这里
```

**每类镜头怎么出**（`work/`、`out/` 被 gitignore 了，但里面的 .py/.ps1 脚本已强制加入 git）：

1. **代码动画 c1–c8：** 数据由 `film/work/cN_data.py`（或 `_compute.py`）写进 `scenes/cN_*.json`。
   渲染命令是 `node render.mjs scenes/c7_lastplay.html out/c7/c7.mp4`（在 `film/` 下执行）。
2. **fxclip 镜头（不跟踪的特效）：** 在 `film/` 下执行 `python tools/fxclip.py shots/s06.json`。
   `shots/bk_*.json` 是复杂版的保底版本，输出到 `out/bk/`。
3. **跟踪 AR 镜头：** 在 `spurs_g4/` 下执行 `python ..\tools\render_play.py e676w_s08_edl.json`。
   - **同一个 work 目录不能并行：** render_play 会改写 `<work>/mix.wav`，同目录的 EDL 必须串行渲染。e676w 是先 s08 再 s06，e727w 是先 s16 再 s01。
   - **一键重渲：** `work/rerender_ar.ps1` 会按正确顺序重渲全部 AR 镜头，再拼 s04r、s09r。脚本里的绝对路径要先改成新机器的。
   - **两个拼接镜头：** s04r 用 `film/out/s04r/_tools/montage_fz.py s04r_montage.json` 拼，s09r 用 `work/s09r/assemble.py film/out/s09r/s09r.mp4` 拼。
   - **高质量定格蒙版：** 缓存在 `<work>/masks_hq/NNNN_KEY.npz`。删掉 npz 就会重算；EDL 里的 `mask_box` 可以指定 SAM2 用的框。
4. **新回合从零跟踪：** 依次执行 `track.py`、`camera.py`、`idsheet.py`（人工认人，写进 `eNNN_players.json`）、`traj.py`、`seg.py`，然后写 EDL 渲染。
   各脚本的用法写在文件开头的 docstring 里。
5. **sampleA：** 先 `render_play.py e715_en_h_edl.json`，再在 `film/` 下 `python tools/sample_a.py`。
6. **成片：** 在 `film/` 下执行
   `python tools/assemble.py timeline_simple.json` 或 `timeline_complex.json`，输出到 `out/final_*`。

**QA 脚本（`work/`）：**

| 脚本 | 用途 |
|---|---|
| `sub_cover.py film.ass asr.json` | 找没被字幕覆盖的说话段 |
| `vo_words.py` | 旁白逐词时间和停顿 |
| `head_crops.py` / `frames_grid.py` | 抽帧检查名牌有没有挡住头 |
| `lufs_all.py` | 响度 |

## 4. 时间线要点（`film/timeline_complex.json`）

各镜头起点（秒）：

| 镜头 | 起点 | 镜头 | 起点 | 镜头 | 起点 |
|---|---|---|---|---|---|
| s01 | 0 | c3 | 29.07 | fox | 82.57 |
| c1 | 5.37 | s06 | 34.47 | c6 | 85.73 |
| c2 | 10.97 | c4 | 41.63 | c7 | 91.53 |
| s04 | 17.87 | s08 | 46.03 | s16 | 96.13 |
| s05a | 27.27 | s09 | 55.17 | s17 | 104.2 |
| | | sampleA | 64.37 | c8 | 111.8 |

总长 117.8 s。

- **字幕：** `vo` 条目的字幕自动取自 `subs_en.json`；`vo_split`（旁白烤进 AR 片子的）**不会自动出字幕**，要在条目里手写 `subs`。现场解说的字幕也要手写。
- **音量：** AR 片子的原声是峰值归一化的，比 fxclip 响得多，所以要用 `audio_db` 压下来（s06 −11、s08 −10、s16 −8.5、s09 −21）。
- **配乐：** 顶层 `music` 段落控制配乐，简化版和复杂版共用同一套编排（Montauk Point，接 The Escalation，在 fox 到 c6 之间压到 −40，片尾 Calmant）。
- **保底：** `fallback` 字段指向保底镜头，主镜头缺失时自动用保底。

## 5. 没做完 / 可以改进的

- s09 旁白说 "2.5 feet"，画面标签是 "HAND 1.7 FT"（单回合值）。可以加一个 "Q4 AVG 2.5 FT" 的小标签，或者改旁白。
- c7 里瓦塞尔、哈珀没打点（他们在禁区里，离阿努诺比 20 多英尺）。可以考虑加空心标记。
- s08 布伦森脚下没有地面圈；阿尔瓦拉多的圈和观众有重叠。
- GitHub 推送：本机没有 GitHub 凭据，需要在自己的终端运行 `git push origin main`。

## 6. 规矩

- 密钥只放 `.env`，绝不打印、不提交，也不要备份到服务器。远程只用 ssh 和 git，不用 scp。
- 只删自己生成的中间文件；用户文件要先列清单征得同意。
