# 《HOW DO YOU BLOW 29?》横屏 2 分钟英文版 · 文稿 v2

1920×1080，英文旁白（Gemini 3.8 Flash TTS · Charon，长句提速 10%，见下方"配音"）+ 英文字幕。
v1 → v2 的改动：画面以**真实比赛画面上的追踪加工和特效**为主，纯代码动画只留冷开场的分差曲线和片尾一张卡；
数据上屏参考 NBA Inside the Game（AWS）/ Prime Insights 的做法：数字钉在球员身上、跟着人走，不做满屏图表。
YouTube 素材全部去掉：采访用腾讯 NBA 库的片段，布朗的话做成场边画面上的引语字幕。

## 画面语言（全片统一，先做样片定风格）

| 名称 | 做法 | 用在 |
|---|---|---|
| 扫描启动 | 定格帧上一道扫描线扫过，球员身上依次弹出骨架关键点和跟踪框，再收成名牌 | 冷开场、每段拆解的第一帧 |
| AR 名牌 | 名牌钉在球员头顶、跟着跟踪框走；只亮旁白点到的人 | 全片 |
| xFG 标签 | 出手瞬间投篮人头顶弹出圆环仪表 + 百分比，命中变绿、不中变红 | 借来的领先、e676、e714、e725 |
| 引力绳 | 两个球员之间一条发光的"绳子"，被拉长时数字跟着变（距离 / 离篮筐距离） | e676 唐斯拉走文班 |
| 防守距离圈 | 出手人脚下一圈地板光环，半径 = 最近防守人手离球距离，数字贴在圈上 | 第四节马刺出手串烧 |
| 时停 + 去色 | 画面变灰，只留点名的人是彩色；带 1.05–1.16 倍缓推 | 每段拆解 |
| 残影追防 | 慢放里追防的人身后拖 4–6 个半透明残影 | e715 阿努诺比追福克斯 |
| 子弹时间 + 冲击波 | 钉板 / 补篮那一帧环形冲击波、闪白、轻微震屏 | e715、e727 |
| 地板线 | 跑位、换防、扑防线画在地板上，被球员身体遮挡（人形蒙版） | e676、e725 |

## 数据口径

沿用 v1 的数据表（`文稿_横屏2min_en_v1.md`），不重复。新增：

| 上屏 | 值 | 出处 |
|---|---|---|
| 福克斯原话 | "以为能跑过 OG"（英文原句以片段原声为准） | 腾讯 2606111356236401（4.9 s，竖版） |
| 卡斯尔原话 | "我不认为我们任何人看到了他"（英文原句以片段原声为准） | 腾讯 2606111429332601 |
| 布朗原话（字幕，不放原声） | "He's got to be a monster on the offensive glass tonight." | `research/quotes_verified.md` q4_4（逐字核对过） |

## 文稿

### 0:00–0:10 冷开场
- 【实况】e727 补篮，MSG 现场声 2 秒 → 球落网那一帧定格去色。
- 【扫描启动】十个人身上依次弹出骨架点，收成名牌；阿努诺比的名牌放大：**OG ANUNOBY · TIP-IN · 2.1 s**。
- 【代码动画 · 角落】左下角小分差曲线 +29 → −1 一笔画完，标题砸入 **HOW DO YOU BLOW 29?**
- VO: Up twenty-nine in the NBA Finals. And the Spurs lost — by one. Let's run the tracking data.

### 0:10–0:28 借来的领先
- 【实况串烧】上半场 4 个马刺三分（瓦塞尔、卡斯尔、文班、哈珀），每球出手瞬间 xFG 标签弹出（多数 30%–40%），命中变绿；右上角计数器 **EXPECTED / ACTUAL** 跟着每球跳。
- VO: First half, the Spurs couldn't miss. The tracking model expected forty-nine points from those shots. They scored seventy.
- 【实况串烧】第三节马刺三分连续打铁 4 球，标签全红，计数器换成 **9 STRAIGHT MISSES**；下半场计数器停在 **EXPECTED 39 / ACTUAL 19**。
- VO: Then the shots stopped falling. Nineteen points on shots worth thirty-nine. The lead was borrowed — and the second half came to collect.

