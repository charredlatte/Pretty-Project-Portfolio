#!/usr/bin/env python3
"""Make the app's one committed font: Nunito, the page's --body, cut to the weights the page uses.

    pip install fonttools && python3 catio-app/tools/fonts.py

Nunito is SIL Open Font License 1.1 with no Reserved Font Name, so instancing and subsetting it are
allowed, and so is shipping the result, with the licence beside it (assets/OFL.txt). Google Fonts
ships it as one variable font; SDL_ttf has no call to choose a weight from one, so this writes a static
font for each weight the page's CSS sets body text in: 500 (prose, the body's own), 700 (.tip small, an ask) and 800
(an aside, a count, a pip). Each keeps Latin-1 (her French accents), the general punctuation (the
middle dot, the ellipsis, curly quotes) and the arrows the keyboard line names.

The source is pinned to one commit of github.com/google/fonts, so re-running it gives the same bytes.
"""

import io
import pathlib
import urllib.parse
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

COMMIT = "6e8069ff8ba3dab2a397fb30e7fbd243aba9b57a"
BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/nunito/"
WEIGHTS = {500: "Medium", 700: "Bold", 800: "ExtraBold"}
UNICODES = "U+0020-007E,U+00A0-00FF,U+0152-0153,U+2010-2027,U+2030-205E,U+20AC,U+2122,U+2190-2193"

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"


def fetch(name):
    with urllib.request.urlopen(BASE + urllib.parse.quote(name)) as r:
        return r.read()


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "OFL.txt").write_bytes(fetch("OFL.txt"))
    var = fetch("Nunito[wght].ttf")
    for wght, style in WEIGHTS.items():
        font = instancer.instantiateVariableFont(TTFont(io.BytesIO(var)), {"wght": wght}, updateFontNames=True)
        opts = subset.Options()
        opts.layout_features = ["kern", "liga"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        s = subset.Subsetter(opts)
        s.populate(unicodes=subset.parse_unicodes(UNICODES))
        s.subset(font)
        out = ASSETS / f"Nunito-{style}.ttf"
        font.save(out)
        print(out.name, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
