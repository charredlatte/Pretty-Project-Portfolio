"""The manor's furniture: a catalogue of pieces, and where each one stands by default.

Furniture is not drawn into the house any more. Each piece is a sprite the page places, so renovation mode
can move it (see docs/renovation-mode.md). This file is the one source for:

  CATALOGUE  key -> sheet, box on the sheet, kind, footprint, stations
  LAYOUT     room -> [(key, x, y)], the default placement (native pixels, the sprite's top-left)

kind       essential: never moves (front door mat, stairs, filing cabinets, the brain's desk)
           connected: carries a station, so it can move but not be removed
           decor:     can move, be added and be removed
layer      rug (under everything), wall (on the back wall band), floor (sorted by bottom edge, like cats),
           top (set into a floor piece: a sink in a counter)
footprint  the part of the sprite that stands on the floor, as (dx, dy, w, h) inside the box; no cat
           stands on it. Rugs and wall pieces have none.
stations   where a cat goes to show its state: (state, dx, dy), the point under its feet, relative to the
           piece's top-left. States: needs, review, work, fail, sleep, upstairs; queen for the room's queen.

Sheets are paths inside Charlotte's unpacked packs. "cc" is Cosy Cabin (committable); every other sheet
is licensed and ships only inside the private artifact.
"""
from PIL import Image

WG = "Wood_Garden_Asset_Pack/Wood Garden Asset Pack/"   # rowdy41: one piece per file; a sheet named "wg:<file>"
SHEETS = {
    "cc": "CosyCabin/CosyCabin_Objects.png",
    "tc": "CatMegaFree/CatMegaFree/CatRoomFree/Furnitures.png",
    "cainos": "Pixel_Art_Top_Down_-_Basic_v1.2.3/Texture/TX Struct.png",
    "pochi": "CatMegaFree/CatMegaFree/PochiFree/FreeSprites.png",
}
COMMITTABLE = {"cc"}


def piece(sheet, box, kind="decor", layer="floor", foot=None, stations=(), scale=1):
    x, y, w, h = box
    w2, h2 = round(w * scale), round(h * scale)
    if foot is None and layer == "floor":
        fh = max(4, round(h2 * 0.75))                 # a 3/4-view piece: all but its top quarter is in the way
        foot = (0, h2 - fh, w2, fh)
    return {"sheet": sheet, "box": list(box), "kind": kind, "layer": layer, "foot": list(foot) if foot else None,
            "stations": [list(s) for s in stations], "scale": scale, "size": [w2, h2]}


