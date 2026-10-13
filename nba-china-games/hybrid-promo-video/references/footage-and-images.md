# 素材检索、挑镜头、片段预处理、AI 生图

## 目录
1. 来源规则
2. 各渠道的搜索与下载
3. 挑镜头
4. 裁切：官方竖版模板与烧录字幕
5. 片段规格与 prep_clip.py
6. AI 生图

## 1. 来源规则

- 画面只用委托方或其球队、品牌的官方账号发布的素材。账号认证信息要核实，`tikhub.py` 会在官方号前标 ★。
- 第三方媒体（Getty、路透、新华社、央视、球迷上传的录像）只能用来核对比赛细节，不能进成片。
- 找不到某个画面时，如实告诉用户：列出已经翻过的渠道，给出替代方案让用户选。不要用相似画面冒充，也不要用 AI 生成真人。本项目里"2004 年麦迪传球、姚明扣篮"这一球，所有官方渠道都没有，最后由用户选择用另一个姚明补扣的官方画面替代。
- 每下载一条，就把文件名、账号、视频 ID 记进 `assets/CREDITS.md`。没用上的素材在收尾时可以删，删之前也要把来源记下来。

## 2. 各渠道的搜索与下载

优先级：官方抖音 → 官方 YouTube → 官方 B 站。

| 渠道 | 搜索 | 下载 | 备注 |
| --- | --- | --- | --- |
| 抖音 | `tikhub.py users "NBA"`、`tikhub.py videos "关键词" 2`、`tikhub.py posts <sec_uid> 5` | `tikhub.py get <aweme_id> out.mp4` | 走 TikHub API。大文件慢时用 curl 断点续传 |
| YouTube | `yt_search.py "关键词"`（经 TikHub）；或 `yt-dlp --flat-playlist --print "%(id)s \| %(title)s" "https://www.youtube.com/@NBA/search?query=…"` | `yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]" --merge-output-format mp4 -o out.mp4 URL` | 中国大陆需要代理。TikHub 返回的 googlevideo 直链绑定了它服务器的 IP，本机用不了，下载只用 yt-dlp。遇到 403 加 `--extractor-args "youtube:player_client=web_safari,android"` |
| B 站 | `bili.py search "关键词"`、`bili.py up <mid> "关键词"` | `bili.py get BV号 out.mp4` | 未登录最高 480p。akamai 镜像对单连接限速，脚本已改成 16 段 Range 并行下载 |

- 球队官方号也算官方来源，例如 B 站「休斯顿火箭」(1683463886)、「迈阿密热火」(1681299250)。
- 下载慢时先测速再决定在哪里下。本项目实测：本机开代理下 B 站 6.6 MB/s，国内服务器只有 1.3 MB/s。
- 下载命令需要不受限的网络。在有沙箱的 agent 里，要申请网络权限或在沙箱外执行。

## 3. 挑镜头

```bash
.venv/bin/python tools/sheet.py assets/footage/x.mp4 out/sheets/x.jpg 2 8          # 每 2 秒一格、8 列，带时间码
ffmpeg -ss 55.9 -i assets/footage/x.mp4 -frames:v 1 out/check/x_55.9.jpg              # 抽单帧确认
```

1. 用接触表粗选时间段。时间标签按"行号 × 列数 × 步长"自己换算一遍，再抽单帧确认。
2. 对选中的片段，抽首、中、尾三帧，确认里面没有转场、甩镜头或切到别的画面。
3. 测烧录字幕和台标的位置（见下一节），再写裁切参数。
4. 写进 `clips_h.json`。

## 4. 裁切：官方竖版模板与烧录字幕

NBA 官方抖音的竖版视频，上下是渐变边框，中间嵌一个画面窗口：

| 素材分辨率 | 画面窗口的 y 范围 |
| --- | --- |
| 1080×1920 | ≈ 290–1630 |
| 1440×2560 | ≈ 387–2173 |
| 720×1280 | ≈ 194–1087 |

烧录字幕通常在画面窗口的下部。先测出白字所在的行：

```python
g = cv2.cvtColor(cv2.imread(frame), cv2.COLOR_BGR2GRAY)
w = (g > 240).sum(1); ys = [y for y in range(top, bottom) if w[y] > 40]   # 白字所在的行
```

然后把裁切框放在 `ys` 的上方。裁切框的宽高比要和输出尺寸一致，例如 834×1080 是 0.772，640×700 是 0.914。

横版素材里烧录的说明文字如果被裁掉一半，要么整段保留，要么完全裁掉。只露半截比不裁更糟。

## 5. 片段规格与 prep_clip.py

`clips_h.json` 里每一项描述一个片段：

```json
{"name": "f2016", "src": "assets/footage/cg2016_harden.mp4", "t0": 55.95, "t1": 56.9,
 "crop": [0, 493, 1440, 1575], "size": [640, 700], "dur": 2.4,
 "rife": 4, "map": [[0, 0], [2.4, 0.95]],
 "grade": {"contrast": 1.22, "sat": 1.05, "bloom": 0.3, "mono": 0}, "sharpen": 0.5}
```

- 输出到 `scenes/clips/<name>/00000.jpg …`，帧数等于 `dur × 30`，同时更新 `scenes/clips/manifest.json`。
- `map` 是分段线性的时间映射，格式为 `[[成片相对秒, 素材相对秒], …]`，可以做变速、慢放、定格。比 0.5 倍速还慢时，加 `"rife": 4` 补帧。
- 运行：

```bash
.venv/bin/python -u tools/prep_clip.py clips_h.json 名字1 名字2 | grep --line-buffered ^clip
```

- 只能串行运行，并发会把 manifest 写乱。
- RIFE 补帧调用的是 `venhance`（Apple Silicon，MPS 推理），必须在沙箱外运行。它只接受恒定帧率的输入，prep_clip 会先转成恒定帧率再交给它。非 Mac 平台要换一个 RIFE 实现，并改 prep_clip.py 里调用 venhance 的那一行。
- 素材里有甩镜头时，缩短入出点，再用 rife 慢放补足时长。

## 6. AI 生图

```bash
.venv/bin/python tools/genimg.py assets/gen/prompts.json assets/gen            # 百炼 qwen-image，已存在的跳过
```

- 只生成环境画面。提示词里写明"空无一人"或"远景背影、看不清脸"，并指定年代和胶片质感，例如"1979 年北京街景，彩色胶片，颗粒感，空无一人"。
- 不生成真实球员、明星或任何可辨认的人脸。
- 生成完逐张看一遍：有没有冒出人脸、文字乱码、时代不符的物件（例如 1979 年的街景里出现现代汽车）。
- 提示词存进 `assets/gen/prompts.json`，在 CREDITS 里注明是 AI 生成。
