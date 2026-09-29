"""The manor's floor plans: two floors of a refurbished stone house, drawn from Cosy Cabin alone (committable).

Layout, in 16 px tiles (the page's MANOR block carries these numbers; see furniture.py):

    ground (the cat café)   café | kitchen & counter | cat lounge
                            craft room (bay window) | entrance hall (the stair) | terrace (glazed)   catio, outdoors
    upper (her quarters)    library (the brain) | ensuite | bedroom
                                          landing (over the hall)

It runs from public to private, the way houses and game levels both do. The front door opens into the hall, with
the counter straight ahead (where you order), the café to the left and the cat lounge to the right. The craft room
is the Montfortoise shop, so its bay window is its shop window on the drive, at the bottom left. The terrace is the
café's glass verrière, and the catio is fenced against it at the bottom right, reached by the cat flap. The one
stair rises from the middle of the hall to the landing, in the same place on both floors, so going up never moves
the camera. Upstairs covers the back range and the landing. The craft room and the terrace are single-storey
wings, and the page shows the ground floor faded under them.

This module is the shell only: floors, back walls, walls, doorways and glass. Furniture is placed as pieces by
the page (furniture.py).
"""
from PIL import Image

T = 16
FACE = 32                       # a back wall, ceiling to floor
SIZE = (60 * T, 36 * T)         # the whole grounds, native pixels

# walls: 5 px bands, outer to inner. Outside walls are the pack's grey stone, inside ones its warm stone.
STONE_OUT = [(65, 9, 9), (121, 101, 98), (152, 134, 129), (165, 149, 143), (121, 101, 98)]
STONE_IN = [(65, 9, 9), (102, 63, 57), (134, 98, 86), (151, 115, 100), (102, 63, 57)]
MORTAR_OUT, MORTAR_IN = (105, 86, 83), (88, 52, 46)
GLASS = [(65, 9, 9), (116, 141, 172), (142, 177, 204), (130, 165, 190), (65, 9, 9)]
WOOD = [(65, 9, 9), (107, 46, 26), (151, 75, 42), (188, 91, 48)]        # the balustrade and the attic ladder
SASH = (946, 354, 28, 18)       # Cosy Cabin's cream sash window, on the objects sheet

# key: floor, tile box (x0, y0, x1, y1), floor, back wall (None: floor to the top, as in a glass room)
ROOMS = {
    "dining":  ("ground", (6, 3, 19, 13), "wood", "paper32"),          # the café: pale boards, blue stripes
    "kitchen": ("ground", (19, 3, 29, 13), "pink", "paper16"),         # the counter: terracotta tiles, poppy paper
    "living":  ("ground", (29, 3, 43, 13), "wood", "paper64"),         # the cat lounge: boards, damask
    "study":   ("ground", (6, 13, 17, 24), "wood", "stone_brown"),     # the craft room: the old brick, bay window
    "hall":    ("ground", (17, 13, 32, 25), "stone", "stone_white"),   # stone flags, the old white stone left bare
    "sunroom": ("ground", (32, 13, 43, 24), "sand", None),             # the terrace: sandstone under glass
    "brain":   ("upper", (6, 3, 20, 13), "dark", "panel_dark"),        # the library: dark boards, panelled
    "bath":    ("upper", (20, 3, 26, 13), "blue", "paper0"),           # the ensuite
    "bedroom": ("upper", (26, 3, 43, 13), "wood", "paper48"),          # vines
}
LANDING = (17, 13, 32, 25)      # upstairs over the hall: not a room, just the way between them
BAY = (9, 24, 14, 26)           # the craft room's canted bay, merged into it
CHAMFER = 12                    # the bay's corners, cut at 45 degrees
CATIO = (43, 11, 57, 29)        # outdoors: decking fenced against the terrace, reached by the cat flap
STAIRS = (362, 213, 64, 80)     # native px: the stair in the hall, and its well in the landing
FRONT_DOOR = (378, 410)         # x span in the hall's south wall

