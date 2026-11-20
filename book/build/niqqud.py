"""Full niqqud with Dicta's official model (dicta-il/dictabert-large-char-menaked).

Rules:
- Text inside ⟦ref|…⟧ quotes is NOT sent to the model when it already carries niqqud (from Sefaria).
- Markup tokens ([[ts]], {{…}}, [?…], [מן הקהל:], ## headings) are kept verbatim.
- The model is run with mark_matres_lectionis='*' so we can verify that removing the niqqud
  and the starred letters gives back exactly the input letters (no word was changed).
- Output keeps the edited spelling (ktiv male) with niqqud; the doubled ו/י of ktiv male that the model marks
  is dropped, and data/niqqud_fixes.json (reviewed by the editor) is applied last, never inside Sefaria text.

usage: python3 -I book/build/niqqud.py <in.md> <out.md>
"""
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
FIXES = HERE.parent / "data" / "niqqud_fixes.json"
NIQQUD_RE = re.compile(r"[֑-ׇ]")
HEB_RE = re.compile(r"[א-ת]")
# segments that must not be vocalized
PROTECT_RE = re.compile(r"(\[\[[0-9:]+\]\]|\{\{[^}]*\}\}|⟦(?:sefaria|~)\|[^⟧]*⟧|⟦(?:=|src)\||⟧|\[\?[0-9:]*\]|\[מן הקהל[^\]]*\]|\([^)]*[A-Za-z][^)]*\))")

_model = _tok = None


def load():
    global _model, _tok
    if _model is None:
        from transformers import AutoModel, AutoTokenizer
        import torch
        torch.set_num_threads(4)
        _tok = AutoTokenizer.from_pretrained("dicta-il/dictabert-large-char-menaked")
        _model = AutoModel.from_pretrained("dicta-il/dictabert-large-char-menaked", trust_remote_code=True)
        _model.eval()
    return _model, _tok


def strip_niqqud(s):
    return NIQQUD_RE.sub("", s)


def predict(sentences):
    model, tok = load()
    import torch
    with torch.no_grad():
        return model.predict(sentences, tok, mark_matres_lectionis="*")


def chunk_text(text, limit=400):
    """Split text into model-sized pieces on sentence punctuation."""
    parts, cur = [], ""
    for piece in re.split(r"(?<=[.!?;:,–])\s+", text):
        if len(cur) + len(piece) + 1 > limit and cur:
            parts.append(cur)
            cur = piece
        else:
            cur = f"{cur} {piece}".strip()
    if cur:
        parts.append(cur)
    return parts


L = "[א-ת]"          # a letter
M = "[֑-ׇ]"          # any mark
DAGESH, QUBUTZ, HOLAM, QAMATZ, SHVA = "ּ", "ֻ", "ֹ", "ָ", "ְ"


def _fix_word(word):
    cl = []  # [letter, [marks]]
    for ch in word:
        if "א" <= ch <= "ת":
            cl.append([ch, []])
        elif "֑" <= ch <= "ׇ" and cl:
            cl[-1][1].append(ch)
        else:
            cl.append([ch, None])  # punctuation etc.
    i = 0
    while i < len(cl) - 1:
        a, b = cl[i], cl[i + 1]
        if a[1] is None or b[1] is None:
            i += 1
            continue
        # word-final bare "יי" -> "י"  (אֵלַיי, רַבּוֹתַיי)
        if a[0] == b[0] == "י" and not a[1] and not b[1] and (i + 2 == len(cl) or cl[i + 2][1] is None):
            del cl[i + 1]
            continue
        # a bare vav followed by another vav is a doubled consonantal vav (הָעֲנָווֹת), not a vowel letter
        doubled = i + 2 < len(cl) and cl[i + 2][0] == "ו"
        # qubutz + bare vav -> shuruk  (גְּאֻולָּה -> גְּאוּלָּה)
        if QUBUTZ in a[1] and b[0] == "ו" and not b[1] and not doubled:
            a[1].remove(QUBUTZ)
            b[1].append(DAGESH)
        # holam + vav with holam -> only the vav's holam  (אֹוֹמֵר)
        elif HOLAM in a[1] and b[0] == "ו" and HOLAM in b[1]:
            a[1].remove(HOLAM)
        # qamatz (qatan) + bare vav -> holam male  (אָופְיוֹ -> אוֹפְיוֹ)
        elif QAMATZ in a[1] and a[0] != "ו" and b[0] == "ו" and not b[1] and not doubled:
            a[1].remove(QAMATZ)
            b[1].append(HOLAM)
        i += 1
    # no dagesh right after a word-initial prefix letter with shva (בְּמִּילִּים -> בְּמִילִּים)
    if len(cl) > 2 and cl[0][1] and cl[0][0] in "בכלמשו" and SHVA in cl[0][1] and cl[1][1] and DAGESH in cl[1][1]:
        cl[1][1].remove(DAGESH)
    return "".join(c[0] + "".join(c[1] or []) for c in cl)


