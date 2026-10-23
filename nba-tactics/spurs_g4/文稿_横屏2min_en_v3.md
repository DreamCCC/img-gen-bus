# 《HOW DO YOU BLOW 29?》横屏 2 分钟英文版 · 文稿 v3（效果规划）

1920×1080 · 30 fps · 英文旁白 Charon（Gemini 3.8 Flash TTS，长句提速 10%）+ 英文字幕。
v2 → v3：分工定下来——**比赛画面讲"发生了什么"，代码动画讲画面讲不清的东西**（规则、时钟账、空间、看不见的指标）。
节奏参考 AWS / NBA Inside the Game 的宣传片：实拍和数据画面 6–10 秒一换，代码段每段只讲一件事；风格是 NBA 转播包装，不是科技发布会。

## 一、分工原则

| 交给比赛画面（实拍 + AR 加工） | 交给代码动画 |
|---|---|
| 进球、打铁、盖帽、补篮——情绪和冲击 | 规则：罚球状态、犯规可用（foul to give）、进攻时钟 vs 比赛时钟 |
| 谁在防谁、离多近（名牌、防守距离圈） | 算账：预期得分 vs 实得、领先怎么流失、53.8 秒 |
| 慢放、时停、子弹时间、冲击波 | 空间：五外站位把文班拉离篮筐、最后一攻谁空着——用**NBA 追踪坐标**画俯视 3D 球场 |
| | 看不见的指标：xFG 怎么算（距离、防守人手离球、出手角度） |

铁律不变：代码动画里的球员是**圆点 + 名字**，位置来自 `shot_detail.playersOnCourt`（NBA 追踪，英尺，中圈为原点；缺的人用画面跟踪 `traj.py` 补，并标注）；不画人形，不从转播画面"飞"进俯视（用户否定过）。代码段和实拍之间用硬切或闪白，不做假的镜头过渡。

## 二、视觉规范（NBA 包装）

- 底色：深海军蓝 `#0A1428` → 黑的径向渐变，细网格 + 极淡的球场线；数据粒子缓慢漂移。
- 主色：NBA 红 `#C8102E`、NBA 蓝 `#1D428A`、白。球队色：尼克斯 `#006BB6` / `#F58426`，马刺 银 `#C4CED4` / 黑。正面指标绿 `#2BD67B`，负面红 `#FF3B3B`。
- 字体：Barlow Condensed（数字、标题，粗体斜切）+ Inter（小字说明）。全大写标题，数字等宽。
- 动效：入场 0.25 s ease-out + 轻微过冲；数字滚动计数；线条"描出来"而不是直接出现；关键数字落地时一帧闪白 + 低频"砰"音效（代码合成）。
- 实拍上的 AR 元素和代码段用同一套颜色、字体、线宽，保证两种画面像同一个包装。

## 三、分镜（≈ 2:00；代码段合计约 38 秒，占 32%）

