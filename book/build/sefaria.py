"""Resolve quotations and footnotes against texts fetched from sefaria.org.il.

Input : book/drashot/<id>.md              (edited, unvocalized)
        book/data/sefaria_raw/*.json       (raw Sefaria bulktext responses, fetched via Firecrawl)
Output: book/build/.work/stage1/<id>.md     (quotes replaced by the exact Sefaria wording, vocalized where Sefaria is;
                                            footnotes rendered as {{=Hebrew label}})
        book/data/sources_report.json       (what was matched, anchored, or not found)

Markup handled:
  ⟦Ref|text⟧   quote: text is aligned to the Sefaria text of Ref; aligned words replace it.
  {{Ref}}      footnote with a Sefaria reference -> {{=label}}
  {{!text}}    footnote with free Hebrew text   -> {{=text}}
  {{?desc}}    source not located              -> removed from the book, listed in the report
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
BOOK = HERE.parent
RAW = BOOK / "data" / "sefaria_raw"
STAGE1 = HERE / ".work" / "stage1"

TAAMIM = re.compile(r"[֑-ֽ֯׀׃]")
NIQQUD = re.compile(r"[֑-ׇ]")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

# heRef labels for footnote-only references (verified on sefaria.org.il; see sources_report.json)
EXTRA_HEREF = {
    "Bava Batra 21a": "בבא בתרא כ״א א", "Bava Batra 74a": "בבא בתרא ע״ד א", "Bava Batra 75a": "בבא בתרא ע״ה א",
    "Berakhot 35a": "ברכות ל״ה א", "Berakhot 16a": "ברכות ט״ז א", "Menachot 43b": "מנחות מ״ג ב",
    "Jerusalem Talmud Makkot 2:6": "תלמוד ירושלמי מכות ב׳:ו׳",
    "Or HaChaim on Leviticus 16:1": "אור החיים על ויקרא ט״ז:א׳", "Or HaChaim on Numbers 16:4": "אור החיים על במדבר ט״ז:ד׳",
    "Ramban on Exodus 25:1": "רמב״ן על שמות כ״ה:א׳", "Ramban on Leviticus 23:24": "רמב״ן על ויקרא כ״ג:כ״ד",
    "Rashi on Genesis 49:6": "רש״י על בראשית מ״ט:ו׳", "Rashi on Leviticus 23:36": "רש״י על ויקרא כ״ג:ל״ו",
    "Rashi on Numbers 16:7": "רש״י על במדבר ט״ז:ז׳", "Sanhedrin 59b": "סנהדרין נ״ט ב", "Sanhedrin 98a": "סנהדרין צ״ח א",
    "Vayikra Rabbah 30:2": "ויקרא רבה ל׳:ב׳", "Yoma 86a": "יומא פ״ו א", "Yoma 86b": "יומא פ״ו ב",
    "Nehemiah 8:14-17": "נחמיה ח׳:י״ד-י״ז",
}


def load_sources():
    src = {}
    for f in sorted(RAW.glob("batch_*.json")):
        data = json.loads(json.load(open(f, encoding="utf-8"))["rawHtml"])
        for v in data.values():
            he = v["he"] if isinstance(v["he"], str) else " ".join(map(str, v["he"]))
            src[v["ref"]] = {"heRef": v["heRef"], "he": he}
    ak = RAW / "Akeidat_Yitzchak.77.1.txt"
    if ak.exists():
        src["Akeidat Yitzchak 77:1"] = {"heRef": "עקידת יצחק ע״ז:א׳", "he": ak.read_text(encoding="utf-8")}
    return src


def clean_sefaria(he):
    he = re.sub(r"<[^>]+>", "", he)
    he = re.sub(r"\{[פס]\}", "", he)
    he = re.sub(r"\s*\([^)]*\)", "", he)
    he = he.replace("׀", " ").replace("׃", "")
    he = TAAMIM.sub("", he)
    he = he.replace("ׇ", "ָ")  # qamatz qatan -> qamatz (font coverage)
    return re.sub(r"\s+", " ", he).strip()


NAME_RE = re.compile(r"^([ובלמכשה]?[ְ-ׇ]*)(יְהֹוָה|יְהוָה|יֱהֹוִה|יְיָ|יהוה|יי)$")


def divine_name(word):
    """Replace the Tetragrammaton (with optional prefix letter) by ה׳."""
    bare = NIQQUD.sub("", word)
    m = re.match(r"^([ובלמכשה]?)(יהוה|ייי|יי)$", bare)
    if not m:
        return word
    prefix_letters = m.group(1)
    if not prefix_letters:
        return "ה׳"
    # keep the vocalized prefix letter (first letter + its marks)
    pm = re.match(r"^([א-ת][֑-ׇ]*)", word)
    return (pm.group(1) if pm else prefix_letters) + "ה׳"


def key(word):
    w = NIQQUD.sub("", word)
    w = re.sub(r"[^א-ת׳']", "", w)
    if w in ("ה׳", "ה'"):
        return "@N"
    m = re.match(r"^([ובלמכשה]?)(ה׳|ה')$", w)
    if m:
        return m.group(1) + "@N"
    w = re.sub(r"[׳']", "", w)
    w = re.sub(r"^([ובלמכשה]?)(יהוה|ייי|יי)$", r"\1@N", w)
    w = w.translate(FINALS)
    head, tail = (w.split("@N") + [""])[:2] if "@N" in w else (w, None)
    w = re.sub(r"[וי]", "", head) + ("@N" + tail if tail is not None else "")
    return w


def tokenize(text):
    """-> list of (word, separator_after)."""
    parts = re.split(r"(\s+|־)", text)
    toks = []
    for i in range(0, len(parts), 2):
        w = parts[i]
        sep = parts[i + 1] if i + 1 < len(parts) else ""
        if w:
            toks.append([w, " " if sep.strip() == "" and sep else sep])
        elif toks and sep:
            toks[-1][1] = sep
    return toks


def render(tokens):
    out = ""
    for i, (w, sep) in enumerate(tokens):
        out += divine_name(w)
        if i < len(tokens) - 1:
            out += "־" if sep == "־" else " "
    return out


def align(quote, src_tokens, start=0):
    qwords = [w for w in re.split(r"\s+", quote) if re.search(r"[א-ת]", w)]
    qkeys = [key(w) for w in qwords]
    skeys = [key(w) for w, _ in src_tokens]
    n = len(qkeys)
    for i in range(start, len(skeys) - n + 1):
        if skeys[i:i + n] == qkeys:
            return i, i + n, "exact"
    # anchor fallback: first two and last two words (for long quotes quoted from memory)
    if n >= 6:
        for i in range(start, len(skeys)):
            if skeys[i:i + 2] == qkeys[:2]:
                for j in range(i + 2, min(len(skeys), i + n * 2) - 1):
                    if skeys[j:j + 2] == qkeys[-2:]:
                        return i, j + 2, "anchored"
    return None


def resolve_quote(ref, text, sources, report, drasha):
    s = sources.get(ref)
    if not s:
        report.append({"drasha": drasha, "ref": ref, "status": "ref-missing", "quote": text})
        return text
    src_text = clean_sefaria(s["he"])
    if not NIQQUD.search(src_text):
        # unvocalized source (e.g. Akeidat Yitzchak): the quote was already copied verbatim from it
        report.append({"drasha": drasha, "ref": ref, "status": "verbatim-unvocalized-source", "quote": text})
        return text
    toks = tokenize(src_text)
    segments = [seg.strip() for seg in re.split(r"\.\.\.|…", text)]
    out, pos, status = [], 0, "exact"
    for seg in segments:
        if not re.search(r"[א-ת]", seg):
            continue
        m = align(seg, toks, pos)
        if not m:
            report.append({"drasha": drasha, "ref": ref, "status": "no-match", "quote": seg})
            out.append(seg)
            status = "partial"
            continue
        a, b, how = m
        if how == "anchored":
            status = "anchored" if status == "exact" else status
            report.append({"drasha": drasha, "ref": ref, "status": "anchored", "quote": seg,
                           "sefaria": render(toks[a:b])})
        out.append(render(toks[a:b]))
        pos = b
    return " ... ".join(out)


def fmt_label(heref):
    if heref.startswith("חובות הלבבות, שער שישי"):
        return "חובות הלבבות, שער הכניעה, פרק ב"
    s = heref.replace('"', "״").replace("רמב״ן על", "רמב״ן").replace("רש״י על", "רש״י")
    s = s.replace("אור החיים על", "אור החיים").replace("תרגום יונתן על", "תרגום יונתן")
    s = s.replace("תלמוד ירושלמי", "ירושלמי").replace("משנה אבות", "אבות")
    s = re.sub(r"^עקידת יצחק ע״ז:א׳$", "עקדת יצחק, שער עז", s)
    s = s.replace("חובות הלבבות, שער שישי - שער הכניעה ב׳", "חובות הלבבות, שער הכניעה, פרק ב")
    # Talmud daf: "ט״ז א" -> "טז ע״א"
    s = re.sub(r"(\S+) ([אב])$", lambda m: f"{m.group(1)} ע״{m.group(2)}", s)
    s = re.sub(r"(\S+):(\S+)", r"\1, \2", s)
    s = s.replace("-", "–")
    s = re.sub(r"([א-ת])[״׳]([א-ת])", r"\1\2", s)   # י״ח -> יח
    s = re.sub(r"(?<=[א-ת])׳(?=[,\s–]|$)", "", s)               # ט׳ -> ט
    s = s.replace("ע״א", "ע״א").replace("ע״ב", "ע״ב")
    return s


def footnote(ref, sources, report, drasha):
    if ref.startswith("!"):
        return "{{=" + ref[1:].strip() + "}}"
    if ref.startswith("?"):
        report.append({"drasha": drasha, "ref": ref[1:], "status": "not-located"})
        return ""
    he = sources.get(ref, {}).get("heRef") or EXTRA_HEREF.get(ref)
    if not he:
        report.append({"drasha": drasha, "ref": ref, "status": "no-label"})
        return ""
    return "{{=" + fmt_label(he) + "}}"


def requote(t, refs, sources, report, drasha):
    """A short quotation in plain quote marks that repeats words of a source already cited in this
    drasha ("אשר לא צוה אתם") gets that source's exact vocalized wording, as ⟦~|…⟧ (no new footnote)."""
    toks = {}
    for r in dict.fromkeys(refs):
        src = clean_sefaria(sources[r]["he"])
        if NIQQUD.search(src):
            toks[r] = tokenize(src)

    def one(m):
        inner = m.group(1)
        words = [w for w in re.split(r"\s+", inner) if re.search(r"[א-ת]", w)]
        if len(words) < 2 or re.search(r"[⟦⟧{}\[\]]", inner):
            return m.group(0)
        core = re.sub(r"[.,;:!?–]+$", "", inner.strip())
        for r, tk in toks.items():
            hit = align(core, tk)
            if hit and hit[2] == "exact":
                report.append({"drasha": drasha, "ref": r, "status": "requoted", "quote": core})
                tail = inner.strip()[len(core):]
                return '"⟦~|' + render(tk[hit[0]:hit[1]]) + '⟧' + tail + '"'
        return m.group(0)

    # only outside existing ⟦…⟧ spans
    parts = re.split(r"(⟦[^⟧]*⟧)", t)
    return "".join(pt if pt.startswith("⟦") else re.sub(r'"([^"\n]{3,200})"', one, pt) for pt in parts)


