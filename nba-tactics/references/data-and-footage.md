# 数据与素材：查库、找片段、下载、核对事实

## 访问方式

- SQL 网关：`GET https://tech-api.nbadata.cn/dev/sql?sql=...`，不带 token。查编辑上传的素材时加 `db=nba_data_biz`。
- 网关按 IP 白名单拦截，本机（尤其开着 VPN 时）一律返回 nginx 403，换请求头也没用。白名单服务器 `root@8.152.222.232` 能通。
- `tools/nba_sql.py` 的做法：本机通过 SSH 把一段 Python 脚本经 stdin 传给服务器，由服务器发 GET 请求，结果以 JSON 返回本机。**不用 scp。** 这个命令要在沙箱外运行。

```bash
python tools/nba_sql.py "SELECT ..."                  # 打印 JSON
python tools/nba_sql.py "SELECT ..." --db nba_data_biz
python tools/nba_sql.py -f q.sql -o data/out.json
```

在代码里调用：`from nba_sql import query; rows = query("SELECT ...")`。

- 下载：`tools/fetch_clip.py <news_id> ... -d raw/`。流程是 `testapi.nba.cn/nba-web/api/web/content/videoPlay?newsId=...` 拿签名 m3u8，再用 ffmpeg 拷流成 mp4。这个接口不限 IP，本机直连就行。

## 库和表

| 库.表 | 用途 | 关键字段 |
| --- | --- | --- |
| `nba_game_prod.kb_tbs` | 球队单场数据，用来找比赛 | `GAME_ID, GAME_DATE, MATCHUP, WL, PTS, SEASON, SEASON_TYPE, TEAM_ABBREVIATION` |
| `nba_game_prod.kb_pbs` | 球员单场数据 | `player_name, player_name_cn, team_abbreviation, min, pts, ast`；号码和首发在 `extend_info` 的 JSON 里（`$.jerseyNum`、`$.starter`） |
| `nba_game_prod.kb_pbp` | 逐回合事件 | `action_number, order_number, period, clock (PT07M06.00S), team_tricode, action_type, sub_type, descriptor, qualifiers, person_id, player_name_i, assist_player_name_i, shot_distance, shot_result, x, y, score_home, score_away, points_total, assist_total, description` |
| `nba_game_prod.nba_shot_detail` | 出手时最近的防守人、距离、预期命中率 | `event_id, joint_defenderId, joint_ball_distance, expected_fg`。**季前赛没有数据** |
| `nba_cms_prod.item_info` | 资讯和视频总库，最全 | `id`（就是 news_id）、`title, duration, game, event_id, players, star, is_twins_x, create_at` |
| `nba_cms_prod.video_material` | 自动切的单回合片段，约 33 万条 | `news_id, type (1=自动片段), game_id, event, period, game_clock, players, tags, new_tags` |

## 必须知道的坑

- **表里混着多个联赛。** `SEASON='2026'` 是 WNBA，`20` 开头的 game_id 是 G League。查 NBA 一律加 `GAME_ID LIKE '00%'`。季前赛 game_id 以 `001` 开头，常规赛 `002`，季后赛 `004`。
- `kb_pbp` 全表 `GROUP BY` 会超时。先用 `game_id` 限定到具体场次。
- 跨库 JOIN（`nba_cms_prod` 关联 `nba_game_prod`）会报排序规则冲突，ON 条件两边都加 `COLLATE utf8mb4_general_ci`。最省事的办法是拆成两次查询，在本地对。
- `kb_pbp` 的 `score_home` 和 `score_away` 是主客队得分，**不是**按你关心的球队排的。例如澳门站名义上独行侠是主队：`score_home=64, score_away=76` 表示火箭 76、独行侠 64。和画面记分牌核对一遍。
- `action_number` 按数字排序时要用 `CAST(action_number AS UNSIGNED)`。
- 季前赛和中国赛经常**没有** `video_material type=1` 的自动片段，但 `item_info` 里每个进球都有单独的片段。
- `item_info` 里同一事件常有两条（id 尾号 01/02，`is_twins_x`），时长和分辨率一样，md5 也一样。下载后比对 md5，只留一份。
- 有的比赛（比如 2025-26 总决赛 G5）素材库里一条都没有。选题前先查目标比赛有没有片段。

## 片段和 PBP 怎么对上

- `item_info.game` 对应 `kb_pbp.game_id`，`item_info.event_id` 对应 `kb_pbp.action_number`。
- `video_material.game_id` 对应 `kb_pbp.game_id`，`video_material.event` 对应 `kb_pbp.action_number`。
- 文件命名：`raw/e<action_number>_<动作>.mp4`，例如 `e453_pullup.mp4`。后面所有的配置文件都以 `eNNN_` 开头。

## 常用查询

```sql
-- 球队本季的比赛
SELECT GAME_ID, GAME_DATE, MATCHUP, WL, PTS FROM nba_game_prod.kb_tbs
WHERE SEASON='2026-27' AND TEAM_ABBREVIATION='HOU' AND GAME_ID LIKE '00%' ORDER BY GAME_DATE;

-- 某球员某场的全部命中（杜兰特 person_id=201142）
SELECT action_number, period, clock, action_type, sub_type, descriptor, qualifiers, shot_distance, x, y,
       score_home, score_away, assist_player_name_i, description
FROM nba_game_prod.kb_pbp WHERE game_id='0012600012' AND person_id='201142' AND shot_result='Made'
ORDER BY CAST(action_number AS UNSIGNED);

-- 这场比赛的单回合片段（标题里通常有球员名）
SELECT id, type, title, duration, game, event_id, star, create_at FROM nba_cms_prod.item_info
WHERE create_at >= '2026-10-09 18:00:00' AND (title LIKE '%杜兰特%' OR players LIKE '%201142%')
ORDER BY create_at;

-- 目标事件前后的回合（讲上下文、找"35 秒内第二记"这类叙事点）
SELECT action_number, clock, team_tricode, action_type, sub_type, player_name_i, shot_distance,
       score_home, score_away, points_total, assist_total, description
FROM nba_game_prod.kb_pbp WHERE game_id='0012600012' AND period='3'
  AND CAST(action_number AS UNSIGNED) BETWEEN 440 AND 466 ORDER BY CAST(action_number AS UNSIGNED);

-- 名单、号码、中文名
SELECT team_abbreviation t, player_name, player_name_cn, pts, ast, min,
       JSON_UNQUOTE(JSON_EXTRACT(extend_info,'$.jerseyNum')) num
FROM nba_game_prod.kb_pbs WHERE game_id='0012600012' AND min>0 ORDER BY t, min DESC;

-- 换人记录：反推某一时刻场上是哪五个人
SELECT action_number, period, clock, team_tricode, player_name_i, description FROM nba_game_prod.kb_pbp
WHERE game_id='0012600012' AND action_type='substitution' AND period<=3 ORDER BY order_number;
```

## 事实核对清单

- [ ] 片段里的记分牌（比分、节次、比赛时钟）和 PBP 的 `clock`、`score_*` 一致。出手通常比 PBP 的 `clock` 早 0–2 秒。
- [ ] `points_total` 就是本场第几分，`assist_total` 就是助攻人本场第几次助攻，写卡片直接用。
- [ ] 叙事点（"35 秒内第二记""火箭 4 个进球里他拿了 3 个"）都从相邻的 PBP 算出来，不靠印象。
- [ ] 球员身份：号码从原图裁切里认，名单查 `kb_pbs`，在场五人用换人记录确认。
- [ ] 中文译名用 `player_name_cn`，或者用户认可的通行译名，全片统一（马绍尔、里萨谢、比贝罗维奇）。
