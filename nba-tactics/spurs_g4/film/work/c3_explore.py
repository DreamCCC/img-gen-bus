import json
from collections import Counter, defaultdict
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'data'
shots = json.load(open(D / 'shot_detail.json', encoding='utf-8'))
pbp = json.load(open(D / 'pbp.json', encoding='utf-8'))
SAS, NYK = 1610612759, 1610612752

fg = [p for p in pbp if p['is_field_goal'] == '1']
print('pbp FG rows', len(fg), Counter(p['team_tricode'] for p in fg))
byact = {int(p['action_number']): p for p in fg}
sd = {int(s['event_id']): s for s in shots}
print('shot_detail', len(shots), 'teams', Counter(int(s['team_id']) for s in shots))
print('shot_detail event ids matched to pbp FG action_number:', sum(1 for k in sd if k in byact))
miss = [k for k in byact if k not in sd]
print('pbp FG without shot_detail', len(miss), [(k, byact[k]['team_tricode'], byact[k]['period'], byact[k]['description']) for k in miss])
nomatch = [k for k in sd if k not in byact]
print('shot_detail without pbp FG', nomatch)

# compare shot_detail fields to pbp
diff = 0
for k, s in sd.items():
    p = byact.get(k)
    if not p:
        continue
    e = json.loads(s['ext'])
    pe = json.loads(p['extend_info'])
    made_p = p['shot_result'] == 'Made'
    if bool(int(s['success'])) != made_p or str(e['period']) != p['period'] or int(s['shooter_id']) != int(p['person_id']):
        diff += 1
        print('DIFF', k, s['success'], p['shot_result'], e['period'], p['period'], s['shooter_id'], p['person_id'])
    t = e['ngssEventInfo']['type']
    if (t == '3pt') != (pe.get('shotValue', None) == 3 if 'shotValue' in pe else (pe.get('actionType') == '3pt')):
        print('type mismatch', k, t, pe.get('actionType'), pe.get('shotValue'))
print('diffs', diff)
print('pbp extend keys sample', sorted(json.loads(fg[0]['extend_info']).keys()))
print('expected_fg vs expFieldGoalPct max abs diff', max(abs(float(s['expected_fg']) - json.loads(s['ext'])['expFieldGoalPct']) for s in shots if json.loads(s['ext']).get('expFieldGoalPct') is not None))
print('none xfg', sum(1 for s in shots if json.loads(s['ext']).get('expFieldGoalPct') is None), sum(1 for s in shots if s['expected_fg'] is None))
print('closestJoint', Counter(json.loads(s['ext'])['defensiveInfo'].get('closestJoint') for s in shots))
