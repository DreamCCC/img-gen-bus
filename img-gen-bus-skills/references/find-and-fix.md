# 识别错误的手段

原则：先把"感觉不对"变成一个数字或一张图，再动手改。改完用同一个数字复查。

## 目录

- 画面：接触表、逐帧差分、重复帧和卡顿、黑边和水印、码率
- 声音：响度、分轨能量、拍点、识别核对
- 时间轴：帧数、对齐、字幕
- 代码重构：像素级 A/B 对比、性能剖析
- 修正手法：只重渲受影响的区段再拼接

---

## 画面

### 接触表（第一道检查）

| 场景 | 命令 |
| --- | --- |
| 任意视频，按固定间隔抽帧 | `python creator-channel/ep01_4.8pct/tools/sheet.py in.mp4 out.jpg 2 8 [起点] [终点]` |
| 原始素材按镜头切换抽帧（挑素材） | `python creator-channel/music_remix/baby_citypop/footage/scan.py [名字]`，结果在 `sheets/` 下 |
| HTML/Canvas 场景的静帧 | `creator-channel/ep02_threebody/tools/qa.sh <名字> 12.5,30,47` |
| 只看用户指出的那几秒 | `ffmpeg -ss 165 -t 6 -i in.mp4 -vf fps=5,scale=480:-1,tile=6x5 -frames:v 1 sheet.jpg` |

每格都要标时间码。用户说"某段有问题"时，先按 0.2 秒一帧抽那段，而不是全片抽 3 秒一帧。

接触表能看出：空画面、模糊、文字卡、水印、黑边、白底上的白字、色调不一致、人物"呆"。看不出：卡顿、闪烁、音画不同步。这几项要用下面的量化手段。

### 逐帧差分：卡顿、重复帧、冻结

```bash
python img-gen-bus-skills/scripts/video_qa.py in.mp4 [--from 秒 --to 秒] [--region x,y,w,h]
```

- 原理：先缩到 320×180 灰度，算相邻帧的平均绝对差。如果一帧的差值小于 `max(0.25, 0.3 × 前后各 7 帧的中位数)`，就算重复帧。
- `--region` 用来只看画面的一部分。九宫格、画中画里只有一格在卡时，看全画面会被其他格的运动掩盖。
- **万相（wan2.7-i2v）对口型视频标称 30 fps，但部分片段每 5 帧有 2 帧重复，实际只有约 18 fps**，看起来就是卡。ffmpeg 自带的 mpdecimate 检测不出这种"近似重复"，要用上面的判定。
- 修复：`smooth_dups.py` 用 select 删掉重复帧，再用 `minterpolate=mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1` 按原时间戳插帧，口型不会错位。

### 黑边、水印、字幕条

```bash
ffmpeg -ss 30 -t 10 -i src.mp4 -vf cropdetect=24:2:0 -f null - 2>&1 | grep -o 'crop=[0-9:]*' | sort | uniq -c | sort -rn | head -3
```

- 4:3 素材放进 16:9 会有左右黑边；有的素材两侧是文字横幅或台标，cropdetect 测不出，需要看接触表手工定裁切框。
- 裁切框写成相对比例 `[x, y, w, h]`，在 picks 或 EDL 里统一处理。
- 水印和文字多的素材直接弃用，比裁切更省事。

### 码率

`video_qa.py` 按每秒统计视频包的大小。胶片颗粒和噪点会把 x264 的码率推到 100 Mbps 以上，播放器解码跟不上就会卡（文件本身没坏）。交付编码用 `-crf 18 -maxrate 40M -bufsize 80M`。

### 素材参数

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames -of csv=p=0 a.mp4
```

ffprobe 一次只能带一个输入文件，多个文件要循环调用。

---

## 声音

### 响度和峰值

```bash
ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1:print_format=summary -f null -
ffmpeg -i mix.wav -af astats=metadata=1:reset=0 -f null - 2>&1 | grep -E 'Peak level|RMS level'
```

B 站和 YouTube 的目标响度约为 -14 LUFS，真峰值不超过 -1 dBTP。限幅器要过采样，否则真峰值会超标。

### 用分轨找段落

要找独奏、间奏或人声起止时，用 demucs 分轨后每 0.5 秒算一次 RMS。例子：萨克斯旋律会漏进人声轨，人声轨的能量曲线一画，独奏就是 164.7–171.0 秒，比按小节去猜准得多。

### 拍点和时间轴

- 拍点用 librosa beat_track 提取；Suno 生成的歌速度会漂移（标称 149 BPM），**不要用固定 BPM 去推算时间**，一律吸附到实测拍点上。
- paraformer 给出的字级时间戳是把一句话的时长平均分给每个字，做逐字卡拉 OK 不准。逐字擦除要用人声轨的起音点（onset），句级时间可以用识别结果做锚点。

### 识别核对（TTS、翻唱）

- TTS 的每条台词合成后用识别（ASR）转回文字，和**实际念出的文本**（`say` 字段）比，而不是和字幕比。字幕里写"4.8%"，念出来是"百分之四点八"。见 `ep01_4.8pct/tools/vo_takes.py`。
- 每条台词合成多个版本，按字错率、语速、能否放进时间槽自动选；最终好不好听要请用户试听。

---

## 时间轴

- 帧数应该等于时长 × 帧率（`video_qa.py` 第一行会报）。用 `-frames:v` 截帧会让慢动作段被截短。
- 用户给的是"分:秒"，换算成秒再查 EDL，看那段是哪几个镜头、哪几个素材，再逐个量化。
- 字幕：标题卡和第一句歌词或旁白不要重叠；白字放在亮背景上要加描边或底板。

---

## 代码重构

- **像素级 A/B 对比**：换实现（例如把 scipy 换成 OpenCV）之前，固定随机种子或关掉噪点，新旧两版各渲几帧，算最大和平均差值，确认在 1/255 级别再替换。
- **性能剖析**：`python -m cProfile -s cumtime render.py --from 10 --to 11` 找到真正慢的函数。例子：调色函数里的高斯模糊占了 80% 的时间，换成 `cv2.GaussianBlur` 后单帧从 1.08 秒降到 0.26 秒。
- 多进程渲染时，每个进程里设 `cv2.setNumThreads(1)`，否则线程互相抢占反而更慢。

---

## 修正手法：局部重渲 + 拼接

整片重渲很慢，且会把其他已经确认的段落一并改动。

1. 渲染器支持 `--from/--to`，只渲受影响的区段，区段两端各多留一点。
2. 按帧号拼接（不要按秒，以免浮点误差差一帧）：

```bash
ffmpeg -i full.mp4 -i patch.mp4 -filter_complex \
 "[0:v]trim=end_frame=4950,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];\
  [0:v]trim=start_frame=5130,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[v]" \
 -map "[v]" -map 0:a -c:v libx264 -crf 18 -maxrate 40M -bufsize 80M -c:a copy out.mp4
```

3. 拼完对接缝前后各 1 秒跑 `video_qa.py`，再抽帧看一眼。
4. 参考 `ep01_4.8pct/rerender_part.sh`。
