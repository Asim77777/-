#!/bin/bash
# usage: make.sh [style] [output.pdf]
set -e
cd "$(dirname "$0")"
STYLE="${1:-classic}"
OUT="${2:-../ראה-אנכי-דרשה.pdf}"
TMP="$(mktemp -d)"
python3 build.py "$TMP/pass1.html" "$STYLE" "" markers >/dev/null
cp "$TMP/pass1.html" ./_pass1.html
node pdf.js "$PWD/_pass1.html" "$TMP/pass1.pdf"
PAGES=$(python3 - "$TMP/pass1.pdf" <<'PY'
import subprocess,re,sys
f=sys.argv[1]
n=int(re.search(r'Pages:\s+(\d+)',subprocess.run(['pdfinfo',f],capture_output=True,text=True).stdout).group(1))
found={}
for i in range(1,n+1):
    t=subprocess.run(['pdftotext','-f',str(i),'-l',str(i),f,'-'],capture_output=True,text=True).stdout
    for m in re.findall(r'QQH(\d\d)QQ',t): found.setdefault(int(m),i)
print(','.join(str(found[k]) for k in sorted(found)))
PY
)
echo "$PAGES" > "$TMP/pages.txt"
python3 build.py "_${STYLE}.html" "$STYLE" "$PAGES" >/dev/null
node pdf.js "$PWD/_${STYLE}.html" "$OUT"
rm -f _pass1.html
[ "$STYLE" = classic ] && mv "_${STYLE}.html" drasha.html || rm -f "_${STYLE}.html"
echo "$STYLE: sections on pages $PAGES -> $OUT ($(pdfinfo "$OUT" | awk '/Pages/{print $2}') pages)"
