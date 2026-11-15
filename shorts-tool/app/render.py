"""Cut a clip, reframe it to 9:16 and burn in the ASS subtitles with ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .subtitles import FONTS_DIR, H, W


def _filter_path(p: Path) -> str:
    """Escape a path for use inside an ffmpeg filter argument."""
    s = str(p).replace("\\", "/")
    return s.replace(":", "\\:").replace("'", "\\'")


def build_filter(crop: dict, ass_path: Path) -> str:
    mode = (crop or {}).get("mode", "fill")
    try:
        cx = max(0.0, min(1.0, float((crop or {}).get("x", 0.5))))
    except (TypeError, ValueError):
        cx = 0.5
    subs = f"ass='{_filter_path(ass_path)}':fontsdir='{_filter_path(FONTS_DIR)}'"
    if mode == "fit":
        return (
            f"[0:v]split[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},boxblur=24:4,eq=brightness=-0.12[bg];"
            f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,{subs}[v]"
        )
    return (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H}:(iw-{W})*{cx:.4f}:(ih-{H})/2,setsar=1,{subs}[v]"
    )


def render_clip(source: Path, out: Path, start: float, end: float, crop: dict,
                ass_path: Path, has_audio: bool = True, on_progress=None) -> None:
    duration = end - start
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-progress", "pipe:1", "-nostats",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source),
        "-filter_complex", build_filter(crop, ass_path), "-map", "[v]",
    ]
    if has_audio:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "160k"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        if on_progress and line.startswith("out_time_us="):
            try:
                done = int(line.split("=", 1)[1]) / 1e6
                on_progress(max(0.0, min(done / duration, 1.0)))
            except ValueError:
                pass
    err = proc.stderr.read() if proc.stderr else ""
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed: {err[-800:]}")
