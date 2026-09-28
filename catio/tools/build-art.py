#!/usr/bin/env python3
"""Rebuild the catio's art from Charlotte's three asset-pack zips.

    pip install pillow
    python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip Top_down_garden_castle.zip Wood_Garden_Asset_Pack.zip

Writes, next to catio/index.html:
  art/house.png                  the Cosy Cabin example cabin at native 16 px tiles, placeholder figure removed
  art/ui/*.png                   frames, plaques, wallpaper and trim cut from the Cosy Cabin tile sheet
  art/licensed/garden.png        the catio garden: pond, rocks and tree from Top Down Garden Castle,
                                 fence, gate, decking and flower boxes from Wood Garden
  art/licensed/meadow.png        a grass tile from Top Down Garden Castle, repeated under the cabin
  art/licensed/mochi-idle.png, mochi-box.png, pochi.png, cat-ui.png   the ToffeeCraft cats, unchanged

Only art/house.png and art/ui/ are committed (Cosy Cabin allows copying, with credit). The ToffeeCraft
and Top Down Garden Castle licences forbid redistributing the files, so art/licensed/ is
gitignored and ships only inside the private artifact. See CLAUDE.md.
"""
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "art"


def member(zf, suffix):
    for n in zf.namelist():
        if n.endswith(suffix) and not n.startswith("__MACOSX"):
            return Image.open(io.BytesIO(zf.read(n))).convert("RGBA")
    raise SystemExit(f"{suffix} not found in {zf.filename}")


