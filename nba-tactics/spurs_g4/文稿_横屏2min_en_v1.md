# 《HOW DO YOU BLOW 29?》横屏 2 分钟英文版 · 文稿 v1（讨论稿）

1920×1080，英文旁白 + 英文字幕。重心：战术拆解和高阶数据上屏，故事线压到四段。
旁白约 290 词（≈ 115 秒，150 wpm），布朗原声 3 段约 12 秒；超出的部分在定稿时删。

## 数据口径（全部来自本地 `data/`，脚本见 `work/brown_lineups.py`、`work/brown_stints.py`、`work/adv_stats.py`）

| 上屏数字 | 值 | 出处 |
|---|---|---|
| 最大领先 | 29（Q3 9:27，81:52） | kb_pbp |
| 总决赛历史最大逆转 | 29 分，此前纪录 24 分（2008 G4 凯尔特人） | `research/facts_record.json` |
| 上半场投篮 预期 / 实得 | 49.2 / 70（+20.8） | shot_detail `expected_fg` |
| 下半场投篮 预期 / 实得 | 39.1 / 19（−20.1） | 同上 |
| 第三节马刺三分 | 12 投 2 中，中间连丢 9 个（`xOxxxxxxxxxO`） | shot_detail + kb_pbp |
| 收尾阵容 | 阿尔瓦拉多、布伦森、哈特、唐斯、阿努诺比；Q4 7:14 起 7.0 分钟 22:9 | kb_pbp 换人推算 |
| 第四节尼克斯三分、最近防守人是文班 | 5 投 3 中 | shot_detail `joint_defenderid` |
| 第四节马刺 | 19 投 4 中，手离球平均约 2.5 英尺 | shot_detail（与旧稿 2.7 的口径差异待对齐 `shot_quality.py`） |
| e676 布伦森 27 英尺 | xFG 33.2%，进攻时钟 4.8 秒，文班手离球 3.0 英尺 | shot_detail |
| e714 福克斯上篮 | xFG 49.6% | shot_detail |
| e725 布伦森 31 英尺 / e727 补篮 | xFG 30.3% / 65.7% | shot_detail |
| 尼克斯全场领先时间 | 53.8 秒 | 文稿 v2（维基引文 [101]） |
| 半场 14 个三分、总决赛纪录 | 14 | 沿用文稿 v2 口径，**出处待补** |

## 文稿

### 0:00–0:12 冷开场
- 【画面】e727 补篮实况，MSG 现场声 3 秒；球落网那一帧定格，画面去色。
- 【代码动画】分差曲线从左往右画：+29 的峰值亮起，随后一路下坠，补篮那一刻穿过 0 线变红（−1）。标题砸入：**HOW DO YOU BLOW 29?**
- VO: Up twenty-nine in the NBA Finals. And the Spurs lost — by one.
- VO: The biggest collapse in Finals history. So we went to the tracking data.

### 0:12–0:30 借来的领先
- 【代码动画】半场投篮图：每个出手点按预期命中率着色；两根柱子"EXPECTED 49 / ACTUAL 70"，差值计数器跳到 **+21**。
- VO: First half: fourteen threes, a Finals record. But the tracking model grades every shot. Expected: forty-nine points. Actual: seventy.
- 【代码动画】柱子翻面到下半场："EXPECTED 39 / ACTUAL 19"，计数器跳到 **−20**；第三节 12 个三分排成一行逐个点亮，中间 9 个连续变红。
- VO: After halftime, they paid it all back — nineteen points on shots worth thirty-nine. Nine straight missed threes in the third.

