"""Sizes of git-ignored / untracked top-level paths in the repo (skips venvs, node_modules)."""
import os
import subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\mgs-code-01")
SKIP = {".venv", "node_modules", "__pycache__", ".git"}
out = subprocess.run(["git", "status", "--ignored", "--porcelain", "-uall" if False else "-unormal"], cwd=ROOT,
                     capture_output=True, text=True, encoding="utf-8").stdout
rows = []
for line in out.splitlines():
    if not line.startswith(("!!", "??")):
        continue
    p = ROOT / line[3:].strip().strip('"')
    if any(part in SKIP for part in p.parts):
        continue
    n = 0
    if p.is_file():
        n = p.stat().st_size
    else:
        for dp, dns, fns in os.walk(p):
            dns[:] = [d for d in dns if d not in SKIP]
            n += sum((Path(dp) / f).stat().st_size for f in fns if (Path(dp) / f).exists())
    rows.append((n, line[:2], p.relative_to(ROOT).as_posix()))
for n, st, p in sorted(rows, reverse=True)[:40]:
    print(f"{n / 1e9:8.2f} GB {st} {p}")
print(f"TOTAL {sum(r[0] for r in rows) / 1e9:.2f} GB in {len(rows)} paths")
envs = [r[2] for r in rows if Path(r[2]).name.startswith(".env")]
print("env-like paths:", envs)
