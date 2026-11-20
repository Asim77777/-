"""Typeset the book with XeLaTeX: a printed sefer, 17×24 cm.

  Body      Taamey Frank CLM (drawn for full niqqud)
  Titles    Keter Aram Tsova
  Footnotes Noto Rashi Hebrew (Rashi script), sources only
  Colour    black, plus one deep red for opening words and section marks

usage: python3 -I book/build/build_tex.py [--only id,id] [--out name]
"""
import argparse
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import book as B  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "output"
WORK = HERE / ".work" / "tex"

PREAMBLE = r"""
\documentclass[12pt,twoside,openany]{book}
\usepackage[paperwidth=170mm,paperheight=240mm,inner=22mm,outer=17mm,top=24mm,bottom=24mm,
  headheight=16pt,headsep=7mm,footskip=11mm,footnotesep=6mm]{geometry}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{setspace}
\usepackage{qrcode}
\usepackage{polyglossia}
\setmainlanguage[numerals=hebrew]{hebrew}
\setotherlanguage{english}
\newfontfamily\hebrewfont[Script=Hebrew,Scale=1.0]{Taamey Frank CLM}
\newfontfamily\hebrewfontsf[Script=Hebrew]{Taamey Frank CLM}
\newfontfamily\keter[Script=Hebrew]{Keter Aram Tsova}
\newfontfamily\ketersmall[Script=Hebrew]{Keter YG}
\newfontfamily\rashi[Script=Hebrew]{Noto Rashi Hebrew}
\newfontfamily\englishfont{Frank Ruehl CLM}
\newfontfamily\punctfont[Script=Hebrew]{Frank Ruehl CLM}  % – and … are missing from Taamey Frank and from the Rashi font
\newcommand{\dash}{{\punctfont –}}
\newcommand{\elli}{{\punctfont …}}
\newcommand{\rc}{{\punctfont ,}}
\definecolor{adom}{HTML}{8E1B1B}
\definecolor{afor}{HTML}{555555}

\setstretch{1.22}
\setlength{\parindent}{1.4em}
\setlength{\parskip}{0pt}
\emergencystretch=2.5em
\tolerance=1800
\clubpenalty=10000 \widowpenalty=10000 \brokenpenalty=10000
\raggedbottom

% page numbers, footnote marks and references in Hebrew letters: polyglossia's numerals=hebrew
% footnotes: rule on the right, the letter in red, text in Rashi script (set per note)
\rightfootnoterule
\makeatletter
\renewcommand{\@makefnmark}{\raisebox{0.55ex}{\normalfont\scriptsize\color{adom}\@thefnmark}}
\renewcommand{\@makefntext}[1]{\noindent{\normalfont\small\color{adom}\@thefnmark}\hskip0.45em #1}
\makeatother

% running heads, written directly (bidi's adaptation of fancyhdr predates fancyhdr 4 and clashes with it):
% book title on even pages, drasha title on odd pages, page number on the outer edge, hairline below.
\newcommand{\drashahead}{}
\newcommand{\seferhead}[1]{\vbox{\hbox to\textwidth{#1}\vskip3pt{\color{afor}\hrule height 0.3pt}}}
\makeatletter
\def\ps@sefer{%
  % the head box runs right-to-left; the odd page is the left-hand page of a Hebrew book,
  % so its number comes last (left edge) and the even page's number first (right edge)
  \def\@oddhead{\seferhead{\ketersmall\small\makebox[2em]{}\hfil\drashahead\hfil\makebox[2em][l]{\normalsize\thepage}}}%
  \def\@evenhead{\seferhead{\ketersmall\small\makebox[2em][r]{\normalsize\thepage}\hfil\BookTitle\hfil\makebox[2em]{}}}%
  \def\@oddfoot{}\def\@evenfoot{}}
\def\ps@plain{\def\@oddhead{}\def\@evenhead{}%
  \def\@oddfoot{\hfil{\ketersmall\small\thepage}\hfil}\def\@evenfoot{\@oddfoot}}
\makeatother
\pagestyle{sefer}

% building blocks
% the qrcode package counts with \arabic internally; numerals=hebrew would turn those numbers into letters
\makeatletter
\newcommand{\qr}[1]{\begingroup\let\@arabic\xpg@save@arabic\begin{LTR}\qrcode[height=15mm]{#1}\end{LTR}\endgroup}
\makeatother
\newcommand{\subhead}[1]{\par\addvspace{1.1\baselineskip}\penalty-200
  {\centering\large\bfseries #1\par}\nobreak\vspace{0.35\baselineskip}\nobreak\noindent\ignorespaces}
\newcommand{\opening}[1]{{\keter\Large\textcolor{adom}{#1}}}
\newcommand{\unclear}{\textcolor{afor}{\scriptsize[?]}}
\newcommand{\qahal}[1]{{\small[#1:]}}
\newenvironment{longquote}{\par\vspace{0.4\baselineskip}\begin{list}{}{\leftmargin=1.6em\rightmargin=1.6em}\item\relax\small\setstretch{1.15}}{\end{list}\vspace{0.2\baselineskip}}
"""


