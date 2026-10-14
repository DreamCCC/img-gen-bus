"""Voice audition across Bailian TTS backends (qwen3-tts / CosyVoice / MiniMax). Key: DASHSCOPE_API_KEY in <项目根目录>/.env.

usage:
  python tools/tts_audition.py out_dir [config.json]   # every candidate × every test line, skips existing
config.json (all keys optional, defaults below are the NBA project):
  {"base": "统一语气指令", "lines": [["L03", "台词", "该句附加指令"], ...],
   "cands": [["名字", "backend", "voice"], ...],
   "designs": {"名字": ["qwen|cosy", "声音描述"]}, "preview": "声音设计试听句"}
  backend: qwen-i (instructions = base + 句指令) | qwen | minimax | qwen-audio-3.0-tts-plus (instruction 同 qwen-i)
           | qwen-vd / cosyvoice-v3.5-plus (声音设计音色) | 其他 CosyVoice 模型名
  designs 里的音色只创建一次（id 缓存在 out_dir/voices.json），自动加进候选。声音描述只写音色特征，不写真人。
  Test lines should include at least one climax line and one quiet line.
Writes out_dir/<cand>/<line>.wav, out_dir/<cand>.wav (lines joined) and out_dir/ALL.wav (candidates in order, 1.5 s gaps).
"""
import json
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts import ENV, synth as qwen_synth  # noqa: E402

BASE = "富有力量感和感染力的纪录片旁白，成熟男声，声音饱满、有胸腔共鸣，吐字有力，情绪真诚投入，不要播音腔。"
LINES = [
    ("L03", "而这颗球，第一次落在中国的地板上——是四十七年前。", "破折号处停顿，后半句放慢。"),
    ("L14", "二零零二年，那代人里，走出了一个巨人。", "逐渐升温，“巨人”两个字加重。"),
    ("L21", "詹姆斯来了，科比来了，库里来了。", "节奏紧凑，一句比一句更有力。"),
    ("L23", "然后，灯，灭了。", "压低声音，放慢，每个逗号都停顿。"),
]
CANDS = [
    ("q_Kai", "qwen-i", "Kai"),
    ("q_EldricSage", "qwen-i", "Eldric Sage"),
    ("q_Vincent", "qwen-i", "Vincent"),
    ("q_Moon", "qwen-i", "Moon"),
    ("q_Ryan", "qwen", "Ryan"),
    ("q_Andre", "qwen", "Andre"),
    ("c_longfei", "cosyvoice-v3-flash", "longfei_v3"),
    ("c_longsanshu", "cosyvoice-v3-flash", "longsanshu_v3"),
    ("c_longtian", "cosyvoice-v3-flash", "longtian_v3"),
    ("c_longxiaocheng", "cosyvoice-v2", "longxiaocheng_v2"),
    ("m_jingying", "minimax", "male-qn-jingying"),
    ("m_badao", "minimax", "male-qn-badao"),
    ("m_presenter", "minimax", "presenter_male"),
    ("m_audiobook2", "minimax", "audiobook_male_2"),
    ("m_executive", "minimax", "Chinese (Mandarin)_Reliable_Executive"),
    ("m_announcer", "minimax", "Chinese (Mandarin)_Male_Announcer"),
]


def to_wav(src_bytes, out, ext):
    tmp = Path(out).with_suffix("." + ext)
    tmp.write_bytes(src_bytes)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()


def cosy(out, model, voice, text, instruction=None):
    audio = SpeechSynthesizer(model=model, voice=voice, instruction=instruction).call(text)
    if not audio:
        raise RuntimeError(f"{voice}: empty audio")
    to_wav(audio, out, "mp3")


