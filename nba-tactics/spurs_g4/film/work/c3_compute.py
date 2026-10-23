"""C3 ledger numbers: SAS field-goal points, actual vs expected, per half.

Definitions
  actual   = sum(shot value for made FG)          shot value = 3 if ngssEventInfo.type == '3pt' else 2
  expected = sum(xFG * shot value)                 xFG = ext.expFieldGoalPct (== row expected_fg rounded)
  Free throws excluded. Halves: period 1-2 / 3-4.
  Cross-checked against pbp (is_field_goal == '1', shot_result, actionType, period).
"""
import json
from collections import defaultdict
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'data'
OUT = Path(__file__).resolve().parent / 'c3_numbers.json'
shots = json.load(open(D / 'shot_detail.json', encoding='utf-8'))
pbp = json.load(open(D / 'pbp.json', encoding='utf-8'))
SAS = 1610612759

fg = {int(p['action_number']): p for p in pbp if p['is_field_goal'] == '1'}
agg = defaultdict(lambda: defaultdict(float))
for s in shots:
    if int(s['team_id']) != SAS:
        continue
    e = json.loads(s['ext'])
    p = fg[int(s['event_id'])]
    pe = json.loads(p['extend_info'])
    v = 3 if e['ngssEventInfo']['type'] == '3pt' else 2
    assert pe['actionType'] == e['ngssEventInfo']['type'], (s['event_id'], pe['actionType'])
    made = int(s['success']) == 1
    assert made == (p['shot_result'] == 'Made')
    half = 'H1' if int(e['period']) <= 2 else 'H2'
    x = e['expFieldGoalPct']
    for key in (half, f'Q{e["period"]}', 'GAME'):
        a = agg[key]
        a['fga'] += 1
        a['fgm'] += made
        a['act'] += v * made
        a['exp'] += v * x
        a['exp_rowfield'] += v * float(s['expected_fg'])
        a[f'fg{v}a'] += 1
        a[f'fg{v}m'] += made
        a[f'act{v}'] += v * made
        a[f'exp{v}'] += v * x
        a[f'xfg_sum{v}'] += x

# pbp totals (incl. the one SAS FG with no shot_detail row)
pb = defaultdict(lambda: defaultdict(float))
untracked = []
for k, p in fg.items():
    if p['team_tricode'] != 'SAS':
        continue
    pe = json.loads(p['extend_info'])
    v = 3 if pe['actionType'] == '3pt' else 2
    half = 'H1' if int(p['period']) <= 2 else 'H2'
    made = p['shot_result'] == 'Made'
    pb[half]['fga'] += 1
    pb[half]['act'] += v * made
    if k not in {int(s['event_id']) for s in shots}:
        untracked.append({'action_number': k, 'period': p['period'], 'desc': p['description'], 'value': v, 'made': made})

res = {}
for k in ('H1', 'H2', 'Q1', 'Q2', 'Q3', 'Q4', 'GAME'):
    a = agg[k]
    res[k] = {kk: round(vv, 3) for kk, vv in a.items()}
    print(k, f"FGA {a['fga']:.0f} FGM {a['fgm']:.0f}  actual {a['act']:.0f}  expected {a['exp']:.3f} (row field {a['exp_rowfield']:.3f})  "
          f"diff {a['act'] - a['exp']:+.3f} | 3s {a['fg3m']:.0f}/{a['fg3a']:.0f} act3 {a['act3']:.0f} exp3 {a['exp3']:.2f} | 2s {a['fg2m']:.0f}/{a['fg2a']:.0f} act2 {a['act2']:.0f} exp2 {a['exp2']:.2f}")
print('pbp check', {k: dict(v) for k, v in pb.items()})
print('untracked', untracked)
h1, h2 = agg['H1'], agg['H2']
r1, r2 = round(h1['exp']), round(h2['exp'])
a1, a2 = round(h1['act']), round(h2['act'])
print(f'ROUNDED  H1 {r1}->{a1} = {a1 - r1:+d}   H2 {r2}->{a2} = {a2 - r2:+d}   net(rounded rows) {a1 - r1 + a2 - r2:+d}  net(exact) {h1["act"] - h1["exp"] + h2["act"] - h2["exp"]:+.2f}')
res['untracked'] = untracked
res['rounded'] = {'H1_exp': r1, 'H1_act': a1, 'H2_exp': r2, 'H2_act': a2, 'H1_diff': a1 - r1, 'H2_diff': a2 - r2, 'net': a1 - r1 + a2 - r2,
                  'net_exact': round(h1['act'] - h1['exp'] + h2['act'] - h2['exp'], 3)}
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1)
print('wrote', OUT)

near = [json.loads(s['ext'])['expFieldGoalPct'] for s in shots
        if int(s['team_id']) == SAS and json.loads(s['ext'])['features']['shotDistance'] < 6]
near_mean = sum(near) / len(near)
print(f'SAS xFG mean for shots < 6 ft: {near_mean:.3f} (n={len(near)})')

SCENE = Path(__file__).resolve().parents[1] / 'scenes' / 'c3_ledger.json'
cfg = json.load(open(SCENE, encoding='utf-8'))
R = res['rounded']
cfg['ledger'] = {
    'h1': {'expected': R['H1_exp'], 'actual': R['H1_act'], 'diff': R['H1_diff']},
    'h2': {'expected': R['H2_exp'], 'actual': R['H2_act'], 'diff': R['H2_diff']},
    'net': R['net'], 'game_expected': R['H1_exp'] + R['H2_exp'], 'game_actual': R['H1_act'] + R['H2_act'],
    'exact': {'h1_expected': round(h1['exp'], 3), 'h2_expected': round(h2['exp'], 3), 'net': R['net_exact']},
}
cfg['_sources'] = {
    'definition': 'SAS field-goal points only (2PT + 3PT, no free throws). actual = sum of shot value on made FGs; expected = sum(ext.expFieldGoalPct x shot value); shot value from ext.ngssEventInfo.type (== pbp actionType). Halves = period 1-2 / 3-4. Computed by film/work/c3_compute.py.',
    'h1': f"46 tracked SAS FGA in Q1-Q2 (28 made: 14/26 3PT, 14/20 2PT). actual 70 (pbp agrees: 70). expected {h1['exp']:.3f} -> 49. diff +{h1['act'] - h1['exp']:.2f} -> shown +21 (70 - 49).",
    'h2': f"39 SAS FGA in Q3-Q4 (8 made: 3/17 3PT, 5/22 2PT). actual 19. expected {h2['exp']:.3f} -> 39. diff {h2['act'] - h2['exp']:.2f} -> shown -20 (19 - 39).",
    'net': f"(70 + 19) - (49 + 39) = 89 - 88 = +1; unrounded 89 - {h1['exp'] + h2['exp']:.3f} = +{R['net_exact']:.2f}.",
    'untracked': f"pbp has 86 SAS FGA; action 133 (Q1, MISS Wembanyama 5' Driving Layup) has no shot_detail row / no xFG and is excluded from expected (adds 0 to actual). If it were graded at the game's mean SAS xFG for shots under 6 ft ({near_mean:.2f}), H1 expected would be {h1['exp'] + 2 * near_mean:.2f} (rounds to {round(h1['exp'] + 2 * near_mean)}) and the exact net {R['net_exact'] - 2 * near_mean:+.2f}.",
    'data': 'data/shot_detail.json (team_id, success, ext.period, ext.expFieldGoalPct, ext.ngssEventInfo.type), cross-checked with data/pbp.json (is_field_goal == "1", shot_result, extend_info.actionType, period).',
}
json.dump(cfg, open(SCENE, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('updated', SCENE)
