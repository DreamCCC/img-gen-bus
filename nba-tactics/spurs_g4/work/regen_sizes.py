"""Size of regenerable data: extracted frame dirs (fr/), fxclip caches, model weights."""
import os
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\mgs-code-01")
fr = fx = pt = 0
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in {".venv", "node_modules", ".git"}]
    parts = Path(dp).parts
    n = sum((Path(dp) / f).stat().st_size for f in fns)
    if "fr" in parts:
        fr += n
    elif "fxcache" in parts:
        fx += n
    else:
        pt += sum((Path(dp) / f).stat().st_size for f in fns if f.endswith(".pt"))
print(f"fr/ frames {fr / 1e9:.2f} GB, fxcache {fx / 1e9:.2f} GB, model weights {pt / 1e9:.2f} GB")
