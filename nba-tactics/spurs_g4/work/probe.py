import json
import subprocess
import sys

for p in sys.argv[1:]:
    r = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p],
                                  capture_output=True, text=True).stdout)
    v = next(s for s in r["streams"] if s["codec_type"] == "video")
    a = [s for s in r["streams"] if s["codec_type"] == "audio"]
    print(f"{p:40s} {v['width']}x{v['height']} {v['r_frame_rate']:>8s} {float(r['format']['duration']):6.2f}s "
          f"frames={v.get('nb_frames')} audio={'yes' if a else 'no'}")
