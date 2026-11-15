"""Download a YouTube video with yt-dlp and extract audio for transcription."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


BROWSERS = ("chrome", "firefox", "edge", "brave", "safari", "opera")


def download_video(url: str, out_dir: Path, on_progress=None,
                   cookies_browser: str = "") -> dict:
    """Download `url` into out_dir/source.mp4. Returns {title, duration}."""
    import yt_dlp

    def hook(d):
        if on_progress and d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                on_progress(min(d.get("downloaded_bytes", 0) / total, 1.0))

    opts = {
        # H.264 + AAC so the browser can preview the source directly
        "format": (
            "bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/"
            "b[ext=mp4][height<=1080]/bv*[height<=1080]+ba/b"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "retries": 3,
    }
    # Recent YouTube needs a JS runtime; use node when deno is not installed.
    if not shutil.which("deno") and shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}

    if cookies_browser in BROWSERS:
        opts["cookiesfrombrowser"] = (cookies_browser,)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "Sign in to confirm" in msg or "cookies" in msg:
            raise RuntimeError(
                "יוטיוב דורש התחברות כדי להוריד את הסרטון. פתח 'הגדרות מתקדמות', "
                "בחר את הדפדפן שבו אתה מחובר ליוטיוב ונסה שוב - או העלה קובץ וידאו "
                "מהמחשב.") from exc
        raise

    src = out_dir / "source.mp4"
    if not src.exists():
        found = [p for p in out_dir.glob("source.*") if p.suffix != ".part"]
        if not found:
            raise RuntimeError("ההורדה נכשלה - לא נוצר קובץ וידאו")
        to_browser_mp4(found[0], src)
        found[0].unlink()
    return {"title": info.get("title") or "video", "duration": info.get("duration")}


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