def process(md_path, sources, report):
    t = pathlib.Path(md_path).read_text(encoding="utf-8")
    drasha = pathlib.Path(md_path).stem

    def q(m):
        ref, text = m.group(1).strip(), m.group(2)
        if ref.startswith("?"):
            report.append({"drasha": drasha, "ref": ref[1:], "status": "not-located", "quote": text})
            return "⟦=|" + text + "⟧"
        resolved = resolve_quote(ref, text, sources, report, drasha)
        label = footnote(ref, sources, report, drasha)
        if ref not in sources:
            kind = "="
        elif NIQQUD.search(resolved):
            kind = "sefaria"       # exact vocalized wording from Sefaria: not touched by the niqqud model
        else:
            kind = "src"           # verbatim from an unvocalized Sefaria text: vocalized by the model, letters verified
        return "⟦" + kind + "|" + resolved + "⟧" + label

    used_refs = [r.strip() for r in re.findall(r"⟦([^|⟧?]+)\|", t) if r.strip() in sources]
    t = re.sub(r"⟦([^|⟧]+)\|([^⟧]*)⟧", q, t)
    t = requote(t, used_refs, sources, report, drasha)
    t = re.sub(r"\{\{([^=}][^}]*)\}\}", lambda m: footnote(m.group(1).strip(), sources, report, drasha), t)
    # a free-text footnote that names where the quote was found ("…, הובא בעקדת יצחק") replaces the automatic one
    t = re.sub(r"\{\{=[^}]*\}\}(\{\{=[^}]*הובא[^}]*\}\})", r"\1", t)
    STAGE1.mkdir(parents=True, exist_ok=True)
    (STAGE1 / pathlib.Path(md_path).name).write_text(t, encoding="utf-8")


def main(paths):
    sources = load_sources()
    report = []
    for p in paths:
        process(p, sources, report)
    (BOOK / "data" / "sources_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(r["status"] for r in report))
    for r in report:
        if r["status"] != "exact":
            print(r["status"], r["drasha"], r["ref"], "|", r.get("quote", "")[:60], "=>", r.get("sefaria", "")[:60])


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(str(p) for p in [*(BOOK / "drashot").glob("*.md"), *(BOOK / "front").glob("*.md")]))
