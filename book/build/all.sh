#!/usr/bin/env bash
# Build the whole book, in pipeline order. Run from the repository root.
set -euo pipefail
B=book/build
python3 -I $B/sefaria.py                                   # quotations -> Sefaria wording, footnote labels
for f in $B/.work/stage1/*.md; do                          # full niqqud (Dicta model), letters verified
  python3 -I $B/niqqud.py "$f" "book/vocalized/$(basename "$f")"
done
python3 -I $B/build_tex.py                                 # book/output/sefer.pdf
python3 -I $B/build_docx.py                                # book/output/sefer.docx
python3 -I $B/build_web.py                                 # sefer/
python3 -I $B/build_fill.py                                # book/fill/hashlama.html (fill-in page for [?])
python3 -I $B/qa.py
