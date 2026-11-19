#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 build.py pass1.html "" markers >/dev/null
node pdf.js "$PWD/pass1.html" "$PWD/pass1.pdf"
PAGES=$(python3 - <<'PY'
import subprocess,re
n=int(re.search(r'Pages:\s+(\d+)',subprocess.run(['pdfinfo','pass1.pdf'],capture_output=True,text=True).stdout).group(1))
found={}
for i in range(1,n+1):
    t=subprocess.run(['pdftotext','-f',str(i),'-l',str(i),'pass1.pdf','-'],capture_output=True,text=True).stdout
    for m in re.findall(r'QQH(\d\d)QQ',t): found.setdefault(int(m),i)
print(','.join(str(found[k]) for k in sorted(found)))
PY
)
echo "section pages: $PAGES"
python3 build.py drasha.html "$PAGES"
node pdf.js "$PWD/drasha.html" "$PWD/../ראה-אנכי-דרשה.pdf"
pdfinfo "../ראה-אנכי-דרשה.pdf" | grep Pages
