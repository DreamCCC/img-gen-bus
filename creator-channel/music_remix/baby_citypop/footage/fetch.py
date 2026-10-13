"""按 sources.json 从 YouTube 下载素材到 raw/<name>.mp4，同时把标题、频道、链接写进 raw/<name>.json（片尾出处用）。

python fetch.py [名字 ...]      已存在的跳过
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PY = HERE.parents[2] / "ep01_4.8pct/.venv/bin/python"
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)

want = set(sys.argv[1:])
for s in json.loads((HERE / "sources.json").read_text()):
    if want and s["name"] not in want:
        continue
    dst = RAW / f'{s["name"]}.mp4'
    if dst.exists():
        continue
    url = f'https://www.youtube.com/watch?v={s["id"]}'
    h = s.get("max_h", 1080)
    meta = subprocess.run([str(PY), "-m", "yt_dlp", "--socket-timeout", "30", "--print",
                           "%(title)s\t%(channel)s\t%(upload_date)s\t%(duration)s", "--skip-download", url],
                          capture_output=True, text=True)
    r = subprocess.run([str(PY), "-m", "yt_dlp", "--socket-timeout", "30", "-q", "--no-warnings",
                        "-f", f"bv*[height<={h}][vcodec^=avc1]+ba[ext=m4a]/bv*[height<={h}]+ba/b[height<={h}]/b",
                        "--merge-output-format", "mp4", "-o", str(dst), url], capture_output=True, text=True)
    if not dst.exists():
        print(s["name"], "FAIL", r.stderr.strip()[-300:], flush=True)
        continue
    title, channel, date, dur = (meta.stdout.strip().split("\t") + ["", "", "", ""])[:4]
    (RAW / f'{s["name"]}.json').write_text(json.dumps(dict(s, url=url, title=title, channel=channel, upload_date=date,
                                                           duration=dur), ensure_ascii=False, indent=1))
    print(s["name"], "ok", flush=True)
print("ALLDONE")
