#!/bin/sh
# Wrap the page like the Artifact publish skeleton, with the test runtime first, and run the e2e test.
#   sh catio/test/run.sh
# Needs Playwright and Chromium. In Claude's cloud sessions both are preinstalled:
#   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright  CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
set -e
T=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$T")
{
  printf '<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
  printf '<base href="file://%s/"><style>body{margin:0}img{max-width:100%%}[hidden]{display:none!important}</style><script>' "$P"
  cat "$T/runtime-stub.js"
  printf '</script></head><body>'
  cat "$P/index.html"
  printf '</body></html>'
} > "$T/.page.html"
# the same page over a folder with only the committed art, as anyone else's checkout is
N="$T/.noart"
rm -rf "$N"; mkdir -p "$N/art"; cp "$P/art/furniture.png" "$N/art/"
sed "s#<base href=\"file://$P/\">#<base href=\"file://$N/\">#" "$T/.page.html" > "$T/.page-noart.html"
: "${PLAYWRIGHT:=/opt/node22/lib/node_modules/playwright}"
: "${CHROMIUM:=/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
[ -x "$CHROMIUM" ] || unset CHROMIUM
# local mode: serve a copy of the bundle on localhost with no runtime at all, and invented sessions
python3 "$P/tools/bundle.py" >/dev/null
L=$(mktemp -d)
cp -R "$P/dist/catio-local/." "$L/"
cp "$T/sessions.json" "$L/data/sessions.json"
PORT=${PORT:-8791}
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$L" >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; rm -rf "$L"' EXIT
sleep 1
LOCAL_URL="http://127.0.0.1:$PORT/index.html" PLAYWRIGHT="$PLAYWRIGHT" CHROMIUM="$CHROMIUM" node "$T/e2e.mjs"
