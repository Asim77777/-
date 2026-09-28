"""Render the 16:9 promo video from scene.html with headless Chromium and encode with ffmpeg.

Usage: python3 render.py [--preview T1,T2,...]
"""
import functools
import http.server
import os
import subprocess
import sys
import threading

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
W, H = 1920, 1080
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
FINAL = os.path.join(OUT, "promo-16x9.mp4")


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=HERE)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def soundtrack(duration, transitions, path):
    """Soft A-minor pad plus an airy filtered-noise swell on every transition."""
    notes = [110.0, 164.81, 220.0, 261.63, 329.63]
    parts = [f"sine=f={f}:d={duration}[s{i}];sine=f={f * 1.003}:d={duration}[d{i}];" for i, f in enumerate(notes)]
    mix_in = "".join(f"[s{i}][d{i}]" for i in range(len(notes)))
    parts.append(
        f"{mix_in}amix=inputs={2 * len(notes)}:normalize=1,"
        "tremolo=f=0.18:d=0.35,lowpass=f=1800,aecho=0.8:0.7:420|780:0.35|0.25,"
        f"afade=t=in:d=2.5,afade=t=out:st={duration - 3}:d=3,volume=14dB[pad];"
    )
    labels = ["[pad]"]
    for k, t in enumerate(transitions):
        start = max(0.0, t - 0.35)
        ms = int(start * 1000)
        parts.append(
            f"anoisesrc=d=1.6:c=pink:a=0.5:seed={k + 3},highpass=f=500,lowpass=f=3200,"
            "afade=t=in:d=0.55:curve=qsin,afade=t=out:st=0.55:d=1.05:curve=exp,"
            f"aecho=0.6:0.5:180:0.3,volume=-17dB,adelay={ms}|{ms},apad=whole_dur={duration}[w{k}];"
        )
        labels.append(f"[w{k}]")
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-filter_complex", "".join(parts), "-map", "[a]",
         "-t", str(duration), "-ar", "48000", "-ac", "2", path],
        check=True,
    )


def render(preview=None):
    httpd = serve()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/scene.html"
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(url)
        total = page.evaluate("window.ready")
        transitions = page.evaluate("window.TRANSITIONS")
        if preview:
            for t in preview:
                page.evaluate(f"setTime({t})")
                page.screenshot(path=os.path.join(OUT, f"preview-{t:05.2f}.png"))
            browser.close()
            return total
        n = int(round(total * FPS))
        silent = os.path.join(OUT, ".video.mp4")
        enc = subprocess.Popen(
            [FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
             "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
            stdin=subprocess.PIPE,
        )
        for i in range(n):
            page.evaluate(f"setTime({i / FPS})")
            enc.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % 300 == 0:
                print(f"frame {i}/{n}", flush=True)
        enc.stdin.close()
        enc.wait()
        browser.close()
    audio = os.path.join(OUT, ".audio.m4a")
    soundtrack(total, transitions, audio)
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", FINAL],
        check=True,
    )
    os.remove(silent)
    os.remove(audio)
    print("wrote", FINAL)
    return total


if __name__ == "__main__":
    preview = None
    if "--preview" in sys.argv:
        preview = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
    print("duration", render(preview))