# doorways: ("v", wall tile x, y from, y to) through a side wall; ("h", wall tile y, x from, x to) through a back wall
DOORS = {
    "ground": [
        ("v", 19, 120, 172),    # café <-> counter (the servery)
        ("v", 29, 120, 172),    # counter <-> cat lounge
        ("h", 13, 150, 196),    # café -> craft room
        ("h", 13, 318, 350),    # hall -> counter, west of the stair
        ("h", 13, 474, 508),    # hall -> cat lounge, east of it
        ("h", 13, 560, 640),    # cat lounge -> terrace, wide open
        ("v", 17, 290, 340),    # craft room <-> hall (the shop's door)
        ("v", 32, 290, 340),    # hall <-> terrace
    ],
    "upper": [
        ("h", 13, 282, 316),    # landing -> library
        ("h", 13, 446, 500),    # landing -> bedroom
        ("v", 26, 120, 168),    # bedroom <-> ensuite
    ],
}
# glass: ("tall", x, y, w) floor-to-ceiling on a back wall; ("v", wall x, y0, y1) and ("h", wall y, x0, x1) strips
WINDOWS = {
    "ground": [
        ("tall", 150, 53, 60),                                  # café
        ("tall", 360, 53, 40),                                  # the counter, over the sink
        ("tall", 500, 53, 40), ("tall", 616, 53, 40),           # cat lounge, either side of the fireplace
        ("v", 6, 96, 176),                                      # café west
        ("v", 6, 250, 360),                                     # craft room west
        ("h", 25, 300, 364), ("h", 25, 424, 488),               # hall south, either side of the front door
        ("h", 24, 530, 680),                                    # terrace south
        ("v", 43, 214, 290), ("v", 43, 336, 384),               # terrace east, broken by the cat flap
        ("v", 43, 90, 190),                                     # cat lounge east, over the catio
    ],
    "upper": [
        ("tall", 158, 53, 52), ("v", 6, 96, 190),               # library, between the bookcases
        ("tall", 344, 53, 30),                                  # ensuite
        ("tall", 500, 53, 40), ("tall", 620, 53, 40),           # bedroom
        ("v", 43, 90, 190),                                     # bedroom east, over the catio
        ("h", 25, 300, 364), ("h", 25, 424, 488),               # landing, over the front door
    ],
}
CAT_FLAP = (688, 312, 328)      # x of the terrace's east wall, y span


def box_px(box):
    x0, y0, x1, y1 = box
    return x0 * T, y0 * T, x1 * T + 5, y1 * T + 5


def boxes(floor):
    """Every walled box on a floor: its rooms, and upstairs the landing."""
    out = {k: (box, fl, wall) for k, (f, box, fl, wall) in ROOMS.items() if f == floor}
    if floor == "upper":
        out["landing"] = (LANDING, "wood", None)
    return out


def bay_poly():
    """The bay's outline, in native px: straight sides out of the craft room's wall, cut corners, a front."""
    X0, _, X1, _ = box_px(BAY)
    y0, y1 = ROOMS["study"][1][3] * T, BAY[3] * T + 5
    return [(X0, y0), (X0, y1 - CHAMFER), (X0 + CHAMFER, y1), (X1 - CHAMFER, y1), (X1, y1 - CHAMFER), (X1, y0)]


