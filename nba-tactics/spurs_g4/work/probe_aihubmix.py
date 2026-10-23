import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = dict(l.split("=", 1) for l in Path("film/.env").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
KEY = ENV["AIHUBMIX_API_KEY"].strip()
out = Path("work/tts_probe")
out.mkdir(parents=True, exist_ok=True)


def post(path, body):
    req = urllib.request.Request("https://aihubmix.com" + path, data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


text = "Spurs up one. Thirteen seconds left. The shot clock is longer than the game."
for model, voice, fmt in [("gemini-3.8-flash-tts", "Charon", "wav"), ("qwen-audio-3.0-tts-plus", "Ethan", "wav"),
                          ("gpt-4o-mini-tts", "onyx", "wav")]:
    body = {"model": model, "input": text, "voice": voice, "response_format": fmt,
            "instructions": "NBA broadcast narrator, tense and controlled."}
    code, ct, data = post("/v1/audio/speech", body)
    if code == 200 and ct and ("audio" in ct or "octet" in ct):
        (out / f"{model}.{fmt}").write_bytes(data)
        print(model, "OK", ct, len(data), "bytes")
    else:
        print(model, code, ct, data[:300].decode("utf-8", "replace"))