def esc(s):
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s.replace("–", r"\dash{}").replace("…", r"\elli{}")


def fn_tex(s):
    """Footnote text in Rashi script; the Rashi font has no Latin punctuation."""
    return esc(s).replace(",", r"\rc{}")


def seg_tex(sg):
    t = sg["t"]
    if t == "text":
        return esc(sg["s"])
    if t == "quote":
        body = esc(sg["s"])
        return f"\"{body}\"" if sg["marks"] else body
    if t == "fn":
        if sg.get("skip"):
            return ""
        return r"\footnote{\rashi " + fn_tex(sg["show"]) + "}"
    if t == "unclear":
        return r"\unclear{}"
    if t == "note":
        return r"\qahal{" + esc(sg["s"]) + "}"
    if t == "add":
        return "[" + esc(sg["s"]) + "]"
    return ""


def para_tex(segs, first=False):
    """A paragraph; a long quotation becomes an indented block of its own."""
    out, cur = [], []
    for i, sg in enumerate(segs):
        if sg["t"] == "quote" and sg["long"]:
            # keep the footnote that follows the quote inside the block
            out.append(("p", "".join(cur)))
            cur = []
            out.append(("q", seg_tex(sg)))
            continue
        if sg["t"] == "fn" and out and out[-1][0] == "q" and not "".join(cur).strip():
            out[-1] = ("q", out[-1][1] + seg_tex(sg))
            continue
        if sg["t"] == "text" and out and out[-1][0] == "q" and not "".join(cur).strip():
            m = re.match(r"^\s*([.,;:]+)", sg["s"])
            if m:
                out[-1] = ("q", out[-1][1] + m.group(1))
                sg = dict(sg, s=sg["s"][m.end():])
        cur.append(seg_tex(sg))
    out.append(("p", "".join(cur)))
    tex = []
    for k, (kind, s) in enumerate(out):
        s = s.strip()
        if not s:
            continue
        if kind == "q":
            tex.append(r"\begin{longquote}" + s + r"\end{longquote}")
        else:
            cont = k > 0 and out[k - 1][0] == "q"  # text that continues after a block quotation is not indented
            if first and k == 0:
                s = opening_words(s)
            tex.append((r"\noindent " if cont or (first and k == 0) else "") + s + "\n")
    return "\n".join(tex)


def opening_words(s, n=2):
    """Set the first words of a drasha in large red letters, siddur style."""
    m = re.match(r"^((?:[^\s\\]+\s+){%d})" % n, s)
    if not m:
        return s
    head = m.group(1).rstrip()
    return r"\opening{" + head + "} " + s[m.end():]


def drasha_tex(d, labels):
    t = []
    t.append(r"\clearpage\thispagestyle{empty}")
    t.append(r"\renewcommand{\drashahead}{" + esc(d["title_plain"]) + "}")
    t.append(r"\setcounter{footnote}{0}")
    t.append(r"\begin{center}\vspace*{14mm}")
    t.append(r"{\ketersmall\textcolor{adom}{" + esc(labels.get("label-drasha", "דְּרָשָׁה")) + " " + d["num_heb"] + r"}}\par\vspace{5mm}")
    t.append(r"{\keter\fontsize{22}{31}\selectfont " + esc(d["title"]) + r"\par}\vspace{4mm}")
    t.append(r"{\small " + esc(labels.get("label-said", "נֶאֶמְרָה")) + " " + esc(d["date"]) + r"\par}")
    t.append(r"\vspace{5mm}{\color{adom}\rule{18mm}{0.5pt}}\par\vspace{9mm}")
    t.append(r"\end{center}")
    t.append(r"\label{d-" + d["id"] + "}")
    first = True
    for b in d["blocks"]:
        if b["type"] == "h":
            t.append(r"\subhead{" + "".join(seg_tex(s) for s in b["segs"]) + "}")
            continue
        t.append(para_tex(b["segs"], first=first))
        first = False
    # closing: the recording
    t.append(r"\par\vspace{1.4\baselineskip}\nopagebreak\begin{center}{\color{adom}\rule{18mm}{0.5pt}}\par\vspace{3mm}")
    t.append(r"\qr{" + d["url"] + r"}\par\vspace{1.5mm}")
    t.append(r"{\footnotesize " + esc(labels.get("label-watch", "")) + r"}\end{center}")
    return "\n".join(t)


