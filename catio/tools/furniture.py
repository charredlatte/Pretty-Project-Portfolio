"""The manor's furniture: a catalogue of pieces, and where each one stands by default.

Furniture is not drawn into the house any more. Each piece is a sprite the page places, so renovation mode
can move it (see docs/renovation-mode.md). This file is the one source for:

  CATALOGUE  key -> sheet, box on the sheet, kind, footprint, stations
  LAYOUT     room -> [(key, x, y)], the default placement (native pixels, the sprite's top-left)

kind       essential: never moves (front door mat, stairs, filing cabinets, the brain's desk)
           connected: carries a station, so it can move but not be removed
           decor:     can move, be added and be removed
layer      rug (under everything), wall (on the back wall band), floor (sorted by bottom edge, like cats)
footprint  the part of the sprite that stands on the floor, as (dx, dy, w, h) inside the box; no cat
           stands on it. Rugs and wall pieces have none.
stations   where a cat goes to show its state: (state, dx, dy), the point under its feet, relative to the
           piece's top-left. States: needs, review, work, fail, sleep, upstairs; queen for the room's queen.

Sheets are paths inside Charlotte's unpacked packs. "cc" is Cosy Cabin (committable); every other sheet
is licensed and ships only inside the private artifact.
"""
from PIL import Image

SHEETS = {
    "cc": "CosyCabin/CosyCabin_Objects.png",
    "tc": "CatMegaFree/CatMegaFree/CatRoomFree/Furnitures.png",
    "cainos": "Pixel_Art_Top_Down_-_Basic_v1.2.3/Texture/TX Struct.png",
}
COMMITTABLE = {"cc"}


def piece(sheet, box, kind="decor", layer="floor", foot=None, stations=(), scale=1):
    x, y, w, h = box
    w2, h2 = round(w * scale), round(h * scale)
    if foot is None and layer == "floor":
        fh = max(4, round(h2 * 0.45))                 # a 3/4-view piece stands on its lower part
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
}


def sprite(key, packs, cache={}):
    c = CATALOGUE[key]
    if c["sheet"] not in cache:
        cache[c["sheet"]] = Image.open(packs + SHEETS[c["sheet"]]).convert("RGBA")
    x, y, w, h = c["box"]
    im = cache[c["sheet"]].crop((x, y, x + w, y + h))
    if c["scale"] != 1:
        im = im.resize(tuple(c["size"]), Image.NEAREST)
    return im


def placed(only=None):
    """Every piece in the layout as (key, x, y, room), in draw order: rugs, wall pieces, then by bottom edge."""
    rows = [(k, x, y, room) for room, items in LAYOUT.items() if not only or room == only for k, x, y in items]
    order = {"rug": 0, "wall": 1, "floor": 2}
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
