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
# drawings. Say so, so it doesn't read as a regression: art/licensed/ is gitignored, so a fresh clone and
# every cloud session start without it.
#   Say WHICH checks, never how many. A count in prose has drifted every time one was written here, and a
#   stale one reads as checks having gone missing. Nor by what the failure says: most of these fail with a
#   computed value or a timeout and never mention art/licensed, so "it names a path" would mark the
#   majority of them real -- the very chase this note exists to stop.
art_note() {   # $1: "look" when only screenshots are being taken
  echo "note: some of $P/art/licensed/ is missing, so the page here draws its no-art fallbacks."
  if [ "$1" = look ]; then
    echo "      These screenshots show the warning sign and the pack-less fallbacks rather than the page,"
    echo "      so they cannot be held against her words. Get the art first."
  else
    echo "      This run is NOT a verdict. The missing art explains exactly these, and nothing else: the"
    echo "      check that wants no warning sign, and the checks of The look and a skin -- the ones about"
    echo "      her own pieces, slots, frames and fonts. A failure outside those is real, and once the art"
    echo "      is here every failure is. Most of them say nothing about art/licensed, so go by the check."
  fi
  echo "      Two ways back, in CLAUDE.md, \"Republishing\": read every path under art/licensed/ back from"
  echo "      the published artifact (list its files, then one read -- those paths and no others: the rest"
  echo "      of the listing is committed work here), or rebuild from her zips with catio/tools/build-art.py."
  echo
}
# One file per group, each the LAST its build writes -- build-art.py writes pochi.png last of the top-level
# pieces (463), pastel/icons.png last of the map panel's (364) and ui/logo.png last of the whole run (128) --
# so a build or a fetch that stopped part way is caught too, not just an empty folder. -s, not -f: a
# truncated fetch leaves a file of nothing.
have_art() { [ -s "$P/art/licensed/pochi.png" ] && [ -s "$P/art/licensed/ui/logo.png" ] && [ -s "$P/art/licensed/pastel/icons.png" ]; }
have_art || art_note "$1"
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
LOCAL_URL="http://127.0.0.1:$PORT/index.html" node "$T/e2e.mjs" || { have_art || { echo; art_note; }; exit 1; }
