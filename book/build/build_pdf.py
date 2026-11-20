"""Build the print book (PDF) via HTML + Chromium, with a two-pass table of contents.

usage: python3 -I book/build/build_pdf.py [out.pdf]
"""
import pathlib
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse import load_book, heb_number  # noqa: E402
from render_html import BOOK_TITLE, BOOK_SUBTITLE, BOOK_SPAN, INTRO_HTML, esc, render_drasha  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
FONTS = HERE / "fonts"
FONT_URLS = {
    "FrankRuhlLibre-Regular.ttf": "https://fonts.gstatic.com/s/frankruhllibre/v23/j8_96_fAw7jrcalD7oKYNX0QfAnPcbzNEEB7OoicBw7FYVqQ.ttf",
    "FrankRuhlLibre-Bold.ttf": "https://fonts.gstatic.com/s/frankruhllibre/v23/j8_96_fAw7jrcalD7oKYNX0QfAnPcbzNEEB7OoicBw4iZlqQ.ttf",
    "Assistant-Regular.ttf": "https://fonts.gstatic.com/s/assistant/v24/2sDPZGJYnIjSi6H75xkZZE1I0yCmYzzQtuZnEGE.ttf",
    "Assistant-Bold.ttf": "https://fonts.gstatic.com/s/assistant/v24/2sDPZGJYnIjSi6H75xkZZE1I0yCmYzzQtgFgEGE.ttf",
}


def ensure_fonts():
    FONTS.mkdir(exist_ok=True)
    for name, url in FONT_URLS.items():
        f = FONTS / name
        if not f.exists():
            with urllib.request.urlopen(url, timeout=60) as r:
                f.write_bytes(r.read())


def font_css():
    u = lambda n: (FONTS / n).as_uri()  # noqa: E731
    return f"""
@font-face{{font-family:"FRL";src:url("{u('FrankRuhlLibre-Regular.ttf')}");font-weight:400}}
@font-face{{font-family:"FRL";src:url("{u('FrankRuhlLibre-Bold.ttf')}");font-weight:700}}
@font-face{{font-family:"AST";src:url("{u('Assistant-Regular.ttf')}");font-weight:400}}
@font-face{{font-family:"AST";src:url("{u('Assistant-Bold.ttf')}");font-weight:700}}
"""


PRINT_CSS = """
@page{size:170mm 240mm;margin:18mm 17mm 20mm 17mm}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font-family:"FRL",FreeSerif,serif;font-size:11.4pt;line-height:1.62;color:#1d1a17;direction:rtl}
a{color:inherit;text-decoration:none}
.page{break-after:page}
.cover{height:200mm;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}
.cover h1{font-size:34pt;line-height:1.25;margin:0 0 6mm}
.cover .rule{width:40mm;border-top:1.2pt solid #8a5a2b;margin:4mm auto}
.cover .sub{font-size:15pt;color:#444}
.cover .span{font-family:"AST",sans-serif;font-size:10pt;color:#666;margin-top:8mm}
h1.part{font-size:20pt;text-align:center;margin:0 0 8mm}
.intro{font-size:11pt;line-height:1.7}
.intro ul{padding-right:6mm}
.toc .tt{font-family:"AST",sans-serif;font-weight:700;color:#8a5a2b;margin:5mm 0 1.5mm;font-size:11pt}
.toc .row{display:flex;align-items:baseline;gap:2mm;font-size:10.8pt;margin:0 0 1.2mm}
.toc .row .n{color:#777;min-width:7mm}
.toc .row .t{flex:0 1 auto}
.toc .row .dots{flex:1 1 auto;border-bottom:1px dotted #999;transform:translateY(-1mm);min-width:5mm}
.toc .row .pg{font-family:"AST",sans-serif;min-width:8mm;text-align:left}
.theme-page{height:190mm;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;break-after:page}
.theme-page .lbl{font-family:"AST",sans-serif;font-size:12pt;color:#777;letter-spacing:.05em}
.theme-page h1{font-size:26pt;color:#8a5a2b;margin:3mm 0 0}
.drasha{break-before:page}
.dh{text-align:center;margin-bottom:6mm;padding-bottom:4mm;border-bottom:.6pt solid #c9b99f}
.dnum{font-family:"AST",sans-serif;font-size:10pt;color:#777}
.dtitle{font-size:18pt;line-height:1.35;margin:1.5mm 0 2mm}
.dmeta{font-family:"AST",sans-serif;font-size:8.6pt;color:#666;display:flex;flex-direction:column;gap:.5mm}
.dvideo{direction:ltr;unicode-bidi:embed}
.sh{font-family:"AST",sans-serif;font-size:12pt;color:#8a5a2b;margin:5mm 0 1.5mm;break-after:avoid}
p{margin:0 0 2.6mm;text-align:justify;orphans:2;widows:2}
.add{color:#8b6b49}
.unc{color:#b3541e;font-family:"AST",sans-serif;font-size:7.5pt;vertical-align:.3em;font-weight:700}
.ref{color:#4f6377;font-size:9.6pt}
.note{color:#5f6f4c;font-style:italic;font-size:10.2pt}
.mk{color:#fff;font-size:1pt;line-height:0}
.ts{display:none}
"""