CATALOGUE = {
    # the great hall
    "stairs_west": piece("cainos", (48, 288, 90, 96), "essential", foot=(0, 30, 90, 66),
                         stations=[("upstairs", 30, 60), ("upstairs", 52, 44), ("upstairs", 72, 30)]),
    "stairs_east": piece("cainos", (56, 384, 88, 96), "essential", foot=(0, 30, 88, 66),
                         stations=[("upstairs", 58, 60), ("upstairs", 36, 44), ("upstairs", 16, 30)]),
    "door_mat": piece("cc", (1009, 245, 30, 10), "essential", "rug", stations=[("needs", 9, 8), ("needs", 22, 8)]),
    "rug_red_diamond": piece("cc", (1008, 81, 48, 30), "connected", "rug", stations=[("fail", 24, 18)]),
    "rug_blue_diamond": piece("cc", (1008, 49, 48, 30), "connected", "rug", stations=[("fail", 24, 18)]),
    "filing_cabinet": piece("cc", (608, 628, 16, 27), "essential", stations=[("review", -8, 34)]),
    "writing_desk": piece("cc", (304, 507, 32, 32), "connected", stations=[("work", 16, 42)]),
    "armchair_pink": piece("cc", (12, 66, 24, 30), "connected", stations=[("queen", 12, 36)]),
    "lamp_floor": piece("cc", (897, 50, 13, 30)),
    "plant_pampas": piece("cc", (17, 868, 15, 43)),
    "plant_snake": piece("cc", (82, 880, 11, 31)),
    # cat cushions: Cosy Cabin's little round rugs, where a cat curls up asleep
    "cushion_blue": piece("cc", (1009, 314, 14, 14), "connected", "rug", stations=[("sleep", 7, 10)]),
    "cushion_green": piece("cc", (1025, 314, 14, 14), "connected", "rug", stations=[("sleep", 7, 10)]),
    "cushion_orange": piece("cc", (1009, 346, 14, 14), "connected", "rug", stations=[("sleep", 7, 10)]),
    "cushion_white": piece("cc", (1025, 346, 14, 14), "connected", "rug", stations=[("sleep", 7, 10)]),
    # the library, the brain
    "bookcase_dark_books": piece("wg:Bookshelf/Dark-wooden-bookshelf-2.png", (0, 0, 52, 58), foot=(0, 34, 52, 24)),
    "bookcase_red_books": piece("wg:Bookshelf/Red-wooden-bookshelf-2.png", (0, 0, 52, 58), foot=(0, 34, 52, 24)),
    "bookcase_filled": piece("cc", (657, 406, 46, 52), foot=(0, 30, 46, 22)),
    "brain_desk": piece("cc", (7, 272, 50, 32), "essential", foot=(0, 6, 50, 26)),
    "chair_back": piece("cc", (641, 282, 14, 22), "connected", foot=(0, 0, 0, 0), stations=[("work", 7, 22)]),
    "brain_chest": piece("wg:Chest/Chest-1.png", (0, 0, 22, 21), "essential"),
    "armchair_blue": piece("cc", (409, 66, 22, 30), "connected", stations=[("queen", 11, 36)]),
    # the drawing room
    "fireplace": piece("cc", (368, 176, 32, 42), "essential", foot=(0, 30, 32, 12)),
    "sofa_blue_back": piece("cc", (620, 74, 40, 22), "connected", foot=(0, 0, 0, 0), stations=[("sleep", 20, 16)]),
    "armchair_blue_l": piece("cc", (409, 66, 22, 30), "connected", stations=[("queen", 11, 36)]),
    "armchair_blue_r": piece("cc", (481, 66, 22, 30), "decor"),
    # the kitchen
    "fridge": piece("cc", (384, 808, 16, 40), "decor", foot=(0, 20, 16, 20)),
    "pantry": piece("cc", (448, 806, 16, 42), "decor", foot=(0, 22, 16, 20)),
    "counter": piece("cc", (576, 628, 16, 27), foot=(0, 10, 16, 17)),
    "counter_drawers": piece("cc", (608, 628, 16, 27), foot=(0, 10, 16, 17)),
    "counter_door": piece("cc", (640, 628, 16, 27), foot=(0, 10, 16, 17)),
    "hob": piece("cc", (576, 756, 16, 27), foot=(0, 10, 16, 17)),
    "sink": piece("cc", (2, 784, 28, 15), layer="top"),
    "island": piece("cc", (576, 628, 16, 27), "connected", foot=(0, 10, 16, 17), stations=[("work", 8, 32)]),
    "chair_front": piece("cc", (609, 276, 14, 28), "connected", stations=[("queen", 7, 32)]),
    "runner_blue": piece("cc", (1009, 113, 30, 15), "connected", "rug", stations=[("fail", 15, 10)]),
    "bowl_food": piece("pochi", (9, 207, 43, 37), scale=0.5),
    "bowl_water": piece("tc", (395, 335, 43, 37), scale=0.5),
    "food_bag": piece("pochi", (216, 267, 33, 62), scale=0.5),
}

