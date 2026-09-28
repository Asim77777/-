"""Render the 16:9 promo video from scene.html with headless Chromium and encode with ffmpeg.

Usage: python3 render.py [--vertical] [--preview T1,T2,...]
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
VERTICAL = "--vertical" in sys.argv
W, H = (1080, 1920) if VERTICAL else (1920, 1080)
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
FINAL = os.path.join(OUT, "promo-9x16.mp4" if VERTICAL else "promo-16x9.mp4")


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=HERE)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def render(preview=None):
    httpd = serve()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/scene.html" + ("?format=vertical" if VERTICAL else "")
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(url)
        total = page.evaluate("window.ready")
        if preview:
            for t in preview:
                page.evaluate(f"setTime({t})")
                page.screenshot(path=os.path.join(OUT, f"preview-{'v' if VERTICAL else 'h'}-{t:05.2f}.png"))
            browser.close()
            return total
        n = int(round(total * FPS))
        silent = os.path.join(OUT, ".video.mp4")  # no audio track
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
    os.replace(silent, FINAL)
    print("wrote", FINAL)
    return total


if __name__ == "__main__":
    preview = None
    if "--preview" in sys.argv:
        preview = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
    print("duration", render(preview))
