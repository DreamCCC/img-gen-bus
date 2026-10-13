# Canvas 画面、竖版重新构图、渲染与自检

## 目录
1. film.html 页面约定
2. 页面内部结构
3. 竖版重新构图
4. render.mjs 与并行渲染
5. 自检循环

## 1. film.html 页面约定

render.mjs 用 puppeteer 打开页面，逐帧调用 `renderFrame(t)`，把画布截图送进 ffmpeg 编码。页面必须提供：

- `<canvas id="c">`：输出画布，尺寸就是成片尺寸（横版 1920×1080，竖版 1080×1920）。
- `window.FPS`、`window.DURATION`。
- `window.ready`：一个 Promise，负责加载时间轴 JSON、`scenes/clips/manifest.json`、字体和 AI 图。
- `async window.renderFrame(t)`：给定时间，确定性地画出一帧。同一个 t 永远画出同一张图，这样才能分段并行渲染、局部重渲。

参考实现：`templates/film.html`（约 1300 行，包含全部场景和竖版逻辑）。

## 2. 页面内部结构

- **工具函数**：`prog(t,a,b)`、`fade`、`ease*`、`hash(f,k)`（伪随机数一律用 hash，不用 `Math.random`）、`text`、`strokeText`、`cover`、`panel`、`blurBack`、`flash`、`decay(t,t0,tau)`（打击后的衰减包络）。
- **真人帧**：`clip(name, localT)` 取第 `floor(localT × 30)` 帧，同时预加载下一帧，LRU 缓存 240 帧。
- **场景分发**：`SCENES = {name: sc_name}`。`renderH(t)` 先找出 t 落在哪个场景，调用 `sc_name(t, f)`，再统一叠加 bloom、字幕、颗粒和暗角。
- **场景函数只读时间轴里的时间**（`S`、`EV`、`A`），不要在场景里写死秒数。音效读的是同一份数据，所以画面和声音天然对齐。
- **字幕**：
  - 横版在页面里绘制：44 px，y = 960，底板半透明。
  - 竖版单独绘制：58 px，每行不超过 14 个字，按逗号句号断行。
  - 显示区间是 `[t, t + dur + 0.25]`。已经用大字排版呈现的句子（例如引语）放进 `NOSUB`，不再出字幕。
- **质感层**：颗粒是 4 张 512 px 预生成噪声图轮换使用，再加暗角和 bloom（半分辨率模糊后用 lighter 模式叠加，单个场景可以关掉）。
- **常用组件**（本项目做过的）：开场光点、年份倒退计数、地图连线、身高标尺、报纸版面、传达室时钟、电视墙、票根、计分牌式年份翻页、灯一盏盏熄灭、天数计数器、对阵卡、阵容快切、片尾标版。
- **压在真人画面上的名字条**：底部加一层渐变（透明到 0.7 黑），不然白字压在白球衣上看不清。

## 3. 竖版重新构图

竖版不重做场景，而是复用横版的画面重新构图：

1. 带 `?v=1` 打开页面时，`cv` 是一张离屏的 1920×1080 画布。`renderV` 先调用 `renderH(shot.h0 + 镜头内时间)` 画到离屏画布上，再按 `layout` 合成到 1080×1920 的输出画布：
   - `zoom`：缩放后放在 (540, 900) 居中，上下边缘渐隐。zoom 取 1.295、配合 cx/cy，可以对准横版里的画中画面板。
   - `regions`：从横版画面里裁出几个矩形，分别放到竖版的不同位置。常用于"上面放真人、下面放计分牌"。
   - `native`：竖版原生画面，例如钩子大字、"6 年"、对阵卡、片尾。
2. 背景是横版画面缩小、模糊、压暗后铺满整屏。
3. 在竖版画布上画文字时，要用 `onV(() => text(...))` 包一层，否则文字会画到离屏画布上。本项目踩过这个坑：字幕底板出来了，文字却不见了。

## 4. render.mjs 与并行渲染

```bash
node render.mjs scenes/film.html out/st --stills 12.5,30,47.2                 # 导出 PNG 静帧
QUERY=v=1 node render.mjs scenes/film.html out/stv --stills 3,20              # 竖版静帧
./render_par.sh h 4 out/film_h_master.mp4 out/film_h_mix.wav                  # 4 进程并行渲染并拼接
./rerender_part.sh h 2 4 out/film_h_master.mp4 out/film_h_mix.wav             # 只重渲第 2 段（共 4 段）
```

- 环境变量：`JPEG=1` 用 JPEG 管道（更快），`FRAMES=a:b` 只渲染一个帧区间，`QUERY=v=1` 切到竖版，`CHROME_PATH` 指定 Chrome 路径。
- render.mjs 会在本地起一个静态文件服务器，所以页面里的资源用相对项目根目录的路径。
- 需要本机有 Google Chrome。有沙箱的 agent 必须在沙箱外运行 Chrome。
- 速度参考：M 系列 Mac，4 个 Chrome 进程并行，1080p 每个进程约 3 帧每秒。3 分钟横版约 9 分钟，60 秒竖版约 3.5 分钟。
- 母版用 crf 16。每帧都有随机颗粒，母版码率会到 80 Mbps 以上，这是正常的。交付另外压制，见 sound-and-delivery.md。
- `rerender_part.sh` 需要 `out/parts/` 里其余各段还在。清理过中间文件后，直接重跑 `render_par.sh`。

## 5. 自检循环

每改一处画面，就渲染静帧亲眼看，不要只看代码：

```bash
node render.mjs scenes/film.html out/st --stills 12.5,30,47.2
.venv/bin/python tools/montage.py out/st.jpg 3 480 out/st/*.png              # 拼成一张，单格宽度不要超过 480
```

- 每个场景至少看 2 帧：场景开头附近一帧、高潮一帧。
- 成片渲染完，用接触表把全片扫一遍：`tools/sheet.py out/film.mp4 out/sheet.jpg 2.5 8`。
- 关键帧单独抽出来核对：重音、硬停、爆点这几帧，画面要正好落在事件时间上。
- 换完旁白，抽最短的几句和安静句的帧，确认字幕正常出现。
