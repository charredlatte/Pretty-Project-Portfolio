#!/bin/sh
# Wrap the page like the Artifact publish skeleton, with the test runtime first, and run the e2e test.
#   sh catio/test/run.sh
# Needs Playwright and Chromium. In Claude's cloud sessions both are preinstalled:
#   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright  CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
set -e
T=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$T")
# The suite assumes this checkout has the licensed art. Without it the page quite correctly shows its
# no-art warning on the status sign, so the check that wants a clear sign cannot pass, and the checks of
# The look and a skin can't either: they read the packs' files from art/licensed/ to stand in for her own
# drawings. A run without it is therefore not a verdict. Say so, so it doesn't read as a regression:
# art/licensed/ is gitignored, so a fresh clone and every cloud session start without it. CLAUDE.md,
# "Republishing", has the two ways back (one Artifact read from the published page, or her zips).
if [ ! -d "$P/art/licensed" ]; then
  echo "note: $P/art/licensed/ is missing, so this run is NOT a verdict."
  echo "      Expect 29 failures (5 October): the one that wants no warning sign, and the checks of The"
  echo "      look and a skin, which read the packs' files. With the art there, all 339 pass."
  echo "      Get it back first, one call of a few seconds: CLAUDE.md, \"Republishing\", route 1 reads all"
  echo "      38 files from the published artifact in a single Artifact read with \"paths\"."
  echo "      After that, a failure is real. Until then it is the missing art, not the page."
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
