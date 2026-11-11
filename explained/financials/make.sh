#!/usr/bin/env bash
# Rebuild the financial appendix: model -> charts -> Word document with a page-numbered table of contents.
# Needs Python (matplotlib), Node (docx), LibreOffice and poppler-utils (pdftotext). Run from anywhere:
#   bash explained/financials/make.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../Trace_Appendix_Financials.docx"
TMP="$(mktemp -d)"
python "$HERE/model.py"
python "$HERE/charts.py"
# pass 1: render once to learn which page each heading lands on
node "$HERE/build_docx.js" "$TMP/pass1.docx"
soffice --headless --convert-to pdf --outdir "$TMP" "$TMP/pass1.docx" >/dev/null 2>&1
python "$HERE/pages.py" "$TMP/pass1.pdf" "$TMP/pass1.toc.json" "$TMP/pages.json"
# pass 2: the real document, with those page numbers in the contents
node "$HERE/build_docx.js" "$OUT" "$TMP/pages.json"
rm -f "${OUT%.docx}.toc.json"
python "$HERE/fix_bookmarks.py" "$OUT"
# check: the page numbers must not have moved
cp "$OUT" "$TMP/final.docx"
soffice --headless --convert-to pdf --outdir "$TMP" "$TMP/final.docx" >/dev/null 2>&1
python "$HERE/pages.py" "$TMP/final.pdf" "$TMP/pass1.toc.json" "$TMP/check.json" >/dev/null
cmp -s "$TMP/pages.json" "$TMP/check.json" && echo "contents page numbers verified" || echo "WARNING: page numbers moved, run again"
cp "$TMP/final.pdf" "$HERE/../Trace_Appendix_Financials.pdf"
echo "wrote $OUT"
