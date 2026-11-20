"""Build the Word edition (RTL, Hebrew fonts, TOC field, page numbers, clickable links).

usage: python3 -I book/build/build_docx.py [out.docx]
"""
import pathlib
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse import load_book, heb_number, video_link, fmt_ts  # noqa: E402
from render_html import BOOK_TITLE, BOOK_SUBTITLE, BOOK_SPAN  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
FONT = "David"
UI_FONT = "Arial"
COL = {"add": "8B6B49", "unc": "B3541E", "ref": "4F6377", "note": "5F6F4C", "accent": "8A5A2B", "muted": "777777"}

INTRO = [
    ("p", "הספר שלפניכם נערך מתוך הדרשות המצולמות של הרב חיים דרעי שליט״א, כפי שהן מופיעות באתר השיעורים ובערוץ היוטיוב "
          "\"דרשות הרב חיים דרעי שליט״א\". כל פרק בספר הוא דרשה אחת, והדרשות מסודרות לפי שערים על פי נושאיהן."),
    ("p", "דרך העריכה: הטקסט הוא העתקה של הדברים כפי שנאמרו בעל פה, בלשון הדיבור, בלי תוספות, בלי השמטות ובלי סיכומים. "
          "התמלול נעשה מתוך התמלול האוטומטי של יוטיוב, ותוקנו בו רק שגיאות זיהוי ברורות. נוספו פיסוק וחלוקה לפסקאות."),
    ("p", "סימנים:"),
    ("li", [("add", "מילה"), ("text", " – מילה או אותיות שהושלמו על ידי העורך, במקום שבו ההקלטה לא נקלטה היטב.")]),
    ("li", [("unc_plain", "[?]"), ("text", " – מילים שלא ניתן היה לשחזר בוודאות מתוך ההקלטה. הסימן מקשר לרגע המדויק בסרטון.")]),
    ("li", [("ref", "במדבר יג, ב"), ("text", " – מראה מקום שהוסיף העורך.")]),
    ("li", [("note", "מן הקהל: …"), ("text", " – דברים שנאמרו מפי השומעים, והערות על המתרחש בשיעור.")]),
    ("li", [("text", "כותרות המשנה בתוך הדרשות נוספו על ידי העורך לנוחות הקורא, ואינן מדברי הרב.")]),
    ("p", "מי שמבקש לדייק בלשון הדברים מוזמן לצפות בדרשה עצמה דרך הקישור שבראש כל פרק."),
]


# ---------- low-level helpers ----------
def set_cs(rpr_parent, font=FONT, size=None, bold=None, color=None, italic=None):
    """Set complex-script (Hebrew) font properties on a run/style rPr."""
    rpr = rpr_parent.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(a), font)
    if bold is not None:
        for tag in ("w:b", "w:bCs"):
            el = rpr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                rpr.append(el)
            el.set(qn("w:val"), "1" if bold else "0")
    if italic is not None:
        for tag in ("w:i", "w:iCs"):
            el = rpr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                rpr.append(el)
            el.set(qn("w:val"), "1" if italic else "0")
    if color:
        el = rpr.find(qn("w:color"))
        if el is None:
            el = OxmlElement("w:color")
            rpr.append(el)
        el.set(qn("w:val"), color)
    if size:
        for tag in ("w:sz", "w:szCs"):
            el = rpr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                rpr.append(el)
            el.set(qn("w:val"), str(int(size * 2)))
    if rpr.find(qn("w:rtl")) is None:
        rpr.append(OxmlElement("w:rtl"))


def set_bidi(par_or_style):
    ppr = par_or_style._element.get_or_add_pPr() if hasattr(par_or_style, "_element") else par_or_style.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.insert(0, OxmlElement("w:bidi"))


def add_run(par, text, **kw):
    r = par.add_run(text)
    set_cs(r._r, **kw)
    return r


def add_link(par, url, text, color=COL["unc"], size=None, bold=False):
    rid = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    h.append(r)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)

    class _R:  # minimal adapter for set_cs
        def __init__(self, el):
            self.el = el

        def get_or_add_rPr(self):
            rpr = self.el.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                self.el.insert(0, rpr)
            return rpr

    set_cs(_R(r), font=FONT, size=size, bold=bold, color=color)
    par._p.append(h)


def add_field(par, instr, placeholder=""):
    r1 = OxmlElement("w:r")
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "begin")
    r1.append(fc)
    r2 = OxmlElement("w:r")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r2.append(it)
    r3 = OxmlElement("w:r")
    fc3 = OxmlElement("w:fldChar")
    fc3.set(qn("w:fldCharType"), "separate")
    r3.append(fc3)
    r4 = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = placeholder
    r4.append(t)
    r5 = OxmlElement("w:r")
    fc5 = OxmlElement("w:fldChar")
    fc5.set(qn("w:fldCharType"), "end")
    r5.append(fc5)
    for r in (r1, r2, r3, r4, r5):
        par._p.append(r)


def para(doc, style=None, align=None, space_after=None, keep_next=False, page_break=False):
    p = doc.add_paragraph(style=style)
    set_bidi(p)
    if align is None and style is None:
        align = WD_ALIGN_PARAGRAPH.JUSTIFY
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    if space_after is not None:
        pf.space_after = Pt(space_after)
    if keep_next:
        pf.keep_with_next = True
    if page_break:
        pf.page_break_before = True
    return p


