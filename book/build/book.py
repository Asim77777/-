"""Load the vocalized book (build/.work/stage2) into one structure shared by the PDF, Word and web builders.

Stage-2 markup (produced by sefaria.py + niqqud.py):
  [[mm:ss]]           paragraph start time in the video
  ## heading          editorial sub-heading
  ⟦sefaria|text⟧      quotation, exact vocalized wording from Sefaria
  ⟦src|text⟧          quotation copied from an unvocalized Sefaria text (vocalized by the model, letters verified)
  ⟦=|text⟧            quotation whose source was not located
  ⟦~|text⟧            short repeat of a verse already cited (Sefaria wording; quote marks are in the text)
  {{=label}}          footnote (source reference)
  [?mm:ss]            unclear spot in the recording
  [מן הקהל:]          audience remark follows
  [word]              editorial completion
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
BOOK = HERE.parent
STAGE2 = BOOK / "vocalized"   # the vocalized text (output of niqqud.py), kept in git
NIQQUD = re.compile(r"[֑-ׇ]")

BOOK_TITLE = "דרשות הרב חיים דרעי שליט״א"
BOOK_TITLE_MAIN = "דרשות"
BOOK_TITLE_BY = "הרב חיים דרעי שליט״א"
BOOK_SUBTITLE = "שיחות ודרשות בתורה, באמונה ובעבודת ה׳"
BOOK_YEAR = "ה׳תשפ״ז"

ORDINALS = ["רִאשׁוֹן", "שֵׁנִי", "שְׁלִישִׁי", "רְבִיעִי", "חֲמִישִׁי", "שִׁשִּׁי", "שְׁבִיעִי", "שְׁמִינִי", "תְּשִׁיעִי", "עֲשִׂירִי"]

SEG_RE = re.compile(
    r"⟦(sefaria|src|=|~)\|([^⟧]*)⟧"      # 1,2 quotation
    r"|\{\{=([^}]*)\}\}"                 # 3 footnote
    r"|\[\?(\d{1,3}:\d{2})?\]"           # 4 unclear
    r"|\[(מן הקהל[^\]]*)\]"              # 5 audience
    r"|\[([^\[\]]+)\]"                   # 6 editorial completion
)
LONG_QUOTE_WORDS = 40


def to_sec(ts):
    sec = 0
    for p in ts.split(":"):
        sec = sec * 60 + int(p)
    return sec


def fmt_ts(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def strip_niqqud(s):
    """Remove niqqud (and te'amim); a maqaf becomes a space."""
    return NIQQUD.sub("", s.replace("־", " "))


def typo(s):
    """Typographic clean-up shared by all outputs."""
    s = s.replace("...", "…").replace(" - ", " – ")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def heb_numeral(n, geresh=True):
    ones = "אבגדהוזחט"
    tens = "יכלמנסעפצ"
    hund = "קרשת"
    out = ""
    while n >= 400:
        out += "ת"
        n -= 400
    if n >= 100:
        out += hund[n // 100 - 1]
        n %= 100
    if n == 15:
        out += "טו"
    elif n == 16:
        out += "טז"
    else:
        if n >= 10:
            out += tens[n // 10 - 1]
        if n % 10:
            out += ones[n % 10 - 1]
    if not geresh:
        return out
    return out + "׳" if len(out) == 1 else out[:-1] + "״" + out[-1]


def parse_inline(text, sec):
    segs, pos = [], 0
    for m in SEG_RE.finditer(text):
        if m.start() > pos:
            segs.append({"t": "text", "s": typo(text[pos:m.start()])})
        kind, q, fn, unc, note, add = m.groups()
        if kind:
            prev = segs[-1]["s"] if segs and segs[-1]["t"] == "text" else ""
            segs.append({"t": "quote", "s": typo(q), "kind": kind,
                         "marks": kind != "~" and not prev.rstrip().endswith(('"', "״")),
                         "long": kind in ("src", "sefaria") and len(q.split()) >= LONG_QUOTE_WORDS})
        elif fn is not None:
            segs.append({"t": "fn", "s": fn.strip()})
        elif m.group(0).startswith("[?"):
            segs.append({"t": "unclear", "sec": to_sec(unc) if unc else sec})
        elif note:
            segs.append({"t": "note", "s": note.strip().rstrip(":")})
        else:
            segs.append({"t": "add", "s": add.strip()})
        pos = m.end()
    if pos < len(text):
        segs.append({"t": "text", "s": typo(text[pos:])})
    return segs


def parse_body(body):
    blocks, last = [], 0
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = " ".join(l.strip() for l in chunk.strip().splitlines())
        if not chunk:
            continue
        if chunk.startswith("## "):
            blocks.append({"type": "h", "segs": parse_inline(chunk[3:].strip(), last)})
            continue
        m = re.match(r"\[\[(\d{1,3}:\d{2})\]\]\s*", chunk)
        sec = None
        if m:
            last = sec = to_sec(m.group(1))
            chunk = chunk[m.end():]
        blocks.append({"type": "p", "sec": sec, "anchor": last, "segs": parse_inline(chunk, last)})
    return blocks


def read_md(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    return meta, body


def number_footnotes(blocks):
    """Footnote policy of a printed sefer: a source is cited once per section (between sub-headings);
    further quotations from the same source in that section carry no new note."""
    seen = set()
    for b in blocks:
        if b["type"] == "h":
            seen = set()
            continue
        for sg in b["segs"]:
            if sg["t"] != "fn":
                continue
            if sg["s"] in seen:
                sg["skip"] = True
                continue
            seen.add(sg["s"])
            sg["show"] = sg["s"]


def titles():
    meta, body = read_md(STAGE2 / "titles.md")
    out = {}
    for b in parse_body(body):
        segs = [s for s in b["segs"] if s["t"] in ("text", "quote")]
        txt = "".join(s["s"] for s in segs).strip()
        m = re.match(r"\(([^)]+)\)\s*(.*)$", txt)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def load_book(only_ids=None):
    """-> dict(title, subtitle, year, intro_blocks, shaarim=[{index, name, ordinal, drashot=[…]}])."""
    items = json.loads((BOOK / "data" / "drashot.json").read_text(encoding="utf-8"))
    tt = titles()
    shaarim, num = [], 0
    for it in items:
        f = STAGE2 / f"{it['id']}.md"
        if not f.exists() or (only_ids and it["id"] not in only_ids):
            continue
        meta, body = read_md(f)
        blocks = parse_body(body)
        number_footnotes(blocks)
        num += 1
        d = {"id": it["id"], "num": num, "num_heb": heb_numeral(num), "url": it["url"], "date": meta.get("date", it["date"]),
             "title": tt.get(it["id"], meta["title"]), "title_plain": re.sub(r"⟦[^|⟧]*\||⟧|\{\{[^}]*\}\}|\"", "", strip_niqqud(meta["title"])),
             "blocks": blocks}
        ti = it["theme_index"]
        if not shaarim or shaarim[-1]["index"] != ti:
            shaarim.append({"index": ti, "name": tt.get(f"theme{ti}", it["theme"]), "name_plain": it["theme"],
                            "ordinal": ORDINALS[ti], "drashot": []})
        shaarim[-1]["drashot"].append(d)
    _, ibody = read_md(STAGE2 / "intro.md")
    return {"title": BOOK_TITLE, "title_main": BOOK_TITLE_MAIN, "title_by": BOOK_TITLE_BY, "subtitle": BOOK_SUBTITLE, "year": BOOK_YEAR, "labels": tt,
            "intro": parse_body(ibody), "shaarim": shaarim}



def export_json(path, only_ids=None):
    """Write the whole book (plus a QR image per drasha) as JSON for the Word builder (docx-js)."""
    import segno
    bk = load_book(only_ids)
    qr_dir = HERE / ".work" / "qr"
    qr_dir.mkdir(parents=True, exist_ok=True)
    for s in bk["shaarim"]:
        for d in s["drashot"]:
            png = qr_dir / f"{d['id']}.png"
            segno.make(d["url"], error="m").save(str(png), scale=10, border=2)
            d["qr"] = str(png)
    pathlib.Path(path).write_text(json.dumps(bk, ensure_ascii=False), encoding="utf-8")
    return bk

if __name__ == "__main__":
    b = load_book()
    for s in b["shaarim"]:
        print(s["ordinal"], s["name"])
        for d in s["drashot"]:
            fns = sum(1 for bl in d["blocks"] for sg in bl["segs"] if sg["t"] == "fn" and not sg.get("skip"))
            print("  ", d["num_heb"], d["title"], "| blocks", len(d["blocks"]), "| footnotes", fns)
