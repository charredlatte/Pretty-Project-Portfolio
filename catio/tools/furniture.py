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

Sheets are named by the end of their path, which finds them both in Charlotte's zips and in an unpacked
copy. "cc" is Cosy Cabin (committable: art/furniture.png); every other sheet is licensed and goes into
art/licensed/furniture.png, which ships only inside the private artifact.

    python3 catio/tools/furniture.py      writes the page's generated MANOR block (no zips needed: atlas
                                          positions depend only on the pieces' sizes)
"""
import json
import re
from pathlib import Path

from PIL import Image

WG = "Wood_Garden_Asset_Pack/Wood Garden Asset Pack/"   # rowdy41: one piece per file; a sheet named "wg:<file>"
SHEETS = {
    "cc": "CosyCabin_Objects.png",
    "tc": "CatRoomFree/Furnitures.png",
    "cainos": "Texture/TX Struct.png",
    "pochi": "PochiFree/FreeSprites.png",
    "plants": "plants.png",
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
    "filing_cabinet": piece("cc", (608, 628, 16, 27), "essential", stations=[("review", 8, 36)]),
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
    # the dining room
    "dining_table": piece("cc", (7, 272, 50, 32), "decor", foot=(0, 6, 50, 26)),
    "chair_front_decor": piece("cc", (609, 276, 14, 28), foot=(0, 0, 0, 0)),
    "chair_back_work": piece("cc", (641, 282, 14, 22), "connected", foot=(0, 0, 0, 0), stations=[("work", 7, 22)]),
    "chair_right": piece("cc", (624, 277, 14, 27), foot=(0, 0, 0, 0)),
    "chair_left_queen": piece("cc", (658, 277, 14, 27), "connected", foot=(0, 0, 0, 0), stations=[("queen", 7, 30)]),
    "sideboard": piece("cc", (16, 501, 32, 27), foot=(0, 10, 32, 17)),
    "runner_yellow": piece("cc", (1009, 145, 30, 15), "connected", "rug", stations=[("fail", 15, 10)]),
    "sunflower": piece("cc", (33, 871, 14, 40)),
    # the conservatory
    "armchair_green": piece("cc", (12, 114, 24, 30), "connected", stations=[("queen", 12, 36)]),
    "scratching_post": piece("tc", (197, 331, 55, 77), "connected", scale=0.5, stations=[("work", 14, 44)]),
    "runner_green": piece("cc", (1009, 177, 30, 15), "connected", "rug", stations=[("fail", 15, 10)]),
    "palm": piece("plants", (20, 30, 23, 34)),
    "fiddle_fig": piece("plants", (55, 26, 19, 38)),
    "fern": piece("plants", (181, 86, 22, 26)),
    "monstera": piece("plants", (19, 86, 24, 25)),
    "trailing_ivy": piece("plants", (211, 94, 23, 17)),
    # the studio (the craft room: the Montfortoise shop's workroom)
    "shelves_supplies": piece("cc", (657, 486, 46, 36), foot=(0, 16, 46, 20)),
    "worktable": piece("wg:Table/Table-1.png", (0, 0, 58, 50), "connected", foot=(0, 8, 58, 42), stations=[("work", 29, 58)]),
    "yarn_red": piece("pochi", (168, 407, 22, 20), layer="top", scale=0.5),
    "yarn_blue": piece("pochi", (103, 405, 22, 20), layer="top", scale=0.5),
    "tin_buttons": piece("pochi", (103, 343, 18, 18), layer="top", scale=0.5),
    "supply_chest": piece("wg:Chest/Chest-3.png", (0, 0, 21, 26)),
    "chair_right_queen": piece("cc", (624, 277, 14, 27), "connected", foot=(0, 0, 0, 0), stations=[("queen", 7, 30)]),
    # the bedroom
    "bed": piece("cc", (176, 416, 32, 47), "connected", foot=(0, 8, 32, 39), stations=[("sleep", 16, 34)]),
    "nightstand": piece("cc", (176, 520, 16, 22), foot=(0, 8, 16, 14)),
    "dresser": piece("cc", (16, 501, 32, 27), foot=(0, 10, 32, 17)),
    "foot_chest": piece("wg:Chest/Chest-1.png", (0, 0, 22, 21)),
    # the bathroom (the ensuite)
    "toilet": piece("cc", (32, 577, 16, 31), foot=(0, 10, 16, 21)),
    "basin": piece("cc", (353, 578, 14, 14), layer="wall"),
    "mirror_small": piece("cc", (946, 593, 12, 21), layer="wall"),
    "shower": piece("cc", (691, 578, 12, 25), layer="wall"),
    "towel": piece("cc", (834, 738, 12, 14), layer="wall"),
    "bath_mat": piece("cc", (1008, 277, 16, 10), "connected", "rug", stations=[("queen", 8, 8)]),
    "plant_bath": piece("cc", (834, 584, 14, 24)),
    # the catio (outdoors)
    "cat_tree": piece("pochi", (6, 256, 85, 175), "connected", scale=0.5, foot=(4, 60, 36, 28), stations=[("work", 22, 92)]),
    "garden_table": piece("wg:Table/Table-2.png", (0, 0, 39, 66), foot=(0, 20, 39, 46)),
    "garden_chair": piece("wg:Chairs/Medium Chair/Medium wooden chair/Medium-chair-1.png", (0, 0, 28, 36), "connected", foot=(0, 0, 0, 0), stations=[("queen", 14, 38)]),
    "catio_chest": piece("wg:Chest/Chest-1.png", (0, 0, 22, 21), "essential", stations=[("review", 11, 28)]),
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
    # Dining room: a long table under the window light with chairs all round (cats at it are working on the
    # business plans), a sideboard and a sunflower, the filing cabinet, a runner, a cushion
    "dining": [
        ("filing_cabinet", 232, 89), ("sideboard", 314, 89), ("sunflower", 336, 84),
        ("dining_table", 264, 128),
        ("chair_front_decor", 271, 110), ("chair_front_decor", 293, 110),
        ("chair_right", 248, 131), ("chair_left_queen", 316, 131),
        ("chair_back_work", 271, 154), ("chair_back_work", 293, 154),
        ("runner_yellow", 252, 184), ("cushion_green", 300, 186),
    ],
    # Conservatory: glass on three sides and plants all round; the green armchair in the sun (the queen's),
    # a cushion for the warmest spot, a runner by the drawing-room door. The cat flap on the east wall stays
    # clear; the scratching post lives out on the catio
    "sunroom": [
        ("palm", 664, 108), ("fiddle_fig", 729, 102), ("trailing_ivy", 700, 120),
        ("armchair_green", 686, 132), ("fern", 728, 136),
        ("cushion_white", 712, 176), ("runner_green", 670, 188),
    ],
    # Studio, the shop's workroom: shelves of supplies against the old brick, the big worktable with yarn and
    # a tin of buttons on it (working), a sewing desk (working too), the supply chest, the filing cabinet
    "study": [
        ("bookcase_filled", 556, 213), ("shelves_supplies", 604, 222),
        ("writing_desk", 636, 222), ("filing_cabinet", 670, 222),
        ("worktable", 590, 272), ("yarn_red", 598, 282), ("yarn_blue", 612, 284), ("tin_buttons", 628, 281),
        ("chair_right_queen", 572, 290), ("supply_chest", 662, 318),
        ("cushion_blue", 572, 326), ("runner_yellow", 600, 334),
    ],
    # Bedroom (legal questions, kept quiet): the bed against the vine paper (a cat asleep on it), nightstands,
    # a dresser, a chest at the bed's foot, a reading chair for the queen, the filing cabinet, a rug
    "bedroom": [
        ("nightstand", 184, 232), ("bed", 202, 222), ("nightstand", 236, 232), ("dresser", 254, 226),
        ("filing_cabinet", 288, 226), ("foot_chest", 207, 272),
        ("rug_blue_diamond", 214, 296), ("armchair_pink", 266, 290), ("plant_snake", 292, 300),
    ],
    # Bathroom, the ensuite: the toilet, a basin under its mirror, a shower with its mat (the queen stands on
    # it), a towel, a plant, a cushion; the door to the bedroom on the east stays clear
    "bath": [
        ("mirror_small", 111, 216), ("basin", 110, 236), ("shower", 137, 216), ("towel", 90, 222),
        ("bath_mat", 135, 250), ("toilet", 88, 240),
        ("plant_bath", 88, 290), ("cushion_white", 116, 296),
    ],
    # Catio: the chest (its filing cabinet), a cat tree to climb (working), a scratching post, a table and
    # chair for people (the queen's), water, a cushion in the sun, a runner by the cat flap
    "garden": [
        ("catio_chest", 770, 92), ("scratching_post", 812, 96), ("cat_tree", 846, 118),
        ("garden_table", 780, 200), ("garden_chair", 822, 232), ("bowl_water", 770, 150),
        ("cushion_orange", 858, 262), ("runner_blue", 764, 172),
    ],
}


def suffix(sheet):
    return sheet[3:] if sheet.startswith("wg:") else SHEETS[sheet]


def folder_loader(packs):
    """Find a sheet by the end of its path in an unpacked folder of packs."""
    files = [str(f) for f in Path(packs).rglob("*.png")]
    def load(end):
        hit = [f for f in files if f == end or f.endswith("/" + end)]
        if not hit:
            raise SystemExit(end + " not found under " + packs)
        return Image.open(sorted(hit, key=len)[0]).convert("RGBA")
    return load


def sprite(key, load, cache={}):
    """One piece's picture. load(path end) opens a sheet: folder_loader(packs), or a zip lookup."""
    if isinstance(load, str):
        load = folder_loader(load)
    c = CATALOGUE[key]
    if c["sheet"] not in cache:
        cache[c["sheet"]] = load(suffix(c["sheet"]))
    x, y, w, h = c["box"]
    im = cache[c["sheet"]].crop((x, y, x + w, y + h))
    if c["scale"] != 1:
        im = im.resize(tuple(c["size"]), Image.NEAREST)
    return im


