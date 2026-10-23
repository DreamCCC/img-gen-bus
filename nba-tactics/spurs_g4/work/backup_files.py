"""Upload individual files over ssh (cat >, no scp) and verify sha256. usage: python backup_files.py DEST_DIR file..."""
import hashlib
import subprocess
import sys
from pathlib import Path

HOST = "root@8.152.222.232"
dest, files = sys.argv[1], [Path(f) for f in sys.argv[2:]]
ok = True
for f in files:
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    rf = f"{dest}/{f.name}"
    with open(f, "rb") as fh:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"cat > '{rf}.part' && sha256sum '{rf}.part' | cut -d' ' -f1"],
                           stdin=fh, capture_output=True, text=True)
    remote = r.stdout.strip()
    if r.returncode == 0 and remote == h:
        subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"mv '{rf}.part' '{rf}'"], check=True, capture_output=True)
        print(f"OK   {f.name}  {f.stat().st_size / 1e6:.1f} MB  sha256 {h[:16]}")
    else:
        ok = False
        print(f"FAIL {f.name} rc={r.returncode}")
sys.exit(0 if ok else 1)
