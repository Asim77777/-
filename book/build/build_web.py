"""Build the digital edition: sefer/index.html (title, contents, introduction), one page per drasha,
search.json (paragraph text without niqqud), shared sefer.css / sefer.js and the Culmus web fonts.

usage: python3 -I book/build/build_web.py [--only id,id]
"""
import argparse
import html
import json
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book as B  # noqa: E402

SITE = HERE.parents[1] / "sefer"
ICON_SEARCH = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>'
ICON_MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>'


def esc(s):
    return html.escape(s, quote=True)


def ts(sec):
    return B.fmt_ts(sec)


class Notes:
    """Footnote numbering per drasha, in Hebrew letters."""
    def __init__(self):
        self.items = []

    def add(self, label):
        self.items.append(label)
        return len(self.items)


def seg_html(sg, notes, did):
    t = sg["t"]
    if t == "text":
        return esc(sg["s"])
    if t == "quote":
        return f'"{esc(sg["s"])}"' if sg["marks"] else esc(sg["s"])
    if t == "fn":
        if sg.get("skip"):
            return ""
        n = notes.add(sg["show"])
        letter = B.heb_numeral(n, geresh=False)
        return (f'<span class="fn"><button type="button" aria-expanded="false" aria-label="מקור {letter}">{letter}</button>'
                f'<span class="pop" role="note">{esc(sg["show"])}</span></span>')
    if t == "unclear":
        return (f'<a class="unc" href="https://www.youtube.com/watch?v={did}&amp;t={sg["sec"]}s" data-seek="{sg["sec"]}" '
                f'title="מקום שלא נשמע היטב – האזנה מן הרגע {ts(sg["sec"])}">[?]</a>')
    if t == "note":
        return f'<span class="qahal">[{esc(sg["s"])}:]</span> '
    if t == "add":
        return f"[{esc(sg['s'])}]"
    return ""


def opening(html_text):
    """The first two words of a drasha in the red opening face."""
    m = re.match(r"^(\s*[^\s<]+\s+[^\s<]+)(\s|$)", html_text)
    if not m:
        return html_text
    return f'<span class="open">{m.group(1).strip()}</span>' + html_text[m.end(1):]


def paragraph_html(b, k, notes, did, first):
    """-> (html, plain text). A long quotation becomes a blockquote."""
    parts, cur, after_quote = [], [], False
    segs = b["segs"]
    i = 0
    while i < len(segs):
        sg = segs[i]
        if sg["t"] == "quote" and sg["long"]:
            if "".join(cur).strip():
                parts.append(("p", "".join(cur), after_quote))
            cur = []
            q = seg_html(sg, notes, did)
            if i + 1 < len(segs) and segs[i + 1]["t"] == "fn":
                q += seg_html(segs[i + 1], notes, did)
                i += 1
            if i + 1 < len(segs) and segs[i + 1]["t"] == "text":
                m = re.match(r"^\s*([.,;:]+)", segs[i + 1]["s"])
                if m:
                    q += m.group(1)
                    segs[i + 1] = dict(segs[i + 1], s=segs[i + 1]["s"][m.end():])
            parts.append(("q", q, False))
            after_quote = True
            i += 1
            continue
        cur.append(seg_html(sg, notes, did))
        i += 1
    if "".join(cur).strip():
        parts.append(("p", "".join(cur), after_quote))
    sec = b["anchor"]
    tbtn = f'<button type="button" class="t" data-seek="{sec}" aria-label="האזנה מן הרגע {ts(sec)}">{ts(sec)}</button>'
    out = []
    for j, (kind, h, aq) in enumerate(parts):
        pid = f' id="p{k}"' if j == 0 else ""
        if kind == "q":
            out.append(f'<blockquote{pid} data-t="{sec}">{h.strip()}</blockquote>')
            continue
        cls = []
        if first and j == 0:
            h = opening(h)
            cls.append("first")
        if aq:
            cls.append("after-quote")
        c = f' class="{" ".join(cls)}"' if cls else ""
        out.append(f'<p{pid}{c} data-t="{sec}">{tbtn if j == 0 else ""}{h.strip()}</p>')
    plain = B.strip_niqqud(re.sub(r"<span class=\"pop\"[^>]*>.*?</span>|<[^>]+>|\[\?\]|\d+:\d\d", "", "".join(h for _, h, _ in parts)))
    return "\n".join(out), html.unescape(re.sub(r"\s+", " ", plain)).strip()


def page(title, body, root="", here="", desc=""):
    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="preload" href="{root}fonts/taamey-frank.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}sefer.css">
</head>
<body data-root="{root}">
<header class="head">
  <div class="head-in">
    <a class="book" href="{root}index.html">{esc(B.BOOK_TITLE)}{(' <span class="here">/ ' + esc(here) + '</span>') if here else ''}</a>
    <button class="tool" type="button" data-act="search" aria-label="חיפוש בספר">{ICON_SEARCH}<span class="lbl">חיפוש</span></button>
    <button class="tool" type="button" data-act="smaller" aria-label="הקטנת האותיות">א־</button>
    <button class="tool" type="button" data-act="bigger" aria-label="הגדלת האותיות">א+</button>
    <button class="tool" type="button" data-act="theme" aria-label="מצב לילה">{ICON_MOON}</button>
  </div>
  <div class="search" id="search" role="search">
    <div class="search-in">
      <input id="q" type="search" placeholder="חיפוש מילה או ביטוי בכל הדרשות" aria-label="חיפוש בספר" autocomplete="off">
      <ul class="results" id="results" aria-live="polite"></ul>
    </div>
  </div>