def shaar_tex(s, labels):
    return "\n".join([
        r"\cleardoublepage\thispagestyle{empty}",
        r"\vspace*{\fill}\begin{center}",
        r"{\ketersmall\Large\textcolor{adom}{" + esc(labels.get("label-shaar", "שַׁעַר")) + " " + s["ordinal"] + r"}}\par\vspace{8mm}",
        r"{\keter\fontsize{28}{40}\selectfont " + esc(s["name"]) + r"\par}",
        r"\vspace{10mm}{\color{adom}\rule{24mm}{0.5pt}}",
        r"\end{center}\vspace*{\fill}\vspace*{\fill}",
        r"\clearpage\thispagestyle{empty}\mbox{}",
    ])


def front_tex(bk):
    L = bk["labels"]
    t = [r"\pagestyle{empty}",
         # title page
         r"\begin{center}\vspace*{38mm}",
         r"{\keter\fontsize{46}{56}\selectfont " + esc(bk["title_main"]) + r"\par}\vspace{7mm}",
         r"{\keter\fontsize{22}{30}\selectfont " + esc(bk["title_by"]) + r"\par}\vspace{9mm}",
         r"{\color{adom}\rule{30mm}{0.6pt}}\par\vspace{9mm}",
         r"{\Large " + esc(bk["subtitle"]) + r"\par}",
         r"\vspace*{\fill}",
         r"{\ketersmall\large " + esc(bk["year"]) + r"\par}\vspace{6mm}",
         r"\end{center}",
         r"\clearpage\mbox{}\clearpage"]
    # table of contents
    t.append(r"\pagestyle{plain}")
    t.append(r"\begin{center}{\keter\fontsize{20}{28}\selectfont " + esc(L.get("label-toc", "תּוֹכֶן הָעִנְיָנִים")) +
             r"\par}\vspace{3mm}{\color{adom}\rule{18mm}{0.5pt}}\end{center}\vspace{6mm}")
    t.append(r"{\setlength{\parindent}{0pt}\setstretch{1.35}")
    t.append(r"\noindent " + esc(strip_heading(bk["intro"])) + r"\dotfill\pageref{intro}\par\vspace{4mm}")
    for s in bk["shaarim"]:
        t.append(r"\vspace{3mm}{\ketersmall\textcolor{adom}{" + esc(L.get("label-shaar", "שַׁעַר")) + " " + s["ordinal"] +
                 r"}\quad\keter\large " + esc(s["name"]) + r"}\par\vspace{1.5mm}")
        for d in s["drashot"]:
            t.append(r"\hangindent=3.2em\hangafter=1\noindent\hbox to 2.2em{" + d["num_heb"] + r"\hfil}" + esc(d["title"]) +
                     r"\dotfill\pageref{d-" + d["id"] + r"}\par")
    t.append(r"}\clearpage")
    # introduction
    t.append(r"\label{intro}")
    first = True
    for b in bk["intro"]:
        segs = "".join(seg_tex(s) for s in b["segs"])
        if b["type"] == "h":
            if first:
                t.append(r"\begin{center}{\keter\fontsize{20}{28}\selectfont " + segs + r"\par}\vspace{3mm}{\color{adom}\rule{18mm}{0.5pt}}\end{center}\vspace{4mm}\noindent ")
                first = False
            else:
                t.append(r"\subhead{" + segs + "}")
        else:
            t.append(segs + "\n")
    t.append(r"\pagestyle{sefer}")
    return "\n".join(t)


def strip_heading(blocks):
    for b in blocks:
        if b["type"] == "h":
            return "".join(s["s"] for s in b["segs"] if s["t"] == "text")
    return ""


def build(only=None, name="sefer"):
    bk = B.load_book(only)
    bk["labels"].setdefault("label-watch", "")
    body = [front_tex(bk)]
    for s in bk["shaarim"]:
        body.append(shaar_tex(s, bk["labels"]))
        for d in s["drashot"]:
            body.append(drasha_tex(d, bk["labels"]))
    doc = (PREAMBLE + r"\newcommand{\BookTitle}{" + esc(bk["title"]) + "}\n" +
           r"\begin{document}" + "\n" + "\n\n".join(body) + "\n" + r"\end{document}" + "\n")
    WORK.mkdir(parents=True, exist_ok=True)
    tex = WORK / f"{name}.tex"
    tex.write_text(doc, encoding="utf-8")
    for _ in range(3):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name], cwd=WORK,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-3000:])
            raise SystemExit("xelatex failed")
    log = (WORK / f"{name}.log").read_text(encoding="utf-8", errors="replace")
    missing = sorted(set(re.findall(r"Missing character: There is no (.) ", log)))
    over = len(re.findall(r"Overfull \\hbox", log))
    OUT.mkdir(exist_ok=True)
    pdf = OUT / f"{name}.pdf"
    pdf.write_bytes((WORK / f"{name}.pdf").read_bytes())
    print(f"{pdf}  missing glyphs: {missing}  overfull boxes: {over}")
    return pdf


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--out", default="sefer")
    a = ap.parse_args()
    build(a.only.split(",") if a.only else None, a.out)