| # | 时间 | 类型 | 画面 | 旁白（Charon） |
|---|---|---|---|---|
| 1 | 0:00–0:05 | 实拍 | e727 补篮，MSG 现场声；球落网定格去色，**扫描启动**：十人骨架点 → 名牌 | — |
| 2 | 0:05–0:11 | **代码 C1** | **领先崩塌**：48 分钟时间轴上每分钟一根马刺领先柱，+29 峰值亮起后柱子一根根塌下去，最后一根翻到 −1 变红；标题砸入 HOW DO YOU BLOW 29? | Up twenty-nine in the NBA Finals. And the Spurs lost — by one. |
| 3 | 0:11–0:17 | **代码 C2** | **xFG 是什么**：一个出手点在 3D 球场上亮起，三个因子依次飞入——出手距离、防守人手离球、出手角度——汇成一个环形仪表 **xFG 34%**（用 e74 瓦塞尔真实数据） | Every shot gets graded. Distance, defender, angle — that's expected field goal percentage. |
| 4 | 0:17–0:24 | 实拍 | 上半场 4 个马刺三分串烧，出手瞬间投篮人头顶弹 xFG 环，命中变绿；右上角 **EXPECTED / ACTUAL** 计数器跟着跳 | First half, the Spurs beat those odds every time. Expected forty-nine. Scored seventy. |
| 5 | 0:24–0:31 | 实拍 → **代码 C3** | 第三节打铁串烧（4 球，环全红）→ 硬切账本：**+21 BORROWED**，下半场 **−20 PAID BACK**，两块数字互相抵消归零 | Then the bill came. Nineteen points on shots worth thirty-nine. |
| 6 | 0:31–0:38 | 实拍 + AR | 第四节尼克斯落位，五个名牌依次点亮，角标 **FIVE-OUT · +13 IN 7 MIN** | Mike Brown's answer: go small. Towns at center, four guys around him — all of them can shoot. |
| 7 | 0:38–0:47 | **代码 C4** | **为什么五外能拆掉文班**：e676 出手前一刻的追踪坐标，3D 斜俯视球场；篮下一圈"护框区"发光；唐斯上提掩护，文班的圆点被一条引力线拉出护框区，护框区变红闪烁 **RIM: EMPTY**；文班和布伦森之间亮 **SWITCH** | Towns can shoot, so Wembanyama has to come out with him. One screen, one switch — |
| 8 | 0:47–0:53 | 实拍 + AR | e676 实况：布伦森拔起，头顶 xFG 环 **33%**，地板测距 **27 FT**，命中 → 104–103 | — and the best rim protector in the league is guarding Brunson twenty-seven feet out. Bang. |
| 9 | 0:53–0:59 | 实拍 + AR | 马刺第四节 3 次出手串烧，脚下防守距离圈收紧到 **1.2 FT**；角标 **Q4: 4 / 19** | At the other end, every shot had a hand in the face. Four of nineteen. |
| 10 | 0:59–1:04 | 实拍 | e715 福克斯拿住球 → 时停去色 | Spurs up one. Thirteen seconds left. |
| 11 | 1:04–1:14 | **代码 C5** | **残局算术（规则动画）**：两个大时钟 **GAME 0:13 / SHOT 24**，24 那根进度条比 13 长；分叉成两条路：① HOLD → 尼克斯处于罚球状态（**KNICKS IN THE PENALTY**）→ 只能犯规 → 两罚 → 两罚全中就领先 3 分，而且时间更少了；② SHOOT → 打不进 → 尼克斯拿球、还有 11 秒。①亮绿，②亮红 | The shot clock is longer than the game, and the Knicks are in the penalty. Hold the ball, and they have to foul you. |
| 12 | 1:14–1:24 | 实拍 + 特效 | e715 慢放 ×0.25：福克斯路线银白，阿努诺比身后**残影追防**，间距数字往下掉，福克斯头顶 **xFG 49.6%** → 钉板**子弹时间 + 冲击波** | Instead, Fox goes. A coin-flip layup nobody needed. Pinned. |
| 13 | 1:24–1:27 | 采访 | 福克斯赛后（腾讯片段）2–3 秒，原声 + 字幕 | （原声："以为能跑过 OG"那句） |
| 14 | 1:27–1:33 | **代码 C6** | **犯规可用（规则动画）**：马刺第四节团队犯规 **1 / 5**，五格里亮一格；5.7 秒福克斯犯规点亮第二格 → **NO FREE THROWS · RESET**；尼克斯换人卡 SHAMET · BRIDGES IN → **FIVE SHOOTERS** | Five point seven left. The Spurs use a foul to give. Brown answers with five shooters. |
| 15 | 1:33–1:40 | **代码 C7** | **最后一攻谁空着**：e725 出手瞬间的追踪坐标，3D 球场；文班、福克斯两条蓝线同时扑向布伦森；阿努诺比的圆点亮红 **UNBOXED**，离他最近的马刺（卡斯尔）虚线圈 **12 FT**；一条橙色冲抢箭头从三分线外直插篮下 | Fox and Wemby both jump Brunson. Nobody touches Anunoby. |
| 16 | 1:40–1:46 | 实拍 + 特效 | e725/e727 实况：布伦森打铁 → 阿努诺比补篮，**冲击波 + 闪白 + 震屏**，107–106 | Tip. In. |
| 17 | 1:46–1:50 | 采访 / 字幕 | 卡斯尔赛后（"我们没人看到他"）2 秒；或布朗引语字幕 "He's got to be a monster on the offensive glass tonight." 压在尼克斯庆祝画面上 | — |
| 18 | 1:50–2:00 | **代码 C8** | **53.8 秒**：48 分钟的长条，马刺领先的部分是银色，尼克斯领先只有几道细红线，镜头推近到最后一道；数字 **53.8 SECONDS** 落地 | The Knicks led this game for fifty-three point eight seconds. It was enough. |

## 四、数据口径（新增，均来自本地 `data/`）

| 上屏 | 值 | 出处 |
|---|---|---|
| 尼克斯进入罚球状态 | Q4 7:14 起（阿尔瓦拉多第 5 次团队犯规，PN） | kb_pbp |
| 马刺犯规可用 | 5.7 秒福克斯犯规前马刺 Q4 团队犯规 1 次，犯规后 2 次（`P3.T2`），不罚球 | kb_pbp |
| e676 出手瞬间 | 布伦森 (23.8, −20.2) ft，文班 (26.0, −15.3) ft，相距 5.4 ft；唐斯在篮下 (41.1, 9.1) | shot_detail playersOnCourt |
| e725 出手瞬间 | 布伦森 31 ft；文班、福克斯都在他 5 ft 内；阿努诺比离篮约 30 ft，最近马刺卡斯尔 12.6 ft | 同上 |
| C2 示例出手 | e74 瓦塞尔三分的 xFG / 距离 / 手离球（制作时取值） | shot_detail |

其余沿用 `文稿_横屏2min_en_v1.md` 的数据表。

## 五、样片顺序

1. **样片 A（约 15 秒）**：第 10–12 镜（时停 → 残局算术规则动画 → 慢放钉板），一段里同时看到"实拍加工 + 代码动画 + 特效 + Charon 配音"，用来定整体风格。
2. 用户确认后再铺 C4/C7（3D 追踪球场）和其余实拍段。

## 六、待核

- 福克斯、卡斯尔采访的英文原句（下载后 Whisper 听写）。
- e676 文班换防前在防唐斯：用跟踪坐标确认。
- 追踪里缺的球员（每帧只有 7–9 人）：用画面跟踪补，补的点在代码动画里画成空心圆。
