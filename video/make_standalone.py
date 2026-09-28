"""Build a single self-contained HTML file (video embedded) with a clickable link at the end.

Usage: python3 make_standalone.py
Output: out/70-panim-latorah.html – can be sent as a file and opened in any browser.
"""
import base64
import os
import subprocess

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "promo-16x9-voice.mp4")  # narrated cut
OUT = os.path.join(HERE, "out", "70-panim-latorah.html")
TMP = os.path.join(HERE, "out", ".small.mp4")

# a lighter encode keeps the single file small enough to send
subprocess.run(
    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", SRC, "-c:v", "libx264", "-preset", "slow",
     "-crf", "25", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", TMP],
    check=True,
)
with open(TMP, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
os.remove(TMP)

html = open(os.path.join(HERE, "player.html"), encoding="utf-8").read()
html = html.replace('src="out/promo-16x9.mp4" ', "")
loader = (
    "<script>\n"
    "  // the video is embedded in this file, so it plays offline and can be sent as a single attachment\n"
    f"  const VIDEO_B64 = '{b64}';\n"
    "  (() => {\n"
    "    const bin = atob(VIDEO_B64), bytes = new Uint8Array(bin.length);\n"
    "    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);\n"
    "    document.getElementById('v').src = URL.createObjectURL(new Blob([bytes], { type: 'video/mp4' }));\n"
    "  })();\n"
    "</script>\n"
)
html = html.replace("</body>", loader + "</body>")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB")
