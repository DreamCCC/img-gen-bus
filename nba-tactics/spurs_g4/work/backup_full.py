"""Stream the whole repo (code, .git, raw media, work dirs, renders) as one tar over ssh, with a sha256 check.
Skips venvs, node_modules, __pycache__ and .env files. usage: python backup_full.py NAME"""
import hashlib
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\mgs-code-01")
HOST = "root@8.152.222.232"
DEST = "/root/backup/spurs_g4_film"
SKIP_DIRS = {".venv", "node_modules", "__pycache__"}
name = sys.argv[1]


class Tee:
    def __init__(self, f):
        self.f, self.h, self.n = f, hashlib.sha256(), 0

    def write(self, b):
        self.h.update(b)
        self.n += len(b)
        self.f.write(b)
        return len(b)


remote = (f"cat > {DEST}/{name}.part && sha256sum {DEST}/{name}.part | cut -d' ' -f1 > {DEST}/{name}.sha256 "
          f"&& cat {DEST}/{name}.sha256")
p = subprocess.Popen(["ssh", "-o", "BatchMode=yes", HOST, remote], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
tee = Tee(p.stdin)
t0, files, last = time.time(), 0, 0.0
with tarfile.open(fileobj=tee, mode="w|", bufsize=1 << 20) as tar:
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            if fn == ".env" or fn.startswith(".env."):
                continue
            fp = Path(dp) / fn
            try:
                tar.add(fp, arcname=fp.relative_to(ROOT.parent).as_posix(), recursive=False)
            except (FileNotFoundError, PermissionError) as e:
                print("skip", fp, e, flush=True)
                continue
            files += 1
            if time.time() - last > 30:
                last = time.time()
                print(f"{files} files, {tee.n / 1e9:.2f} GB, {tee.n / 1e6 / (last - t0):.1f} MB/s", flush=True)
p.stdin.close()
remote_sha = p.stdout.read().decode().strip()
rc = p.wait()
local_sha = tee.h.hexdigest()
print(f"done: {files} files, {tee.n / 1e9:.2f} GB in {(time.time() - t0) / 60:.1f} min, ssh rc {rc}")
print("local ", local_sha)
print("remote", remote_sha)
if rc == 0 and remote_sha == local_sha:
    subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"mv {DEST}/{name}.part {DEST}/{name} && ls -la {DEST}"], check=True)
    print("BACKUP_OK")
else:
    print("BACKUP_FAILED")
    sys.exit(1)
