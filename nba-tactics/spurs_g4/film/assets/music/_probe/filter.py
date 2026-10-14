import json
import sys

d = json.load(open(sys.path[0] + '/pieces.json'))
BAD = ('vocal', 'voice', 'choir', 'singer', 'sung')


def secs(p):
    try:
        h, m, s = map(int, p['length'].split(':'))
        return h * 3600 + m * 60 + s
    except Exception:
        return 0


def show(name, need, anyof, bpm=(0, 999), minlen=90, words=()):
    print('\n=====', name)
    for p in d:
        f = {x.strip() for x in (p.get('feel') or '').split(',')}
        ins = (p.get('instruments') or '').lower()
        if any(b in ins for b in BAD):
            continue
        try:
            b = int(p.get('bpm') or 0)
        except ValueError:
            b = 0
        if words and not any(w in ins for w in words):
            continue
        if need <= f and (not anyof or f & anyof) and bpm[0] <= b <= bpm[1] and secs(p) >= minlen:
            print(f"{p['title'][:34]:34s}|{p.get('bpm')!s:>4}|{p['length']}|{','.join(sorted(f))[:40]:40s}|"
                  f"{(p.get('instruments') or '')[:50]:50s}|{(p.get('description') or '')[:80]}")


show('S1 明亮推进', {'Bright'}, {'Driving', 'Grooving', 'Bouncy'}, (95, 135))
show('S2 不安收紧', {'Driving'}, {'Unnerving', 'Suspenseful', 'Mysterious'}, (90, 140))
show('S3 低沉压迫', {'Dark'}, {'Intense', 'Suspenseful', 'Driving'}, (0, 130), words=('synth', 'bass', 'drum', 'percussion', 'string', 'cello'))
show('S4 紧张稀疏', {'Suspenseful'}, {'Mysterious', 'Unnerving', 'Eerie'}, (0, 999))
show('S5 钢琴沉静', set(), {'Somber', 'Calming'}, (0, 999), words=('piano',))
show('S0 冷开场', {'Epic'}, {'Dark', 'Suspenseful', 'Intense'}, (0, 999))
