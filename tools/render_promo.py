"""Render concept/promo.html to MP4: deterministic frames plus a synthesized soundtrack.

The sound is generated here with numpy, so the video carries no third-party music.
Cue times match the timeline in concept/promo.html (120 BPM, one beat = 0.5 s).

Usage: python tools/render_promo.py [--stills 1.2 4 8 ...]
"""
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "tools" / "frames"
OUT = ROOT / "assets" / "video" / "promo.mp4"
FPS, DUR, SR = 30, 20, 44100


def env(n, decay):
    return np.exp(-np.arange(n) / (SR * decay))


def add(buf, t, sig, gain=1.0):
    i = int(t * SR)
    end = min(len(buf), i + len(sig))
    buf[i:end] += sig[: end - i] * gain


def kick():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (48 * t + 22 * (1 - np.exp(-t * 30)))) * env(n, 0.09)


def click(seed):
    n = int(SR * 0.03)
    noise = np.random.default_rng(seed).standard_normal(n)
    return np.diff(noise, prepend=0) * env(n, 0.005)


def tone(freq, length, decay):
    n = int(SR * length)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)) * env(n, decay)


def whoosh(length):
    n = int(SR * length)
    noise = np.random.default_rng(7).standard_normal(n)
    smooth = np.convolve(noise, np.ones(24) / 24, mode="same")
    return smooth * np.sin(np.pi * np.arange(n) / n) ** 2 * 2.2


def soundtrack():
    buf = np.zeros(SR * DUR)
    for i, t in enumerate(np.arange(0, 2, 0.5)):
        add(buf, t, click(i), 0.5)
        add(buf, t, kick(), 0.8)
    for i, t in enumerate(np.arange(2, 3, 0.25)):
        add(buf, t, click(10 + i), 0.55)
        add(buf, t, kick(), 0.8)
    for i in range(14):                       # paper pile
        add(buf, 3.25 + i * 0.1, whoosh(0.16), 0.14)
    add(buf, 3.0, whoosh(2.0), 0.3)
    add(buf, 5.0, kick(), 1.0)                # Stop, then silence
    for t in np.arange(6, 17.5, 0.5):         # calm pulse
        add(buf, t, kick(), 0.42)
    notes = [392, 440, 494, 587, 659]
    for i, f in enumerate(notes):             # one tone per locked field
        add(buf, 7 + i * 0.5, tone(f, 0.5, 0.14), 0.22)
    add(buf, 6.5, whoosh(3.5), 0.05)
    add(buf, 10, tone(784, 1.2, 0.35), 0.2)
    for t, f in zip((12, 13, 14), (523, 659, 784)):
        add(buf, t, tone(f, 0.7, 0.2), 0.26)
        add(buf, t - 0.12, whoosh(0.26), 0.16)
    for f in (523, 659, 784):                 # payoff chord
        add(buf, 15.5, tone(f, 2.0, 0.6), 0.18)
        add(buf, 17.5, tone(f / 2, 2.4, 0.9), 0.18)
    add(buf, 17.5, kick(), 0.9)
    peak = np.max(np.abs(buf))
    return (buf / peak * 0.85 * 32767).astype(np.int16)


def write_wav(path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(soundtrack().tobytes())


def main():
    stills = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1:]] if "--stills" in sys.argv else None
    shutil.rmtree(FRAMES, ignore_errors=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.goto((ROOT / "concept" / "promo.html").as_uri())
        page.evaluate("document.fonts.ready")
        times = stills if stills else [i / FPS for i in range(FPS * DUR)]
        for i, t in enumerate(times):
            page.evaluate(f"seek({t})")
            page.screenshot(path=str(FRAMES / f"{i:04d}.jpg"), type="jpeg", quality=95)
        browser.close()
    if stills:
        return
    wav = FRAMES / "audio.wav"
    write_wav(wav)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(FRAMES / "%04d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", "-shortest", str(OUT)], check=True)
    print(OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
