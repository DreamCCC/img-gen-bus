# AI 翻唱 + MV 流程

完整实现在 `creator-channel/music_remix/baby_citypop/`：Bieber《Baby》改成日语 City Pop，虚拟歌手 MINA 演唱，配 80–90 年代泡沫经济 MV。分镜和实际制作记录见该目录下的 `MV导演脚本_v1.md`。这里只写可复用的步骤和坑。

## 目录

1. 翻唱：Suno
2. 分析：分轨、拍点、歌词时间轴
3. 虚拟歌手：定妆照和镜头首帧
4. 演唱镜头：万相对口型
5. 影视素材
6. 年代质感：统一调色和字幕
7. 剪辑和渲染
8. 交付和清理

---

## 1. 翻唱：Suno

1. 上传素材：先试原曲；被版权检测拒收时，用 `melody_guide.py` 生成"合成音色主旋律 + 和声引导轨"再传。`guide.py` 生成只有和声的引导轨，用来定调和对齐速度。
2. 模式选 **Cover**（不是 Extend）。
3. 风格描述：写年代、乐器、制作手法、嗓音特征；歌手名会被过滤，不要写。上传后风格框里会自动填一段描述，要替换掉。
4. 参数：Audio Influence 80%，Style Influence 75%，Weirdness 35%。
5. 想加原创桥段：歌词里写 `[Bridge]`，引导音轨里那一段不给旋律，让 Suno 自己写，之后再接回原曲副歌。
6. 喜欢的版本存成 Persona，后续版本复用音色。自定义 Voice 只能用本人验证过的声音，不能复刻真人歌手。
7. 网页播放器经常坏（Service Worker 报 `Failed to fetch`），直接下载 wav。下载次数有限，先确定要哪一版再下。

## 2. 分析：分轨、拍点、歌词时间轴

| 步骤 | 脚本 | 要点 |
| --- | --- | --- |
| 分轨 | demucs htdemucs_ft | 人声轨同时用于：对口型驱动音频、逐字卡拉 OK、找独奏段（乐器旋律会漏进人声轨） |
| 拍点、段落 | `analyze.py` | Suno 输出速度会漂（标称 149 BPM），所有剪辑点吸附到实测拍点 |
| 逐句识别 | `lyric_times.py` | 人声切句后逐句识别（需要 dashscope，用 ep01 的 venv） |
| 时间轴 | `timeline.py` | paraformer 词时间戳做锚点，其余按 2 小节一句插值，再吸附拍点，输出 `suno/pop_1_timeline.json` |

## 3. 虚拟歌手：定妆照和镜头首帧

- 先出几版画风给用户选，选定后出三视图和不同场景造型。
- 后续所有首帧都用 qwen-image-3.0-pro 的**图像编辑**，以定妆照或上一张场景图做参考（`mina/edit.py`），不要每张都文生图，否则脸和画风会漂。
- 虚拟角色可以 AI 生成；不能做成可辨认的真人。

## 4. 演唱镜头：万相对口型

- 模型 `wan2.7-i2v`：首帧图 + 驱动音频（`driving_audio`）。音频先用 `OssUtils.upload` 传到临时 OSS，请求头加 `X-DashScope-OssResourceResolve: enable`。见 `creator-channel/tools/wan_video.py` 和 `wan/batch.py`。
- 非演唱镜头用 `wan3.0-video`（不支持音频驱动）。
- **多机位**：每段副歌拍两条完整的同步演唱（近景和全景），每条 15 秒，驱动音频从人声轨按歌曲时间切出。剪辑时在两条之间切换，歌曲时间始终对齐，怎么切口型都不会错位。
- **每条生成后必须跑重复帧检查**：

```bash
python img-gen-bus-skills/scripts/video_qa.py wan/F2.mp4 --max-mbps 0
python img-gen-bus-skills/scripts/smooth_dups.py wan/F2.mp4 wan/smooth/F2.mp4
```

  `edl.py` 在 `wan/smooth/<名字>.mp4` 存在时优先用它。
- 独奏、间奏也要有镜头。萨克斯独奏的位置从人声轨能量找（164.7–171.0 秒），然后生成演奏镜头（`wan/shots3.json`）。

## 5. 影视素材

1. `footage/sources.json` 列候选；`footage/fetch.py` 用 yt-dlp 下载，同时把标题、频道、链接存进 `raw/<名字>.json`，片尾出处表从这里生成。
2. `footage/scan.py` 做镜头检测和接触表；人工看接触表挑入点。
3. `footage/make_picks.py` 按标签写 `picks.json`（素材、入点、裁切比例、出处标签）。入点比镜头起点略往后，避开转场。
4. 黑边、台标、文字横幅：用 `cropdetect` 加接触表确定裁切比例。字幕和水印多的源直接弃用。
5. 九宫格小格：片段设 `loop`（防止播到预告片的字幕卡）；模糊或太暗的片段排除；没轮到的格子放电视雪花和频道号，不能留空。

## 6. 年代质感：统一调色和字幕

- `look/grade.py`：所有画面（万相、代码、影视）最后都过同一个 `grade()`，全片才统一。有两套风格：`tv89`（录像带：奶油黑位、色度渗色、扫描线、磁带噪点）和 `film89`（35mm 富士胶片：暖高光、光晕、颗粒、暗角）。
- 已经用 OpenCV 实现，每帧约 0.26 秒。改实现时要做像素级 A/B 对比。
- 字幕 `look/subs.py`、`look/subtrack.py`：日中双语，有歌番組テロップ和レーザーカラオケ两种样式，放在 4:3 安全区内。逐字变色用人声起音强度推进，不用识别器的平均时间戳。
- 片名卡不要压在第一句歌词上。

## 7. 剪辑和渲染

```bash
python mv/edl.py                                 # 导演脚本 → mv/edl.json，剪辑点吸附拍点
python mv/render.py --jobs 8                     # 整片
python mv/render.py --from 160 --to 185 --out patch.mp4   # 只渲一段，再按帧号拼回去
```

- 渲染顺序：取画面 → 代码叠层 → `grade()` → 字幕 → x264 → 拼接 → 混入原曲。
- 每个进程设 `cv2.setNumThreads(1)`。
- 编码 `-crf 18 -maxrate 40M -bufsize 80M`，不加码率上限时颗粒会把峰值推到 100 Mbps 以上，播放卡顿。
- 局部修改用局部重渲加拼接（见 [find-and-fix.md](find-and-fix.md) 最后一节）。

## 8. 交付和清理

- 全片跑 `video_qa.py`；用户指出过的时间点逐帧看。
- 片尾列出处（作品名、年份），写明演唱和编曲是 AI 生成。
- 清理：万相原片（保留 smooth 版和最终用到的）、分段渲染、临时拼接、预览文件都删；原始影视素材和用户下载的歌曲先问用户。
