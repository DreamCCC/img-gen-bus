"""Probe what features.shotAngleAbs / shotDistance / jointBallDistance are measured against."""
import json, math
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'data'
shots = json.load(open(D / 'shot_detail.json', encoding='utf-8'))
rows = []
for s in shots:
    e = json.loads(s['ext'])
    f = e['features']
    hx = 501 if e['attackingPositiveX'] else -501
    sh = next((p['centroid'] for p in e['playersOnCourt'] if p['nbaId'] == e['shooterId']), None)
    loc = e['shotReleaseInfo']['shotLocation']
    out = {'ev': s['event_id'], 'abs': f.get('shotAngleAbs'), 'a2d': e['shotReleaseInfo'].get('shotAngle2D'),
           'fd': f.get('shotDistance'), 'rd': e['shotReleaseInfo'].get('shotDistance')}
    for name, pt in (('loc', loc), ('cen', sh)):
        if pt is None:
            continue
        dx, dy = pt[0] - hx, pt[1]
        out[name + '_d'] = math.hypot(dx, dy) / 12
        out[name + '_fromX'] = math.degrees(math.atan2(abs(dy), abs(dx)))  # 0 = straight on, 90 = baseline
        out[name + '_fromBase'] = 90 - out[name + '_fromX']
    out['jbd_ft'] = f.get('jointBallDistance')
    out['jbd_in'] = e['defensiveInfo'].get('jointBallDistance')
    out['row_jbd'] = s['joint_ball_distance']
    out['n_on'] = len(e['playersOnCourt'])
    rows.append(out)

for r in rows[:25]:
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})


def mae(a, b):
    xs = [abs(r[a] - r[b]) for r in rows if r.get(a) is not None and r.get(b) is not None]
    return sum(xs) / len(xs), max(xs)


for a, b in (('abs', 'loc_fromX'), ('abs', 'loc_fromBase'), ('abs', 'cen_fromX'), ('abs', 'cen_fromBase'), ('fd', 'cen_d'), ('rd', 'loc_d'), ('fd', 'loc_d')):
    print(a, b, 'MAE/max', [round(x, 3) for x in mae(a, b)])
print('a2d abs vs loc_fromX', mae('a2d', 'loc_fromX') if False else '')
xs = [abs(abs(r['a2d']) - r['loc_fromX']) for r in rows if r.get('a2d') is not None]
print('|a2d| vs loc_fromX', sum(xs) / len(xs), max(xs))
xs = [abs(r['jbd_ft'] * 12 - r['jbd_in']) for r in rows]
print('jbd ft*12 vs in: mean', sum(xs) / len(xs), 'max', max(xs))
print('row joint_ball_distance == defensiveInfo in:', all(abs(float(r['row_jbd']) - r['jbd_in']) < 1e-6 for r in rows))
print('players on court counts', sorted({r['n_on'] for r in rows}))
