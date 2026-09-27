#!/usr/bin/env python3
"""יוצר רילס אנכיים (1080x1920) עם כתוביות עבריות משיעור ביוטיוב.

שימוש:
    pip install yt-dlp imageio-ffmpeg
    python3 reels/make_reels.py            # כל הרילס
    python3 reels/make_reels.py 2 3        # רק רילס מספר 2 ו-3

הסקריפט מוריד את הסרטון ואת הכתוביות האוטומטיות, מאתר כל קטע לפי
משפט פתיחה ומשפט סיום, וחותך אותו לפורמט אנכי עם כותרת וכתוביות.
"""
import json
import re
import shutil
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

VIDEO_URL = "https://www.youtube.com/watch?v=e_omlrb8vFg"
HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
OUT = HERE / "out"
CREDIT = 'הרב חיים דרעי שליט"א'
FONT = "DejaVu Sans"

# כל רילס: כותרת, משפט פתיחה, משפט סיום. אפשר לקבע זמנים ידנית עם start/end בשניות.
# "after" = הקטע מתחיל אחרי המופע הזה של ביטוי (לדילוג על מופעים מוקדמים).
REELS = [
    {
        "slug": "each-one-alone",
        "title": "ביום הדין – כל אחד עובר לבד",
        "start": "אתם חושבים שרק אני צריך לומר",
        "end": "לא עובר עם התלמידים",
    },
    {
        "slug": "baal-shem-tov-horses",
        "title": "הסוסים של הבעל שם טוב",
        "start": "יודעים את הסיפור של הסוסים של הבעל שם טוב",
        "end": "אנחנו סוסים אנחנו לא מלאכים",
    },
    {
        "slug": "how-you-see-the-world",
        "title": "מה ההבדל בינינו לבין האור החיים?",
        "start": "השם זיכה אותי לקרוא את זה מילה במילה",
        "end": "הכל תלוי איך אתה רואה את העולם ואת החיים",
    },
    {
        "slug": "sin-changes-creation",
        "title": "כשאנחנו חוטאים – משנים את הבריאה",
        "start": "המחלות המלחמות הצרות",
        "end": "ושעה שעה",
    },
    {
        "slug": "shaliach-mitzva",
        "title": "שליח מצווה – אפילו יצר הרע בורח",
        "start": "כשבן אדם עושה מצווה הוא מתלבש באור השכינה",
        "end": "הכוח של שליח מצווה הוא חזק",
    },
    {
        "slug": "one-word-of-torah",
        "title": "מילה אחת של תורה מקיימת את כל העולם",
        "start": "כי לימוד התורה",
        "end": "מילה אחת אחת אחת",
    },
]

MAX_LEN = 180  # שניות


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def yt_dlp(*args):
    cmd = [sys.executable, "-m", "yt_dlp", VIDEO_URL, *args]
    cookies = WORK / "cookies.txt"  # יוטיוב חוסם שרתים ("not a bot") בלי עוגיות
    if cookies.exists():
        cmd += ["--cookies", str(cookies)]
    subprocess.run(cmd, check=True)


def download():
    WORK.mkdir(parents=True, exist_ok=True)
    video = WORK / "source.mp4"
    subs = WORK / "source.he.json3"
    if not video.exists():
        yt_dlp("-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
               "--merge-output-format", "mp4",
               "--ffmpeg-location", ffmpeg(),
               "-o", str(video))
    if not subs.exists():
        yt_dlp("--skip-download",
               "--write-subs", "--write-auto-subs", "--sub-langs", "he,iw",
               "--sub-format", "json3", "-o", str(WORK / "source"))
        found = sorted(WORK.glob("source.*.json3"))
        if not found:
            sys.exit("לא נמצאו כתוביות בעברית לסרטון")
        if found[0] != subs:
            found[0].rename(subs)
    return video, subs


def norm(word):
    word = re.sub(r"[֑-ׇ]", "", word)  # ניקוד וטעמים
    return re.sub(r"[^\w]", "", word)


