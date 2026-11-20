"""Quality checks for the book. Exit code 1 if a check fails.

1. Niqqud did not change a word: stage-2 text without niqqud has the same words as stage-1, up to the
   vowel letters ו/י (ktiv male doubling, traditional spellings in niqqud_fixes.json).
2. Spelling: hspell on the rabbi's own words (quotations excluded); every flagged word must be in
   data/hspell_reviewed.txt (words checked by the editor: names, Aramaic, accepted spellings).
3. Sources: every quotation was matched to Sefaria or is listed as not located.
4. No markup left in the outputs (PDF source, Word, web).
5. Unclear spots ([?]) per drasha – for the fill-in page.

usage: python3 -I book/build/qa.py
"""
import collections
import json
import pathlib
import re
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
BOOK = HERE.parent
REPO = BOOK.parent
W = HERE / ".work"
NQ = re.compile(r"[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
fail = False


def report(ok, msg):
    global fail
    print(("  ok   " if ok else "  FAIL ") + msg)
    fail |= not ok


def skeleton(word):
    w = NQ.sub("", word.replace("־", " ")).translate(FINALS)
    return re.sub(r"[וי]", "", w)


def words_outside_sefaria(t):
    t = t.split("---", 2)[2]
    t = re.sub(r"⟦(?:sefaria|~)\|[^⟧]*⟧", " ", t)              # Sefaria's own vocalized text
    t = re.sub(r"\{\{[^}]*\}\}|\[\[[0-9:]+\]\]|\[\?[0-9:]*\]|⟦(?:=|src)\||⟧", " ", t)
    return [w for w in re.findall(r"[א-ת֑-ׇ־]+", t) if re.search(r"[א-ת]", w)]


print("1. niqqud kept every word")
for s1 in sorted((W / "stage1").glob("*.md")):
    s2 = BOOK / "vocalized" / s1.name
    a = [skeleton(w) for w in words_outside_sefaria(s1.read_text(encoding="utf-8"))]
    b = [skeleton(w) for w in words_outside_sefaria(s2.read_text(encoding="utf-8"))]
    a, b = " ".join(a).split(), " ".join(b).split()
    diffs = [(x, y) for x, y in zip(a, b) if x != y]
    report(len(a) == len(b) and not diffs, f"{s1.stem}: {len(a)} words" + (f"; differences: {diffs[:5]} (counts {len(a)}/{len(b)})" if diffs or len(a) != len(b) else ""))

print("2. spelling (hspell, the rabbi's words)")
reviewed = set((BOOK / "data" / "hspell_reviewed.txt").read_text(encoding="utf-8").split())
for f in sorted((BOOK / "drashot").glob("*.md")):
    t = f.read_text(encoding="utf-8").split("---", 2)[2]
    t = re.sub(r"⟦[^⟧]*⟧|\"[^\"\n]*\"|\{\{[^}]*\}\}|\[\[[0-9:]+\]\]|\[\?[0-9:]*\]|\([^)]*[A-Za-z][^)]*\)", " ", t)
    t = t.replace("״", '"').replace("׳", "'").replace("–", "-").replace("…", "...")
    enc = t.encode("iso-8859-8", errors="replace")
    out = subprocess.run(["hspell"], input=enc, capture_output=True).stdout.decode("iso-8859-8", errors="replace")
    flagged = [w for w in out.split("\n", 1)[-1].split() if w not in reviewed] if out.strip() else []
    report(not flagged, f"{f.stem}: unreviewed words: {flagged}" if flagged else f"{f.stem}: all flagged words reviewed")

print("3. sources")
rep = json.loads((BOOK / "data" / "sources_report.json").read_text(encoding="utf-8"))
c = collections.Counter(r["status"] for r in rep)
bad = {k: v for k, v in c.items() if k not in ("exact", "requoted", "verbatim-unvocalized-source", "not-located")}
report(not bad, f"statuses {dict(c)}" + (f"; unresolved: {bad}" if bad else ""))
for r in rep:
    if r["status"] == "not-located":
        print(f"         not located in Sefaria ({r['drasha']}): {r['ref']}")

print("4. no markup left in the outputs")
texts = {"tex": (W / "tex" / "sefer.tex").read_text(encoding="utf-8") if (W / "tex" / "sefer.tex").exists() else ""}
docx = BOOK / "output" / "sefer.docx"
if docx.exists():
    texts["docx"] = zipfile.ZipFile(docx).read("word/document.xml").decode("utf-8")
texts["web"] = "".join(p.read_text(encoding="utf-8") for p in (REPO / "sefer").glob("*.html"))
for k, t in texts.items():
    # in TeX source "{{" and "}}" are ordinary syntax; there only the book's own brackets count
    left = re.findall(r"⟦|⟧|\[\[\d" if k == "tex" else r"⟦|⟧|\{\{|\}\}|\[\[\d", t)
    report(not left, f"{k}: {len(left)} leftover markers")

print("5. unclear spots ([?]) still to be filled")
for s2 in sorted((BOOK / "vocalized").glob("*.md")):
    n = len(re.findall(r"\[\?[0-9:]*\]", s2.read_text(encoding="utf-8")))
    if n:
        print(f"         {s2.stem}: {n}")

sys.exit(1 if fail else 0)
