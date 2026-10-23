"""C4 FIVE-OUT data: positions at the e676 shot moment (Brunson pull-up 3, Q4) from data/shot_detail.json.

Also holds the shared helpers used by c7_data.py (tracking snapshot, lineup reconstruction from pbp subs).
Merges `data` + `_sources` into scenes/c4_fiveout.json (beats/sfx in that file are hand-tuned and preserved).

Court frame: NBA tracking centroid inches, origin = center court -> /12 = feet. Both e676 and e725 attack the
+x hoop (verified: |shooter - (41.75, 0)| matches features.shotDistance), so no mirroring is applied.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILM = ROOT / 'film'
SHOTS = ROOT / 'data' / 'shot_detail.json'
PBP = ROOT / 'data' / 'pbp.json'
PBS = ROOT / 'data' / 'pbs.json'
GAME = '0042500404'
HOOP = (41.75, 0.0)  # rim center, ft: 47 ft half-length - 4 ft (backboard) - 1.25 ft (rim offset)


def players():
    out = {}
    for r in json.loads(PBS.read_text(encoding='utf-8')):
        e = json.loads(r['extend_info'])
        out[e['personId']] = dict(id=e['personId'], name=r['player_name'], last=e['familyName'], team=r['team_abbreviation'],
                                  starter=e.get('starter') == '1', jersey=e['jerseyNum'])
    return out


def shot(event_id):
    rows = [r for r in json.loads(SHOTS.read_text(encoding='utf-8')) if r['game_id'] == GAME and r['event_id'] == event_id]
    assert len(rows) == 1, (event_id, len(rows))
    return rows[0], json.loads(rows[0]['ext'])


def ft(c):
    return (c[0] / 12.0, c[1] / 12.0)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clock_s(c):
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', c)
    return int(m.group(1)) * 60 + float(m.group(2))


def pbp_rows():
    rows = [r for r in json.loads(PBP.read_text(encoding='utf-8')) if r.get('game_id') == GAME]
    rows.sort(key=lambda r: int(r['order_number']))
    return rows


def lineup_at(action_number, info):
    """On-court players just before pbp action `action_number`, from starters + every substitution row (in/out by person_id)."""
    on = {pid for pid, p in info.items() if p['starter']}
    assert len(on) == 10, on
    for r in pbp_rows():
        if int(r['action_number']) == action_number:
            break
        if r.get('action_type') != 'substitution':
            continue
        pid = int(r['person_id'])
        if r['sub_type'] == 'out':
            assert pid in on, ('sub out but not on court', r['action_number'], r['description'])
            on.discard(pid)
        elif r['sub_type'] == 'in':
            assert pid not in on, ('sub in but already on court', r['action_number'], r['description'])
            on.add(pid)
    return on


def pbp_event(action_number):
    r = next(r for r in pbp_rows() if int(r['action_number']) == action_number)
    return dict(clock=r['clock'], desc=r['description'], sas=int(r['score_away']), nyk=int(r['score_home']), team=r.get('team_tricode'))


def snapshot(event_id, info):
    row, ext = shot(event_id)
    pos = {}
    for p in ext['playersOnCourt']:
        pos[p['nbaId']] = ft(p['centroid'])
    shooter = ext['shooterId']
    d_hoop = dist(pos[shooter], HOOP)
    assert abs(d_hoop - ext['features']['shotDistance']) < 0.1, (d_hoop, ext['features']['shotDistance'])
    on = lineup_at(event_id, info)
    for pid in pos:
        assert pid in on, ('tracked player not in reconstructed lineup', pid)
    missing = sorted(on - set(pos), key=lambda p: info[p]['team'])
    plist = []
    for pid, (x, y) in pos.items():
        p = info[pid]
        plist.append(dict(id=pid, name=p['last'].upper(), full=p['name'], team=p['team'], x=round(x, 2), y=round(y, 2),
                          d_rim=round(dist((x, y), HOOP), 2)))
    plist.sort(key=lambda p: (p['team'], p['name']))
    return row, ext, pos, plist, missing, d_hoop


def merge_scene(path, data, sources):
    cfg = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    cfg['data'] = data
    cfg['_sources'] = sources
    s = json.dumps(cfg, indent=1, ensure_ascii=False)
    # keep short numeric lists ([x, y], [t, "sfx"]) on one line so the hand-tuned keys stay editable
    s = re.sub(r'\[\s*(-?[\d.]+(?:\s*,\s*(?:-?[\d.]+|"[a-z_]+"))*)\s*\]', lambda m: '[' + ', '.join(v.strip() for v in m.group(1).split(',')) + ']', s)
    path.write_text(s, encoding='utf-8')


def main():
    info = players()
    WEMBY, BRUNSON, TOWNS = 1641705, 1628973, 1626157
    row, ext, pos, plist, missing, d_hoop = snapshot(676, info)
    ev = pbp_event(676)
    prev = pbp_event(675)
    rim_r = 8.0
    in_zone = [dict(name=info[p]['last'].upper(), team=info[p]['team'], d=round(dist(pos[p], HOOP), 2))
               for p in pos if dist(pos[p], HOOP) <= rim_r]
    spurs_in_zone = [z for z in in_zone if z['team'] == 'SAS']
    wemby_rim = dist(pos[WEMBY], HOOP)
    wb = dist(pos[WEMBY], pos[BRUNSON])
    # nearest tracked Spur to each Knick, for context
    near = {}
    for p in pos:
        if info[p]['team'] != 'NYK':
            continue
        best = min((dist(pos[p], pos[q]), q) for q in pos if info[q]['team'] == 'SAS')
        near[info[p]['last'].upper()] = [info[best[1]]['last'].upper(), round(best[0], 2)]

    data = dict(
        event_id=676, period=ext['period'], clock_tracking=ext['gameClockTime'], clock_pbp=ev['clock'],
        shot_clock=round(ext['shotClockTime'], 1), shot_distance=round(ext['features']['shotDistance'], 2),
        score_before=dict(sas=prev['sas'], nyk=prev['nyk']), score_after=dict(sas=ev['sas'], nyk=ev['nyk']),
        pbp_desc=ev['desc'], hoop=list(HOOP), rim_zone_r=rim_r,
        players=plist, missing=[dict(id=m, name=info[m]['last'].upper(), team=info[m]['team']) for m in missing],
        wemby_rim_ft=round(wemby_rim, 1), wemby_brunson_ft=round(wb, 1),
        closest_def_joint=info[ext['defensiveInfo']['jointDefenderId']]['last'].upper(),
        closest_def_com=info[ext['defensiveInfo']['comDefenderId']]['last'].upper(),
        in_rim_zone=in_zone, spur_in_rim_zone=bool(spurs_in_zone),
        towns_rim_ft=round(dist(pos[TOWNS], HOOP), 1), nearest_spur=near,
    )
    sources = {
        'positions': 'data/shot_detail.json row event_id=676 (game 0042500404), ext.playersOnCourt[].centroid (inches, center-court origin) / 12 -> ft',
        'hoop': 'rim center (41.75, 0) ft by NBA geometry; check |Brunson - hoop| = %.2f vs ext.features.shotDistance %.2f' % (d_hoop, ext['features']['shotDistance']),
        'wemby_rim_ft': 'hypot(Wembanyama(1641705) - hoop) = %.2f ft' % wemby_rim,
        'wemby_brunson_ft': 'hypot(Wembanyama - Brunson(1628973)) = %.3f ft; ext.defensiveInfo.jointDefenderId = comDefenderId = 1641705' % wb,
        'rim_zone': '%.0f ft radius around hoop; tracked players inside: %s' % (rim_r, in_zone),
        'clock': 'tracking ext.gameClockTime %s (shot release); pbp action 676 clock %s' % (ext['gameClockTime'], ev['clock']),
        'score': 'pbp 675 -> 676: SAS %d NYK %d -> SAS %d NYK %d (score_away = SAS, score_home = NYK)' % (prev['sas'], prev['nyk'], ev['sas'], ev['nyk']),
        'lineup': 'pbs.json starters + every pbp substitution row before action 676 (by person_id); tracked players all in that lineup',
        'missing': [info[m]['name'] for m in missing],
    }
    merge_scene(FILM / 'scenes' / 'c4_fiveout.json', data, sources)
    print(json.dumps(data, indent=1))
    print(json.dumps(sources, indent=1))


if __name__ == '__main__':
    main()
