"""Assemble ../bgm_plan.json: snap each suggested in/out to the nearest downbeat of the beat grid in ../beats/."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.dirname(HERE)
ISRC = {p['title']: p.get('isrc') for p in json.load(open(f'{HERE}/pieces.json'))}
REF = json.load(open(f'{HERE}/refine.json'))


def page(title):
    return f'https://incompetech.com/music/royalty-free/index.html?isrc={ISRC[title]}'


def extend(grid, dur):
    """Beat tracking stops where the pulse blurs (climaxes, fade-outs); carry the last local bar length to the end."""
    if len(grid) < 3:
        return list(grid), len(grid)
    bar = grid[-1] - grid[-2]
    out = list(grid)
    while out[-1] + bar < dur:
        out.append(round(out[-1] + bar, 3))
    return out, len(grid)


def snap(grid, t, out=False):
    if not grid:
        return round(t, 2)
    if out:
        ok = [x for x in grid if x <= t + 0.3]
        if ok:
            return ok[-1]
    return min(grid, key=lambda x: abs(x - t))


def entry(title, fn, start, end, mood, extra=None):
    g = json.load(open(f'{MUSIC}/beats/{os.path.splitext(fn)[0]}.json'))
    grid, n_real = extend(g.get('downbeats') or [], g['duration'])
    s, e = snap(grid, start), snap(grid, end, out=True)
    r = REF[fn]
    out = {
        'file': f'assets/music/{fn}',
        'title': title,
        'artist': 'Kevin MacLeod',
        'url': page(title),
        'download_url': 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/' + title.replace(' ', '%20') + '.mp3',
        'license': 'CC BY 4.0 https://creativecommons.org/licenses/by/4.0/',
        'duration': g['duration'],
        'bpm': g['bpm_measured'] if 'bpm_by_span' not in g else [x[2] for x in g['bpm_by_span']],
        'bpm_catalog': g['catalog_bpm'],
        'beats_file': f'assets/music/beats/{os.path.splitext(fn)[0]}.json',
        'suggest_in': s,
        'suggest_out': e,
        'suggest_len': round(e - s, 2),
        'downbeats': [x for x in grid if s - 1e-3 <= x <= e + 1e-3],
        'voice_band_1to4k_median': r['voice_share_median'],
        'voice_band_worst_4s': r['voice_share_worst4s'],
        'mood': mood,
    }
    if 'bpm_by_span' in g:
        out['bpm_by_span'] = g['bpm_by_span']
    if grid and n_real < len(grid) and e > grid[n_real - 1] + 1e-3:
        out['downbeats_extrapolated_after'] = grid[n_real - 1]
    if not grid:
        out['cue_points'] = g.get('cue_points', [])
        out.pop('downbeats')
    if extra:
        out.update(extra)
    return out


plan = {
    '_说明': {
        '时间': 'suggest_in/out 为曲目内秒数，已吸附到最近的小节第一拍（downbeats）；无拍点的铺底曲给 cue_points（最强起音）。',
        'bpm': '实测（librosa 拍点追踪，以曲库标称 BPM 作起点）；变速曲给分段 bpm_by_span。music_probe.py 原始输出见 _probe/music_probe.log。',
        '人声频段': 'voice_band_* = 1–4 kHz 能量占全频比例，越低越不和旁白打架；worst_4s 给出最该避开的 4 秒窗（曲内秒数, 占比）。',
        '文稿差异': '文稿 v2 写第 0 段"BGM 无，只留现场声"、第 4 段"BGM 撤掉，只留现场声和心跳低频"。这两段按任务仍给了选曲，均为低密度铺底，用不用由剪辑定。',
        '响度': '全部曲目中低频为主，旁白下建议整体 -18~-22 dB 铺底；时停/慢放处可再压 3–6 dB 或加 800 Hz 低通。',
    },
    '0_冷开场': {
        'film_window': '样片 v3：12.08 计分牌出现 → 49.41 片名重击（约 37 s）',
        'main': entry('Long Note Three', 'Long_Note_Three.mp3', 0.0, 38.0,
                      '一条很长的暗色低音长音，厂牌原文就是"Use under dialog"。0–22 s 有一次缓慢鼓起（峰值约 14–16 s），从 12.08 计分牌出现时淡入，峰值正好落在"之前的纪录是 24 分"附近，之后几乎静默，交给旁白和 Inside 原声；片名重击仍用合成 impact。',
                      {'avoid': '120–140 s 有高音弦乐（1–4 kHz 占比到 0.9），不要用这段',
                       'place_hint': '曲内 0.0 → 片内 12.08，淡入 1.5 s，38 s 处 3 s 淡出'}),
        'alt': entry('Ominous Intro', 'Ominous_Intro.mp3', 0.093, 38.0,
                     '70 BPM 的慢速 Moog 式合成器铺底，比主选更有"出事了"的阴影感，持续稳定无突变，适合计分牌翻转那几秒压暗画面。',
                     {'place_hint': '小节 3.44 s；可把曲内 0.093 对到片内 21.4（翻牌）前一小节 17.96，让翻牌落在小节头'}),
    },
    '1_29分是怎么来的': {
        'film_window': '约 0:40–2:00（80 s）',
        'main': entry('Montauk Point', 'Montauk_Point.mp3', 0.07, 79.8,
                      '吉他+贝斯+鼓的轻快小编制摇滚，117.5 BPM，厂牌描述"Unobtrusive"。能量从开头往后逐步抬升，和分差曲线往上爬同向；1–4 kHz 占比全曲最高也只有 0.028，几乎不碰人声频段。78–80 s 有一处乐句换气，正好收在数据卡/手感柱状图出现前。',
                      {'loop_hint': '如果本段超过 80 s，可续到 114 s（下一个乐句抬升点）'}),
        'alt': entry('Loopster', 'Loopster.mp3', 2.299, 82.5,
                     '电钢琴+贝斯+鼓的 Funk 律动，107.7 BPM，"用简单乐句叠出来"，全曲能量非常平，可随意按 2.23 s 小节剪接/循环。比主选更"松弛自信"，少一点体育感。'),
    },
    '2_第三节13比0': {
        'film_window': '约 2:00–3:45（105 s）',
        'main': entry('Invariance', 'Invariance.mp3', 41.3, 146.4,
                      '马林巴/木琴+低音提琴+打击乐，暗色、神秘、带悬念。这首的特点是同一段旋律前半 107.7 BPM、116.0 s 起提速到 129.2 BPM，"节奏收紧"是写在曲子里的。按建议起点，提速点落在本段第 75 s 左右（布伦森/阿努诺比/哈特三分那一串），之前的慢速段压在恶意犯规和拆①下面。1–4 kHz 占比 0.003，全片最干净。',
                      {'tempo_switch_at': 116.0,
                       'place_hint': '提速点在曲内 116.0 s（114–116 s 有约 1.5 s 静音，可当一次"停顿"用）。若想让提速对到别的画面，起点 = 116.0 − 目标在本段内的秒数，再吸附到 downbeats'}),
        'alt': entry('Industrial Cinematic', 'Industrial_Cinematic.mp3', 0.255, 105.0,
                     '合成器+打击乐的工业感律动，约 110 BPM，0–80 s 逐步加厚，80 s 后突然变薄（可对巴克利片段让位），低频足、人声频段占比 0.008。比主选更"机械压迫"，少一点悬疑。'),
    },
    '3_第四节': {
        'film_window': '约 3:45–6:00（135 s）',
        'main': entry('The Escalation', 'The_Escalation.mp3', 187.0, 321.5,
                      '低音提琴+弦乐+打击乐，厂牌原文"One really long build… Like Bolero but for suspense"。建议用后半：187–200 s 几乎静默（让开场两句旁白），200 s 起一路加厚加速（129 → 152 BPM），在本段结尾"马刺手里还握着 7 分，这都能输？"处到达全曲最高点，紧接第 4 段撤乐，落差最大。',
                      {'avoid': '308–316 s 弦乐上行进入 1–4 kHz（占比约 0.2），旁白若压在这里建议 EQ 衰减 2–3 kHz 3 dB',
                       'place_hint': '建议出点 320.5 s 之后约 1.5 s 是全曲最高点和终止重音（322 s 起骤降），可把它留作第 3 段最后一拍再硬切到第 4 段；306.3 s 以后的小节点是按末段 152 BPM 外推的'}),
        'alt': entry('Constance', 'Constance.mp3', 0.07, 136.2,
                     '马林巴/木琴+低音+合成器，83.4 BPM，厂牌原文"A low-level intensity burn to underscore a tense situation"。全曲 140 s，几乎正好等于本段时长，强度恒定不抢话，人声频段占比 0.003。缺点是没有主选那种逐步抬升。'),
    },
    '4_最后3分31秒': {
        'film_window': '约 6:00–8:45（165 s），含 4 段战术拆解（时停/慢放/倒回）',
        'main': entry('Stay the Course', 'Stay_the_Course.mp3', 2.067, 167.8,
                      '合成器低频轰鸣+打击乐，60.1 BPM——每秒一下，厂牌原文"A low rumble marks the seconds"，正好对应比赛时钟一秒一秒往下走。全曲 272 s 强度恒定、没有旋律，1–4 kHz 占比 0.004，时停时可以直接压低或低通，不会因为切断旋律而显得突兀。',
                      {'place_hint': '每拍 1 s，可把一拍对到计分牌秒数跳变；时停处建议 -6 dB + 400 Hz 低通，恢复原速时拉回'}),
        'alt': entry('Enter the Maze', 'Enter_the_Maze.mp3', 10.054, 134.2,
                     '一记一记的低音"咚"加金属质感噪声，92.3 BPM，sub 低频占 90%，就是文稿说的"心跳低频"感。能量一起一伏，比主选更有情绪但也更跳。',
                     {'avoid': '136–148 s 有尖锐的合成器长音（1–4 kHz 占比 0.52），必须避开',
                      'loop_hint': '干净可用段 10.05–133.9 s（约 124 s），不够 165 s 时从小节点 35.875 s 起循环一次补足（36 s 处有一次 +13.5 dB 起拍，接缝自然）'}),
    },
    '5_结尾': {
        'film_window': '约 8:45–9:30（45 s）',
        'main': entry('Calmant', 'Calmant.mp3', 2.6, 47.6,
                      '钢琴独奏，约 56 BPM（自由速度），厂牌原文"Slow moving, semi-arpeggio theme"，Relaxed/Somber。音区集中在中低音（250–1000 Hz 占 74%），1–4 kHz 占比 0.004，压在文班原声和最后一句旁白下面不打架；收得住，又不至于太丧。',
                      {'place_hint': '自由速度，downbeats 仅供参考；42 s 处有一句稍强的乐句，可对到黑场片尾'}),
        'alt': entry('Danse Morialta', 'Danse_Morialta.mp3', 0.836, 46.6,
                     '钢琴独奏，约 76 BPM，厂牌说"难以界定情绪，所以同时标了 somber 和 uplifting"——正好对应"要么放弃，要么变得更强"。前 60 s 是安静段。',
                     {'avoid': '124–136 s 高音区旋律（1–4 kHz 占比 0.4–0.5），不要用'}),
    },
}
json.dump(plan, open(f'{MUSIC}/bgm_plan.json', 'w'), ensure_ascii=False, indent=1)
for k, v in plan.items():
    if k.startswith('_'):
        continue
    for role in ('main', 'alt'):
        x = v[role]
        print(k, role, x['title'], x['bpm'], x['suggest_in'], '→', x['suggest_out'], f"({x['suggest_len']}s)")
