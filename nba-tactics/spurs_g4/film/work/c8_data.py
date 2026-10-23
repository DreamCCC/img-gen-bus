"""C8 lead-time data: how long each side led over the 2,880 regulation seconds, from data/pbp.json.

Writes film/work/c8_data.json (consumed by scenes/c8_lead.json).
State changes happen at the game clock of the scoring event (pbp `clock`, tenths in the last minute).
"""
import json
from pathlib import Path

from c1_data import fmt_clock, load_events, pretty, scoring_steps

OUT = Path(__file__).with_name('c8_data.json')
GAME = 2880.0


def main():
    ev = load_events()
    steps = scoring_steps(ev)
    clock_of = {}
    for e in ev:
        clock_of.setdefault((round(e['t'], 2), e['sas'], e['nyk']), (e['period'], e['clock'], e['desc']))

    segs = []
    for i, (t, s, n) in enumerate(steps):
        t1 = steps[i + 1][0] if i + 1 < len(steps) else GAME
        state = 'SAS' if s > n else 'NYK' if n > s else 'TIE'
        if t1 > t:
            if segs and segs[-1][2] == state:
                segs[-1][1] = t1
            else:
                segs.append([t, t1, state])
    tot = {k: round(sum(b - a for a, b, st in segs if st == k), 2) for k in ('SAS', 'NYK', 'TIE')}
    nyk_segs = [s for s in segs if s[2] == 'NYK']
    lead_changes = sum(1 for a, b in zip(segs, segs[1:]) if {a[2], b[2]} == {'SAS', 'NYK'} or
                       (a[2] == 'TIE' and False))

    print('segments:')
    for a, b, st in segs:
        print(f'  {a:8.2f} -> {b:8.2f}  {st}  ({b - a:.2f}s)')
    print('totals', tot, 'sum', sum(tot.values()))
    print('NYK lead segments', nyk_segs)
    print('last 14 score steps:')
    for t, s, n in steps[-14:]:
        p, c, d = clock_of[(round(t, 2), s, n)]
        print(f'  t={t:8.2f}  Q{p} {c}  SAS {s} - NYK {n}  {d}')

    nyk_info = []
    for a, b, _ in nyk_segs:
        start = next(e for e in ev if abs(e['t'] - a) < 1e-6 and e['nyk'] > e['sas'])
        nyk_info.append(dict(t0=a, t1=b, dur=round(b - a, 2), period=start['period'], clock=fmt_clock(start['clock']),
                             clock_raw=start['clock'], desc=start['desc'], score=f"NYK {start['nyk']}-{start['sas']}"))
    out = dict(game_s=GAME, totals=tot, segments=[[round(a, 2), round(b, 2), st] for a, b, st in segs],
               nyk_segments=nyk_info, final=dict(sas=steps[-1][1], nyk=steps[-1][2]))
    OUT.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(nyk_info, indent=1))
    write_scene(out, nyk_info, len(ev))


def clock_label(t):
    """4th-quarter clock at elapsed game second t, tenths under a minute."""
    left = round(GAME - t, 2)
    if left < 60:
        return f'0:{left:04.1f}'
    return f'{int(left // 60)}:{int(round(left % 60)):02d}'


def write_scene(out, nyk_info, n_events):
    root = Path(__file__).resolve().parents[2]
    scene = root / 'film' / 'scenes' / 'c8_lead.json'
    cfg = json.loads(scene.read_text(encoding='utf-8')) if scene.exists() else {}
    nyk_total = out['totals']['NYK']
    zoom0 = 2790.0
    assert all(s['t0'] >= zoom0 for s in nyk_info)
    cfg['data'] = dict(
        game_s=GAME,
        game_s_label=f'{int(GAME):,}',
        segments=out['segments'],
        nyk_total=nyk_total,
        nyk_total_int=str(int(nyk_total)),
        nyk_total_frac=f'.{round(nyk_total * 10) % 10}',
        nyk_segments=[dict(t0=s['t0'], t1=s['t1'], dur=f"{s['dur']:.1f}", range=f"{s['clock']} → {clock_label(s['t1']) if s['t1'] < GAME else '0:00'}")
                      for s in nyk_info],
        zoom_t0=zoom0,
        zoom_label=f'4TH QTR · LAST {clock_label(zoom0)}',
        final_nyk=out['final']['nyk'], final_sas=out['final']['sas'],
    )
    segs = '; '.join(f"{s['clock']} ({s['score']}, {s['desc']}) until {clock_label(s['t1']) if s['t1'] < GAME else 'the final horn'} = {s['dur']:.1f} s"
                     for s in nyk_info)
    cfg['_sources'] = {
        'all numbers': f'spurs_g4/data/pbp.json (game_id 0042500404, {n_events} events), computed by film/work/c8_data.py',
        'sides': 'SAS = score_away (extend_info.location "v"), NYK = score_home ("h")',
        'method': 'events sorted by order_number; elapsed = (period-1)*720 + (720 - clock); leader state changes at the '
                  'clock of each scoring event and holds until the next score change; regulation only (periods 1-4, no OT)',
        'NYK led': f'{nyk_total:.1f} s total = ' + segs,
        'totals': f"SAS led {out['totals']['SAS']:.1f} s, tied {out['totals']['TIE']:.1f} s, NYK led {nyk_total:.1f} s; sum {sum(out['totals'].values()):.1f} = 4 x 720",
        'final': f"NYK {out['final']['nyk']} - SAS {out['final']['sas']}",
        'render note': 'segments narrower than 3 px in the full-game view are drawn at 3 px so the 2.1-s sliver is visible',
    }
    order = ['_note', 'dur', 'vo_line', 'vo_offset', 'beats', 'sfx', 'data', '_sources']
    cfg = {k: cfg[k] for k in order if k in cfg} | {k: v for k, v in cfg.items() if k not in order}
    scene.write_text(pretty(cfg) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
