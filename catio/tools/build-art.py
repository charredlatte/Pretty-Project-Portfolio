#!/usr/bin/env python3
"""Rebuild the catio's art from Charlotte's nine asset-pack zips.

    pip install pillow fonttools
    python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip "Top down garden castle.zip" \
        "Wood Garden Asset Pack.zip" "Pixel Art Top Down - Basic v1.2.3.zip" \
        "Sprout Lands - UI Pack - Basic pack.zip" plants.zip \
        "Sprout Lands - Sprites - Basic pack.zip" "Little Dreamyland - Free Pack.zip"
    python3 catio/tools/build-art.py "Sprout Lands - UI Pack - Basic pack.zip"    # the interface alone

(The zips' names don't matter, only their order.) Writes, next to catio/index.html:
  art/licensed/house.png         the manor's ground floor (floors, walls, glass, doors, the south facade),
                                 drawn to manor.py from every pack
  art/licensed/house-upper.png   its upper floor: the library, bedroom and ensuite, and the landing over the
                                 kitchen and hall
  art/furniture.png              the Cosy Cabin furniture, one cell per piece in furniture.py's catalogue
  art/licensed/furniture.png     the rest of the furniture (ToffeeCraft, Wood Garden, Cainos, plants.zip)
  art/licensed/decor.png         the grounds: the catio's deck and fence, the drive, fountain, the parterre,
                                 arch gate, spruce forest and lawn (every pack but the cats; manor.grounds)
  art/licensed/meadow.png        a grass tile from Top Down Garden Castle, repeated under the manor
  art/licensed/mochi-idle.png, mochi-box.png, pochi.png   the ToffeeCraft cats, unchanged
  art/licensed/ui/               the interface, cut from Sprout Lands: panels, buttons, fields, bubbles,
                                 brackets, the sound switch, the mood faces, the cursors and sprout.ttf
and rewrites the page's MANOR block (furniture.py), which needs no zips on its own.

Only art/furniture.png is committed (Cosy Cabin allows copying, with credit). The house mixes every pack,
and the other packs' licences forbid redistributing the files, so art/licensed/ is gitignored and ships
only inside the private artifact. See CLAUDE.md.
"""
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

import furniture
import manor

OUT = Path(__file__).resolve().parent.parent / "art"


def member(zf, suffix):
    for n in zf.namelist():
        if n.endswith(suffix) and not n.startswith("__MACOSX"):
            return Image.open(io.BytesIO(zf.read(n))).convert("RGBA")
    raise SystemExit(f"{suffix} not found in {zf.filename}")


def raw(zf, suffix):
    for n in zf.namelist():
        if n.endswith(suffix) and not n.startswith("__MACOSX"):
            return zf.read(n)
    raise SystemExit(f"{suffix} not found in {zf.filename}")


def recolor(im, ramp):
    """Swap a piece's colours, e.g. the cream button's face, highlight and bottom for greens."""
    im = im.copy()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            hexa = "%02X%02X%02X" % (r, g, b)
            if a and hexa in ramp:
                px[x, y] = tuple(int(ramp[hexa][i:i + 2], 16) for i in (0, 2, 4)) + (a,)
    return im


# The cream button's colours (outline, highlight, face, bottom face, shadow) and their green and pink twins.
GREEN = {"E8CFA6": "C0D470", "F3E5C2": "DDE8A6", "C49A6C": "93B259", "AA7959": "6E7F45", "90625D": "5A6443"}
PINK = {"E8CFA6": "EBB7AE", "F3E5C2": "F7D8CF", "C49A6C": "C98583", "AA7959": "9B5670", "90625D": "7C4459"}

# Cells of faces.png, in the page's MOODS order: which of the pack's cat emoji each mood wears.
FACES = [("cry", 1, 6), ("meow", 2, 5), ("box", 0, 5), ("idle", 1, 5), ("sleep", 2, 6), ("keep", 3, 5)]   # (mood, column, row); keep: a queen's heart eyes