### 0:28–1:00 布朗的那一步
- 【实况 + AR 名牌】第四节尼克斯落位，五个名牌依次点亮 ALVARADO · BRUNSON · HART · TOWNS · ANUNOBY，画面角标 **NO TRUE CENTER · +13 IN 7 MIN**。
- VO: Mike Brown went small. No Mitchell Robinson. Karl-Anthony Towns at center, two guards, everybody spaced. That group won the last seven minutes by thirteen.
- 【拆 · e676】时停去色，只留唐斯、文班、布伦森彩色；**引力绳**从唐斯连到文班，唐斯上提掩护，绳子拉长，文班被拖出油漆区，绳上数字 **RIM → 27 FT**；换防瞬间地板上亮 **SWITCH**；恢复播放，布伦森出手，xFG 环 **33%**，进 → 104–103。
- VO: Here's the trick. Towns can shoot, so Wembanyama has to follow him out. One screen, one switch — and the best rim protector in the league is guarding Brunson twenty-seven feet from the basket. Bang.
- 【实况串烧】马刺第四节 4 次出手，每次脚下防守距离圈收紧，数字 **2.1 FT · 1.7 FT · 1.2 FT …**；角标 **Q4: 4 / 19**。
- VO: At the other end, the hands were right there. Four of nineteen in the fourth.

### 1:00–1:38 最后 13 秒
- 【拆 · e715】福克斯拿住球那一帧时停去色；画面上方左右两个大时钟 **GAME 0:13.0 / SHOT 24**，24 压过 13；地板上福克斯脚下亮字 **HOLD IT**。
- VO: Spurs up one. Thirteen seconds left. The shot clock is longer than the game. Just hold the ball.
- 【慢放 ×0.25 + 残影追防】福克斯路线（银白）往篮下冲，阿努诺比身后拖残影追上，两人间距数字往下掉；福克斯头顶 xFG 环 **49.6%**。
- VO: Instead, Fox goes. Less than a second from gather to takeoff — a coin-flip layup nobody needed.
- 【子弹时间 + 冲击波】钉板那一帧。
- VO: Pinned.
- 【采访 · 2 s】福克斯原声 + 字幕（"以为能跑过 OG"那句）。

### 1:38–2:00 最后一攻
- 【实况 + AR 名牌】5.7 秒暂停后落位，尼克斯五个名牌全亮 **FIVE SHOOTERS**。
- 【拆 · e725/e727】布伦森出手瞬间时停：地板线两条蓝线（文班、福克斯）同时扑向布伦森；阿努诺比脚下亮红圈 **UNBOXED**，一条橙色长箭头从 28 英尺外冲进来；最近的马刺在 12 英尺外（虚线圈 **12 FT**）。
- VO: Last possession. Fox and Wemby both jump Brunson — and nobody touches Anunoby, crashing in from twenty-eight feet.
- 【场边画面 + 引语字幕】布朗："He's got to be a monster on the offensive glass tonight."
- 【实况 + 冲击波】补篮进网，闪白，107–106。
- VO: Tip. In.
- 【采访 · 2 s】卡斯尔原声 + 字幕（"我们没人看到他"那句）。
- 【收尾卡 · 代码动画】分差曲线完整版，尼克斯领先的那一小段高亮：**KNICKS LED FOR 53.8 SECONDS**。
- VO: The Knicks led this game for fifty-three point eight seconds. It was enough.

## 配音

- Gemini 3.8 Flash TTS，音色 Charon，经 AIHubMix（`film/tools/tts_aihubmix.py`）。
- 长句用 v2b 指令（快、情绪饱满），合成后 rubberband 提速 10%（保留音高和共振峰）；"Pinned." "Tip. In." 这类爆点短句用 v1 指令、不提速。
- 每句合成后 Whisper 核对；数字念法以字幕为准（"twenty-seven"）。

## 本机 vs 服务器分工

全部在本机（RTX 5080）：跟踪、SAM2 蒙版、补帧慢放、渲染、混音。服务器只用来查库和取片段签名地址。

## 待核

- 福克斯、卡斯尔两段采访的英文原句，下载完听写后填进字幕。
- 布朗场边画面：在第四节集锦 / 单回合片段里找有他站在场边的镜头。
- "NO TRUE CENTER" 的说法：唐斯本来就是中锋，准确说法是"没有护框中锋 / 五个人都能投"，定稿时改成 **FIVE-OUT**。
- e676 文班换防前在防唐斯、e725 阿努诺比起跑位置，样片阶段在跟踪坐标上复核。
