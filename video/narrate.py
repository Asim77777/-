"""Generate the Hebrew voice-over (Edge neural TTS, male voice) and lay it on the video at the scene times.

Usage: python3 narrate.py
Needs network access to speech.platform.bing.com. Output: out/promo-16x9-voice.mp4
"""
import asyncio
import os
import subprocess

import certifi
import imageio_ffmpeg

# the sandbox proxy re-signs TLS; point edge-tts at its CA bundle when present
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    certifi.where = lambda: "/root/.ccr/ca-bundle.crt"
import edge_tts  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = os.path.join(OUT, "promo-16x9.mp4")
FINAL = os.path.join(OUT, "promo-16x9-voice.mp4")
VOICE = "he-IL-AvriNeural"
TOTAL = 78.8

# (start second, latest end second, text) – matches the scenes in scene.html
LINES = [
    (0.6, 7.7, "שבעים פנים לתורה. לימוד תורה יומי – הכול במקום אחד, ובחינם."),
    (8.0, 20.8, "במסך הבית: שעון ותאריך עברי, חגים ומועדים, פרשת השבוע וההפטרה, פסוק יומי ללימוד – וזמני הדלקת נרות וצאת שבת לפי העיר שלכם."),
    (21.6, 32.3, "ועוד במסך הבית: צאת שבת לרבנו תם, חוקת יומא, רמב״ם היומי, הדף היומי ותהילים יומי – ומחשבה יומית מספרי המוסר."),
    (33.1, 41.4, "כל זמני היום ההלכתיים, מעלות השחר ועד סוף זמן תפילה – עם התראה לכל זמן שחשוב לכם."),
    (42.2, 57.5, "בלימוד הפסוק: כל פסוק בתורה בניקוד מלא, מאות מקורות קשורים, מבחר מפרשים ופירושים מלאים – ואפשר להוסיף חידוש או שאילתא משלכם, גם בהקלטה קולית."),
    (58.0, 67.0, "בסידור שלי: תפילת חול בנוסח עדות המזרח ובנוסח אשכנז, תפילות וברכות נוספות, וקיצור שולחן ערוך."),
    (67.3, 71.4, "הכול נגיש בלחיצה אחת מסרגל הניווט."),
    (71.9, 78.5, "שבעים פנים לתורה. האפליקציה חינמית – הצטרפו עכשיו!"),
]


def duration(path):
    err = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    h, m, s = err.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


async def synth(text, path, rate):
    # wss:// is not covered by HTTPS_PROXY in aiohttp, so pass the proxy explicitly
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    await edge_tts.Communicate(text, VOICE, rate=rate, proxy=proxy).save(path)


def main():
    tmp = os.path.join(OUT, ".vo")
    os.makedirs(tmp, exist_ok=True)
    clips = []
    for i, (start, end, text) in enumerate(LINES):
        path = os.path.join(tmp, f"{i}.mp3")
        rate = "-4%"
        asyncio.run(synth(text, path, rate))
        d = duration(path)
        room = end - start
        # speed up slightly (never more than +18%) only if a line would overrun its scene
        for pct in (0, 6, 12, 18):
            if d <= room:
                break
            rate = f"+{pct}%"
            asyncio.run(synth(text, path, rate))
            d = duration(path)
        print(f"line {i}: {d:.1f}s of {room:.1f}s (rate {rate})")
        clips.append((start, path))

    inputs, chains = [], []
    for k, (start, path) in enumerate(clips):
        inputs += ["-i", path]
        ms = int(start * 1000)
        chains.append(f"[{k + 1}:a]aresample=48000,adelay={ms}|{ms}[c{k}]")
    mix = "".join(f"[c{k}]" for k in range(len(clips)))
    graph = ";".join(chains) + f";{mix}amix=inputs={len(clips)}:normalize=0,apad=whole_dur={TOTAL},loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", VIDEO, *inputs, "-filter_complex", graph,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
         "-t", str(TOTAL), "-movflags", "+faststart", FINAL],
        check=True,
    )
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print("wrote", FINAL)


if __name__ == "__main__":
    main()
