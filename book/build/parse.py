"""Parse an edited drasha markdown file into a simple structure used by all builders.

Markup conventions (see book/README.md):
  [[mm:ss]]      paragraph start time in the video (start of a paragraph)
  ## heading     editorial sub-heading (not the rabbi's words)
  {{ref}}        editorial source reference, e.g. {{במדבר יג, ב}}
  [?] / [?mm:ss] unclear words in the recording (link to the video at that time)
  [מן הקהל: ...], [שירה ...], [קטע לא תומלל ...], [צחוק], [שאלה מן הקהל:] ...  stage notes
  [word]         editorial completion of a word/letters the transcript dropped
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTE_PREFIXES = ("מן הקהל", "שאלה מן הקהל", "שירה", "קטע לא תומלל", "קדיש", "צחוק")

TOKEN_RE = re.compile(r"\{\{([^}]+)\}\}|\[\?(\d{1,3}:\d{2})?\]|\[([^\[\]]+)\]")


def to_seconds(ts):
    parts = [int(p) for p in ts.split(":")]
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fmt_ts(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_inline(text, para_sec):
    """Split paragraph text into typed segments."""
    out = []
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            out.append(("text", text[pos:m.start()]))
        ref, qts, br = m.groups()
        if ref is not None:
            out.append(("ref", ref.strip()))
        elif m.group(0).startswith("[?"):
            sec = to_seconds(qts) if qts else para_sec
            out.append(("unclear", sec))
        else:
            inner = br.strip()
            if inner.startswith(NOTE_PREFIXES):
                out.append(("note", inner))
            else:
                out.append(("add", inner))
        pos = m.end()
    if pos < len(text):
        out.append(("text", text[pos:]))
    return out


def parse_file(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    blocks = []
    last_sec = 0
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("## "):
            blocks.append({"type": "h", "text": chunk[3:].strip()})
            continue
        m = re.match(r"\[\[(\d{1,3}:\d{2})\]\]\s*", chunk)
        if m:
            last_sec = to_seconds(m.group(1))
            chunk = chunk[m.end():]
            sec = last_sec
        else:
            sec = None
        text = " ".join(l.strip() for l in chunk.splitlines())
        blocks.append({"type": "p", "sec": sec, "anchor_sec": last_sec,
                       "segs": parse_inline(text, last_sec)})
    meta["blocks"] = blocks
    return meta


def load_book(only_ids=None):
    """Return list of (theme_name, [drasha dicts]) in book order, for drashot that exist."""
    items = json.loads((ROOT / "data/drashot.json").read_text(encoding="utf-8"))
    themes = []
    num = 0
    for it in items:
        f = ROOT / "drashot" / f"{it['id']}.md"
        if not f.exists() or (only_ids and it["id"] not in only_ids):
            continue
        d = parse_file(f)
        d.update({"theme": it["theme"], "date": it["date"], "url": it["url"], "id": it["id"]})
        if not themes or themes[-1][0] != it["theme"]:
            themes.append((it["theme"], []))
        num += 1
        d["num"] = num
        themes[-1][1].append(d)
    return themes


def video_link(url, sec):
    return f"{url}&t={int(sec)}s"


HEB_NUM = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"]
HEB_TENS = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"]


def heb_number(n):
    """Hebrew numeral (1–99) with gershayim, e.g. 15 -> ט״ו."""
    if n == 15:
        s = "טו"
    elif n == 16:
        s = "טז"
    else:
        s = HEB_TENS[n // 10] + HEB_NUM[n % 10]
    return s + "׳" if len(s) == 1 else s[:-1] + "״" + s[-1]