def normalize_vocalized(s):
    """Systematic clean-ups of the model output in ktiv-male text (word by word)."""
    out = re.sub(r"[א-ת֑-ׇ]+", lambda m: _fix_word(m.group(0)), s)
    return unicodedata.normalize("NFC", out)


def apply_fixes(s, fixes):
    """Whole-word replacements from book/data/niqqud_fixes.json (reviewed by the editor)."""
    if not fixes:
        return s
    return re.sub(r"[\u05D0-\u05EA\u0591-\u05C7״׳]+", lambda m: fixes.get(m.group(0), m.group(0)), s)


def vocalize_plain(text, report):
    """Vocalize a run of plain text (no markup). Returns ktiv-chaser vocalized text."""
    if not HEB_RE.search(text):
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    core = text.strip()
    out_parts = []
    for piece in chunk_text(core):
        res = predict([piece])[0]
        # verification: remove niqqud and '*' marker -> must equal input letters
        check = strip_niqqud(res).replace("*", "")
        if check != strip_niqqud(piece):
            report.append({"input": piece, "output": res})
            out_parts.append(piece)  # keep unvocalized rather than risk a changed word
            continue
        # keep the spelling exactly as edited (ktiv male with niqqud): drop only the '*' markers,
        # and put a holam that precedes a vowel-letter vav on the vav itself (holam male: וֹ)
        res = re.sub("ֹ" + r"ו\*", "וֹ", res)
        # doubled consonantal vav/yod of ktiv male, which the model itself marks with '*'
        # (גַּאֲוָו*ה -> גַּאֲוָה, עֲדַיִי*ן -> עֲדַיִן); an unmarked second letter is a real vowel letter (הָיִיתִי, חַיֵּי)
        res = re.sub(r"([וי])([֑-ׇ]*)\*?\1\*", r"\1\2", res)
        res = res.replace("*", "").replace("ׇ", "ָ")  # qamatz qatan -> qamatz (font coverage)
        out_parts.append(normalize_vocalized(res))
    return lead + " ".join(out_parts) + trail


def vocalize_line(line, fixes, report):
    if line.startswith("## ") or not line.strip() or line.startswith("---"):
        return vocalize_heading(line, fixes, report) if line.startswith("## ") else line
    out, pos = [], 0
    for m in PROTECT_RE.finditer(line):
        out.append(vocalize_plain(line[pos:m.start()], report))
        out.append(m.group(0))
        pos = m.end()
    out.append(vocalize_plain(line[pos:], report))
    return apply_fixes(unicodedata.normalize("NFC", "".join(out)), fixes)


def vocalize_heading(line, fixes, report):
    return "## " + vocalize_line(line[3:], fixes, report)


def run(inp, outp):
    raw = pathlib.Path(inp).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    fixes = {k: v for k, v in json.loads(FIXES.read_text(encoding="utf-8")).items() if not k.startswith("_")} if FIXES.exists() else {}
    report = []
    lines = body.split("\n")
    out = [vocalize_line(l, fixes, report) for l in lines]
    pathlib.Path(outp).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(outp).write_text("---" + fm + "---" + "\n".join(out), encoding="utf-8")
    print(f"{inp} -> {outp}; unverifiable chunks kept unvocalized: {len(report)}")
    for r in report[:10]:
        print("  !", r["input"][:80])
    return report


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        print(predict(["אנו עסוקים בפרשיותיו של אברהם אבינו עליו השלום, ונכון לנצל את הפרשה האחרונה שבה אברהם אבינו עדיין חי."]))
    else:
        run(sys.argv[1], sys.argv[2])