def in_poly(x, y, poly):
    hit = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def seg_dist(x, y, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return ((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2) ** 0.5


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
        "stone": tm.crop((336, 112, 352, 128)), "brownstone": tm.crop((400, 112, 416, 128)), "cobble": tm.crop((464, 112, 480, 128)),
    }


def tall_glass(objects, w):
    """A floor-to-ceiling window: the pack's cream sash window stretched to the wall's height and repeated."""
    x, y, sw, sh = SASH
    s = objects.crop((x, y, x + sw, y + sh))
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


def textures(tm, ex):
    """Floors and back walls, all from the Cosy Cabin sheets."""
    walls = {f"paper{c}": tm.crop((c, 32, c + 16, 52)) for c in (0, 16, 32, 48, 64)}
    walls.update({
        "panel_light": tm.crop((0, 112, 32, 132)), "panel_dark": tm.crop((32, 112, 64, 132)),
        "stone_brown": tm.crop((0, 176, 16, 196)), "stone_white": tm.crop((16, 176, 32, 196)),
    })
    return floors(tm, ex), walls, tm.crop((0, 68, 16, 80))


def shell(tm, objects, ex, floor="ground"):
    """One floor of the house: art/house.png (ground) or art/house-upper.png (upper)."""
    img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    px = img.load()
    tex, walls, rail = textures(tm, ex)
    rooms = boxes(floor)
    bay = bay_poly() if floor == "ground" else None
    floor_at = {}

    def fill(x, y, name):
        t = tex[name]
        px[x, y] = t.getpixel((x % t.width, y % t.height))

    def inside(x, y):
        """Is this native pixel inside some box on this floor (walls included), or in the bay?"""
        for box, _, _ in rooms.values():
            X0, Y0, X1, Y1 = box_px(box)
            if X0 <= x < X1 and Y0 <= y < Y1:
                return True
        return bool(bay) and in_poly(x, y, bay)

    # floors, and each room's back wall: paper (20 px) over a rail (12 px), or panelling/stone the full height
    for name, (box, fl, wall) in rooms.items():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0 + 5, X1 - 5):
            for y in range(Y0 + 5, Y1 - 5):
                fy = y - (Y0 + 5)
                if wall and fy < FACE:
                    w = walls[wall]
                    if not wall.startswith("stone"):
                        px[x, y] = w.getpixel((x % 16, fy)) if fy < 20 else rail.getpixel((x % 16, fy - 20))
                    else:
                        px[x, y] = w.getpixel((x % w.width, fy % w.height))
                else:
                    fill(x, y, fl)
                    floor_at[(x // T, y // T)] = fl
    # walls: a mitred 5 px band round each box, grey stone where the other side is outdoors
    for box, _, _ in rooms.values():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0, X1):
            for y in range(Y0, Y1):
                d = min(x - X0, X1 - 1 - x, y - Y0, Y1 - 1 - y)
                if d >= 5:
                    continue
                side = [(x - X0, (-6, 0)), (X1 - 1 - x, (6, 0)), (y - Y0, (0, -6)), (Y1 - 1 - y, (0, 6))]
                _, (dx, dy) = min(side, key=lambda s: s[0])
                out = not inside(x + dx, y + dy)
                band, mortar = (STONE_OUT, MORTAR_OUT) if out else (STONE_IN, MORTAR_IN)
                along = y if dx else x
                px[x, y] = mortar if 1 <= d <= 3 and along % 9 == 0 else band[d]

    # the bay: the craft room's floor runs out into it through the south wall; glass on its three faces
    if bay:
        xs, ys = [p[0] for p in bay], [p[1] for p in bay]
        edges = list(zip(bay[1:-1], bay[2:]))              # the five glazed edges (not the wall it opens from)
        for x in range(min(xs), max(xs)):
            for y in range(min(ys), max(ys)):
                if not in_poly(x + .5, y + .5, bay):
                    continue
                d = min(seg_dist(x + .5, y + .5, a, b) for a, b in edges)
                if d < 5:
                    px[x, y] = GLASS[int(d)] if int(d) in (0, 4) or (x + y) % 16 else GLASS[0]
                else:
                    fill(x, y, "wood")
        X0, X1 = box_px(BAY)[0], box_px(BAY)[2]
        sy = ROOMS["study"][1][3] * T
        for x in range(X0 + 5, X1 - 5):                     # clear the wall between room and bay
            for y in range(sy, sy + 5):
                fill(x, y, "wood")

    def floor_near(x, y):
        for dx in (8, -8, 0):
            for dy in (0, 8, 40):
                f = floor_at.get(((x + dx) // T, (y + dy) // T))
                if f:
                    return f
        return "wood"

    for kind, w, a, b in DOORS[floor]:
        if kind == "v":
            for x in range(w * T, w * T + 5):
                for y in range(a, b):
                    fill(x, y, floor_near(x, y))
        else:
            y0 = w * T
            fl = floor_near((a + b) // 2, y0 + FACE + 8)
            below = [wl for bx, _, wl in rooms.values() if box_px(bx)[0] <= a < box_px(bx)[2] and box_px(bx)[1] <= y0 + 8 < box_px(bx)[3]]
            deep = 5 + (FACE if below and below[0] else 0)          # through the back wall below, if it has one
            for x in range(a, b):
                for y in range(y0, y0 + deep):
                    fill(x, y, fl)
            for y in range(y0, y0 + deep):
                for i in range(5):
                    px[a - 5 + i, y] = STONE_IN[4 - i]
                    px[b + i, y] = STONE_IN[i]
    for kind, *a in WINDOWS[floor]:
        if kind == "tall":
            x, y, w = a
            img.alpha_composite(tall_glass(objects, w), (x, y))
        elif kind == "v":
            w, y0, y1 = a
            for y in range(y0, y1):
                for i in range(5):
                    px[w * T + i, y] = GLASS[0] if (y - y0) % 16 == 0 or y == y1 - 1 else GLASS[i]
        else:
            h, x0, x1 = a
            for x in range(x0, x1):
                for i in range(5):
                    px[x, h * T + i] = GLASS[0] if (x - x0) % 16 == 0 or x == x1 - 1 else GLASS[i]

    hy = ROOMS["hall"][1][3] * T
    if floor == "ground":
        fx, fy0, fy1 = CAT_FLAP
        for y in range(fy0, fy1):
            for i in range(5):
                px[fx + i, y] = (65, 9, 9) if y in (fy0, fy1 - 1) else (88, 26, 17)
        for x in range(*FRONT_DOOR):
            for y in range(hy, hy + 5):
                fill(x, y, "stone")
        # front steps: two stone treads down from the front door
        for i, (inset, dark) in enumerate(((0, (121, 101, 98)), (4, (102, 84, 80)))):
            for x in range(FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 6 + inset):
                for y in range(hy + 5 + i * 5, hy + 10 + i * 5):
                    fill(x, y, "stone")
                    if y == hy + 9 + i * 5 or x in (FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 5 + inset):
                        px[x, y] = dark
    else:
        # the stairwell: open to the hall below, with a balustrade round its three open sides
        sx, sy, sw, sh = STAIRS
        for x in range(sx, sx + sw):
            for y in range(sy, sy + sh):
                px[x, y] = (0, 0, 0, 0)
        for x in range(sx - 4, sx + sw + 4):
            for y in range(sy, sy + sh + 4):
                d = min(x - (sx - 4), sx + sw + 3 - x, sy + sh + 3 - y)
                if 0 <= d < 4 and not (sx <= x < sx + sw and sy <= y < sy + sh):
                    post = (y - sy) % 12 < 3 if x < sx or x >= sx + sw else (x - sx) % 12 < 3
                    px[x, y] = WOOD[0] if d in (0, 3) else WOOD[3 if post else 2]
        # the attic ladder, where the old cats go to nap: a hatch and rungs in the landing's south-east corner
        lx, ly = box_px(LANDING)[2] - 5 - 28, hy - 44
        for x in range(lx, lx + 18):
            for y in range(ly, ly + 34):
                edge = x in (lx, lx + 17) or y in (ly, ly + 33)
                rungs = x in (lx + 3, lx + 4, lx + 13, lx + 14) or (y - ly) % 6 == 3
                px[x, y] = WOOD[0] if edge else WOOD[2] if rungs else (50, 30, 26)
    # the house casts a soft shadow to the south-east, so it sits on the ground; the upper floor, higher, casts it
    # further
    off = 4 if floor == "ground" else 8
    alpha = img.getchannel("A").point(lambda a: 255 if a else 0)
    shade = Image.new("RGBA", SIZE, (28, 44, 20, 110))
    under = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    under.paste(shade, (off, off), alpha)
    under.alpha_composite(img)
    return under


def grounds(sheet, wood, props, struct):
    """Outdoors, from the licensed packs (never committed): the catio's deck and fence, the drive, the
    fountain on it, parterres either side, the arch gate, a pond, trees, bushes and rocks.
    sheet: Heosphorus's garden (already greened by build-art's spring()); wood(name): a Wood Garden piece;
    props, struct: Cainos's sheets (drawn on a 32 px grid, so they read large: garden stonework only)."""
    g = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    crop = lambda x, y, w, h: sheet.crop((x, y, x + w, y + h))
    stone = lambda x, y, w, h: props.crop((x, y, x + w, y + h))
    stamp = lambda im, x, y: g.alpha_composite(im, (x, y))
    cx = (FRONT_DOOR[0] + FRONT_DOOR[1]) // 2          # the drive's axis
    hy = ROOMS["hall"][1][3] * T + 5 + 10               # the foot of the front steps

    # the catio, at the bottom right: decking against the cat lounge and the terrace, fenced where it meets the
    # garden, with a rose-arch gate on its south side
    X0, Y0, X1, Y1 = CATIO[0] * T + 8, CATIO[1] * T + 16, CATIO[2] * T, CATIO[3] * T
    deck = wood("Floor/Brown-floor-1.png")
    for x in range(X0 - 4, X1, 32):
        for y in range(Y0, Y1, 32):
            stamp(deck.crop((0, 0, min(32, X1 - x), min(32, Y1 - y))), x, y)
    for x in range(X0 - 2, X1 - 28, 32):
        stamp(wood("White fence/White-fence-2.png"), x, Y0 - 14)
    for y in range(Y0 - 8, Y1 - 20, 36):
        stamp(wood("White fence/White-fence-4.png"), X1 - 4, y)
    wall_end = ROOMS["sunroom"][1][3] * T + 5            # below the terrace, the catio's west side is open garden
    for y in range(wall_end - 4, Y1 - 20, 36):
        stamp(wood("White fence/White-fence-4.png"), X0 - 12, y)
    gx = X0 + 40
    for x in range(X0 - 12, gx - 4, 28):
        stamp(wood("White fence/White-fence-2.png"), x, Y1 - 8)
    stamp(wood("White gate/White-red-flower-gate-1.png"), gx, Y1 - 29)
    for x in range(gx + 42, X1 - 24, 28):
        stamp(wood("White fence/White-fence-2.png"), x, Y1 - 8)
    stamp(wood("White fence/White-fence-5.png"), X1 - 4, Y1 - 31)
    stamp(crop(113, 293, 81, 121), X1 - 16, Y0 - 58)                                          # a shade tree over the fence

    # the drive: stepping stones from the front steps round the fountain to the arch gate
    fy = hy + 22
    stamp(stone(353, 269, 94, 72), cx - 47, fy)                          # the round fountain
    stamp(stone(445, 21, 37, 72), cx - 18, fy - 22)                      # the praying statue in it
    path = [(-30, 4), (30, 4), (-56, 22), (56, 22), (-66, 42), (66, 42), (-60, 62), (60, 62), (-36, 80), (36, 80), (-14, 90), (14, 90)]
    for i, (dx, dy) in enumerate(path):
        stamp(crop(64 + 16 * (i % 4), 49, 15, 15), cx + dx - 7, hy + dy)
    ay = SIZE[1] - 64
    stamp(stone(29, 166, 9, 53), cx - 16, ay + 8)                        # the gate's wooden doors, swung open
    stamp(stone(57, 166, 9, 53), cx + 10, ay + 8)
    stamp(struct.crop((408, 27, 488, 91)), cx - 40, ay)                  # the stone archway
    stamp(stone(165, 217, 21, 34), cx - 60, ay + 30)                     # vases either side
    stamp(stone(165, 348, 21, 32), cx + 40, ay + 32)
    stamp(stone(453, 118, 22, 37), FRONT_DOOR[0] - 36, hy - 8)           # lanterns by the front steps
    stamp(stone(453, 118, 22, 37), FRONT_DOOR[1] + 14, hy - 8)

    # parterres either side of the drive: one before the shop's bay, one towards the catio; a bench facing it
    bed = crop(150, 6, 102, 86)
    stamp(bed, box_px(BAY)[0] - 10, BAY[3] * T + 22)
    stamp(bed, cx + 98, hy + 20)
    stamp(stone(292, 19, 56, 41), cx + 120, hy + 112)                    # a stone bench
    stamp(stone(99, 160, 27, 32), X0 + 4, Y1 + 10)                       # a signpost to the catio gate

    # the edges: a pond, trees, bushes and rocks
    stamp(crop(64, 84, 64, 56), 18, SIZE[1] - 110)
    stamp(crop(19, 295, 93, 125), -40, 150)                              # big tree, west
    stamp(crop(204, 291, 72, 138), SIZE[0] - 80, SIZE[1] - 120)          # blossom tree, south-east
    for x, y, b in [(96, 404, (49, 424, 34, 30)), (240, 430, (16, 427, 26, 23)), (640, 400, (49, 424, 34, 30)),
                    (620, 440, (16, 427, 26, 23)), (18, 36, (49, 424, 34, 30)), (900, 40, (16, 427, 26, 23))]:
        stamp(crop(*b), x, y)
    for x, y, b in [(126, 520, (99, 251, 24, 23)), (760, 530, (41, 258, 23, 16)), (60, 20, (71, 252, 22, 22))]:
        stamp(crop(*b), x, y)
    return g
