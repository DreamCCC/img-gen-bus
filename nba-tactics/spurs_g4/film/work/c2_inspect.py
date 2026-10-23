import json, sys
from pathlib import Path

D = Path(__file__).resolve().parents[2] / 'data'
shots = json.load(open(D / 'shot_detail.json', encoding='utf-8'))
print('n shots', len(shots))
r = shots[0]
e = json.loads(r['ext'])


def walk(o, pre='', depth=0):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print('  ' * depth + f'{pre}{k}: {type(v).__name__}' + (f' len={len(v)}' if isinstance(v, list) else ''))
                if isinstance(v, list):
                    if v and isinstance(v[0], (dict, list)):
                        walk(v[0], '[0].', depth + 1)
                    else:
                        print('  ' * (depth + 1) + str(v)[:200])
                else:
                    walk(v, '', depth + 1)
            else:
                print('  ' * depth + f'{pre}{k} = {str(v)[:120]}')
    elif isinstance(o, list):
        print('  ' * depth + str(o)[:200])


walk(e)
print('---- event 74 ----')
for s in shots:
    if int(s['event_id']) == 74:
        for k, v in s.items():
            if k != 'ext':
                print(k, v)
        walk(json.loads(s['ext']))