ATLAS_W = 512


def atlas_plan():
    """Where each piece sits in its atlas: cc (committable) or lic (licensed). Shelf-packed by height."""
    plan, sizes = {}, {"cc": [0, 0], "lic": [0, 0]}
    shelf = {"cc": [0, 0, 0], "lic": [0, 0, 0]}          # x, y, height of the current shelf
    for key in sorted(CATALOGUE, key=lambda k: (-CATALOGUE[k]["size"][1], k)):
        a = "cc" if CATALOGUE[key]["sheet"] in COMMITTABLE else "lic"
        w, h = CATALOGUE[key]["size"]
        x, y, sh = shelf[a]
        if x + w > ATLAS_W:
            x, y, sh = 0, y + sh + 1, 0
        plan[key] = (a, x, y)
        shelf[a] = [x + w + 1, y, max(sh, h)]
        sizes[a] = [ATLAS_W, max(sizes[a][1], y + h)]
    return plan, sizes


def atlases(load):
    """Draw both atlases: {"cc": image, "lic": image}."""
    plan, sizes = atlas_plan()
    out = {a: Image.new("RGBA", tuple(sz), (0, 0, 0, 0)) for a, sz in sizes.items()}
    for key, (a, x, y) in plan.items():
        out[a].alpha_composite(sprite(key, load), (x, y))
    return out