def html_doc(body, title):
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f"<style>{font_css()}{PRINT_CSS}</style></head><body>{body}</body></html>")


def build_body(book, pages=None):
    pages = pages or {}
    toc = ['<div class="page toc"><h1 class="part">תוכן העניינים</h1>',
           f'<div class="row"><span class="t">פתח דבר ודרך העריכה</span><span class="dots"></span>'
           f'<span class="pg">{pages.get("intro", "000")}</span></div>']
    parts = []
    for ti, (theme, ds) in enumerate(book, 1):
        toc.append(f'<div class="tt">שער {heb_number(ti)} · {esc(theme)}</div>')
        parts.append(f'<div class="theme-page"><span class="mk">@@T{ti}@@</span>'
                     f'<div class="lbl">שער {heb_number(ti)}</div><h1>{esc(theme)}</h1></div>')
        for d in ds:
            toc.append(f'<div class="row"><span class="n">{heb_number(d["num"])}.</span><span class="t">{esc(d["title"])}</span>'
                       f'<span class="dots"></span><span class="pg">{pages.get(d["num"], "000")}</span></div>')
            parts.append(render_drasha(d, print_mode=True, marker=f"@@D{d['num']}@@"))
    toc.append("</div>")
    intro = f'<div class="page intro"><span class="mk">@@INTRO@@</span><h1 class="part">פתח דבר ודרך העריכה</h1>{INTRO_HTML}</div>'
    return "".join(toc) + intro + "".join(parts)


def find_markers(pdf_path):
    pages = {}
    for i, pg in enumerate(PdfReader(str(pdf_path)).pages, 1):
        txt = pg.extract_text() or ""
        for m in re.finditer(r"@@(D(\d+)|T\d+|INTRO)@?", txt):
            key = int(m.group(2)) if m.group(2) else ("intro" if m.group(1) == "INTRO" else m.group(1))
            pages.setdefault(key, i)
    return pages


def node_print(html_path, pdf_path, footer):
    cmd = ["node", str(HERE / "print_pdf.js"), str(html_path), str(pdf_path)] + (["--footer"] if footer else [])
    subprocess.run(cmd, check=True, cwd=str(HERE))


def build(out_pdf, only_ids=None):
    ensure_fonts()
    book = load_book(only_ids)
    work = HERE / ".work"
    work.mkdir(exist_ok=True)
    cover = (f'<div class="cover"><h1>{esc(BOOK_TITLE)}</h1><div class="rule"></div>'
             f'<div class="sub">{esc(BOOK_SUBTITLE)}</div><div class="span">{esc(BOOK_SPAN)}</div></div>')
    (work / "cover.html").write_text(html_doc(cover, BOOK_TITLE), encoding="utf-8")
    node_print(work / "cover.html", work / "cover.pdf", footer=False)

    (work / "body.html").write_text(html_doc(build_body(book), BOOK_TITLE), encoding="utf-8")
    node_print(work / "body.html", work / "body1.pdf", footer=True)
    pages = find_markers(work / "body1.pdf")
    missing = [d["num"] for _, ds in book for d in ds if d["num"] not in pages]
    assert not missing, f"markers not found for drashot {missing}"

    (work / "body.html").write_text(html_doc(build_body(book, pages), BOOK_TITLE), encoding="utf-8")
    node_print(work / "body.html", work / "body2.pdf", footer=True)
    pages2 = find_markers(work / "body2.pdf")
    assert pages2 == pages, "page numbers shifted between passes"

    w = PdfWriter()
    w.append(str(work / "cover.pdf"))
    w.append(str(work / "body2.pdf"))
    w.add_metadata({"/Title": BOOK_TITLE, "/Subject": BOOK_SUBTITLE})
    out_pdf = pathlib.Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as fh:
        w.write(fh)
    n = len(PdfReader(str(out_pdf)).pages)
    print("wrote", out_pdf, n, "pages; toc:", pages)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else REPO / "book/output/sefer.pdf")