def minimax(out, voice, text, intensity=None, emotion=None):
    vs = {"voice_id": voice, "speed": 1.0, "vol": 1.0, "pitch": 0}
    if emotion:
        vs["emotion"] = emotion
    inp = {"text": text, "voice_setting": vs, "language_boost": "Chinese",
           "audio_setting": {"sample_rate": 44100, "format": "wav", "channel": 1}}
    if intensity is not None:
        inp["voice_modify"] = {"intensity": intensity}
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        data=json.dumps({"model": "MiniMax/speech-2.8-hd", "input": inp}).encode(),
        headers={"Authorization": f"Bearer {ENV['DASHSCOPE_API_KEY']}", "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    o = r.get("output", {})
    if o.get("base_resp", {}).get("status_code") != 0:
        raise RuntimeError(f"{voice}: {r}")
    to_wav(bytes.fromhex(o["data"]["audio"]), out, "src")


CUSTOM = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
PREVIEW = "詹姆斯来了！科比来了！库里来了！连乔丹，也来了！"


def post(body):
    req = urllib.request.Request(CUSTOM, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {ENV['DASHSCOPE_API_KEY']}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())


def design(name, kind, prompt, preview=None):
    """Create a designed voice (free) and return its id. CosyVoice ones are reused by prefix if they already exist."""
    preview = preview or PREVIEW
    prefix = name.replace("_", "")[:9]
    if kind == "qwen":
        r = post({"model": "qwen-voice-design", "input": {"action": "create", "target_model": "qwen3-tts-vd-2026-01-26",
                  "preferred_name": prefix, "voice_prompt": prompt, "preview_text": preview},
                  "parameters": {"sample_rate": 24000, "response_format": "wav"}})
        return r["output"]["voice"]
    lst = post({"model": "voice-enrollment", "input": {"action": "list_voice", "prefix": prefix, "page_index": 0, "page_size": 10}})
    ok = [v for v in lst["output"].get("voice_list", []) if v["status"] == "OK"]
    if ok:
        return ok[0]["voice_id"]
    r = post({"model": "voice-enrollment", "input": {"action": "create_voice", "target_model": "cosyvoice-v3.5-plus",
              "voice_prompt": prompt, "preview_text": preview, "prefix": prefix},
              "parameters": {"sample_rate": 24000, "response_format": "wav"}})
    return r["output"]["voice_id"]


def qwen_vd(out, voice, text):
    r = dashscope.MultiModalConversation.call(model="qwen3-tts-vd-2026-01-26", text=text, voice=voice)
    if r.status_code != 200:
        raise RuntimeError(f"{voice}: {r.code} {r.message}")
    tmp = Path(out).with_suffix(".src")
    urllib.request.urlretrieve(r.output["audio"]["url"], tmp)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(out)], check=True)
    tmp.unlink()


def one(job):
    cand, backend, voice, lid, text, delta = job
    out = Path(OUT) / cand / f"{lid}.wav"
    if out.exists():
        return cand, lid, "skip"
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            if backend == "qwen-i":
                qwen_synth(out, voice, text, BASE + delta)
            elif backend == "qwen":
                qwen_synth(out, voice, text, None)
            elif backend == "minimax":
                minimax(out, voice, text)
            elif backend == "qwen-vd":
                qwen_vd(out, voice, text)
            elif backend.startswith("qwen-audio"):
                cosy(out, backend, voice, text, BASE + delta)
            else:
                cosy(out, backend, voice, text)
            return cand, lid, "ok"
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if ("Throttling" in msg or "429" in msg) and attempt < 4:
                time.sleep(4 * (attempt + 1))
                continue
            return cand, lid, f"ERR {msg[:160]}"


def join(files, out, gap):
    sil = Path(OUT) / f"_sil{gap}.wav"
    if not sil.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(gap), str(sil)], check=True)
    lst = Path(out).with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(f).resolve()}'\nfile '{sil.resolve()}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-af", "loudnorm=I=-18:TP=-2", "-ar", "48000", str(out)], check=True)
    lst.unlink()


if __name__ == "__main__":
    OUT = sys.argv[1]
    if len(sys.argv) > 2:
        cfg = json.loads(Path(sys.argv[2]).read_text())
        BASE = cfg.get("base", BASE)
        LINES = [tuple(x) for x in cfg.get("lines", LINES)]
        CANDS = [tuple(x) for x in cfg.get("cands", CANDS)]
        PREVIEW = cfg.get("preview", PREVIEW)
        designs = cfg.get("designs", {})
    else:
        designs = {}
    dashscope.api_key = ENV["DASHSCOPE_API_KEY"]
    Path(OUT).mkdir(parents=True, exist_ok=True)
    vf = Path(OUT) / "voices.json"
    voices = json.loads(vf.read_text()) if vf.exists() else {}
    for name, (kind, prompt) in designs.items():
        if name not in voices:
            voices[name] = design(name, kind, prompt)
            vf.write_text(json.dumps(voices, ensure_ascii=False, indent=1))
            print("designed", name, voices[name], flush=True)
        CANDS.append((name, "qwen-vd" if kind == "qwen" else "cosyvoice-v3.5-plus", voices[name]))
    jobs = [(c, b, v, lid, t, d) for c, b, v in CANDS for lid, t, d in LINES]
    with ThreadPoolExecutor(2) as ex:
        for cand, lid, st in ex.map(one, jobs):
            if st != "skip":
                print(cand, lid, st, flush=True)
    done = []
    for c, _, _ in CANDS:
        files = [Path(OUT) / c / f"{lid}.wav" for lid, _, _ in LINES]
        if all(f.exists() for f in files):
            join(files, Path(OUT) / f"{c}.wav", 0.6)
            done.append(c)
    join([Path(OUT) / f"{c}.wav" for c in done], Path(OUT) / "ALL.wav", 1.5)
    (Path(OUT) / "ALL_order.txt").write_text("\n".join(f"{i+1:02d} {c}" for i, c in enumerate(done)) + "\n")
    print("joined:", " ".join(done))