</header>
<main>
{body}
</main>
<script src="{root}sefer.js"></script>
</body>
</html>
"""


def build(only=None):
    bk = B.load_book(only)
    L = bk["labels"]
    SITE.mkdir(exist_ok=True)
    for f in ("sefer.css", "sefer.js"):
        shutil.copy(HERE / "web" / f, SITE / f)
    flat = [d for s in bk["shaarim"] for d in s["drashot"]]
    search = []

    # ---- index: title page, contents, introduction ----
    toc = [f'<section class="toc" aria-labelledby="toc-h"><h2 id="toc-h">{esc(L["label-toc"])}</h2><span class="rule"></span>']
    for s in bk["shaarim"]:
        toc.append(f'<h3 class="shaar"><small>{esc(L["label-shaar"])} {esc(s["ordinal"])}</small>{esc(s["name"])}</h3><ol>')
        for d in s["drashot"]:
            toc.append(f'<li><a href="{d["id"]}.html"><span class="n">{d["num_heb"]}</span><span class="ttl">{esc(d["title"])}</span>'
                       f'<span class="d">{esc(L["label-said"])} {esc(d["date"])}</span></a></li>')
        toc.append("</ol>")
    toc.append("</section>")
    intro = ['<section class="intro">']
    first = True
    for b in bk["intro"]:
        h = "".join(seg_html(sg, Notes(), "") for sg in b["segs"])
        if b["type"] == "h":
            intro.append(f'<h2 class="first">{h}</h2><span class="rule"></span>' if first else f"<h2>{h}</h2>")
            first = False
        elif "הקוד שבסוף" not in B.strip_niqqud(h):   # the QR remark belongs to the printed edition
            intro.append(f"<p>{h}</p>")
    intro.append("</section>")
    title = (f'<section class="titlepage"><h1>{esc(bk["title_main"])}</h1><p class="by">{esc(bk["title_by"])}</p>'
             f'<span class="rule"></span><p class="sub">{esc(bk["subtitle"])}</p></section>')
    (SITE / "index.html").write_text(page(bk["title"], title + "\n".join(toc) + "\n".join(intro),
                                          desc=bk["subtitle"]), encoding="utf-8")

    # ---- one page per drasha ----
    for n, d in enumerate(flat):
        notes = Notes()
        body = []
        first = True
        k = 0
        for b in d["blocks"]:
            if b["type"] == "h":
                body.append(f'<h2>{"".join(seg_html(sg, notes, d["id"]) for sg in b["segs"])}</h2>')
                continue
            k += 1
            h, plain = paragraph_html(b, k, notes, d["id"], first)
            body.append(h)
            search.append({"d": d["id"], "i": k, "h": f'{d["num_heb"]} {d["title_plain"]}', "x": plain})
            first = False
        src = "".join(f'<li id="n{i}">{esc(x)}</li>' for i, x in enumerate(notes.items, 1))
        prev_d = flat[n - 1] if n else None
        next_d = flat[n + 1] if n + 1 < len(flat) else None
        nav = ['<nav class="next" aria-label="דרשות סמוכות">']
        nav.append(f'<a class="prev" href="{prev_d["id"]}.html"><small>הדרשה הקודמת</small>{esc(prev_d["title"])}</a>' if prev_d else "<span></span>")
        nav.append(f'<a class="fwd" href="{next_d["id"]}.html"><small>הדרשה הבאה</small>{esc(next_d["title"])}</a>' if next_d else "<span></span>")
        nav.append("</nav>")
        html_body = f"""<article>
<header class="opening">
  <div class="num">{esc(L["label-drasha"])} {d["num_heb"]}</div>
  <h1>{esc(d["title"])}</h1>
  <div class="said">{esc(L["label-said"])} {esc(d["date"])}</div>
  <span class="rule"></span>
</header>
<div class="video" data-id="{d["id"]}">
  <button type="button" class="poster" style="background-image:url(https://i.ytimg.com/vi/{d["id"]}/hqdefault.jpg)" aria-label="צפייה בדרשה"></button>
</div>
<div class="video-slot" aria-hidden="true"></div>
<div class="video-anchor"></div>
<div class="listen">
  <span>לחיצה על הזמן שליד פסקה משמיעה אותה מפי הרב; הפסקה הנשמעת מסומנת.</span>
  <label><input type="checkbox" id="follow" checked> גלילה עם ההקלטה</label>
</div>
<div class="text">
{chr(10).join(body)}
</div>
<section class="sources" aria-labelledby="src-h"><h3 id="src-h">מראי מקומות</h3><ol>{src}</ol></section>
{"".join(nav)}
</article>"""
        (SITE / f'{d["id"]}.html').write_text(page(f'{d["title_plain"]} – {bk["title"]}', html_body, here=d["num_heb"] + " " + d["title_plain"],
                                                   desc=f'{bk["title"]}: {d["title_plain"]}'), encoding="utf-8")
    (SITE / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{SITE}: index + {len(flat)} drashot, {len(search)} searchable paragraphs")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    build(a.only.split(",") if a.only else None)
