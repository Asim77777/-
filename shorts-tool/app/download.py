"""Download a YouTube video with yt-dlp and extract audio for transcription."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


BROWSERS = ("chrome", "firefox", "edge", "brave", "safari", "opera")
STALL_SECONDS = 150  # no output from yt-dlp for this long = stuck
FORMAT = ("bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/"
          "b[ext=mp4][height<=1080]/bv*[height<=1080]+ba/b")


class Cancelled(Exception):
    pass


def _num(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return 0.0


def friendly_error(output: str) -> str:
    """Turn yt-dlp's last error line into something the user can act on."""
    errors = [ln for ln in output.splitlines() if ln.startswith("ERROR")]
    msg = errors[-1] if errors else output.strip()[-300:]
    if "Sign in to confirm" in msg or "cookies" in msg.lower():
        return ("יוטיוב דורש התחברות כדי להוריד את הסרטון. פתח 'הגדרות מתקדמות', בחר "
                "את הדפדפן שבו אתה מחובר ליוטיוב ונסה שוב - או העלה קובץ וידאו מהמחשב.")
    if "403" in msg or "Requested format is not available" in msg or "nsig" in msg:
        return ("יוטיוב חסם את ההורדה. עדכן את רכיב ההורדה (בטרמינל, בתיקיית הכלי: "
                ".venv/bin/pip install -U yt-dlp), ודא ש-Node.js מותקן, ונסה שוב. "
                "אפשר גם להעלות קובץ וידאו מהמחשב.")
    if "Private video" in msg or "unavailable" in msg.lower():
        return "הסרטון פרטי או לא זמין."
    if "Unsupported URL" in msg or "is not a valid URL" in msg:
        return "הקישור לא מזוהה כסרטון. ודא שהעתקת קישור מלא לסרטון."
    return msg.replace("ERROR: ", "")[:400] or "ההורדה נכשלה"


def download_video(url: str, out_dir: Path, on_progress=None,
                   cookies_browser: str = "", should_cancel=None) -> dict:
    """Download `url` into out_dir/source.mp4. Returns {title}.

    yt-dlp runs as a child process so a hung download can be killed: on cancel,
    or when it prints nothing for STALL_SECONDS.
    on_progress(fraction, text) gets a human-readable status line.
    """
    cmd = [
        sys.executable, "-m", "yt_dlp", "--no-playlist", "--newline", "--progress",
        "--no-simulate", "--no-warnings", "--socket-timeout", "20", "--retries", "3",
        "--fragment-retries", "3", "-f", FORMAT, "--merge-output-format", "mp4",
        "--print", "before_dl:TITLE %(title)s",
        "--progress-template",
        "download:PROG %(progress.downloaded_bytes)s %(progress.total_bytes)s "
        "%(progress.total_bytes_estimate)s %(progress.speed)s",
        "-o", str(out_dir / "source.%(ext)s"),
    ]
    # Recent YouTube needs a JS runtime; use node when deno is not installed.
    if not shutil.which("deno") and shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    if cookies_browser in BROWSERS:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd += ["--", url]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                            errors="replace")
    state = {"last": time.time(), "title": "", "log": []}
    streams = {"n": 0, "prev": 0.0}  # video then audio are separate downloads

    def reader():
        for line in proc.stdout:
            state["last"] = time.time()
            line = line.strip()
            if line.startswith("TITLE "):
                state["title"] = line[6:]
            elif line.startswith("PROG "):
                parts = line.split()
                done = _num(parts[1])
                total = _num(parts[2]) or _num(parts[3])
                speed = _num(parts[4]) if len(parts) > 4 else 0
                if done < streams["prev"]:
                    streams["n"] += 1
                streams["prev"] = done
                if on_progress:
                    text = f"מוריד {'שמע' if streams['n'] else 'וידאו'}: {done / 1e6:.0f}MB"
                    if total:
                        text += f" מתוך {total / 1e6:.0f}MB"
                    if speed:
                        text += f" · {speed / 1e6:.1f}MB לשנייה"
                    on_progress(min(done / total, 1.0) if total else 0.0, text)
            elif line:
                state["log"].append(line)
                if line.startswith("[Merger]") and on_progress:
                    on_progress(1.0, "מאחד וידאו ושמע")

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        while proc.poll() is None:
            time.sleep(0.5)
            if should_cancel and should_cancel():
                raise Cancelled()
            if time.time() - state["last"] > STALL_SECONDS:
                raise RuntimeError(
                    "ההורדה נתקעה ונעצרה. בדוק את חיבור האינטרנט, עדכן את רכיב ההורדה "
                    "(.venv/bin/pip install -U yt-dlp) ונסה שוב, או העלה קובץ מהמחשב.")
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        t.join(timeout=2)

    if proc.returncode != 0:
        raise RuntimeError(friendly_error("\n".join(state["log"])))

    src = out_dir / "source.mp4"
    if not src.exists():
        found = [p for p in out_dir.glob("source.*") if p.suffix not in (".part", ".ytdl")]
        if not found:
            raise RuntimeError("ההורדה נכשלה - לא נוצר קובץ וידאו")
        to_browser_mp4(found[0], src)
        found[0].unlink()
    return {"title": state["title"] or "video"}


def to_browser_mp4(src: Path, dst: Path) -> None:
    """Re-encode any video to H.264/AAC mp4 so it can be previewed."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-movflags", "+faststart", str(dst)],
        check=True,
    )


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise RuntimeError("בקובץ אין ערוץ וידאו")
    return {
        "duration": float(data["format"]["duration"]),
        "width": int(v["width"]),
        "height": int(v["height"]),
        "vcodec": v.get("codec_name"),
        "has_audio": any(s["codec_type"] == "audio" for s in data["streams"]),
    }


def extract_audio(video: Path, wav: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1",
         "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )
