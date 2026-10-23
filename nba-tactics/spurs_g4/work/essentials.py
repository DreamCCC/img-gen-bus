"""List / tar the small, hard-to-recreate files that git ignores: VO and audio wavs under film/audio, film/assets
(fonts, music), json in work dirs (tracks, players, cam, SAM tracks, VO manifests), repo-root *.wav in raw/.
usage: python essentials.py list | python essentials.py tar OUT.tar"""
import os
import sys
import tarfile
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\mgs-code-01")
G4 = ROOT / "nba-tactics/spurs_g4"
SKIP = {".venv", "node_modules", "__pycache__", "fr", "fxcache", "masks", "masks_hq", "masks_extra", "preview", "slow"}


def pick():
    out = []
    for base, keep in [(G4 / "film/audio", lambda f: True), (G4 / "film/assets", lambda f: True),
                       (G4 / "work", lambda f: f.suffix in {".json", ".txt", ".md"}),
                       (G4 / "film/work", lambda f: f.suffix in {".json", ".txt", ".md"})]:
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in SKIP and not d.startswith("_")]
            for fn in fns:
                f = Path(dp) / fn
                if fn != ".env" and keep(f):
                    out.append(f)
    return out


files = pick()
if sys.argv[1] == "list":
    tot = sum(f.stat().st_size for f in files)
    print(f"{len(files)} files, {tot / 1e6:.1f} MB")
    by = {}
    for f in files:
        k = f.relative_to(G4).parts[:2]
        by[k] = by.get(k, 0) + f.stat().st_size
    for k, v in sorted(by.items(), key=lambda x: -x[1])[:15]:
        print(f"  {v / 1e6:8.1f} MB  {'/'.join(k)}")
else:
    with tarfile.open(sys.argv[2], "w") as t:
        for f in files:
            t.add(f, arcname=f.relative_to(ROOT).as_posix())
    print("wrote", sys.argv[2], f"{Path(sys.argv[2]).stat().st_size / 1e6:.1f} MB")