def load_words(subs):
    """מחזיר רשימת (זמן התחלה, זמן סיום, מילה) מתוך קובץ json3."""
    data = json.loads(subs.read_text(encoding="utf-8"))
    words = []
    for ev in data.get("events", []):
        if "segs" not in ev:
            continue
        t0 = ev["tStartMs"]
        for seg in ev["segs"]:
            for w in seg.get("utf8", "").split():
                words.append([(t0 + seg.get("tOffsetMs", 0)) / 1000, None, w])
    for i, w in enumerate(words):
        nxt = words[i + 1][0] if i + 1 < len(words) else w[0] + 0.6
        w[1] = min(nxt, w[0] + 1.2)
    return words


def find_phrase(words, phrase, from_idx=0):
    target = [norm(w) for w in phrase.split()]
    n = len(target)
    tgt = " ".join(target)
    best, best_i = 0.0, None
    for i in range(from_idx, len(words) - n + 1):
        win = " ".join(norm(w[2]) for w in words[i:i + n])
        r = SequenceMatcher(None, win, tgt).ratio()
        if r > best:
            best, best_i = r, i
            if r == 1.0:
                break
    if best < 0.7:
        return None, None
    return best_i, best_i + n - 1


def ass_time(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(words, t0, t1, title, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{FONT},76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,2,8,70,70,260,177
Style: Cap,{FONT},70,&H0000E1FF,&H0000E1FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,2,2,70,70,430,177
Style: Credit,{FONT},46,&H00DDDDDD,&H00DDDDDD,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,1,2,70,70,150,177

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dur = t1 - t0
    lines = [
        f"Dialogue: 0,{ass_time(0)},{ass_time(dur)},Title,,0,0,0,,{title}",
        f"Dialogue: 0,{ass_time(0)},{ass_time(dur)},Credit,,0,0,0,,{CREDIT}",
    ]
    seg = [w for w in words if w[0] >= t0 - 0.05 and w[0] < t1]
    chunk = []
    for i, w in enumerate(seg):
        chunk.append(w)
        nxt = seg[i + 1] if i + 1 < len(seg) else None
        if (len(chunk) >= 4 or nxt is None or nxt[0] - w[1] > 0.7):
            s = chunk[0][0] - t0
            e = (nxt[0] if nxt and nxt[0] - w[1] <= 0.7 else w[1]) - t0
            text = " ".join(c[2] for c in chunk)
            lines.append(f"Dialogue: 1,{ass_time(s)},{ass_time(min(e, dur))},Cap,,0,0,0,,{text}")
            chunk = []
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def render(video, ass, t0, t1, out):
    vf = (
        "[0:v]split=2[a][b];"
        "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "gblur=sigma=30,eq=brightness=-0.15[bg];"
        "[b]scale=1080:-2[fg];"
        "[bg][fg]overlay=0:(H-h)/2,"
        f"ass='{ass.as_posix()}'[v]"
    )
    subprocess.run(
        [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{t0:.2f}", "-to", f"{t1:.2f}", "-i", str(video),
         "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         "-r", "30", str(out)],
        check=True,
    )


def main():
    pick = {int(a) for a in sys.argv[1:]}
    video, subs = download()
    words = load_words(subs)
    OUT.mkdir(parents=True, exist_ok=True)
    for n, reel in enumerate(REELS, 1):
        if pick and n not in pick:
            continue
        if "start_sec" in reel:
            t0, t1 = reel["start_sec"], reel["end_sec"]
        else:
            s_i, _ = find_phrase(words, reel["start"])
            if s_i is None:
                print(f"[{n}] לא נמצא משפט הפתיחה: {reel['start']}")
                continue
            _, e_i = find_phrase(words, reel["end"], s_i)
            if e_i is None:
                print(f"[{n}] לא נמצא משפט הסיום: {reel['end']}")
                continue
            t0 = max(words[s_i][0] - 0.3, 0)
            t1 = words[e_i][1] + 0.6
        if t1 - t0 > MAX_LEN:
            print(f"[{n}] הקטע ארוך מדי ({t1 - t0:.0f} שניות) – מקצר ל-{MAX_LEN}")
            t1 = t0 + MAX_LEN
        ass = WORK / f"reel-{n:02d}.ass"
        out = OUT / f"reel-{n:02d}-{reel['slug']}.mp4"
        build_ass(words, t0, t1, reel["title"], ass)
        render(video, ass, t0, t1, out)
        print(f"[{n}] {out.name}  {ass_time(t0)} → {ass_time(t1)}  ({t1 - t0:.0f} שניות)")


if __name__ == "__main__":
    main()
