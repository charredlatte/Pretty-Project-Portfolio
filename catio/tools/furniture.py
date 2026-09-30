"""The manor's furniture: a catalogue of pieces, and where each one stands by default.

Furniture is not drawn into the house any more. Each piece is a sprite the page places, so renovation mode
can move it (see docs/renovation-mode.md). This file is the one source for:

  CATALOGUE  key -> sheet, box on the sheet, kind, footprint, stations
  LAYOUT     room -> [(key, x, y)], the default placement (native pixels, the sprite's top-left)

kind       essential: never moves (front door mat, the stair, filing cabinets, the brain's desk)
           connected: carries a station, so it can move but not be removed
           decor:     can move, be added and be removed
layer      rug (under everything), wall (on the back wall band), floor (sorted by bottom edge, like cats),
           top (set into a floor piece: a sink in a counter)
footprint  the part of the sprite that stands on the floor, as (dx, dy, w, h) inside the box; no cat
           stands on it. Rugs and wall pieces have none.
stations   where a cat goes to show its state: (state, dx, dy), the point under its feet, relative to the
           piece's top-left. States: needs, review, work, fail, sleep; queen for the room's queen; upstairs for
           the steps of the stair, foot to top, which cats climb on their way to the attic.

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
    "stairs": piece("cainos", (32, 40, 64, 80), "essential", foot=(0, 0, 64, 80),
                    stations=[("upstairs", 32, 78), ("upstairs", 32, 54), ("upstairs", 32, 30), ("upstairs", 32, 6)]),
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

# the default layout, room by room: (key, x, y), native pixels, the sprite's top-left. "landing" is upstairs over
# the hall: not a room, so it has pieces but no stations.
LAYOUT = {
    # Café: tables where people sit, beside the counter; business plans round the big one (cats at its south chairs
    # are working, the queen at its east end), a two-top by the window, a sideboard, the filing cabinet
    "dining": [
        ("filing_cabinet", 106, 72), ("sideboard", 226, 72), ("sunflower", 256, 66),
        ("dining_table", 140, 120),
        ("chair_front_decor", 147, 102), ("chair_front_decor", 169, 102),
        ("chair_right", 124, 123), ("chair_left_queen", 192, 123),
        ("chair_back_work", 147, 146), ("chair_back_work", 169, 146),
        ("writing_desk", 226, 130), ("chair_front_decor", 235, 114),
        ("runner_yellow", 112, 186), ("cushion_green", 240, 190),
    ],
    # Kitchen and counter, straight ahead from the front door behind the stair: the run under the window (fridge,
    # drawers, the sink, the hob, a pantry), the counter facing the hall where you order (cats at it are working),
    # the cats' bowls and food bag, a runner, a cushion
    "kitchen": [
        ("fridge", 330, 58), ("counter_drawers", 346, 73), ("counter", 362, 73), ("counter_door", 378, 73),
        ("hob", 394, 73), ("counter", 410, 73), ("pantry", 428, 56), ("filing_cabinet", 450, 73),
        ("sink", 364, 75),
        ("island", 370, 140), ("island", 386, 140), ("island", 402, 140), ("chair_front", 340, 136),
        ("bowl_food", 470, 150), ("bowl_water", 470, 172), ("food_bag", 452, 150),
        ("runner_blue", 290, 184), ("cushion_orange", 300, 110),
    ],
    # Cat lounge, where new cats come in: the fireplace between two tall windows, armchairs either side of the
    # hearth rug, a sofa facing it (a cat asleep on it), a cat tree to climb (working), cushions
    "living": [
        ("fireplace", 586, 53), ("rug_red_diamond", 578, 120),
        ("armchair_blue_r", 540, 124), ("armchair_blue_l", 616, 124),
        ("sofa_blue_back", 582, 156), ("cat_tree", 646, 112),
        ("filing_cabinet", 522, 73),
        ("cushion_white", 524, 180), ("cushion_blue", 560, 190),
    ],
    # Craft room, the shop: shelves of supplies and books against the old brick, the big worktable with yarn and a
    # tin of buttons (working), a sewing desk (working too), the supply chest, and a cushion in the bay window
    "study": [
        ("bookcase_filled", 104, 213), ("shelves_supplies", 200, 222), ("filing_cabinet", 250, 222),
        ("worktable", 140, 280), ("yarn_red", 148, 290), ("yarn_blue", 162, 292), ("tin_buttons", 178, 289),
        ("writing_desk", 220, 300), ("chair_right_queen", 116, 300), ("supply_chest", 240, 350),
        ("runner_green", 110, 360), ("trailing_ivy", 160, 396), ("cushion_blue", 196, 398),
    ],
    # Entrance hall: the stair up the middle to the landing, the front door's mat (cats who need you wait there),
    # a writing desk and the queen's chair to the west, the filing cabinet and cat beds to the east
    "hall": [
        ("stairs", 362, 213), ("door_mat", 379, 372), ("rug_red_diamond", 370, 310),
        ("lamp_floor", 345, 258), ("lamp_floor", 432, 258), ("plant_pampas", 284, 250), ("plant_snake", 284, 350),
        ("writing_desk", 300, 330), ("armchair_pink", 336, 334),
        ("filing_cabinet", 480, 334), ("cushion_blue", 450, 300), ("cushion_orange", 455, 345),
    ],
    # Terrace, the café's glass verrière: a table in the light and a chair for the queen, a two-top, the scratching
    # post, plants all round; the cat flap to the catio stays clear
    "sunroom": [
        ("palm", 522, 232), ("monstera", 650, 230), ("scratching_post", 650, 258),
        ("garden_table", 560, 262), ("garden_chair", 604, 282),
        ("writing_desk", 620, 336), ("fiddle_fig", 664, 338), ("fern", 530, 300),
        ("runner_green", 560, 350), ("cushion_white", 525, 362),
    ],
    # Catio, outdoors at the bottom right: the chest (its filing cabinet), a cat tree (working), a table and chair
    # for people (the queen's), bowls by the cat flap, cushions in the sun
    "garden": [
        ("catio_chest", 704, 200), ("cat_tree", 850, 200), ("cushion_white", 780, 240),
        ("runner_blue", 710, 280), ("bowl_water", 704, 336), ("bowl_food", 730, 336),
        ("garden_table", 760, 330), ("garden_chair", 805, 350),
        ("cushion_orange", 860, 400), ("fern", 880, 420),
    ],
    # Library, the brain, upstairs over the café: bookcases either side of a tall window, the brain's desk (a cat at
    # it is working), its chest where dropped files land, a reading chair for the queen, a rug
    "brain": [
        ("bookcase_dark_books", 102, 48), ("bookcase_red_books", 214, 48),
        ("armchair_blue", 110, 120), ("lamp_floor", 136, 114),
        ("brain_desk", 160, 120), ("chair_back", 178, 146), ("brain_chest", 224, 150),
        ("filing_cabinet", 250, 120), ("rug_blue_diamond", 120, 170), ("cushion_green", 236, 186),
    ],
    # Ensuite, partitioned off the bedroom: a basin under its mirror, a shower with its mat (the queen stands on
    # it), the toilet, a plant, a cushion; the door from the bedroom stays clear
    "bath": [
        ("mirror_small", 648, 56), ("basin", 647, 76), ("shower", 670, 56),
        ("bath_mat", 668, 96), ("toilet", 668, 130),
        ("plant_bath", 618, 180), ("cushion_white", 640, 186),
    ],
    # Bedroom (legal questions, kept quiet), over the cat lounge: the bed between nightstands under the window (a cat
    # asleep on it), the filing cabinet, a rug, a reading chair for the queen; the doors to the landing and the
    # ensuite stay clear
    "bedroom": [
        ("nightstand", 542, 72), ("bed", 560, 62), ("nightstand", 592, 72),
        ("filing_cabinet", 522, 66), ("rug_blue_diamond", 540, 150), ("armchair_pink", 580, 168),
        ("cushion_orange", 524, 184),
    ],
    # the landing, open over the kitchen and the hall: plants by its windows, a lamp and a rug by the stairwell (the
    # attic ladder is drawn in the shell)
    "landing": [
        ("plant_pampas", 285, 88), ("plant_snake", 495, 95), ("lamp_floor", 300, 300),
        ("rug_red_diamond", 370, 320), ("runner_blue", 380, 150),
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
    """What the page needs: the grounds' size, each room's box and floor, the landing and the stair, the pieces
    as atlas cells, the layout."""
    import manor
    plan, sizes = atlas_plan()
    rooms = {k: [box[0] * manor.T, box[1] * manor.T, (box[2] - box[0]) * manor.T + 5, (box[3] - box[1]) * manor.T + 5]
             for k, (_, box, _, _) in manor.ROOMS.items()}
    x0, y0, x1, y1 = manor.CATIO
    rooms["garden"] = [x0 * manor.T, y0 * manor.T, (x1 - x0) * manor.T, (y1 - y0) * manor.T]
    level = {k: f for k, (f, _, _, _) in manor.ROOMS.items()}
    level["garden"] = "ground"
    lx0, ly0, lx1, ly1 = manor.box_px(manor.LANDING)
    pieces = {k: {"atlas": plan[k][0], "at": plan[k][1:], "size": c["size"], "kind": c["kind"], "layer": c["layer"],
                  "foot": c["foot"], "stations": c["stations"]} for k, c in CATALOGUE.items()}
    return {"world": list(manor.SIZE), "face": manor.FACE, "rooms": rooms, "level": level,
            "landing": [lx0, ly0, lx1 - lx0, ly1 - ly0], "stairs": list(manor.STAIRS),
            "floors": {k: list(floor_of(k)) for k in rooms}, "doors": doors(),
            "atlases": {a: list(sz) for a, sz in sizes.items()}, "pieces": pieces,
            "layout": {room: [list(p) for p in items] for room, items in LAYOUT.items()}}


def doors():
    """How cats get from room to room: [room a, room b, a point on a's floor, a point on b's floor] for each
    doorway on both floors ("landing" is the upstairs landing), the stair (the hall's foot of it to the landing's
    head), the cat flap into the catio, and last the front door (room b null: the way out, on the door mat)."""
    import manor
    T = manor.T

    def room_at(x, y, floor):
        for k, (box, _, _) in manor.boxes(floor).items():
            X0, Y0, X1, Y1 = manor.box_px(box)
            if X0 + 5 <= x < X1 - 5 and Y0 + 5 <= y < Y1 - 5:
                return k
        return "garden" if floor == "ground" and manor.in_catio(x, y) else None

    out = []
    for floor, ds in manor.DOORS.items():
        for kind, w, a, b in ds:
            m = (a + b) // 2
            p, q = ([w * T - 8, m], [w * T + 12, m]) if kind == "v" else ([m, w * T - 8], [m, w * T + 5 + manor.FACE + 7])
            out.append([room_at(*p, floor), room_at(*q, floor), p, q])
    sx, sy, sw, sh = manor.STAIRS
    out.append(["hall", "landing", [sx + sw // 2, sy + sh + 6], [sx + sw // 2, sy - 8]])
    fx, f0, f1 = manor.CAT_FLAP
    out.append(["sunroom", "garden", [fx - 8, (f0 + f1) // 2], [fx + 16, (f0 + f1) // 2]])
    hy = manor.ROOMS["hall"][1][3] * T
    out.append(["hall", None, [sum(manor.FRONT_DOOR) // 2, hy - 6], [sum(manor.FRONT_DOOR) // 2, hy + 20]])
    assert all(d[0] and d[1] for d in out[:-1]), out
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
    """A room's open floor, in native pixels: inside its walls and below its back wall, if it has one (the catio's
    deck; the landing)."""
    import manor
    if room == "garden":
        x0, y0, x1, y1 = manor.CATIO
        return x0 * manor.T + 8, y0 * manor.T + 16, x1 * manor.T - 4, y1 * manor.T - 8
    level = "upper" if room == "landing" else manor.ROOMS[room][0]
    box, _, wall = manor.boxes(level)[room]
    X0, Y0, X1, Y1 = manor.box_px(box)
    return X0 + 5, Y0 + 5 + (manor.FACE if wall else 0), X1 - 5, Y1 - 5


def check(only=None):
    """Stations a cat couldn't stand on: in furniture, or off its room's floor (the craft room's bay counts)."""
    import manor
    bad = []
    for s, sx, sy, room, key in stations(only):
        if s == "upstairs":
            continue                                  # cats sit on the stair's steps on purpose
        x0, y0, x1, y1 = floor_of(room)
        on = x0 + 4 <= sx < x1 - 4 and y0 <= sy < y1 - 2
        if room == "study" and manor.in_poly(sx, sy + 6, manor.bay_poly()):
            on = True
        if not on:
            bad.append((s, sx, sy, key, "off the floor of", room))
        for fx, fy, fw, fh, k, r in footprints(only):
            if k != key and r == room and fx <= sx < fx + fw and fy <= sy < fy + fh:
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
                  "sleep": (60, 180, 90), "queen": (250, 210, 0)}
        for s, x, y, room, k in stations(only):
            d.rectangle([x - 1, y - 1, x + 1, y + 1], fill=colour[s])
    return out


if __name__ == "__main__":
    write_page(Path(__file__).resolve().parent.parent / "index.html")
    print("MANOR block written")