def page_data():
    """What the page needs: the grounds' size, each room's box, the pieces as atlas cells, the layout."""
    import manor
    plan, sizes = atlas_plan()
    rooms = {k: [box[0] * manor.T, box[1] * manor.T, (box[2] - box[0]) * manor.T + 5, (box[3] - box[1]) * manor.T + 5]
             for k, (box, _, _) in manor.ROOMS.items()}
    x0, y0, x1, y1 = manor.CATIO
    rooms["garden"] = [x0 * manor.T, y0 * manor.T, (x1 - x0) * manor.T, (y1 - y0) * manor.T]
    pieces = {k: {"atlas": plan[k][0], "at": plan[k][1:], "size": c["size"], "kind": c["kind"], "layer": c["layer"],
                  "foot": c["foot"], "stations": c["stations"]} for k, c in CATALOGUE.items()}
    return {"world": list(manor.SIZE), "face": manor.FACE, "rooms": rooms, "floors": {k: list(floor_of(k)) for k in rooms},
            "doors": doors(),
            "atlases": {a: list(sz) for a, sz in sizes.items()}, "pieces": pieces,
            "layout": {room: [list(p) for p in items] for room, items in LAYOUT.items()}}


def doors():
    """How cats get from room to room: [room a, room b, a point on a's floor, a point on b's floor] for each
    doorway, the cat flap into the catio, and the front door (room b null: the way out, on the door mat)."""
    import manor
    T = manor.T

    def room_at(x, y):
        for k, (box, _, _) in manor.ROOMS.items():
            X0, Y0, X1, Y1 = manor.box_px(box)
            if X0 + 5 <= x < X1 - 5 and Y0 + 5 <= y < Y1 - 5:
                return k
        return "garden" if manor.in_catio(x, y) else None

    out = []
    for kind, w, a, b in manor.DOORS:
        m = (a + b) // 2
        p, q = ([w * T - 8, m], [w * T + 12, m]) if kind == "v" else ([m, w * T - 8], [m, w * T + 5 + manor.FACE + 7])
        out.append([room_at(*p), room_at(*q), p, q])
    fx, f0, f1 = manor.CAT_FLAP
    out.append(["sunroom", "garden", [fx - 8, (f0 + f1) // 2], [fx + 16, (f0 + f1) // 2]])
    hy = manor.ROOMS["hall"][0][3] * T
    out.append(["hall", None, [sum(manor.FRONT_DOOR) // 2, hy - 6], [sum(manor.FRONT_DOOR) // 2, hy + 20]])
    assert all(d[0] for d in out) and all(d[1] or d[1] is None for d in out[:-1]), out
    return out


def write_page(page):
    """Replace the page's generated MANOR block with page_data()."""
    text = Path(page).read_text(encoding="utf-8")
    block = "/* MANOR:BEGIN generated by catio/tools/furniture.py: edit that, not this */\n  const MANOR = " + \
        json.dumps(page_data(), separators=(",", ":")) + ";\n  /* MANOR:END */"
    new, n = re.subn(r"/\* MANOR:BEGIN.*?/\* MANOR:END \*/", lambda m: block, text, flags=re.S)
    if n != 1:
        raise SystemExit("no MANOR block in " + page)
    Path(page).write_text(new, encoding="utf-8")


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


def floor_of(room):
    """A room's open floor, in native pixels: inside its walls and below its back wall (the catio's deck)."""
    import manor
    if room == "garden":
        x0, y0, x1, y1 = manor.CATIO
        return x0 * manor.T + 8, y0 * manor.T + 16, x1 * manor.T - 4, y1 * manor.T - 8
    X0, Y0, X1, Y1 = manor.box_px(manor.ROOMS[room][0])
    return X0 + 5, Y0 + 5 + manor.FACE, X1 - 5, Y1 - 5


def check(only=None):
    """Stations a cat couldn't stand on: in furniture, or off its room's floor."""
    bad = []
    for s, sx, sy, room, key in stations(only):
        if s != "upstairs":
            x0, y0, x1, y1 = floor_of(room)
            if not (x0 + 4 <= sx < x1 - 4 and y0 <= sy < y1 - 2):
                bad.append((s, sx, sy, key, "off the floor of", room))
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


if __name__ == "__main__":
    write_page(Path(__file__).resolve().parent.parent / "index.html")
    print("MANOR block written")
