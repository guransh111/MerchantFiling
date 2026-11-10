#!/usr/bin/env bash
# Builds the static landing page for Vercel into site_build/.
# Set these in Vercel -> Project -> Settings -> Environment Variables:
#   DASHBOARD_URL  your Streamlit app, e.g. https://trace.streamlit.app
#   REPO_URL       (optional) defaults to the GitHub repo
set -euo pipefail
OUT=site_build
rm -rf "$OUT" && mkdir -p "$OUT/reports"
cp site/index.html "$OUT/index.html"
cp reports/*.png "$OUT/reports/"
DASH="${DASHBOARD_URL:-https://share.streamlit.io}"
REPO="${REPO_URL:-https://github.com/guransh111/merchantfiling}"
sed -i.bak -e "s#__DASHBOARD_URL__#${DASH}#g" -e "s#__REPO_URL__#${REPO}#g" "$OUT/index.html" && rm -f "$OUT/index.html.bak"
echo "Built $OUT (dashboard link: $DASH)"
