"""Concat s09 clips: hard cuts + 2-frame white flash, constant Q4 badge,
red tint after each miss, continuous original audio at render_play level.
usage: assemble.py <out.mp4>   (run from spurs_g4/)"""
import json, subprocess, sys, wave
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS, W, H = 30, 1920, 1080
OUT = Path(sys.argv[1])
TMP = Path("work/q4miss/asm"); TMP.mkdir(parents=True, exist_ok=True)
FONT = "../assets/fonts/BarlowCondensed-ExtraBold.ttf"
KEEP = (465, 945, 1465, 1060)
# ev, src audio start frame (segment a 'from'), red_on (s, clip-local)
CLIPS = [("554", 64, 1.3333 + 0.15), ("593", 66, 1.2 + 0.12), ("613", 104, 1.2667 + 0.5)]
FLASH = [0.78, 0.42]
SR = 48000


def read_frames(p):
    cap = cv2.VideoCapture(str(p)); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(f)
    return fr


def wav_mono(p, t0=None, dur=None):
    tmp = TMP / ("a_" + Path(p).stem + ".wav")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if t0 is not None: cmd += ["-ss", f"{t0:.4f}"]
    if dur is not None: cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-i", str(p), "-vn", "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", str(tmp)]
    subprocess.run(cmd, check=True)
    with wave.open(str(tmp)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, 2)


def badge():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 50)
    x, y = 130, 52
    tw = d.textlength("Q4: 4/19", font=f)
    d.rectangle([x, y, x + 12 + 22 + tw + 22, y + 66], fill=(12, 30, 66, 235))
    d.rectangle([x, y, x + 12, y + 66], fill=(200, 16, 46, 255))
    d.text((x + 12 + 22, y + 33), "Q4: 4/19", font=f, fill=(255, 255, 255, 255), anchor="lm")
    a = np.array(img).astype(np.float32)
    assert not a[860:, :, 3].any()
    return a[..., [2, 1, 0]], a[..., 3:] / 255


def tint_mask():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    m = 0.10 + 0.22 * np.clip(r, 0, 1) ** 1.5
    x1, y1, x2, y2 = KEEP; m[y1:y2, x1:x2] = 0
    return m[..., None]


def main():
    brgb, ba = badge(); tm = tint_mask(); red = np.array([40, 30, 215], np.float32)
    frames, audio = [], []
    for i, (ev, f0, red_on) in enumerate(CLIPS):
        fr = read_frames(f"film/out/s09/s09_{ev}.mp4")
        n = len(fr); last = i == len(CLIPS) - 1
        for k, f in enumerate(fr):
            t = k / FPS
            g = f.astype(np.float32)
            if t >= red_on:
                ramp = min(1.0, (t - red_on) * FPS / 4 + 0.25)
                g = g * (1 - tm * ramp) + red * tm * ramp
            frames.append(g)
        if not last:
            nxt = read_frames(f"film/out/s09/s09_{CLIPS[i + 1][0]}.mp4")[0].astype(np.float32)
            frames.append(frames[-1] * (1 - FLASH[0]) + 255 * FLASH[0])
            frames.append(nxt * (1 - FLASH[1]) + 255 * FLASH[1])
        dur = (n + (0 if last else len(FLASH))) / FPS
        src = wav_mono(f"work/q4miss/e{ev}.wav", f0 / FPS, dur)
        # match render_play's level on the speed-1 segment a
        ra = wav_mono(f"film/out/s09/s09_{ev}.mp4", 0, 0.6)
        sa = wav_mono(f"work/q4miss/e{ev}.wav", f0 / FPS, 0.6)
        gain = np.sqrt((ra ** 2).mean() / max((sa ** 2).mean(), 1e-12))
        need = int(round(dur * SR))
        src = np.pad(src, ((0, max(0, need - len(src))), (0, 0)))[:need] * gain
        fade = int(0.008 * SR); ramp = np.linspace(0, 1, fade)[:, None]
        src[:fade] *= ramp; src[-fade:] *= ramp[::-1]
        audio.append(src)
        print(ev, n, "frames", f"gain {20 * np.log10(gain):+.1f} dB")
    pcm = np.clip(np.concatenate(audio), -1, 1)
    with wave.open(str(TMP / "bed.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((pcm * 32767).astype(np.int16).tobytes())
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(TMP / "bed.wav"),
                          "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(OUT)],
                         stdin=subprocess.PIPE)
    for k, g in enumerate(frames):
        a = ba * min(1.0, (k + 1) / 6)
        g = g * (1 - a) + brgb * a
        p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    print(OUT, len(frames), "frames", f"{len(frames) / FPS:.3f}s")


main()
