#!/bin/bash
# Build 3-page design samples (cover, first content page, a page with Akeida quotes) for each style.
set -e
cd "$(dirname "$0")"
OUTDIR="../דוגמאות-עיצוב"
mkdir -p "$OUTDIR"
TMP="$(mktemp -d)"
declare -A NAME=( [vilna]="א-צורת-הדף" [klaf]="ב-קלף" [maroc]="ג-מורשת-מרוקו" )
for st in vilna klaf maroc; do
  line=$(./make.sh "$st" "$TMP/$st.pdf")
  echo "$line"
  pages=$(echo "$line" | sed -E 's/.*pages ([0-9,]+) ->.*/\1/')
  p1=$(echo "$pages" | cut -d, -f1)      # first content page
  p2=$(echo "$pages" | cut -d, -f5)      # section "זוהמת הנחש" (Akeida quotes)
  [ "$p2" = "$p1" ] && p2=$((p1+1))
  pdfseparate -f 1 -l 1 "$TMP/$st.pdf" "$TMP/${st}_a.pdf"
  pdfseparate -f "$p1" -l "$p1" "$TMP/$st.pdf" "$TMP/${st}_b.pdf"
  pdfseparate -f "$p2" -l "$p2" "$TMP/$st.pdf" "$TMP/${st}_c.pdf"
  pdfunite "$TMP/${st}_a.pdf" "$TMP/${st}_b.pdf" "$TMP/${st}_c.pdf" "$OUTDIR/${NAME[$st]}.pdf"
done
rm -rf "$TMP"
