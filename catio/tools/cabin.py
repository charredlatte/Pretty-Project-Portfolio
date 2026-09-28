"""The cabin's floor plan, drawn from Charlotte's asset packs.

Layout (the page's GEOM mirrors these numbers):

    north   kitchen + dining (open plan) | living room (glass + fireplace) | sunroom (all glass) | catio
    south   bathroom (ensuite) | bedroom | hall (front door) | study

Public rooms share one open run and face north with floor-to-ceiling glass; the private rooms sit
behind them; the bathroom backs onto the kitchen's plumbing; the catio is fenced against the
sunroom's outside wall and reached through a cat flap, with a tree for shade and shelves to climb.

Everything is in native pixels on a 16 px tile grid. `house()` uses only Cosy Cabin (committable);
`decor()` adds pieces from the other packs (licensed, not committed).
"""
from PIL import Image

T = 16
FACE = 32                                   # height of a back wall, ceiling to floor
SIZE = (40 * T, 28 * T)                     # the whole meadow

OUTLINE = [(65, 9, 9), (100, 38, 22), (100, 38, 22), (88, 26, 17), (65, 9, 9)]      # outer -> inner
GLASS = [(65, 9, 9), (116, 141, 172), (142, 177, 204), (130, 165, 190), (65, 9, 9)]

# name: tile box (x0, y0, x1, y1) and its zones (x0 tile, x1 tile, floor, wallpaper)
ROOMS = {
    "kitchen": ((2, 5, 13, 14), [(2, 7, "pink", 48), (7, 13, "wood", 64)]),   # the dining zone is the east end
    "living":  ((13, 3, 23, 14), [(13, 23, "wood", 64)]),
    "sunroom": ((23, 5, 28, 14), [(23, 28, "green", 0)]),
    "bath":    ((2, 14, 6, 21), [(2, 6, "blue", 32)]),
    "bedroom": ((6, 14, 13, 22), [(6, 13, "wood", 16)]),
    "hall":    ((13, 14, 17, 23), [(13, 17, "sand", 0)]),
    "study":   ((17, 14, 24, 22), [(17, 24, "dark", 0)]),
}

# Cosy Cabin object sprites: (x, y, w, h) on CosyCabin_Objects.png
SPRITES = {
    "sofa_blue_back": (620, 74, 40, 22), "armchair_blue_l": (409, 66, 22, 30), "armchair_blue_r": (481, 66, 22, 30),
    "armchair_green": (12, 114, 24, 30), "fireplace": (368, 176, 32, 42),
    "table_round": (279, 272, 34, 32), "chair_front": (609, 276, 14, 28), "chair_right": (624, 277, 14, 27),
    "chair_back": (641, 282, 14, 22), "chair_left": (658, 277, 14, 27),
    "fridge": (384, 808, 16, 40), "ctr_plain": (384, 628, 16, 27), "ctr_drawers": (416, 628, 16, 27),
    "ctr_door": (448, 628, 16, 27), "ctr_hob": (480, 754, 16, 29),
    "bed": (176, 416, 32, 47), "nightstand": (176, 520, 16, 22), "dresser": (16, 501, 32, 27),
    "desk": (304, 507, 32, 32), "bookcase": (657, 406, 46, 52),
    "toilet": (17, 572, 14, 36), "shower": (691, 578, 12, 25), "basin": (353, 578, 14, 14), "towel": (834, 738, 12, 14),
    "mirror": (962, 593, 12, 30), "mirror_small": (946, 593, 12, 21), "plant_bath": (834, 584, 14, 24),
    "lamp_floor": (897, 50, 13, 30), "rug_blue": (1008, 49, 48, 30), "rug_red": (1008, 81, 48, 30),
    "runner_yellow": (1009, 145, 30, 15), "runner_green": (1009, 177, 30, 15), "mat": (1009, 245, 30, 10),
    "mat_small": (1008, 277, 16, 10), "rug_round": (1009, 314, 14, 14),
    "plant_pampas": (17, 868, 15, 43), "sunflower": (33, 871, 14, 40), "plants": (48, 881, 32, 30),
    "plant_snake": (82, 880, 11, 31), "pot": (98, 894, 13, 17),
    "frame1": (948, 386, 8, 13), "frame2": (964, 386, 9, 13), "frame3": (947, 402, 9, 13), "star": (896, 241, 32, 15),
    "win_grid_cream": (946, 290, 28, 18), "win_panes_cream": (946, 354, 28, 18), "shelf_wall": (833, 229, 14, 27),
}