def sprout(sprout_zip):
    """Cut the page's interface from Cup Nooble's Sprout Lands UI pack into art/licensed/ui/.

    Its licence allows changes but no redistribution, even modified, so none of it is committed.
    Every piece is a 9-slice the page scales by --u (one art pixel on screen)."""
    z = zipfile.ZipFile(sprout_zip)
    out = OUT / "licensed" / "ui"
    out.mkdir(parents=True, exist_ok=True)
    basic = member(z, "Sprite sheet for Basic Pack.png")
    square = member(z, "Square Buttons 26x26.png")
    settings = member(z, "UI Settings Buttons.png")

    member(z, "Setting menu.png").crop((139, 12, 245, 134)).save(out / "panel.png")      # menus, dialogs, the sign
    cream = square.crop((11, 59, 37, 87))
    cream.save(out / "button.png")                                                  # buttons, list cards
    square.crop((11, 11, 37, 39)).save(out / "button-hover.png")                    # the white one, lit
    square.crop((59, 59, 85, 85)).save(out / "button-down.png")                     # pressed
    recolor(cream, GREEN).save(out / "button-green.png")
    recolor(cream, PINK).save(out / "button-pink.png")
    square.crop((59, 11, 85, 37)).save(out / "field.png")                           # the white one, pressed in: inputs
    basic.crop((153, 9, 183, 39)).save(out / "frame.png")                           # picture frame, for portraits
    settings.crop((11, 20, 69, 24)).save(out / "divider.png")
    basic.crop((275, 52, 285, 61)).save(out / "arrow.png")                          # the cream arrow on a select

    # the grey speech bubble, with its tail cut off to hang under a 9-slice body
    bub = member(z, "speech_bubble_grey.png").crop((11, 11, 53, 58))
    body = bub.crop((0, 0, 42, 42))
    for y in range(38, 42):
        for x in range(9, 33):
            body.putpixel((x, y), body.getpixel((8, y)))
    body.save(out / "bubble.png")
    bub.crop((16, 38, 27, 47)).save(out / "bubble-tail.png")

    # the white selection brackets, as a 9-slice with empty edges: rooms light up with them
    corners = Image.new("RGBA", (20, 20))
    for box, at in [((148, 148, 156, 157), (0, 0)), ((164, 148, 172, 157), (12, 0)),
                    ((148, 164, 156, 173), (0, 11)), ((164, 164, 172, 173), (12, 11))]:
        corners.alpha_composite(basic.crop(box), at)
    corners.save(out / "corners.png")

    # the sound switch, off then on; the sign's live tick and warning cross
    toggle = Image.new("RGBA", (56, 18))
    toggle.alpha_composite(settings.crop((2, 151, 30, 169)), (0, 0))
    toggle.alpha_composite(settings.crop((66, 151, 94, 169)), (28, 0))
    toggle.save(out / "toggle.png")
    status = Image.new("RGBA", (24, 12))
    status.alpha_composite(basic.crop((242, 67, 254, 78)), (0, 1))
    status.alpha_composite(basic.crop((244, 82, 254, 94)), (13, 0))
    status.save(out / "status.png")

    # the mood faces: the pack's cat emoji
    emoji = member(z, "Emoji_Spritesheet_Free.png")
    faces = Image.new("RGBA", (32 * len(FACES), 32))
    for i, (_, col, row) in enumerate(FACES):
        faces.alpha_composite(emoji.crop((col * 32, row * 32, col * 32 + 32, row * 32 + 32)), (i * 32, 0))
    faces.save(out / "faces.png")

    # the queens' crown: the pack's crown icon, gilded and outlined like its star
    gold = recolor(member(z, "All Icons.png").crop((82, 19, 94, 30)), {"FBFBF6": "EAE178"})
    crown = Image.new("RGBA", (14, 13))
    crown.alpha_composite(gold, (1, 1))
    px = crown.load()
    ring = [(x, y) for y in range(13) for x in range(14) if not px[x, y][3] and any(
        0 <= x + dx < 14 and 0 <= y + dy < 13 and px[x + dx, y + dy][3] and px[x + dx, y + dy][:3] == (0xEA, 0xE1, 0x78)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for xy in ring:
        px[xy] = (0x79, 0x5E, 0x53, 255)
    crown.save(out / "crown.png")
    # the stars by what a queen keeps: gold when she says it, brown otherwise
    special = member(z, "Special Icons.png")
    stars = Image.new("RGBA", (20, 8))
    stars.alpha_composite(special.crop((3, 4, 13, 12)), (0, 0))
    stars.alpha_composite(special.crop((35, 4, 45, 12)), (10, 0))
    stars.save(out / "stars.png")

    # the cat-paw pointers, doubled to the page's scale
    for suffix, name in [("Catpaw Mouse icon.png", "cursor.png"), ("Catpaw pointing Mouse icon.png", "cursor-point.png")]:
        paw = member(z, suffix)
        paw.resize((32, 32), Image.NEAREST).save(out / name)

    (out / "sprout.ttf").write_bytes(pixel_font(raw(z, "pixelFont-7-8x14-sproutLands.ttf")))


# Accents in the font's own 2-pixel strokes, as (x, y) font pixels above the capital (y 15-16) or under it.
ACCENTS = {
    "acute": [(4, 16), (5, 16), (3, 15), (4, 15)],
    "grave": [(2, 16), (3, 16), (3, 15), (4, 15)],
    "circumflex": [(3, 16), (4, 16), (1, 15), (2, 15), (5, 15), (6, 15)],
    "dieresis": [(1, 16), (2, 16), (5, 16), (6, 16), (1, 15), (2, 15), (5, 15), (6, 15)],
    "cedilla": [(3, -1), (4, -1), (2, -2), (3, -2)],
}
ACCENTED = {  # base, accent: the capital and small letter share one glyph, as in the rest of the font
    "A": {"grave": "\u00c0\u00e0", "acute": "\u00c1\u00e1", "circumflex": "\u00c2\u00e2", "dieresis": "\u00c4\u00e4"},
    "C": {"cedilla": "\u00c7\u00e7"},
    "E": {"grave": "\u00c8\u00e8", "acute": "\u00c9\u00e9", "circumflex": "\u00ca\u00ea", "dieresis": "\u00cb\u00eb"},
    "I": {"grave": "\u00cc\u00ec", "acute": "\u00cd\u00ed", "circumflex": "\u00ce\u00ee", "dieresis": "\u00cf\u00ef"},
    "O": {"grave": "\u00d2\u00f2", "acute": "\u00d3\u00f3", "circumflex": "\u00d4\u00f4", "dieresis": "\u00d6\u00f6"},
    "U": {"grave": "\u00d9\u00f9", "acute": "\u00da\u00fa", "circumflex": "\u00db\u00fb", "dieresis": "\u00dc\u00fc"},
    "Y": {"dieresis": "\u0178\u00ff"},
}


def pixel_font(ttf):
    """The pack's pixel font with the letters French names need: accents drawn in its own strokes,
    a middle dot, an ellipsis, and curly quotes and dashes mapped to its straight ones."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTFont

    f = TTFont(io.BytesIO(ttf))
    if "DSIG" in f:
        del f["DSIG"]
    glyf, hmtx = f["glyf"], f["hmtx"]
    P = 128   # font units per pixel
    order = list(f.getGlyphOrder())
    unicode_tables = [t for t in f["cmap"].tables if t.isUnicode()]

    def pixels(name):
        coords, ends, _ = glyf[name].getCoordinates(glyf)
        px, start = set(), 0
        for end in ends:
            pts = coords[start:end + 1]
            start = end + 1
            px.add((min(x for x, _ in pts) // P, min(y for _, y in pts) // P))
        return px

    def add(name, px, advance, chars):
        pen = TTGlyphPen(None)
        for x, y in sorted(px):
            pen.moveTo((x * P, (y + 1) * P)); pen.lineTo(((x + 1) * P, (y + 1) * P))
            pen.lineTo(((x + 1) * P, y * P)); pen.lineTo((x * P, y * P)); pen.closePath()
        g = pen.glyph()
        g.recalcBounds(glyf)
        glyf[name] = g
        hmtx[name] = (advance, min(x for x, _ in px) * P)
        order.append(name)
        for ch in chars:
            for t in unicode_tables:
                t.cmap[ord(ch)] = name

    def alias(existing, chars):
        for ch in chars:
            for t in unicode_tables:
                t.cmap[ord(ch)] = existing

    for base, marks in ACCENTED.items():
        for mark, chars in marks.items():
            add(base + mark, pixels(base) | set(ACCENTS[mark]), hmtx[base][0], chars)
    add("periodcentered", {(0, 6), (1, 6), (0, 7), (1, 7)}, 4 * P, "\u00b7")
    add("ellipsis", {(x + dx, y) for x in (0, 4, 8) for dx in (0, 1) for y in (0, 1)}, 12 * P, "\u2026")
    alias("quotesingle", "\u2018\u2019")
    alias("quotedbl", "\u201c\u201d")
    alias("hyphen", "\u2013\u2014")
    f.setGlyphOrder(order)
    buf = io.BytesIO()
    f.save(buf)
    return buf.getvalue()


def spring(im):
    """Shift the pack's olive greens toward the bright spring green of the reference art."""
    import colorsys
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if 0.12 < h < 0.45 and s > 0.25:
                h, s, v = min(h + 0.045, 0.45), min(s * 0.88, 1), min(v * 1.16 + 0.04, 1)
                r, g, b = (round(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
                px[x, y] = (r, g, b, a)
    return im


def main():
    if len(sys.argv) == 2:
        sprout(sys.argv[1])
        print("interface written to", OUT / "licensed" / "ui")
        return
    if len(sys.argv) != 10:
        raise SystemExit(__doc__)
    (cabin_zip, cats_zip, garden_zip, wood_zip, stone_zip, sprout_zip, plants_zip,
     sprites_zip, dreamy_zip) = sys.argv[1:]
    (OUT / "licensed").mkdir(parents=True, exist_ok=True)
    zips = [zipfile.ZipFile(z) for z in sys.argv[1:]]

    def load(end):
        for z in zips:
            for n in z.namelist():
                if (n == end or n.endswith("/" + end)) and not n.startswith("__MACOSX"):
                    return Image.open(io.BytesIO(z.read(n))).convert("RGBA")
        raise SystemExit(end + " not found in the zips")
    # the manor's shell, from every pack (licensed), and its grounds
    manor.shell(load, "ground").save(OUT / "licensed" / "house.png")
    manor.shell(load, "upper").save(OUT / "licensed" / "house-upper.png")
    sheet = spring(member(zipfile.ZipFile(garden_zip), "Top down Garden Castle.png"))
    wood = zipfile.ZipFile(wood_zip)
    sz = zipfile.ZipFile(stone_zip)
    dreamy = "Little Dreamyland - Free Pack/Tileset/"
    more = {"nature": load(dreamy + "Nature_Tileset.png"), "exterior": load(dreamy + "Exterior_Tileset.png"),
            "floor": load(dreamy + "Tileset_Floor_Detail.png"), "biome": load("Objects/Basic_Grass_Biom_things.png"),
            "plant": spring(load("Texture/TX Plant.png")), "cosy": load("CosyCabin_Objects.png"),
            "ground": load("Texture/TX Tileset Stone Ground.png").crop((128, 0, 160, 32))}
    manor.grounds(sheet, lambda name: member(wood, name), member(sz, "Texture/TX Props.png"),
                  member(sz, "Texture/TX Struct.png"), more).save(OUT / "licensed" / "decor.png")
    # the furniture, as two atlases the page places pieces from: Cosy Cabin's (committed) and the rest
    atl = furniture.atlases(load)
    atl["cc"].save(OUT / "furniture.png")
    atl["lic"].save(OUT / "licensed" / "furniture.png")
    sheet.crop((16, 16, 128, 48)).save(OUT / "licensed" / "meadow.png")
    cats = zipfile.ZipFile(cats_zip)
    for suffix, name in [("MochiFree/Idle.png", "mochi-idle.png"), ("MochiFree/Box3.png", "mochi-box.png"),
                         ("PochiFree/FreeSprites.png", "pochi.png")]:
        member(cats, suffix).save(OUT / "licensed" / name)
    sprout(sprout_zip)
    furniture.write_page(OUT.parent / "index.html")
    print("art written to", OUT, "and the page's MANOR block updated")


if __name__ == "__main__":
    main()
