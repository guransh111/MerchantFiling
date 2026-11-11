#!/usr/bin/env bash
# Rebuild Trace's Word appendices with page-numbered contents pages:
#   explained/Trace_Appendix.docx              the full appendix (reasoning, method, results, costs ...)
#   explained/Trace_Appendix_Financials.docx   the costs on their own
# Needs Python (matplotlib), Node (docx), LibreOffice and poppler-utils. Run from anywhere:
#   bash explained/financials/make.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
python "$HERE/model.py"
python "$HERE/charts.py"

build_doc() {  # build_doc <builder.js> <name>
  local builder="$1" name="$2" out="$HERE/../$2.docx" tmp
  tmp="$(mktemp -d)"
  # pass 1: render once to learn which page each heading lands on
  node "$HERE/$builder" "$tmp/pass1.docx" >/dev/null
  soffice --headless --convert-to pdf --outdir "$tmp" "$tmp/pass1.docx" >/dev/null 2>&1
  python "$HERE/pages.py" "$tmp/pass1.pdf" "$tmp/pass1.toc.json" "$tmp/pages.json" >/dev/null
  # pass 2: the real document, with those page numbers in the contents
  node "$HERE/$builder" "$out" "$tmp/pages.json" >/dev/null
  rm -f "${out%.docx}.toc.json"
  python "$HERE/fix_bookmarks.py" "$out" >/dev/null
  # check that the page numbers did not move, and keep a PDF copy
  cp "$out" "$tmp/final.docx"
  soffice --headless --convert-to pdf --outdir "$tmp" "$tmp/final.docx" >/dev/null 2>&1
  python "$HERE/pages.py" "$tmp/final.pdf" "$tmp/pass1.toc.json" "$tmp/check.json" >/dev/null
  if cmp -s "$tmp/pages.json" "$tmp/check.json"; then echo "$name: contents page numbers verified"; else echo "$name: WARNING page numbers moved"; fi
  cp "$tmp/final.pdf" "$HERE/../$name.pdf"
  echo "$name: $(pdfinfo "$tmp/final.pdf" | awk '/^Pages/{print $2}') pages"
}
build_doc build_docx.js Trace_Appendix_Financials
build_doc build_appendix.js Trace_Appendix