# furniture: (sprite, x, y); rugs first, the rest drawn back to front by their bottom edge
FURNITURE = [
    # kitchen: counters under the window, fridge at the end of the run
    ("fridge", 40, 92), ("ctr_drawers", 56, 105), ("ctr_plain", 72, 105), ("ctr_hob", 88, 103), ("ctr_door", 104, 105),
    ("win_grid_cream", 66, 88), ("plant_snake", 40, 186), ("pot", 96, 206),
    ("ctr_plain", 62, 152), ("ctr_drawers", 78, 152),                            # island
    # dining: round table on a red rug in front of the glass
    ("rug_red", 136, 158), ("table_round", 143, 152), ("chair_front", 153, 138), ("chair_back", 153, 176),
    ("chair_right", 128, 156), ("chair_left", 179, 156), ("sunflower", 190, 180),
    # living: fireplace between two glass walls; sofa and armchairs round a rug
    ("fireplace", 274, 58), ("rug_blue", 266, 140), ("sofa_blue_back", 270, 176),
    ("armchair_blue_l", 236, 132), ("armchair_blue_r", 318, 132), ("lamp_floor", 346, 98), ("plant_pampas", 218, 90),
    # sunroom: green chair and plants in the light
    ("armchair_green", 380, 150), ("plants", 408, 186), ("plant_snake", 432, 124), ("rug_round", 410, 150),
    # bathroom (ensuite)
    ("mat_small", 58, 300), ("toilet", 40, 250), ("mirror_small", 62, 234), ("basin", 61, 258), ("shower", 82, 236),
    ("towel", 82, 264), ("plant_bath", 78, 306),
    # bedroom
    ("runner_yellow", 157, 318), ("dresser", 103, 256), ("mirror", 113, 228), ("nightstand", 138, 264), ("bed", 156, 250),
    ("nightstand", 190, 264), ("plant_snake", 104, 318), ("frame1", 144, 238), ("frame2", 194, 238),
    # hall
    ("mat", 228, 354), ("plant_pampas", 214, 300),
    # study: desk under the frames, a reading lamp
    ("runner_green", 300, 318), ("desk", 342, 258), ("chair_back", 351, 280), ("lamp_floor", 370, 262),
    ("frame1", 348, 236), ("frame3", 360, 236), ("star", 290, 236),
]

# doorways: ("v", wall tile x, y from, y to) through a side wall; ("h", wall tile y, x from, x to) through a back wall
DOORS = [
    ("v", 13, 128, 214),            # dining <-> living, wide open plan
    ("v", 23, 144, 214),            # living <-> sunroom
    ("h", 14, 224, 264),            # living -> hall
    ("v", 13, 272, 318),            # hall <-> bedroom
    ("v", 6, 272, 304),             # bedroom <-> ensuite
    ("v", 17, 272, 318),            # hall <-> study
]
FRONT_DOOR = (229, 257)             # x span in the hall's south wall

# glass: ("v", wall tile x, y from, y to) side walls; ("h", wall tile y, x from, x to) bottom walls;
# ("tall", x, y, w) floor-to-ceiling on a back wall
WINDOWS = [
    ("tall", 124, 85, 78),          # dining
    ("tall", 216, 53, 56), ("tall", 310, 53, 56),     # living, either side of the fireplace
    ("tall", 374, 85, 74),          # sunroom
    ("v", 2, 128, 192),             # kitchen west
    ("v", 28, 88, 172), ("v", 28, 190, 222),         # sunroom east, broken by the cat flap
    ("h", 14, 392, 446),            # sunroom south
    ("v", 2, 276, 322),             # bathroom west
    ("h", 22, 118, 196),            # bedroom south
    ("h", 22, 290, 372),            # study south
    ("v", 24, 272, 340),            # study east
]
CAT_FLAP = (448, 174, 188)          # x of the sunroom's east wall, y span


def box_px(box):
    x0, y0, x1, y1 = box
    return x0 * T, y0 * T, x1 * T + 5, y1 * T + 5


def floors(tm, ex):
    """16/32 px floor textures from the Cosy Cabin sheets."""
    wood = ex.crop((128, 128, 160, 160))
    dark_map = {(203, 138, 82): (107, 46, 26), (195, 127, 76): (100, 38, 22), (188, 91, 48): (100, 38, 22),
                (176, 107, 67): (88, 26, 17), (168, 97, 59): (80, 20, 13), (151, 75, 42): (65, 9, 9)}
    dark = wood.copy()
    dark.putdata([dark_map.get(p[:3], p[:3]) + (255,) for p in dark.getdata()])
    return {
        "wood": wood, "dark": dark, "sand": tm.crop((336, 192, 352, 208)),
        "blue": tm.crop((336, 272, 352, 288)), "pink": tm.crop((400, 272, 416, 288)), "green": tm.crop((464, 272, 480, 288)),
    }


