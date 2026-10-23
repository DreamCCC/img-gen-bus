"""C7 WHO'S OPEN data: positions at the e725 shot moment (Brunson's final 3, missed) + Anunoby's tip spot at e727.

Merges `data` + `_sources` into scenes/c7_lastplay.json (beats/sfx there are hand-tuned and preserved).
Same court frame as c4_data.py (attacking hoop at +x, no mirroring).
"""
import json

from c4_data import FILM, HOOP, dist, merge_scene, pbp_event, players, snapshot

FOX, WEMBY, BRUNSON, ANUNOBY = 1628368, 1641705, 1628973, 1628384


def main():
    info = players()
    row, ext, pos, plist, missing, d_hoop = snapshot(725, info)
    ev = pbp_event(725)
    tip_row, tip_ext, tip_pos, tip_plist, tip_missing, _ = snapshot(727, info)
    tip = pbp_event(727)
    fox_b = dist(pos[FOX], pos[BRUNSON])
    wem_b = dist(pos[WEMBY], pos[BRUNSON])
    spurs = [p for p in pos if info[p]['team'] == 'SAS']
    near = sorted((dist(pos[ANUNOBY], pos[q]), q) for q in spurs)
    nearest_d, nearest_id = near[0]
    anu_rim = dist(pos[ANUNOBY], HOOP)
    b_rim = dist(pos[BRUNSON], HOOP)
    tip_xy = tip_pos[ANUNOBY]

    data = dict(
        event_id=725, period=ext['period'], clock_tracking=ext['gameClockTime'], clock_pbp=ev['clock'],
        shot_clock=round(ext['shotClockTime'], 1), shot_distance=round(ext['features']['shotDistance'], 2),
        score=dict(sas=ev['sas'], nyk=ev['nyk']), pbp_desc=ev['desc'], hoop=list(HOOP),
        players=plist, missing=[dict(id=m, name=info[m]['last'].upper(), team=info[m]['team']) for m in missing],
        fox_brunson_ft=round(fox_b, 1), wemby_brunson_ft=round(wem_b, 1), brunson_rim_ft=round(b_rim, 1),
        anunoby_rim_ft=round(anu_rim, 1),
        nearest_spur=dict(name=info[nearest_id]['last'].upper(), ft=round(nearest_d, 1)),
        spurs_by_dist=[[info[q]['last'].upper(), round(d, 2)] for d, q in near],
        tip=dict(event_id=727, x=round(tip_xy[0], 2), y=round(tip_xy[1], 2), d_rim=round(dist(tip_xy, HOOP), 1),
                 clock=tip_ext['gameClockTime'], score=dict(sas=tip['sas'], nyk=tip['nyk']), desc=tip['desc'],
                 tracked=[p['name'] for p in tip_plist], missing=[info[m]['last'].upper() for m in tip_missing]),
        closest_def_joint=info[ext['defensiveInfo']['jointDefenderId']]['last'].upper(),
        closest_def_com=info[ext['defensiveInfo']['comDefenderId']]['last'].upper(),
    )
    sources = {
        'positions': 'data/shot_detail.json row event_id=725 (game 0042500404), ext.playersOnCourt[].centroid / 12 -> ft',
        'hoop': 'rim center (41.75, 0) ft; check |Brunson - hoop| = %.2f vs ext.features.shotDistance %.2f' % (d_hoop, ext['features']['shotDistance']),
        'fox_brunson_ft': 'hypot(Fox(1628368) - Brunson(1628973)) = %.3f ft; ext.defensiveInfo.comDefenderId = Fox' % fox_b,
        'wemby_brunson_ft': 'hypot(Wembanyama(1641705) - Brunson) = %.3f ft; ext.defensiveInfo.jointDefenderId = Wembanyama (closest joint %.2f ft from ball)'
                            % (wem_b, ext['defensiveInfo']['jointBallDistance'] / 12),
        'nearest_spur': 'min over TRACKED Spurs of hypot(Spur - Anunoby(1628384)): %s' % [[info[q]['last'], round(d, 3)] for d, q in near],
        'anunoby_rim_ft': 'hypot(Anunoby - hoop) = %.2f ft' % anu_rim,
        'tip_spot': 'shot_detail event_id=727 (Anunoby tip, made) shooter centroid / 12 = (%.2f, %.2f) ft; used only as the crash-arrow end point' % tip_xy,
        'clock': 'tracking ext.gameClockTime %s; pbp action 725 clock %s' % (ext['gameClockTime'], ev['clock']),
        'score': 'pbp 725: SAS %d NYK %d; pbp 727: SAS %d NYK %d' % (ev['sas'], ev['nyk'], tip['sas'], tip['nyk']),
        'lineup': 'pbs.json starters + every pbp substitution row before action 725 (by person_id)',
        'missing': [info[m]['name'] for m in missing],
    }
    merge_scene(FILM / 'scenes' / 'c7_lastplay.json', data, sources)
    print(json.dumps(data, indent=1))
    print(json.dumps(sources, indent=1))


if __name__ == '__main__':
    main()
