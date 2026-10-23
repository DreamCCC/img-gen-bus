"""C1 lead-collapse data: SAS-minus-NYK margin over the 48-minute game, from data/pbp.json.

Writes film/work/c1_data.json (consumed by scenes/c1_collapse.json).
SAS = away (score_away), NYK = home (score_home); verified via team_tricode + location in extend_info.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PBP = ROOT / 'data' / 'pbp.json'
OUT = Path(__file__).with_name('c1_data.json')


def pretty(o, ind=0):
    """JSON with dicts expanded one key per line and lists of scalars/short lists kept on one line."""
    pad = ' ' * (ind + 1)
    if isinstance(o, dict):
        if all(not isinstance(v, (dict, list)) for v in o.values()) and len(json.dumps(o)) < 110:
            return json.dumps(o, ensure_ascii=False)
        items = [f'{pad}{json.dumps(k)}: {pretty(v, ind + 1)}' for k, v in o.items()]
        return '{\n' + ',\n'.join(items) + '\n' + ' ' * ind + '}'
    if isinstance(o, list):
        if all(not isinstance(v, dict) for v in o):
            return '[' + ', '.join(json.dumps(v, ensure_ascii=False, separators=(', ', ': ')) for v in o) + ']'
        return '[\n' + ',\n'.join(pad + pretty(v, ind + 1) for v in o) + '\n' + ' ' * ind + ']'
    return json.dumps(o, ensure_ascii=False)


def clock_s(c):
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', c)
    return int(m.group(1)) * 60 + float(m.group(2))


def game_s(period, clock):
    """Elapsed game seconds (regulation only: 4 x 720)."""
    return (int(period) - 1) * 720 + (720 - clock_s(clock))


def fmt_clock(c):
    s = clock_s(c)
    m, r = divmod(s, 60)
    return f'{int(m)}:{r:04.1f}' if s < 60 else f'{int(m)}:{int(round(r)):02d}'


def load_events():
    rows = json.loads(PBP.read_text(encoding='utf-8'))
    rows = [r for r in rows if r.get('game_id') == '0042500404']
    rows.sort(key=lambda r: int(r['order_number']))
    ev = []
    for r in rows:
        ext = json.loads(r['extend_info'])
        ev.append(dict(
            period=int(r['period']), clock=r['clock'], t=game_s(r['period'], r['clock']),
            sas=int(r['score_away']), nyk=int(r['score_home']), desc=r['description'],
            team=r.get('team_tricode', ''), loc=ext.get('location'), order=int(r['order_number']),
            action=r.get('action_type', ''),
        ))
    return ev


def check_sides(ev):
    for e in ev:
        if e['team'] == 'SAS' and e['loc']:
            assert e['loc'] == 'v', e
        if e['team'] == 'NYK' and e['loc']:
            assert e['loc'] == 'h', e


def scoring_steps(ev):
    """List of (t, sas, nyk) where the score changes, in game order."""
    out = [(0.0, 0, 0)]
    for e in ev:
        if (e['sas'], e['nyk']) != out[-1][1:]:
            assert e['t'] >= out[-1][0] - 1e-9, (e, out[-1])
            out.append((e['t'], e['sas'], e['nyk']))
    return out


def margin_at(steps, t):
    m = 0
    for s in steps:
        if s[0] <= t:
            m = s[1] - s[2]
        else:
            break
    return m


def main():
    ev = load_events()
    check_sides(ev)
    periods = sorted({e['period'] for e in ev})
    steps = scoring_steps(ev)
    final = steps[-1]

    # Max SAS lead and the first moment it was reached
    best = max(steps, key=lambda s: (s[1] - s[2], -s[0]))
    max_lead = best[1] - best[2]
    hits = [s for s in steps if s[1] - s[2] == max_lead]
    first = hits[0]
    ev_first = next(e for e in ev if e['t'] == first[0] and (e['sas'], e['nyk']) == (first[1], first[2]))

    # Per-30s margin samples (end-of-bucket margin, i.e. the score at that game second) -> 96 bars
    step = 30
    bars = []
    for i in range(1, 2880 // step + 1):
        t = i * step
        bars.append(margin_at(steps, t - 1e-6) if t == 2880 else margin_at(steps, t))
    # Ensure peak bar shows the real max: use max margin within each bucket for SAS-side, min for NYK-side
    bars_ext = []
    for i in range(2880 // step):
        a, b = i * step, (i + 1) * step
        ms = [margin_at(steps, a)] + [s[1] - s[2] for s in steps if a < s[0] <= b]
        big = max(abs(v) for v in ms)
        bars_ext.append([v for v in ms if abs(v) == big][-1])

    peak_idx = next(i for i, v in enumerate(bars_ext) if v == max_lead)

    out = dict(
        game_id='0042500404',
        periods=periods,
        final=dict(sas=final[1], nyk=final[2]),
        max_lead=max_lead,
        max_lead_first=dict(period=ev_first['period'], clock=fmt_clock(ev_first['clock']), clock_raw=ev_first['clock'],
                            t=first[0], score=f"SAS {first[1]}-{first[2]} NYK", desc=ev_first['desc']),
        max_lead_all=[dict(t=s[0], sas=s[1], nyk=s[2]) for s in hits],
        bucket_s=step,
        bars=bars_ext,
        peak_idx=peak_idx,
        steps=[[round(s[0], 2), s[1], s[2]] for s in steps],
    )
    OUT.write_text(json.dumps(out, indent=1), encoding='utf-8')
    write_scene(out, ev)
    print('periods', periods, 'events', len(ev), 'score steps', len(steps))
    print('final SAS', final[1], 'NYK', final[2])
    print('max lead', max_lead, 'first at', out['max_lead_first'])
    print('all max-lead moments', out['max_lead_all'])
    print('peak bucket', peak_idx, 'bars', bars_ext)
    # quarter-end margins
    for q in range(1, 5):
        print('end Q', q, margin_at(steps, q * 720))


QTR = {1: '1ST QTR', 2: '2ND QTR', 3: '3RD QTR', 4: '4TH QTR'}


def clock_from_elapsed(t):
    left = 720 - (t - (int(t // 720)) * 720)
    return f'{int(left // 60)}:{int(round(left % 60)):02d}'


def write_scene(out, ev):
    """Merge computed numbers into scenes/c1_collapse.json, keeping hand-tuned beats/sfx."""
    scene = ROOT / 'film' / 'scenes' / 'c1_collapse.json'
    cfg = json.loads(scene.read_text(encoding='utf-8')) if scene.exists() else {}
    m = out['max_lead_first']
    second = out['max_lead_all'][1:]
    cfg['data'] = dict(
        bucket_s=out['bucket_s'],
        bars=out['bars'],
        peak_idx=out['peak_idx'],
        peak_idx_all=[i for i, v in enumerate(out['bars']) if v == out['max_lead']],
        max_lead=out['max_lead'],
        peak_label=f"{QTR[m['period']]} · {m['clock']}",
        peak_score=f"SAS {m['score'].split()[1]}",
        final_sas=out['final']['sas'], final_nyk=out['final']['nyk'],
        final_margin=out['final']['sas'] - out['final']['nyk'],
    )
    cfg['_sources'] = {
        'all numbers': 'spurs_g4/data/pbp.json (game_id 0042500404), computed by film/work/c1_data.py',
        'sides': 'SAS = score_away (extend_info.location "v"), NYK = score_home ("h")',
        'game time': 'elapsed = (period-1)*720 + (720 - clock), events sorted by order_number',
        'bars': '96 bars x 30 s; each bar = the SAS-minus-NYK margin with the largest |value| inside its 30-s window '
                '(ties -> later value), so the +29 peak and the closing -1 both show',
        'max_lead': f"+{out['max_lead']}: first at {QTR[m['period']]} {m['clock']} ({m['score']}, {m['desc']}); "
                    + '; '.join(f"reached again at {QTR[int(s['t'] // 720) + 1]} {clock_from_elapsed(s['t'])} "
                                f"(SAS {s['sas']}-{s['nyk']}); callout shows the first" for s in second),
        'final': f"SAS {out['final']['sas']} - NYK {out['final']['nyk']} (last scoring event: score_away/score_home)",
    }
    order = ['_note', 'dur', 'vo_line', 'vo_offset', 'beats', 'sfx', 'data', '_sources']
    cfg = {k: cfg[k] for k in order if k in cfg} | {k: v for k, v in cfg.items() if k not in order}
    scene.write_text(pretty(cfg) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