def house(cabin_zip):
    ex = member(zipfile.ZipFile(cabin_zip), "CosyCabin_Example2.png")
    n = ex.resize((ex.width // 3, ex.height // 3), Image.NEAREST)  # the example is drawn at 3x
    px = n.load()
    for y in range(200, 250):  # paint the green placeholder character out of the living-room floor
        for x in range(165, 200):
            r, g, b, a = px[x, y]
            if g > r + 30 and g > b + 30:
                px[x, y] = px[x, y - 32]
    # Clear the black night around the cabin so it can sit in the meadow.
    w, h = n.size
    todo = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    seen = set()
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        r, g, b, a = px[x, y]
        if a and max(r, g, b) > 34:
            continue
        px[x, y] = (0, 0, 0, 0)
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return n


def ui(cabin_zip):
    """Cut the page's frames, plaques and fills out of the Cosy Cabin tile sheet (committable)."""
    tm = member(zipfile.ZipFile(cabin_zip), "CosyCabin_TileMap.png")
    out = OUT / "ui"
    out.mkdir(exist_ok=True)

    def cut(box, name):
        c = tm.crop(box)
        c = c.crop(c.getbbox())
        c.save(out / name)
        return c

    # The wooden trim the artist framed the sheet's sections with, rebuilt as a 48 px 9-slice.
    tl = tm.crop((320, 16, 336, 32))
    top = tm.crop((352, 16, 368, 32))
    left = tm.crop((320, 64, 336, 80))
    frame = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    lr, tb = Image.FLIP_LEFT_RIGHT, Image.FLIP_TOP_BOTTOM
    frame.paste(tl, (0, 0)); frame.paste(tl.transpose(lr), (32, 0))
    frame.paste(tl.transpose(tb), (0, 32)); frame.paste(tl.transpose(lr).transpose(tb), (32, 32))
    frame.paste(top, (16, 0)); frame.paste(top.transpose(tb), (16, 32))
    frame.paste(left, (0, 16)); frame.paste(left.transpose(lr), (32, 16))
    frame.save(out / "frame.png")
    paper_rgb = tm.getpixel((4, 40))

    def filled(im, name):
        """Paint the transparent inside of a frame with the paper colour, so it can be a 9-slice with fill."""
        im = im.copy()
        px = im.load()
        w, h = im.size
        todo, seen = [(w // 2, h // 2)], set()
        while todo:
            x, y = todo.pop()
            if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or px[x, y][3]:
                continue
            seen.add((x, y))
            px[x, y] = paper_rgb
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        im.save(out / name)

    filled(frame, "frame-fill.png")

    cut((64, 48, 80, 64), "paper-circles.png")   # cream wallpaper with circles
    cut((0, 68, 16, 80), "rail.png")             # wainscot rail
    cut((14, 98, 118, 111), "bar.png")           # capped wooden bar, for dividers
    cut((354, 34, 384, 62), "plaque-wood.png")   # raised floor plaques, for buttons and chips
    cut((418, 34, 448, 62), "plaque-dark.png")
    cut((418, 272, 448, 302), "plaque-pink.png")
    cut((482, 272, 512, 302), "plaque-green.png")
    filled(cut((224, 160, 256, 192), "ring.png"), "ring-fill.png")  # cream wall-outline ring, for cards and inputs
    cut((176, 166, 210, 202), "slot.png")        # framed slot
    objects = member(zipfile.ZipFile(cabin_zip), "CosyCabin_Objects.png")
    objects.crop((960, 82, 976, 112)).save(out / "door.png")  # green door, for the Rooms button


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


def garden(garden_zip, wood_zip, size):
    sheet = spring(member(zipfile.ZipFile(garden_zip), "Top down Garden Castle.png"))
    wood = zipfile.ZipFile(wood_zip)
    crop = lambda x, y, w, h: sheet.crop((x, y, x + w, y + h))
    piece = lambda name: member(wood, name)
    g = Image.new("RGBA", size, (0, 0, 0, 0))
    stamp = lambda im, x, y: g.alpha_composite(im, (x, y))

    stamp(crop(113, 293, 81, 121), 316, 176)         # tree, top right
    stamp(crop(64, 84, 64, 56), 250, 262)            # pond, bottom left
    stamp(crop(99, 251, 24, 23), 302, 300)           # rocks by the pond
    stamp(crop(41, 258, 23, 16), 246, 250)

    # Deck off the living room, with a doorway cut through the wall where the floor inside is clear.
    floor = piece("Floor/Brown-floor-1.png")
    for dx in range(2):
        for dy in range(2):
            stamp(floor, 244 + dx * 32, 186 + dy * 32)
    stamp(floor.crop((0, 0, 10, 32)), 234, 196)
    stamp(piece("Small wooden flower box/Small wooden flower box-18.png"), 288, 184)
    stamp(piece("Small wooden flower box/Small wooden flower box-14.png"), 288, 226)

    for sx, x, y in [(64, 312, 254), (80, 322, 274), (96, 330, 294)]:
        stamp(crop(sx, 49, 15, 15), x, y)            # stepping stones from the deck to the gate

    # White fence round the open sides, with the flower arch as the gate.
    post, rail_end = piece("Fences/White fence/White-fence-4.png"), piece("Fences/White fence/White-fence-5.png")
    for y in range(182, 318, 36):
        stamp(post, 388, y)
    left, mid, right = (piece(f"Fences/White fence/White-fence-{i}.png") for i in (1, 2, 3))
    fy = 328
    stamp(left, 244, fy)
    for x in range(272, 332, 32):
        stamp(mid, x, fy)
    stamp(piece("Fences/Gates/White gate/White-red-flower-gate-1.png"), 334, fy - 21)
    stamp(right, 368, fy)
    stamp(rail_end, 388, fy - 23)
    stamp(crop(49, 424, 34, 30), 350, 184)           # bush tucked under the bedroom wall
    return g, crop(16, 16, 112, 32)


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    cabin_zip, cats_zip, garden_zip, wood_zip = sys.argv[1:]
    (OUT / "licensed").mkdir(parents=True, exist_ok=True)
    h = house(cabin_zip)
    h.save(OUT / "house.png")
    ui(cabin_zip)
    g, meadow = garden(garden_zip, wood_zip, h.size)
    g.save(OUT / "licensed" / "garden.png")
    meadow.save(OUT / "licensed" / "meadow.png")
    cats = zipfile.ZipFile(cats_zip)
    for suffix, name in [("MochiFree/Idle.png", "mochi-idle.png"), ("MochiFree/Box3.png", "mochi-box.png"),
                         ("PochiFree/FreeSprites.png", "pochi.png"), ("CatUIFree/free.png", "cat-ui.png")]:
        member(cats, suffix).save(OUT / "licensed" / name)
    print("art written to", OUT)


if __name__ == "__main__":
    main()