# the default layout, room by room: (key, x, y), native pixels, the sprite's top-left
LAYOUT = {
    # Great hall: a double staircase up to the landing either side of the library door; the front door's
    # mat; a writing desk and the queen's chair to the west, the filing cabinet and a cat bed to the east
    "hall": [
        ("stairs_west", 309, 213), ("stairs_east", 456, 213),
        ("door_mat", 411, 372), ("rug_red_diamond", 403, 318),
        ("lamp_floor", 399, 262), ("lamp_floor", 441, 262),
        ("writing_desk", 316, 316), ("armchair_pink", 360, 322),
        ("filing_cabinet", 524, 316), ("cushion_blue", 470, 344), ("cushion_orange", 494, 356),
        ("plant_pampas", 312, 340), ("plant_snake", 530, 350),
    ],
    # Library, the brain: book-filled shelves either side of a tall window; the brain's desk in the middle
    # (a cat at it is working), its chest where dropped files land, a reading chair for the queen, a rug
    "brain": [
        ("bookcase_dark_books", 357, 64), ("bookcase_dark_books", 442, 64),
        ("rug_blue_diamond", 364, 168),
        ("armchair_blue", 360, 124), ("lamp_floor", 384, 122), ("cushion_green", 386, 150),
        ("brain_desk", 402, 128), ("chair_back", 420, 152),
        ("filing_cabinet", 478, 124), ("brain_chest", 454, 178),
    ],
    # Drawing room: the fireplace between two tall windows, a sofa facing it (a cat asleep on it), armchairs
    # either side of the hearth rug, a writing desk in the corner, the filing cabinet by the east window
    "living": [
        ("fireplace", 569, 69), ("rug_red_diamond", 561, 136),
        ("armchair_blue_r", 532, 140), ("armchair_blue_l", 614, 140),
        ("sofa_blue_back", 565, 172), ("cushion_white", 596, 114),
        ("writing_desk", 504, 104), ("filing_cabinet", 640, 104),
        ("lamp_floor", 520, 168), ("plant_snake", 628, 176),
    ],
    # Kitchen: the counter run under the window (fridge, drawers, the sink, the hob, a pantry), an island to
    # work at, the cats' bowls and food bag by the west glass, a runner, a cushion, the filing cabinet
    "kitchen": [
        ("fridge", 86, 74), ("counter_drawers", 102, 89), ("counter", 118, 89), ("counter_door", 134, 89),
        ("hob", 150, 89), ("counter", 166, 89), ("pantry", 184, 72), ("filing_cabinet", 206, 89),
        ("sink", 120, 91),
        ("island", 132, 140), ("island", 148, 140), ("chair_front", 112, 138),
        ("bowl_food", 90, 170), ("bowl_water", 90, 186), ("food_bag", 114, 172),
        ("runner_blue", 150, 184), ("cushion_orange", 190, 150),
    ],
}


def sprite(key, packs, cache={}):
    c = CATALOGUE[key]
    if c["sheet"] not in cache:
        path = WG + c["sheet"][3:] if c["sheet"].startswith("wg:") else SHEETS[c["sheet"]]
        cache[c["sheet"]] = Image.open(packs + path).convert("RGBA")
    x, y, w, h = c["box"]
    im = cache[c["sheet"]].crop((x, y, x + w, y + h))
    if c["scale"] != 1:
        im = im.resize(tuple(c["size"]), Image.NEAREST)
    return im


def placed(only=None):
    """Every piece in the layout as (key, x, y, room), in draw order: rugs, wall pieces, then by bottom edge."""
    rows = [(k, x, y, room) for room, items in LAYOUT.items() if not only or room == only for k, x, y in items]
    order = {"rug": 0, "wall": 1, "floor": 2, "top": 3}
    return sorted(rows, key=lambda r: (order[CATALOGUE[r[0]]["layer"]], r[2] + CATALOGUE[r[0]]["size"][1]))


def stations(only=None):
    """Every station as (state, x, y, room, key)."""
    return [(s, x + dx, y + dy, room, k) for k, x, y, room in placed(only) for s, dx, dy in CATALOGUE[k]["stations"]]


def footprints(only=None):
    out = []
    for k, x, y, room in placed(only):
        f = CATALOGUE[k]["foot"]
        if f and f[2] and f[3]:
            out.append((x + f[0], y + f[1], f[2], f[3], k, room))
    return out


def check(only=None):
    """Stations that sit on some piece's footprint: each is a cat standing in furniture."""
    bad = []
    for s, sx, sy, room, key in stations(only):
        if s == "upstairs":
            continue                                  # cats sit on the stairs on purpose
        for fx, fy, fw, fh, k, r in footprints(only):
            if k != key and fx <= sx < fx + fw and fy <= sy < fy + fh:
                bad.append((s, sx, sy, key, "on", k))
    return bad


def render(img, packs, only=None, marks=False):
    """Draw the layout over the shell (previews and the old build path). marks=True dots the stations."""
    from PIL import ImageDraw
    out = img.copy()
    for k, x, y, room in placed(only):
        out.alpha_composite(sprite(k, packs), (x, y))
    if marks:
        d = ImageDraw.Draw(out)
        colour = {"needs": (230, 60, 60), "review": (230, 160, 40), "work": (60, 120, 230), "fail": (160, 60, 200),
                  "sleep": (60, 180, 90), "upstairs": (250, 250, 250), "queen": (250, 210, 0)}
        for s, x, y, room, k in stations(only):
            d.rectangle([x - 1, y - 1, x + 1, y + 1], fill=colour[s])
    return out
