"""Objective report for a tts_audition run: ASR accuracy, pitch, range, speaking rate, quiet-vs-climax loudness.

usage:
  python tools/audition_report.py out/tts_doc audio/audition_doc.json [quiet_line_id] [climax_line_id]
Prints one row per candidate and writes out_dir/report.json. Numbers inform the pick; the user's ears decide.
"""
import difflib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vo_takes import asr, metrics, norm  # noqa: E402


def line_stats(p, text):
    y, sr = librosa.load(p, sr=16000)
    yt, _ = librosa.effects.trim(y, top_db=40)
    f0, vf, _ = librosa.pyin(yt, fmin=55, fmax=400, sr=sr, frame_length=1024)
    v = f0[vf]
    rms = librosa.feature.rms(y=yt, frame_length=512, hop_length=160)[0]
    db = 20 * np.log10(rms + 1e-6)
    heard = asr(p)
    return {"acc": round(difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio(), 3), "heard": heard,
            "rate": round(len(norm(text)) / (len(yt) / sr), 2), "loud": round(float(np.mean(db[db > db.max() - 30])), 1),
            "f0s": v.tolist(), **metrics(p)}


if __name__ == "__main__":
    out, cfg = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    lines = cfg["lines"]
    quiet = sys.argv[3] if len(sys.argv) > 3 else lines[-1][0]
    climax = sys.argv[4] if len(sys.argv) > 4 else lines[-2][0]
    cands = [c for c in (out / "ALL_order.txt").read_text().split() if not c.isdigit()]
    jobs = [(c, ln[0], ln[1]) for c in cands for ln in lines]
    with ThreadPoolExecutor(2) as ex:
        res = dict(zip([(c, lid) for c, lid, _ in jobs], ex.map(lambda j: line_stats(out / j[0] / f"{j[1]}.wav", j[2]), jobs)))
    rep = {}
    print(f"{'cand':16s} {'acc':>5s} {'f0':>6s} {'range':>6s} {'rate':>5s} {'dyn':>5s} {'bright':>6s} {'Q-C':>5s}  misheard")
    for c in cands:
        rs = [res[(c, ln[0])] for ln in lines]
        f0 = np.array(sum((r["f0s"] for r in rs), []))
        row = {"acc": round(min(r["acc"] for r in rs), 3), "f0": round(float(np.median(f0)), 1),
               "range": round(float(12 * np.log2(np.percentile(f0, 90) / np.percentile(f0, 10))), 1),
               "rate": round(float(np.mean([r["rate"] for r in rs])), 2), "dyn": round(float(np.mean([r["dyn"] for r in rs])), 1),
               "bright": round(float(np.mean([r["bright"] for r in rs])), 1),
               "q_minus_c": round(res[(c, quiet)]["loud"] - res[(c, climax)]["loud"], 1),
               "misheard": {ln[0]: r["heard"] for ln, r in zip(lines, rs) if r["acc"] < 0.95}}
        rep[c] = row
        print(f"{c:16s} {row['acc']:5.2f} {row['f0']:6.1f} {row['range']:6.1f} {row['rate']:5.2f} {row['dyn']:5.1f} {row['bright']:6.1f} {row['q_minus_c']:5.1f}  {row['misheard'] or ''}")
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
