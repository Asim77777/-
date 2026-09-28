"""Render the promo video frames from scene.html with headless Chromium and encode with ffmpeg.

Usage: python3 render.py [vertical|horizontal|all] [--preview T1,T2,...]
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
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
SIZES = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
NAMES = {"vertical": "promo-vertical-9x16.mp4", "horizontal": "promo-horizontal-16x9.mp4"}


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=HERE)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def ambient_pad(duration, path):
    """Soft A-minor pad: detuned sines with slow tremolo, echo and fades."""
    notes = [110.0, 164.81, 220.0, 261.63, 329.63]
    srcs = "".join(
        f"sine=f={f}:d={duration}[s{i}];sine=f={f * 1.003}:d={duration}[d{i}];"
        for i, f in enumerate(notes)
    )
    mix_in = "".join(f"[s{i}][d{i}]" for i in range(len(notes)))
    graph = (
        srcs
        + f"{mix_in}amix=inputs={2 * len(notes)}:normalize=1,"
        "tremolo=f=0.18:d=0.35,lowpass=f=1800,"
        "aecho=0.8:0.7:420|780:0.35|0.25,"
        f"afade=t=in:d=2.5,afade=t=out:st={duration - 3}:d=3,volume=14dB[a]"
    )
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-filter_complex", graph, "-map", "[a]",
         "-t", str(duration), "-ar", "48000", "-ac", "2", path],
        check=True,
    )


def render(fmt, preview=None):
    w, h = SIZES[fmt]
    httpd = serve()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/scene.html?format={fmt}"
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(url)
        total = page.evaluate("window.ready")
        if preview:
            for t in preview:
                page.evaluate(f"setTime({t})")
                page.screenshot(path=os.path.join(OUT, f"preview-{fmt}-{t:05.1f}.png"))
            browser.close()
            return total
        n = int(round(total * FPS))
        silent = os.path.join(OUT, f".{fmt}-video.mp4")
        enc = subprocess.Popen(
            [FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
             "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
            stdin=subprocess.PIPE,
        )
        for i in range(n):
            page.evaluate(f"setTime({i / FPS})")
            enc.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % 150 == 0:
                print(f"{fmt}: frame {i}/{n}", flush=True)
        enc.stdin.close()
        enc.wait()
        browser.close()
    audio = os.path.join(OUT, f".{fmt}-audio.m4a")
    ambient_pad(total, audio)
    final = os.path.join(OUT, NAMES[fmt])
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", final],
        check=True,
    )
    os.remove(silent)
    os.remove(audio)
    print("wrote", final)
    return total


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    preview = None
    if "--preview" in sys.argv:
        preview = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
    for fmt in (["vertical", "horizontal"] if which == "all" else [which]):
        print(fmt, "duration", render(fmt, preview))
