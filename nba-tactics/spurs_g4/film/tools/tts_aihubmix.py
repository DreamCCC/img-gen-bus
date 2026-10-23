"""English VO via AIHubMix /v1/audio/speech (Gemini 3.8 Flash TTS, gpt-4o-mini-tts). Key: AIHUBMIX_API_KEY in film/.env.

usage:
  python tools/tts_aihubmix.py audition out_dir [config.json]   # every candidate × every line, skips existing
  python tools/tts_aihubmix.py vo out_dir config.json            # production lines for render_play / timeline
audition config.json (all keys optional): {"base": "统一语气指令", "lines": [["L1", "text", "per-line direction"], ...],
                                  "cands": [["name", "model", "voice"], ...]}
Writes out_dir/<cand>/<line>.wav, out_dir/<cand>.wav (lines joined, 0.6 s gaps) and out_dir/ALL.wav
(candidates in order, each preceded by a 1.5 s gap). Gemini returns wav only and has no speed parameter:
prompting for pace barely works, so vo lines take a rubberband tempo factor instead.
vo config.json: {"model", "voice", "bases": {"name": "direction"},
                 "lines": [["id", "text", "per-line direction", tempo, "base name"], ...]}
Writes out_dir/<id>.wav (tempo applied, leading/trailing silence trimmed), out_dir/durations.json and
out_dir/lines.json ([{"id", "text"}], the format render_play's "vo.lines" reads). Delete a wav to regenerate it.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if "=" in l and not l.lstrip().startswith("#"))
URL = "https://aihubmix.com/v1/audio/speech"

BASE = ("You are an NBA broadcast analyst narrating a fast, cinematic breakdown video. Confident American male, "
        "chest voice, crisp consonants, punchy rhythm. Not a movie-trailer voice, not a news anchor.")
LINES = [
    ("L1", "Expected: forty-nine points. Actual: seventy.", "Measured, slight pause after each colon, land 'seventy' hard."),
    ("L2", "One screen, one switch — and the best rim protector in the league is guarding Brunson twenty-seven feet "
           "from the basket.", "Build speed through the sentence, pause at the dash, stress 'twenty-seven feet'."),
    ("L3", "Spurs up one. Thirteen seconds left. The shot clock is longer than the game.",
     "Low and tense, short sentences, almost a whisper on the last one."),
    ("L4", "Pinned.", "One explosive word, like a play-by-play call."),
    ("L5", "Tip. In.", "Two shouted words with a beat between them, crowd-eruption energy."),
]
CANDS = [
    ("g_Charon", "gemini-3.8-flash-tts", "Charon"),
    ("g_Fenrir", "gemini-3.8-flash-tts", "Fenrir"),
    ("g_Orus", "gemini-3.8-flash-tts", "Orus"),
    ("g_Algenib", "gemini-3.8-flash-tts", "Algenib"),
    ("g_Alnilam", "gemini-3.8-flash-tts", "Alnilam"),
    ("o_onyx", "gpt-4o-mini-tts", "onyx"),
    ("o_ash", "gpt-4o-mini-tts", "ash"),
]


def speak(out: Path, model: str, voice: str, text: str, direction: str, tries: int = 6) -> None:
    body = json.dumps({"model": model, "input": text, "voice": voice, "response_format": "wav",
                       "instructions": direction}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": "Bearer " + ENV["AIHUBMIX_API_KEY"].strip(),
                                                          "Content-Type": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if data[:4] == b"RIFF":
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_suffix(".raw.wav")
                tmp.write_bytes(data)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(out)],
                               check=True)
                tmp.unlink()
                return
            err = data[:200]
        except urllib.error.HTTPError as e:
            err = e.read()[:200]
        except (urllib.error.URLError, OSError) as e:
            err = repr(e)
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"{model}/{voice} failed: {err!r}")


def concat(parts: list[Path], out: Path, gap: float, lead: float = 0.0) -> None:
    sil = f"anullsrc=r=48000:cl=mono"
    args, n = ["ffmpeg", "-y", "-loglevel", "error"], 0
    chain = []
    for i, p in enumerate(parts):
        d = lead if i == 0 and lead else gap
        if d:
            args += ["-f", "lavfi", "-t", str(d), "-i", sil]
            chain.append(f"[{n}:a]"); n += 1
        args += ["-i", str(p)]
        chain.append(f"[{n}:a]"); n += 1
    args += ["-filter_complex", "".join(chain) + f"concat=n={n}:v=0:a=1[a]", "-map", "[a]", str(out)]
    subprocess.run(args, check=True)


def audition(out_dir: Path, cfg: dict) -> None:
    base, lines = cfg.get("base", BASE), [tuple(x) for x in cfg.get("lines", LINES)]
    cands = [tuple(x) for x in cfg.get("cands", CANDS)]
    jobs = [(out_dir / c / f"{lid}.wav", m, v, text, f"{base} {d}") for c, m, v in cands for lid, text, d in lines]
    with ThreadPoolExecutor(3) as ex:
        for f in [ex.submit(speak, o, m, v, t, d) for o, m, v, t, d in jobs if not o.exists()]:
            f.result()
    for c, _, _ in cands:
        concat([out_dir / c / f"{lid}.wav" for lid, _, _ in lines], out_dir / f"{c}.wav", 0.6)
    concat([out_dir / f"{c}.wav" for c, _, _ in cands], out_dir / "ALL.wav", 1.5, lead=0.3)
    print("candidates in ALL.wav:", ", ".join(c for c, _, _ in cands))


TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return round(float(out), 3)


def vo(out_dir: Path, cfg: dict) -> None:
    model, voice, bases = cfg["model"], cfg["voice"], cfg["bases"]
    raw = out_dir / "raw"
    jobs = [(raw / f"{lid}.wav", text, f"{bases[b]} {d}") for lid, text, d, _, b in cfg["lines"]]
    with ThreadPoolExecutor(3) as ex:
        for f in [ex.submit(speak, o, model, voice, t, d) for o, t, d in jobs if not o.exists()]:
            f.result()
    dur = {}
    for lid, _, _, tempo, _ in cfg["lines"]:
        out = out_dir / f"{lid}.wav"
        if not out.exists() or out.stat().st_mtime < (raw / f"{lid}.wav").stat().st_mtime:
            af = (f"rubberband=tempo={tempo}:transients=crisp:formant=preserved," if tempo != 1 else "") + TRIM
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw / f"{lid}.wav"), "-af", af,
                            "-ar", "48000", "-ac", "1", str(out)], check=True)
        dur[lid] = duration(out)
    (out_dir / "durations.json").write_text(json.dumps(dur, indent=1), encoding="utf-8")
    (out_dir / "lines.json").write_text(json.dumps([{"id": l[0], "text": l[1]} for l in cfg["lines"]],
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    for lid, d in dur.items():
        print(f"  {lid}  {d:5.2f}s")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("audition", "vo"):
        sys.exit(__doc__)
    cfg = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) > 3 else {}
    (audition if sys.argv[1] == "audition" else vo)(Path(sys.argv[2]), cfg)