### 0:30–1:05 布朗的那一步
- 【代码动画】阵容卡：五个球员名牌依次滑入（ALVARADO · BRUNSON · HART · TOWNS · ANUNOBY），罗宾逊、布里奇斯的名牌划掉；角标 **NO TRUE CENTER**；比分计数 **22–9**。
- VO: Mike Brown's answer: no Mitchell Robinson, no Bridges. Two guards, and Karl-Anthony Towns at center. Over the last seven minutes, that group won twenty-two to nine.
- 【拆 · e676】实况到挡拆前时停；地板线：唐斯掩护路线、哈珀和文班换防箭头；文班从禁区被拖到弧顶的轨迹（发光残影）；测距线 **27 FT**；数据标签 **xFG 33% · SHOT CLOCK 4.8**；出手弧线 → 命中 → 104–103。
- VO: Here's why. Towns can shoot, so Wembanyama has to follow him out. One screen, one switch — and the best rim protector in the league is guarding Brunson twenty-seven feet from the basket. A thirty-three percent shot. Bang. One-oh-four, one-oh-three.
- 【代码动画】半场图：第四节尼克斯 5 次"最近防守人是文班"的三分在弧顶亮起，3 个变绿。
- VO: In the fourth, the Knicks took five threes with Wemby as the closest defender. They made three.
- 【代码动画】马刺第四节 19 个出手点，每个点外圈一个防守人距离圈，圈逐个收紧到 2.5 英尺；**4/19**。
- VO: And on the other end, the hands got closer. Four of nineteen in the fourth.
- 【原声 · 布朗 q3_1】"Defensively, we just did it harder for longer stretches."

### 1:05–1:40 最后 13 秒
- 【拆 · e715】福克斯拿住球那一帧时停；屏幕左右两个大时钟：**GAME 13.0 / SHOT 24**，24 秒的那个压过 13 秒的那个；文字 **HOLD IT → THEY MUST FOUL**。
- VO: Spurs up one. Thirteen seconds left. The shot clock is longer than the game. Hold the ball, and the Knicks have to foul.
- 【慢放 ×0.25】福克斯路线（银白）、阿努诺比追防路线（橙），两条线的间距用数字实时缩小；计时条 **GATHER → TAKEOFF < 1.0 s**；标签 **xFG 49.6%**。
- VO: Instead, he goes. Less than a second from gather to takeoff. A coin-flip layup nobody needed.
- 【子弹时间】钉板瞬间环绕定格 + 冲击波。
- VO: Pinned.
- 【原声 · 布朗 q4_2】"Maybe he was going to drive and wanted to keep the dribble to run out the clock."

### 1:40–2:00 最后一攻
- 【代码动画】换人卡，5.7 秒：SHAMET、BRIDGES 换上 → **FIVE SHOOTERS**。
- 【战术板 · e725/e727】右上角俯视战术板与实况同步：出手瞬间文班、福克斯同时扑布伦森（两条蓝线汇向一点）；阿努诺比从 28 英尺外冲入（橙色长箭头）；最近的马刺在 12 英尺外，正防着别人（虚线圈）。
- VO: Last possession. Brown puts five shooters on the floor. Fox and Wemby both jump Brunson — and nobody puts a body on Anunoby, crashing in from twenty-eight feet.
- 【原声 · 布朗 q4_4】"He's got to be a monster on the offensive glass tonight."
- 【实况】补篮，闪白，比分 107–106。
- VO: Tip. In.
- 【收尾卡】分差曲线完整版缓推，尼克斯领先的那一小段高亮：**KNICKS LED FOR 53.8 SECONDS**。
- VO: The Knicks led this game for fifty-three point eight seconds. It was enough.

## 待定 / 待核

- 旁白音色选了 longfei_v3（百炼中文系统音色）：先出 3 句英文试听，和英文竖版用过的设计音色"现场解说"对比后再定。
- 布朗原声需要 YouTube cookies 下载 qqPT01jE5S0（画面）和 93iEr0LWF8U（SNY 同场录音，替换丢包的音轨）。
- e676 换防、e725 站位：脚本里的说法来自 `research/footage_map.md` 已核对的部分；收尾阵容"唐斯把文班拉出来"要在 e676 跟踪坐标上再确认文班换防前是在防唐斯。
- "14 个三分、总决赛纪录"出处待补，补不到就删掉这半句。
