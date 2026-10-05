#!/bin/sh
# Wrap the page like the Artifact publish skeleton, with the test runtime first, and run the e2e test.
#   sh catio/test/run.sh
# Needs Playwright and Chromium. In Claude's cloud sessions both are preinstalled:
#   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright  CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
set -e
T=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$T")
# The suite assumes this checkout has the licensed art. Without it every check that hands the page a file
# from art/licensed/ fails -- the whole of The look's section, and the gateway sign -- so the run says
# nothing about the page. Say so loudly: art/licensed/ is gitignored, so a fresh clone and every cloud
# session start without it, and reading those failures as breakage costs an hour. CLAUDE.md,
# "Republishing", has the two ways back (one Artifact read from the published page, or her zips).
if [ ! -d "$P/art/licensed" ]; then
  echo "note: $P/art/licensed/ is missing, so this run is NOT a verdict."
  echo "      Every check that hands the page a file from art/licensed/ fails without it: the whole of"
  echo "      The look's section, and the gateway sign. Measured on 5 October 2026: 29 failures; with the"
  echo "      art in place, all 339 checks pass. Don't read those 29 as the page being broken."
  echo "      Get it back first, one call of a few seconds: CLAUDE.md, \"Republishing\", route 1 reads all"
  echo "      38 files from the published artifact in a single Artifact read with \"paths\"."
  echo "      After that, a failure is real."
  echo
fi
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
export PLAYWRIGHT CHROMIUM
# sh catio/test/run.sh look [room…]: screenshots to look at instead of the test (CLAUDE.md, "Checking a change")
if [ "$1" = look ]; then shift; exec node "$T/look.mjs" "$@"; fi
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
LOCAL_URL="http://127.0.0.1:$PORT/index.html" node "$T/e2e.mjs"
