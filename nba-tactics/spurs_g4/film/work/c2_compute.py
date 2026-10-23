"""C2 numbers: event 74 (Vassell 3PT) factor values, player dots, names.

Outputs film/work/c2_numbers.json, consumed (copied) into scenes/c2_xfg.json "shot".
Coordinates: NBA tracking inches, origin = center court, hoops at x = +/-501 in (41.75 ft).
The scene flips x so the attacked hoop is always at +x.
"""
import json, math
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'data'
OUT = Path(__file__).resolve().parent / 'c2_numbers.json'
shots = json.load(open(D / 'shot_detail.json', encoding='utf-8'))
pbp = json.load(open(D / 'pbp.json', encoding='utf-8'))
pbs = json.load(open(D / 'pbs.json', encoding='utf-8'))

names = {}
for p in pbs:
    x = json.loads(p['extend_info'])
    names[int(x['personId'])] = {'name': x['name'], 'last': x['familyName'], 'team': p.get('team_tricode') or p.get('team_abbreviation'),
                                 'jersey': x.get('jerseyNum')}
teams = {}
for p in pbs:
    for k in ('team_tricode', 'team_abbreviation', 'team_id'):
        if k in p:
            teams.setdefault(k, set()).add(p[k])
print('pbs team keys', {k: v for k, v in teams.items()})

EV = 74
s = next(s for s in shots if int(s['event_id']) == EV)
e = json.loads(s['ext'])
f = e['features']
pb = next(p for p in pbp if p['is_field_goal'] == '1' and int(p['action_number']) == EV)
pe = json.loads(pb['extend_info'])
sg = 1 if e['attackingPositiveX'] else -1
team_of = {}
for p in pbs:
    x = json.loads(p['extend_info'])
    team_of[int(x['personId'])] = int(p['team_id']) if 'team_id' in p else None

players = []
for pl in e['playersOnCourt']:
    pid = pl['nbaId']
    c = pl['centroid']
    players.append({'id': pid, 'last': names.get(pid, {}).get('last', str(pid)), 'team': 'SAS' if team_of.get(pid) == 1610612759 else 'NYK',
                    'x': round(sg * c[0] / 12, 3), 'y': round(sg * c[1] / 12, 3)})
shooter = next(p for p in players if p['id'] == e['shooterId'])
dfd = e['defensiveInfo']['jointDefenderId']
shooter_xy = (shooter['x'], shooter['y'])
geo_angle = math.degrees(math.atan2(abs(shooter_xy[1]), 41.75 - shooter_xy[0]))
geo_dist = math.hypot(41.75 - shooter_xy[0], shooter_xy[1])
res = {
    'event_id': EV, 'period': e['period'], 'clock': e['gameClockTime'], 'shot_clock': e['shotClockTime'],
    'pbp_description': pb['description'], 'pbp_score': f"SAS {pb['score_away']} - NYK {pb['score_home']}",
    'shooter_id': e['shooterId'], 'shooter': names[e['shooterId']]['name'], 'made': bool(int(s['success'])),
    'type': e['ngssEventInfo']['type'], 'qualifier': e['ngssEventInfo'].get('qualifier'), 'descriptor': e['ngssEventInfo'].get('descriptor'),
    'xfg': e['expFieldGoalPct'], 'xfg_row_expected_fg': s['expected_fg'],
    'shotDistance_ft': f['shotDistance'], 'release_shotDistance_ft': e['shotReleaseInfo']['shotDistance'],
    'shotAngleAbs_deg': f['shotAngleAbs'], 'geo_angle_from_centroid_deg': geo_angle, 'geo_dist_from_centroid_ft': geo_dist,
    'jointBallDistance_ft': f['jointBallDistance'], 'defensiveInfo_jointBallDistance_in': e['defensiveInfo']['jointBallDistance'],
    'closestJoint': e['defensiveInfo']['closestJoint'], 'defender_id': dfd, 'defender': names[dfd]['name'],
    'defHipDistance': f['defHipDistance'], 'pressureScore': f['pressureScore'],
    'ball_release_xy_ft': [round(sg * v / 12, 3) for v in e['shotReleaseInfo']['shotLocation']],
    'players': players, 'n_players_tracked': len(players),
}
for k, v in res.items():
    if k != 'players':
        print(k, '=', v)
for p in players:
    print(p)
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', OUT)

SCENE = Path(__file__).resolve().parents[1] / 'scenes' / 'c2_xfg.json'
cfg = json.load(open(SCENE, encoding='utf-8'))
cfg['shot'] = {
    'event_id': EV, 'clock': f"Q{e['period']} {e['gameClockTime']}", 'shooter_id': e['shooterId'], 'made': res['made'],
    'xfg_pct': round(100 * e['expFieldGoalPct']),
    'distance_ft': round(f['shotDistance'], 1),
    'defender_ft': round(f['jointBallDistance'], 1), 'defender': names[dfd]['last'], 'defender_id': dfd,
    'angle_deg': round(f['shotAngleAbs']),
    'players': players,
}
cfg['_sources'] = {
    'shot': 'data/shot_detail.json row event_id=74 (ext JSON). Shooter ext.shooterId=1630170 (Devin Vassell, pbs.json); made = row success=1 / pbp action 74 "Vassell 25\' 3PT Running Jump Shot", ext.ngssEventInfo.type=3pt, qualifier fastbreak.',
    'xfg_pct': 'ext.expFieldGoalPct = 0.41975 -> 42% (row expected_fg = 0.42).',
    'distance_ft': 'ext.features.shotDistance = 24.13 ft (equals shooter centroid in playersOnCourt to rim at (41.75 ft, 0); release-point distance ext.shotReleaseInfo.shotDistance = 24.44 ft).',
    'defender_ft': 'ext.features.jointBallDistance = 10.19 ft: closest joint of nearest defender to the ball; defender ext.defensiveInfo.jointDefenderId = 1628404 (Josh Hart), closestJoint = lPinky. (defensiveInfo.jointBallDistance = 121.5 in = 10.13 ft, measured slightly differently.)',
    'angle_deg': 'ext.features.shotAngleAbs = 64.27 deg: shooter position angle around the rim measured from the rim-to-midcourt center line (0 = straight on, 90 = along the baseline); matches atan2(|y|, 41.75 - x) of the shooter centroid within 0.4 deg median for 20+ ft shots (66.1 deg geometric here).',
    'players': 'ext.playersOnCourt[].centroid (inches, origin center court) / 12, flipped so the attacked hoop is +x (attackingPositiveX = true, so no flip). Only 7 of 10 players are present in the tracking snapshot (5 SAS, 2 NYK).',
    'names': 'data/pbs.json extend_info.familyName / team_id.',
}
json.dump(cfg, open(SCENE, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('updated', SCENE)
