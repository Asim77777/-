#!/usr/bin/env python3
"""Build the vocalized drasha: text/*.txt -> drasha.html (two-pass TOC page numbers)."""
import html
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT_DIR = ROOT / "text"

TITLE_MAIN = "רְאֵה אָנֹכִי"
TITLE_SUB = "עַל סוֹד הַבְּחִירָה"
RUNNING = "רְאֵה אָנֹכִי · עַל סוֹד הַבְּחִירָה"

HEB = "א-ת"
MARKS = "֑-ׇ"


def hebrew_numeral(n: int) -> str:
    ones = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"]
    tens = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"]
    hundreds = ["", "ק", "ר", "ש", "ת"]
    s = hundreds[n // 100] if n >= 100 else ""
    n %= 100
    if n == 15:
        s += "טו"
    elif n == 16:
        s += "טז"
    else:
        s += tens[n // 10] + ones[n % 10]
    return s


def typo(s: str) -> str:
    """Hebrew typographic fixes: geresh / gershayim, qamatz qatan, NFC."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ׇ", "ָ")  # qamatz qatan -> qamatz (safer rendering)
    # gershayim inside known abbreviations
    for a, b in [('זַ"ל', "זַ״ל"), ('מוֹ"ר', "מוֹ״ר")]:
        s = s.replace(a, b)
    # geresh after a Hebrew letter (+marks): ה' -> ה׳, וְכוּ' -> וְכוּ׳
    s = re.sub(rf"(?<=[{HEB}{MARKS}])'", "׳", s)
    return s


def ref_text(s: str) -> str:
    s = s.strip().replace('"', "״").replace("'", "׳")
    return html.escape(s)


def inline(s: str) -> str:
    s = typo(s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\[\[(.+?)\]\]", r'<span class="q">"\1"</span>', s)
    s = re.sub(r"\{(.+?)\}", lambda m: f'<span class="ref">({ref_text(html.unescape(m.group(1)))})</span>', s)
    return s


def parse(text: str):
    """Return list of blocks: (kind, payload)."""
    blocks = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        lines = [l.rstrip() for l in chunk.strip().split("\n") if l.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("== "):
            blocks.append(("h2", first[3:].strip()))
        elif first.startswith("> "):
            body = " ".join(l[2:] for l in lines if l.startswith("> "))
            cite = next((l[3:] for l in lines if l.startswith(">> ")), "")
            blocks.append(("pasuk", (body, cite)))
        elif first.startswith("@ "):
            body = " ".join(l[2:] for l in lines if l.startswith("@ "))
            cite = next((l[3:] for l in lines if l.startswith("@@ ")), "")
            blocks.append(("akeida", (body, cite)))
        else:
            blocks.append(("p", " ".join(lines)))
    return blocks


ORN_SVG = (
    '<svg class="orn" viewBox="0 0 220 16" aria-hidden="true">'
    '<line x1="4" y1="8" x2="92" y2="8"/><line x1="128" y1="8" x2="216" y2="8"/>'
    '<path d="M110 1 L117 8 L110 15 L103 8 Z" class="fill"/>'
    '<circle cx="97" cy="8" r="1.6" class="fill"/><circle cx="123" cy="8" r="1.6" class="fill"/>'
    "</svg>"
)


def render_body(blocks, with_markers: bool):
    out = []
    headings = []
    after_h2 = False
    for kind, payload in blocks:
        if kind == "h2":
            idx = len(headings)
            headings.append(payload)
            marker = f'<span class="marker">QQH{idx:02d}QQ</span>' if with_markers else ""
            out.append(f'<section class="sec" id="s{idx}">{marker}{ORN_SVG}<h2>{inline(payload)}</h2>')
            after_h2 = True
            continue
        if kind == "p":
            content = inline(payload)
            if after_h2:
                content = re.sub(r"^(\S+)", r'<span class="lead">\1</span>', content, count=1)
                out.append(f'<p class="first">{content}</p>')
            else:
                cls = ' class="short"' if len(payload) < 420 else ""
                out.append(f"<p{cls}>{content}</p>")
        elif kind == "pasuk":
            body, cite = payload
            c = f"<cite>({ref_text(cite)})</cite>" if cite else ""
            out.append(f'<blockquote class="pasuk"><p>{inline(body)}</p>{c}</blockquote>')
        elif kind == "akeida":
            body, cite = payload
            c = f"<cite>({ref_text(cite)})</cite>" if cite else ""
            out.append(f'<div class="akeida"><p>{inline(body)}</p>{c}</div>')
        after_h2 = False
    # close sections: each h2 opened a <section>; close before next one
    html_out, open_sec = [], False
    for frag in out:
        if frag.startswith('<section class="sec"'):
            if open_sec:
                html_out.append("</section>")
            open_sec = True
        html_out.append(frag)
    if open_sec:
        html_out.append("</section>")
    return "\n".join(html_out), headings


def build(pages=None, with_markers=False):
    text = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(TEXT_DIR.glob("*.txt")))
    blocks = parse(text)
    body, headings = render_body(blocks, with_markers)
    toc_rows = []
    for i, h in enumerate(headings):
        num = hebrew_numeral(pages[i]) if pages else "—"
        toc_rows.append(
            f'<li><span class="t">{inline(h)}</span><span class="dots"></span><span class="n">{num}</span></li>'
        )
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    doc = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>ראה אנכי – על סוד הבחירה</title>
<link rel="stylesheet" href="fonts.css">
<style>{css}</style>
</head>
<body>
<div class="cover">
  <div class="frame">
    <div class="bsd">בס״ד</div>
    <div class="cover-inner">
      <div class="kicker">{typo("דְּרָשָׁה לְפָרָשַׁת רְאֵה")}</div>
      <h1>{typo(TITLE_MAIN)}</h1>
      <div class="sub">{typo(TITLE_SUB)}</div>
      {ORN_SVG}
      <div class="basis">{typo("עַל פִּי סֵפֶר עֲקֵדַת יִצְחָק")}</div>
    </div>
    <div class="cover-verse">
      <p>{inline("[[רְאֵה אָנֹכִי נֹתֵן לִפְנֵיכֶם הַיּוֹם בְּרָכָה וּקְלָלָה]] {דברים יא, כו}")}</p>
      <p>{inline("[[וּבָחַרְתָּ בַּחַיִּים]] {דברים ל, יט}")}</p>
    </div>
    <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
  </div>
</div>
<div class="toc">
  <div class="toc-title">{typo("תֹּכֶן הָעִנְיָנִים")}</div>
  {ORN_SVG}
  <ol>{''.join(toc_rows)}</ol>
</div>
<main>
{body}
<div class="end">{ORN_SVG}<div>{typo("תַּם וְנִשְׁלָם")}</div></div>
</main>
</body>
</html>
"""
    doc = doc.replace("__RUNNING__", typo(RUNNING))
    return doc, headings


if __name__ == "__main__":
    out = Path(sys.argv[1])
    pages = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] else None
    markers = len(sys.argv) > 3 and sys.argv[3] == "markers"
    doc, heads = build(pages, markers)
    out.write_text(doc, encoding="utf-8")
    print(len(heads), "sections")
