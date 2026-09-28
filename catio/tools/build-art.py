#!/usr/bin/env python3
"""Rebuild the catio's art from Charlotte's five asset-pack zips.

    pip install pillow
    python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip Top_down_garden_castle.zip \
        Wood_Garden_Asset_Pack.zip "Pixel_Art_Top_Down_-_Basic_v1.2.3.zip"

Writes, next to catio/index.html:
  art/house.png                  the cabin, drawn from Cosy Cabin tiles and furniture to the plan in cabin.py
  art/ui/*.png                   frames, plaques, wallpaper and trim cut from the Cosy Cabin tile sheet
  art/licensed/decor.png         the catio, the garden and a few indoor pieces from Top Down Garden Castle,
                                 Wood Garden and Cainos's Top Down Basic (see cabin.decor)
  art/licensed/meadow.png        a grass tile from Top Down Garden Castle, repeated under the cabin
  art/licensed/emblems.png       the little things a cat carries to show its project
  art/licensed/mochi-idle.png, mochi-box.png, pochi.png, cat-ui.png   the ToffeeCraft cats, unchanged

Only art/house.png and art/ui/ are committed (Cosy Cabin allows copying, with credit). The ToffeeCraft,
Top Down Garden Castle and Cainos licences forbid redistributing the files, so art/licensed/ is
gitignored and ships only inside the private artifact. See CLAUDE.md.
"""
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

import cabin

OUT = Path(__file__).resolve().parent.parent / "art"


def member(zf, suffix):
    for n in zf.namelist():
        if n.endswith(suffix) and not n.startswith("__MACOSX"):
            return Image.open(io.BytesIO(zf.read(n))).convert("RGBA")
    raise SystemExit(f"{suffix} not found in {zf.filename}")


def example(cabin_zip):
    """The pack's second example cabin at native 16 px tiles (it ships drawn at 3x); used for its floorboards."""
    ex = member(zipfile.ZipFile(cabin_zip), "CosyCabin_Example2.png")
    return ex.resize((ex.width // 3, ex.height // 3), Image.NEAREST)


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


EMBLEM = (20, 24)   # one cell of emblems.png; the page's EMBLEMS list follows this order


def emblems(cats_zip, cabin_zip):
    """Small pieces a cat carries to show its project: tin, coin, books, star, plant, yarn."""
    pochi = member(zipfile.ZipFile(cats_zip), "PochiFree/FreeSprites.png")
    catui = member(zipfile.ZipFile(cats_zip), "CatUIFree/free.png")
    objects = member(zipfile.ZipFile(cabin_zip), "CosyCabin_Objects.png")
    pieces = [
        pochi.crop((103, 343, 121, 361)),     # tin of cat food: groceries, meals
        catui.crop((160, 48, 176, 64)),       # coin button: shops, business, money
        objects.crop((835, 81, 846, 95)),     # books: legal, admin, study
        objects.crop((896, 241, 912, 256)),   # star: portfolio, design
        objects.crop((834, 584, 848, 608)),   # potted plant: home, garden
        pochi.crop((137, 410, 154, 425)),     # yarn: everything else
    ]
    w, h = EMBLEM
    sheet = Image.new("RGBA", (w * len(pieces), h))
    for i, p in enumerate(pieces):
        sheet.alpha_composite(p, (i * w + (w - p.width) // 2, h - p.height))
    return sheet


def main():
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    cabin_zip, cats_zip, garden_zip, wood_zip, stone_zip = sys.argv[1:]
    (OUT / "licensed").mkdir(parents=True, exist_ok=True)
    cz = zipfile.ZipFile(cabin_zip)
    cabin.house(member(cz, "CosyCabin_TileMap.png"), member(cz, "CosyCabin_Objects.png"), example(cabin_zip)).save(OUT / "house.png")
    ui(cabin_zip)
    sheet = spring(member(zipfile.ZipFile(garden_zip), "Top down Garden Castle.png"))
    wood = zipfile.ZipFile(wood_zip)
    sz = zipfile.ZipFile(stone_zip)
    cabin.decor(cabin.SIZE, sheet, lambda name: member(wood, name), member(sz, "Texture/TX Props.png"),
                member(sz, "Texture/TX Struct.png")).save(OUT / "licensed" / "decor.png")
    sheet.crop((16, 16, 128, 48)).save(OUT / "licensed" / "meadow.png")
    emblems(cats_zip, cabin_zip).save(OUT / "licensed" / "emblems.png")
    cats = zipfile.ZipFile(cats_zip)
    for suffix, name in [("MochiFree/Idle.png", "mochi-idle.png"), ("MochiFree/Box3.png", "mochi-box.png"),
                         ("PochiFree/FreeSprites.png", "pochi.png"), ("CatUIFree/free.png", "cat-ui.png")]:
        member(cats, suffix).save(OUT / "licensed" / name)
    print("art written to", OUT)


if __name__ == "__main__":
    main()