def tall_glass(tm_objects, w):
    """A floor-to-ceiling window: the pack's cream sash window stretched to the wall's height and repeated."""
    x, y, sw, sh = SPRITES["win_panes_cream"]
    s = tm_objects.crop((x, y, x + sw, y + sh))
    top, mid, bot = s.crop((0, 0, sw, 3)), s.crop((0, 3, sw, sh - 4)), s.crop((0, sh - 4, sw, sh))
    unit = Image.new("RGBA", (sw, FACE))
    unit.paste(top, (0, 0))
    unit.paste(mid.resize((sw, FACE - 7), Image.NEAREST), (0, 3))
    unit.paste(bot, (0, FACE - 4))
    g = Image.new("RGBA", (w, FACE))
    for gx in range(0, w, sw - 2):
        g.alpha_composite(unit, (gx, 0))
    g.paste(unit.crop((sw - 3, 0, sw, FACE)), (w - 3, 0))
    return g


def house(tm, objects, example):
    img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    px = img.load()
    tex = floors(tm, example)
    paper = {c: tm.crop((c, 32, c + 16, 52)) for c in (0, 16, 32, 48, 64)}
    rail = tm.crop((0, 68, 16, 80))
    floor_at = {}

    def fill(x, y, name):
        t = tex[name]
        px[x, y] = t.getpixel((x % t.width, y % t.height))

    # floors and back walls
    for name, (box, zones) in ROOMS.items():
        X0, Y0, X1, Y1 = box_px(box)
        for zx0, zx1, fl, wp in zones:
            xa, xb = max(X0 + 5, zx0 * T), min(X1 - 5, zx1 * T + 5)
            for x in range(xa, xb):
                for y in range(Y0 + 5, Y1 - 5):
                    fy = y - (Y0 + 5)
                    if fy < 20:
                        px[x, y] = paper[wp].getpixel((x % 16, fy))
                    elif fy < FACE:
                        px[x, y] = rail.getpixel((x % 16, fy - 20))
                    else:
                        fill(x, y, fl)
                        floor_at[(x // T, y // T)] = fl
    # walls: a mitred 5 px band round every room
    for box, _ in ROOMS.values():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0, X1):
            for y in range(Y0, Y1):
                d = min(x - X0, X1 - 1 - x, y - Y0, Y1 - 1 - y)
                if d < 5:
                    px[x, y] = OUTLINE[d]

    def floor_near(x, y):
        for dx in (8, -8, 0):
            for dy in (0, 8, 40):
                f = floor_at.get(((x + dx) // T, (y + dy) // T))
                if f:
                    return f
        return "wood"

    # doorways
    for kind, w, a, b in DOORS:
        if kind == "v":
            for x in range(w * T, w * T + 5):
                for y in range(a, b):
                    fill(x, y, floor_near(x, y))
        else:
            y0 = w * T
            fl = floor_near((a + b) // 2, y0 + FACE + 8)
            for x in range(a, b):
                for y in range(y0, y0 + 5 + FACE):
                    fill(x, y, fl)
            for y in range(y0, y0 + 5 + FACE):
                for i in range(5):
                    px[a - 5 + i, y] = OUTLINE[4 - i]
                    px[b + i, y] = OUTLINE[i]
    # front door: an opening in the hall's south wall
    hy = ROOMS["hall"][0][3] * T
    for x in range(*FRONT_DOOR):
        for y in range(hy, hy + 5):
            fill(x, y, "sand")
    # glass
    for kind, *a in WINDOWS:
        if kind == "tall":
            x, y, w = a
            img.alpha_composite(tall_glass(objects, w), (x, y))
        elif kind == "v":
            w, y0, y1 = a
            for y in range(y0, y1):
                for i in range(5):
                    px[w * T + i, y] = OUTLINE[0] if (y - y0) % 16 == 0 or y == y1 - 1 else GLASS[i]
        else:
            h, x0, x1 = a
            for x in range(x0, x1):
                for i in range(5):
                    px[x, h * T + i] = OUTLINE[0] if (x - x0) % 16 == 0 or x == x1 - 1 else GLASS[i]
    fx, fy0, fy1 = CAT_FLAP
    for y in range(fy0, fy1):
        for i in range(5):
            px[fx + i, y] = (65, 9, 9) if y in (fy0, fy1 - 1) else (88, 26, 17)
    # furniture
    rugs = {"rug_blue", "rug_red", "runner_yellow", "runner_green", "mat", "mat_small", "rug_round"}
    wall = {"win_grid_cream", "mirror", "mirror_small", "frame1", "frame2", "frame3", "star", "shelf_wall"}
    order = sorted(FURNITURE, key=lambda f: (0 if f[0] in rugs else 1 if f[0] in wall else 2, f[2] + SPRITES[f[0]][3]))
    for name, x, y in order:
        sx, sy, w, h = SPRITES[name]
        img.alpha_composite(objects.crop((sx, sy, sx + w, sy + h)), (x, y))
    return img


def decor(size, sheet, wood_piece):
    """Pieces from the other packs: the catio, the garden round the cabin, and a few things indoors."""
    g = Image.new("RGBA", size, (0, 0, 0, 0))
    crop = lambda x, y, w, h: sheet.crop((x, y, x + w, y + h))
    stamp = lambda im, x, y: g.alpha_composite(im, (x, y))

    # catio: a deck against the sunroom, grass beyond, a tree for shade, shelves to climb, a table for people
    deck = wood_piece("Floor/Brown-floor-1.png")
    for dx in range(3):
        for dy in range(4):
            stamp(deck, 453 + dx * 32, 88 + dy * 32)
    stamp(wood_piece("White flower box shelf/White flower box shelf-3.png"), 534, 60)   # cat shelves
    stamp(crop(113, 293, 81, 121), 548, 112)                          # shade tree, east corner
    stamp(wood_piece("Medium wooden chair/Medium-chair-1.png"), 458, 150)
    stamp(wood_piece("Table/Table-1.png"), 484, 150)
    stamp(wood_piece("Small wooden flower box/Small wooden flower box-18.png"), 526, 176)
    # white fence round the catio's open sides, rose arch for people on the south
    post = wood_piece("White fence/White-fence-4.png")
    for y in range(64, 212, 36):
        stamp(post, 600, y)
    for x in range(452, 600, 32):
        stamp(wood_piece("White fence/White-fence-2.png"), x, 50)
    fy = 226
    stamp(wood_piece("White fence/White-fence-1.png"), 452, fy)
    stamp(wood_piece("White fence/White-fence-2.png"), 480, fy)
    stamp(wood_piece("White gate/White-red-flower-gate-1.png"), 512, fy - 21)
    stamp(wood_piece("White fence/White-fence-2.png"), 554, fy)
    stamp(wood_piece("White fence/White-fence-3.png"), 574, fy)
    stamp(wood_piece("White fence/White-fence-5.png"), 600, fy - 23)

    # the way in: steps from the front door, flowers along the front
    stamp(wood_piece("Stairs/Wood-stairs-1.png"), 227, 372)
    for x, n in ((112, 18), (140, 14), (176, 16), (294, 20), (330, 18)):
        stamp(wood_piece(f"Small wooden flower box/Small wooden flower box-{n}.png"), x, 360)

    # the meadow: pond, trees at the edges, bushes and rocks
    stamp(crop(64, 84, 64, 56), 20, 366)                              # pond
    stamp(crop(19, 295, 93, 125), -64, 120)                           # big tree, west edge
    stamp(crop(204, 291, 72, 138), 590, 300)                          # blossom tree, south-east
    stamp(crop(49, 424, 34, 30), 96, 44)
    stamp(crop(16, 427, 26, 23), 150, 50)
    stamp(crop(49, 424, 34, 30), 400, 380)
    stamp(crop(99, 251, 24, 23), 100, 392)
    stamp(crop(41, 258, 23, 16), 440, 330)
    stamp(crop(71, 252, 22, 22), 360, 30)
    for sx, x, y in [(64, 236, 408), (80, 262, 398), (96, 290, 392), (112, 322, 386), (64, 356, 376), (80, 388, 362), (96, 420, 344), (112, 452, 322), (64, 482, 298), (80, 508, 272), (96, 526, 250)]:
        stamp(crop(sx, 49, 15, 15), x, y)                             # stepping stones, front door to the catio gate

    # indoors: a Wood Garden bookshelf in the study, a chest at the foot of the bed
    stamp(wood_piece("Bookshelf/Bookshelf-1.png"), 282, 232)
    stamp(wood_piece("Chest/Chest-1.png"), 161, 296)
    return g