# ---------- styles & layout ----------
def setup(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(17), Cm(24)
    sec.top_margin, sec.bottom_margin = Cm(1.9), Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.footer_distance = Cm(0.9)
    sp = sec._sectPr
    if sp.find(qn("w:bidi")) is None:
        sp.append(OxmlElement("w:bidi"))

    st = doc.styles
    normal = st["Normal"]
    normal.font.size = Pt(12)
    set_cs(normal.element, size=12)
    set_bidi(normal.element)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.3

    spec = {"Title": (28, True, None), "Heading 1": (22, True, COL["accent"]),
            "Heading 2": (17, True, "1D1A17"), "Heading 3": (13, True, COL["accent"])}
    for name, (size, bold, color) in spec.items():
        s = st[name]
        s.font.size = Pt(size)
        s.font.bold = bold
        if color:
            s.font.color.rgb = RGBColor.from_string(color)
        set_cs(s.element, size=size, bold=bold, color=color, font=FONT if name != "Heading 3" else UI_FONT)
        set_bidi(s.element)
        s.paragraph_format.space_before = Pt(10 if name == "Heading 3" else 0)
        s.paragraph_format.space_after = Pt(4)
        s.paragraph_format.keep_with_next = True
    for name in ("Heading 1", "Heading 2", "Title"):
        st[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_ppr = st["Title"].element.get_or_add_pPr()
    for bdr in title_ppr.findall(qn("w:pBdr")):
        title_ppr.remove(bdr)
    st["Title"].font.color.rgb = RGBColor.from_string("1D1A17")

    # page number footer
    fp = sec.footer.paragraphs[0]
    set_bidi(fp)
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(fp, "PAGE", "1")

    # ask Word to refresh fields (TOC, page numbers) on open
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)


def render_segs(p, segs, url):
    for kind, val in segs:
        if kind == "text":
            add_run(p, val)
        elif kind == "unclear":
            add_link(p, video_link(url, val), "[?]", size=8, bold=True)
        elif kind == "unc_plain":
            add_run(p, val, color=COL["unc"], size=8, bold=True)
        elif kind == "add":
            add_run(p, f"[{val}]", color=COL["add"])
        elif kind == "ref":
            add_run(p, f"[{val}]", color=COL["ref"], size=10.5)
        elif kind == "note":
            add_run(p, f"[{val}]", color=COL["note"], italic=True, size=11)


def build(out_path, only_ids=None):
    book = load_book(only_ids)
    doc = Document()
    setup(doc)

    # cover
    for _ in range(7):
        para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    p = para(doc, style="Title", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p, BOOK_TITLE, size=28, bold=True)
    p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p, BOOK_SUBTITLE, size=15, color="444444")
    p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_run(p, BOOK_SPAN, size=10, color=COL["muted"], font=UI_FONT)

    # TOC
    p = para(doc, style="Heading 1", page_break=True)
    add_run(p, "תוכן העניינים", size=20, bold=True, color="1D1A17")
    p = para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT)
    add_field(p, 'TOC \\o "1-2" \\h \\z \\u', "תוכן העניינים ייבנה אוטומטית בפתיחת הקובץ ב-Word (אם לא – לחצו כאן ואז F9)")

    # intro
    p = para(doc, style="Heading 1", page_break=True)
    add_run(p, "פתח דבר ודרך העריכה", size=20, bold=True, color="1D1A17")
    for kind, val in INTRO:
        p = para(doc, style="List Bullet" if kind == "li" else None)
        if kind == "li":
            set_bidi(p)
            render_segs(p, [(k, v) for k, v in val] if not isinstance(val, str) else [("text", val)], "")
        else:
            add_run(p, val)

    for ti, (theme, ds) in enumerate(book, 1):
        for _ in range(8):
            q = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
            if _ == 0:
                q.paragraph_format.page_break_before = True
        p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_run(p, f"שער {heb_number(ti)}", size=12, color=COL["muted"], font=UI_FONT)
        p = para(doc, style="Heading 1")
        add_run(p, theme, size=22, bold=True, color=COL["accent"])

        for d in ds:
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, page_break=True, keep_next=True, space_after=0)
            add_run(p, f"דרשה {heb_number(d['num'])}", size=10, color=COL["muted"], font=UI_FONT)
            p = para(doc, style="Heading 2")
            add_run(p, d["title"], size=17, bold=True)
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True, space_after=0)
            add_run(p, d["date"], size=9.5, color=COL["muted"], font=UI_FONT)
            p = para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True, space_after=10)
            add_run(p, "צפייה בדרשה: ", size=9.5, color=COL["muted"], font=UI_FONT)
            add_link(p, d["url"], d["url"], color=COL["accent"], size=9)
            for b in d["blocks"]:
                if b["type"] == "h":
                    p = para(doc, style="Heading 3", align=WD_ALIGN_PARAGRAPH.RIGHT)
                    add_run(p, b["text"], size=13, bold=True, color=COL["accent"], font=UI_FONT)
                else:
                    p = para(doc)
                    render_segs(p, b["segs"], d["url"])

    doc.core_properties.title = BOOK_TITLE
    doc.core_properties.subject = BOOK_SUBTITLE
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    print("wrote", out_path)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else REPO / "book/output/sefer.docx")
