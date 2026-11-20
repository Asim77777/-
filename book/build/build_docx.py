"""Build the Word edition: book.json (book.py) -> docx-js (build_docx.mjs) -> footnote numbering in Hebrew letters.

usage: python3 -I book/build/build_docx.py [--only id,id] [--out name]
"""
import argparse
import pathlib
import re
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book as B  # noqa: E402

OUT = HERE.parent / "output"
FOOTNOTE_PR = '<w:footnotePr><w:numFmt w:val="hebrew1"/><w:numRestart w:val="eachSect"/></w:footnotePr>'


def hebrew_footnotes(xml):
    """docx-js cannot set the footnote number format or section direction: add <w:footnotePr> and <w:bidi/> to every section
    (schema order: header/footer references, then footnotePr)."""
    def fix(m):
        body = m.group(2)
        refs = list(re.finditer(r"<w:(?:header|footer)Reference[^>]*/>", body))
        pos = refs[-1].end() if refs else 0
        body = body[:pos] + FOOTNOTE_PR + body[pos:]
        # right-to-left section (footnote separator on the right, etc.): <w:bidi/> goes just before <w:docGrid>
        body = body.replace("<w:docGrid", "<w:bidi/><w:docGrid", 1) if "<w:docGrid" in body else body + "<w:bidi/>"
        return m.group(1) + body + m.group(3)
    return re.sub(r"(<w:sectPr[^>]*>)(.*?)(</w:sectPr>)", fix, xml, flags=re.S)


def build(only=None, name="sefer"):
    work = HERE / ".work"
    js = work / "book.json"
    B.export_json(js, only)
    raw = work / f"{name}.raw.docx"
    subprocess.run(["node", str(HERE / "build_docx.mjs"), str(js), str(raw)], check=True)
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{name}.docx"
    with zipfile.ZipFile(raw) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.endswith("/"):
                continue  # no folder entries (Word rejects them through cloud co-editing)
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = hebrew_footnotes(data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
    print(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--out", default="sefer")
    a = ap.parse_args()
    build(a.only.split(",") if a.only else None, a.out)
