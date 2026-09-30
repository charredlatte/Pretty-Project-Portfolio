"""The manor's floor plans: two floors of a storybook Transylvanian Baroque house, drawn from all of Charlotte's
packs (so art/licensed/house.png and house-upper.png are never committed).

Both floors stand on one grid, in 16 px tiles (the page's MANOR block carries these numbers; see furniture.py):

    columns  x = 6 | 17 | 32 | 43        rows  y = 3 | 13 | 24

    ground (the cat café)   café         | kitchen & counter | cat lounge
                            craft room   | entrance hall     | terrace (glazed)     catio, outdoors
                            (bay window)   (the stair, the front door)
    upper (her quarters)    library      | landing           | bedroom | ensuite
                                           (over the kitchen and the hall)

Every upstairs wall stands on a ground-floor wall, except the ensuite's, a light partition inside the bedroom's
bay. It runs from public to private, the way houses and game levels both do. The front door opens into the hall,
with the counter straight ahead behind the stair, the shop's craft room on one side and the terrace on the other.
The craft room's bay window is its shop window on the drive, at the bottom left; the catio is fenced against the
terrace at the bottom right, reached by the cat flap. The one stair rises from the middle of the hall to an open
landing, in the same place on both floors, so going up never moves the camera. The craft room and the terrace are
single-storey wings, and the page shows the ground floor faded under them.

The look: ochre limewash with white stucco and stone quoins outside, a south facade on a stone plinth with
green-shuttered arched windows, and an arched front door under a pediment with a stained-glass fanlight. Inside:
pale plaster walls on an oak beam, dressed stone in the entrance hall, carved panelling with a gilt rail in the
library, white panels with gilt trellis pilasters in the cat lounge, tiles in the kitchen and ensuite, stained
glass in the library, the lounge and the hall. Doorways through a back wall are clean cuts under a carved oak
arch. The details after Peles and Sinaia (Charlotte's photos) are drawn here in one palette; the textures come
from the packs.

Game-UI rules (Charlotte's UI plugin): the house is the map's terrain layer, so it stays quieter than the cats and
signs on it. Floors are softened (quiet()); a sign's corner of each back wall stays calm, so stained glass is
coloured only in a window's lower two-thirds; rooms differ by pattern, not only colour; nothing moves.

This module is the shell and the grounds. Furniture is placed as pieces by the page (furniture.py).
"""
import colorsys

from PIL import Image

T = 16
FACE = 32                       # a back wall, ceiling to floor
FACADE = 32                     # the south face of an outside wall, seen in 3/4 below it (ground floor only)
SIZE = (60 * T, 36 * T)         # the whole grounds, native pixels
SASH = (946, 354, 28, 18)       # Cosy Cabin's cream sash window, on the objects sheet

# the palette: the Sprout Lands interface's creams and tans, with Baroque accents kept soft
INK = (63, 42, 32)
OCHRE = [(240, 212, 160), (228, 192, 134), (204, 164, 108)]      # limewash render: lit, flat, shaded
STUCCO = [(250, 244, 230), (234, 224, 202), (198, 178, 144)]
PLASTER = [(240, 230, 210), (226, 212, 188), (150, 116, 92)]    # inside walls; the last is the oak beam
STONE = [(170, 164, 150), (138, 132, 120), (104, 98, 90)]
OAK = [(120, 82, 56), (90, 58, 40), (63, 42, 32)]
GILT = [(236, 210, 142), (212, 176, 96), (158, 122, 62)]
SHUTTER = [(132, 164, 118), (100, 132, 94), (74, 100, 72)]
IRON = (44, 38, 44)
LEAD = (60, 56, 64)
PANE = [(196, 214, 222), (158, 184, 200), (126, 152, 172)]
JEWELS = [(200, 150, 74), (180, 100, 112), (86, 140, 138), (84, 104, 160), (122, 152, 92)]   # amber rose teal cobalt leaf
GLASS = [INK, PANE[2], PANE[0], PANE[1], INK]                   # a leaded pane edge on, as in the bay
WOOD = [INK, OAK[1], OAK[0], GILT[1]]                            # the balustrade and the attic ladder
INNER = [OAK[1], PLASTER[0], PLASTER[2], PLASTER[1], OAK[1]]     # an inside wall: plaster either side of an oak beam

# key: floor, tile box (x0, y0, x1, y1), floor, back wall
ROOMS = {
    "dining":  ("ground", (6, 3, 17, 13), "wood", "paper32"),         # the café: pale boards, soft blue stripes
    "kitchen": ("ground", (17, 3, 32, 13), "terracotta", "tiles_kitchen"),   # terracotta, whitewash over blue tiles
    "living":  ("ground", (32, 3, 43, 13), "wood", "trellis"),        # the cat lounge: white panels, gilt trellis
    "study":   ("ground", (6, 13, 17, 24), "wood", "stone_brown"),    # the craft room: exposed brick, the bay window
    "hall":    ("ground", (17, 13, 32, 24), "flags", "stone_hall"),   # Cainos's big flags and dressed stone
    "sunroom": ("ground", (32, 13, 43, 24), "chequer", "paper16"),    # the terrace: an orangery chequer, glass on two sides
    "brain":   ("upper", (6, 3, 17, 13), "dark", "panel_library"),    # the library: dark boards, carved panelling, gilt rail
    "bedroom": ("upper", (32, 3, 38, 13), "wood", "paper48"),         # vines
    "bath":    ("upper", (38, 3, 43, 13), "blue", "tiles_bath"),      # the ensuite, partitioned off the bedroom
}
LANDING = (17, 3, 32, 24)       # upstairs over the kitchen and the hall: not a room, the way between them
BAY = (9, 24, 14, 26)           # the craft room's canted bay, merged into it
CHAMFER = 12                    # the bay's corners, cut at 45 degrees
CATIO = (43, 11, 57, 29)        # outdoors: decking fenced against the terrace, reached by the cat flap
STAIRS = (362, 213, 64, 80)     # native px: the stair in the hall, and its well in the landing
FRONT_DOOR = (378, 410)         # x span in the hall's south wall

# doorways: ("v", wall tile x, y from, y to) through a side wall; ("h", wall tile y, x from, x to) through a back wall
DOORS = {
    "ground": [
        ("v", 17, 120, 172),    # café <-> kitchen (the servery)
        ("v", 32, 120, 172),    # kitchen <-> cat lounge
        ("h", 13, 150, 196),    # café -> craft room
        ("h", 13, 296, 336),    # hall -> kitchen, west of the stair
        ("h", 13, 452, 492),    # hall -> kitchen, east of it
        ("h", 13, 560, 640),    # cat lounge -> terrace, wide open
        ("v", 17, 290, 340),    # craft room <-> hall (the shop's door)
        ("v", 32, 290, 340),    # hall <-> terrace
    ],
    "upper": [
        ("v", 17, 120, 172),    # landing <-> library
        ("v", 32, 120, 172),    # landing <-> bedroom
        ("v", 38, 120, 168),    # bedroom <-> ensuite
    ],
}
# glass: ("tall", x, y, w) clear floor-to-ceiling on a back wall, ("stained", x, y, w) the same in stained glass;
# ("v", wall x, y0, y1) and ("h", wall y, x0, x1) leaded strips with shutter ends in outside walls
WINDOWS = {
    "ground": [
        ("tall", 156, 53, 60),                                  # café
        ("tall", 374, 53, 40),                                  # the counter, over the sink
        ("stained", 526, 53, 36), ("stained", 642, 53, 36),     # cat lounge, either side of the fireplace
        ("v", 6, 96, 176),                                      # café west
        ("v", 6, 250, 360),                                     # craft room west
        ("h", 24, 300, 364), ("h", 24, 424, 488),               # hall south, either side of the front door
        ("h", 24, 530, 680),                                    # terrace south
        ("v", 43, 214, 290), ("v", 43, 336, 380),               # terrace east, broken by the cat flap
        ("v", 43, 90, 190),                                     # cat lounge east, over the catio
    ],
    "upper": [
        ("stained", 158, 53, 52), ("v", 6, 96, 190),            # library, between the bookcases
        ("tall", 316, 53, 40), ("tall", 434, 53, 40),           # the landing's back wall
        ("tall", 556, 53, 34),                                  # bedroom
        ("tall", 618, 53, 24), ("v", 43, 90, 190),              # ensuite, and its window over the catio
        ("h", 24, 300, 364), ("h", 24, 424, 488),               # landing, over the front door
    ],
}
STAINED_STRIPS = {(24, 300), (24, 424)}                   # the hall's south windows, either side of the door
CAT_FLAP = (688, 312, 328)      # x of the terrace's east wall, y span


def box_px(box):
    x0, y0, x1, y1 = box
    return x0 * T, y0 * T, x1 * T + 5, y1 * T + 5


def boxes(floor):
    """Every walled box on a floor: its rooms, and upstairs the landing."""
    out = {k: (box, fl, wall) for k, (f, box, fl, wall) in ROOMS.items() if f == floor}
    if floor == "upper":
        out["landing"] = (LANDING, "wood", "paper0")
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


def inside(x, y, floor="ground"):
    """Is this native pixel inside some box on this floor (walls included), or in the bay?"""
    for box, _, _ in boxes(floor).values():
        X0, Y0, X1, Y1 = box_px(box)
        if X0 <= x < X1 and Y0 <= y < Y1:
            return True
    return floor == "ground" and in_poly(x, y, bay_poly())


def in_catio(x, y):
    x0, y0, x1, y1 = CATIO
    return x0 * T <= x < x1 * T and y0 * T <= y < y1 * T


def outdoors(x, y):
    return not inside(x, y) and not in_catio(x, y)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def quiet(tex, desat=0.25, flat=0.18):
    """Soften a floor so cats and furniture read above it: less saturation, less contrast."""
    px = [p for p in tex.getdata() if p[3]]
    mean = [sum(p[i] for p in px) / len(px) for i in range(3)]
    out = tex.copy()
    o = out.load()
    for y in range(tex.height):
        for x in range(tex.width):
            r, g, b, a = o[x, y]
            grey = 0.3 * r + 0.59 * g + 0.11 * b
            c = [v + (grey - v) * desat for v in (r, g, b)]
            c = [v + (mean[i] - v) * flat for i, v in enumerate(c)]
            o[x, y] = tuple(round(v) for v in c) + (a,)
    return out


def hue(tex, h, sat=1.0, val=1.0):
    """Recolour a texture to a hue, keeping its shading (the kitchen's pink tiles become terracotta)."""
    out = tex.copy()
    o = out.load()
    for y in range(tex.height):
        for x in range(tex.width):
            r, g, b, a = o[x, y]
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            o[x, y] = tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, min(s * sat, 1), min(v * val, 1))) + (a,)
    return out


def textures(load):
    """Floors and back walls, from Cosy Cabin (boards, papers, tiles), Cainos (stone) and Little Dreamyland (glazed
    wall tiles)."""
    tm = load("CosyCabin_TileMap.png")
    ex = load("CosyCabin_Example2.png")
    ex = ex.resize((ex.width // 3, ex.height // 3), Image.NEAREST)     # the example ships drawn at 3x
    t = floors(tm, ex)
    ground = load("Texture/TX Tileset Stone Ground.png")
    t["terracotta"] = hue(t["pink"], 0.045, 1.5, 0.92)
    # the orangery chequer: Cosy Cabin's sandstone and pale stone, alternating by tile
    sand, stone = t["sand"], tm.crop((336, 112, 352, 128))
    cheq = Image.new("RGBA", (32, 32))
    for i, tile in enumerate((sand, stone, stone, sand)):
        cheq.paste(tile, ((i % 2) * 16, (i // 2) * 16))
    t["chequer"] = cheq
    # the hall's flags: Cainos's plain stone in 32 px slabs, laid in courses with a lit and a shaded joint
    base = ground.crop((128, 0, 160, 32))
    flags = Image.new("RGBA", (64, 64))
    for y in range(0, 64, 32):
        for x in range(-16 if y else 0, 64, 32):
            flags.paste(base, (x, y))
    f = flags.load()
    for y in range(64):
        for x in range(64):
            off = 16 if y >= 32 else 0
            if y % 32 == 0 or (x + off) % 32 == 0:
                f[x, y] = STONE[2] + (255,)
            elif y % 32 == 1 or (x + off) % 32 == 1:
                f[x, y] = STONE[0] + (255,)
    t["flags"] = flags
    t = {k: quiet(v) for k, v in t.items()}
    papers = {f"paper{c}": tm.crop((c, 32, c + 16, 52)) for c in (0, 16, 32, 48, 64)}
    walls = {k: soften(v) for k, v in papers.items()}
    walls.update({
        "panel_dark": tm.crop((32, 112, 64, 132)), "stone_brown": tm.crop((0, 176, 16, 196)),
        "stone_hall": load("Texture/TX Tileset Wall.png").crop((64, 208, 160, 240)),   # its opaque 96 px
        "rail": tm.crop((0, 68, 16, 80)),
        "glazed": load("Tileset/House_Tileset.png").crop((480, 128, 496, 144)),   # Little Dreamyland's wall tile
    })
    return t, walls


def soften(tex, t=0.22):
    """Pastel a wallpaper: blend it a little toward stucco cream."""
    out = tex.copy()
    o = out.load()
    for y in range(tex.height):
        for x in range(tex.width):
            r, g, b, a = o[x, y]
            o[x, y] = mix((r, g, b), STUCCO[0], t) + (a,)
    return out


def noise(x, y):
    """A fixed speckle (0..3) for limewash and whitewash, so flat colour reads as a hand-finished surface."""
    return ((x * 73856093) ^ (y * 19349663)) % 7 % 4


def back_wall(kind, walls, x, fy):
    """The colour of a back wall at column x, fy pixels below the ceiling (0..FACE-1)."""
    if kind == "stone_hall":                                   # dressed stone, the full height
        w = walls["stone_hall"]
        return w.getpixel((x % w.width, fy))[:3]
    if kind == "stone_brown":                                  # the studio's brick, as it was
        w = walls["stone_brown"]
        return w.getpixel((x % w.width, fy % w.height))[:3]
    if kind == "panel_library":                                # carved panelling, a gilt cornice and scalloped rail
        if fy == 0:
            return GILT[0]
        if fy == 1:
            return GILT[2]
        if fy < 22:
            return walls["panel_dark"].getpixel((x % 32, (fy - 2) % 20))[:3]
        if fy == 22:
            return GILT[1]
        if fy == 23:
            return GILT[2] if x % 4 in (1, 2) else OAK[2]
        return mix(walls["rail"].getpixel((x % 16, fy - 20))[:3], OAK[2], 0.55)
    if fy < 2:                                                 # every other wall: a white stucco cornice
        return STUCCO[fy]
    if fy == 2:
        return STUCCO[2]
    if kind == "trellis":                                      # white panels, gilt trellis pilasters every 3 tiles
        if fy >= 30:
            return GILT[2] if fy == 30 else OAK[1]
        u = x % 48
        if u in (0, 5):
            return GILT[1]
        if 1 <= u <= 4:
            i, j = u - 1, fy % 4
            ring = (i in (0, 3) and j in (1, 2)) or (j in (0, 3) and i in (1, 2))
            return GILT[0] if ring and i < 2 else GILT[1] if ring else STUCCO[0]
        if (u in (10, 42) and 6 <= fy <= 27) or (fy in (6, 27) and 10 <= u <= 42):
            return STUCCO[2]                                   # the panel's moulding
        if (u in (11, 43) and 7 <= fy <= 27) or (fy in (7, 28) and 11 <= u <= 42):
            return STUCCO[0]
        return STUCCO[1] if noise(x, fy) == 0 else mix(STUCCO[0], STUCCO[1], 0.5)
    if kind in ("tiles_kitchen", "tiles_bath"):                # whitewash over a tiled splashback, or tiled walls
        top = 18 if kind == "tiles_kitchen" else 3
        if fy >= 30:
            return OAK[1] if fy == 31 else OAK[0]
        if fy < top:
            return mix(STUCCO[0], STUCCO[1], noise(x, fy) / 4)
        if fy == top:
            return STUCCO[2]
        tile = walls["glazed"].getpixel((x % 16, (fy - top) % 16))[:3]
        if tile[0] < 225:
            return tile                                        # grout
        blue = (104, 138, 178) if kind == "tiles_kitchen" else (132, 178, 176)
        if ((x // 8) + (fy - top) // 8) % 2:                   # every other tile glazed in colour
            tile = mix(tile, blue, 0.75)
        return mix(tile, (255, 255, 255), 0.4) if (x % 8, (fy - top) % 8) == (2, 2) else tile
    # papers: soft pastel paper over a timber rail
    if fy < 20:
        return walls[kind].getpixel((x % 16, fy))[:3]
    return walls["rail"].getpixel((x % 16, fy - 20))[:3]


def stained(w, h=FACE, seed=0):
    """A floor-to-ceiling stained-glass window. The top third is plain leaded glass (a room's sign sits there);
    the lower two-thirds are lights of muted jewel colour, each with a lily."""
    g = Image.new("RGBA", (w, h))
    px = g.load()
    top = h // 3
    lights = max(1, (w - 2) // 10)
    lw = (w - 2) / lights
    for x in range(w):
        for y in range(h):
            if x in (0, w - 1) or y in (0, h - 1):
                c = STUCCO[2] if x == 0 or y == 0 else INK
            elif x in (1, w - 2) or y == h - 2:
                c = STUCCO[0]
            elif y < top:                                      # clear leaded diamonds
                c = LEAD if (x + y) % 5 == 0 or (x - y) % 5 == 0 else PANE[0 if y < top // 2 else 1]
            else:
                k = int((x - 2) // lw)
                u = (x - 2) - k * lw                           # across this light
                v = y - top
                if u < 1 or y == top:
                    c = LEAD
                else:
                    ground_ = JEWELS[(k + seed) % 2 * 2 + 1]   # rose or cobalt ground, alternating
                    mid = lw / 2
                    if abs(u - mid) < 0.8 and v > 5:
                        c = JEWELS[4]                          # the stem
                    elif (u - mid) ** 2 / 9 + (v - 5) ** 2 / 12 < 1:
                        c = JEWELS[0]                          # the bloom
                    elif (u - mid) ** 2 / 16 + (v - 5) ** 2 / 25 < 1.1 and v < 12:
                        c = JEWELS[2]                          # its leaves
                    elif v % 7 == 0:
                        c = LEAD
                    else:
                        c = ground_
                    c = mix(c, PANE[0], 0.18)                  # muted: glass, not a jewel box
            px[x, y] = c + (255,)
    return g


def shell(load, floor="ground"):
    """One floor of the house: floors, back walls, walls, doorways, glass, and on the ground floor the south facade
    and the front steps (art/licensed/house.png); upstairs the landing's stairwell and the attic ladder
    (art/licensed/house-upper.png). load(path end) opens a sheet from Charlotte's packs."""
    img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    px = img.load()
    tex, walls = textures(load)
    rooms = boxes(floor)
    ground = floor == "ground"
    bay = bay_poly() if ground else None
    floor_at = {}

    def fill(x, y, name):
        t = tex[name]
        px[x, y] = t.getpixel((x % t.width, y % t.height))

    # floors and each room's back wall
    for name, (box, fl, wall) in rooms.items():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0 + 5, X1 - 5):
            for y in range(Y0 + 5, Y1 - 5):
                fy = y - (Y0 + 5)
                if wall and fy < FACE:
                    px[x, y] = back_wall(wall, walls, x, fy) + (255,)
                else:
                    fill(x, y, fl)
                    floor_at[(x // T, y // T)] = fl
    # walls: a mitred 5 px band round each box. Outside: ochre limewash on a stone course, stucco quoins at the
    # corners, lit on the north and west. Inside: pale plaster either side of an oak beam.
    for box, _, _ in rooms.values():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0, X1):
            for y in range(Y0, Y1):
                d = min(x - X0, X1 - 1 - x, y - Y0, Y1 - 1 - y)
                if d >= 5:
                    continue
                side = [(x - X0, (-6, 0)), (X1 - 1 - x, (6, 0)), (y - Y0, (0, -6)), (Y1 - 1 - y, (0, 6))]
                _, (dx, dy) = min(side, key=lambda s: s[0])
                if inside(x + dx, y + dy, floor):
                    px[x, y] = INNER[d] + (255,)
                    continue
                lit = dx < 0 or dy < 0
                band = [INK, STONE[1] if lit else STONE[2], OCHRE[0] if lit else OCHRE[1], OCHRE[1], OCHRE[2]]
                c = band[d]
                # quoins: alternate stucco blocks for 20 px from a corner whose other side is outdoors too
                if 1 <= d <= 3:
                    if dy:
                        a, corner = min((x - X0, X0 - 6), (X1 - 1 - x, X1 + 5))
                        other = not inside(corner, y, floor)
                    else:
                        a, corner = min((y - Y0, Y0 - 6), (Y1 - 1 - y, Y1 + 5))
                        other = not inside(x, corner, floor)
                    if other and a < 20 and (a // 5) % 2 == 0:
                        c = STUCCO[0] if lit and d == 1 else STUCCO[1] if d < 3 else STUCCO[2]
                px[x, y] = c + (255,)

    # the bay: the craft room's floor runs out into it through the south wall; leaded glass on its three faces
    if bay:
        xs, ys = [p[0] for p in bay], [p[1] for p in bay]
        edges = list(zip(bay[1:-1], bay[2:]))              # the five glazed edges (not the wall it opens from)
        for x in range(min(xs), max(xs)):
            for y in range(min(ys), max(ys)):
                if not in_poly(x + .5, y + .5, bay):
                    continue
                d = min(seg_dist(x + .5, y + .5, a, b) for a, b in edges)
                if d < 5:
                    px[x, y] = (GLASS[int(d)] if int(d) in (0, 4) or (x + y) % 12 else LEAD) + (255,)
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

    # doorways: the floor runs through the wall and its cut ends are capped. Through a back wall the cut goes down
    # the room's wall face too, edged, under a carved oak arch with a gilt line: a doorway, not a corridor.
    for kind, w, a, b in DOORS[floor]:
        if kind == "v":
            for x in range(w * T, w * T + 5):
                for y in range(a, b):
                    fill(x, y, floor_near(x, y))
                px[x, a - 1] = px[x, b] = INK + (255,)
            for y in range(a, b):                              # the threshold
                px[w * T + 2, y] = mix(px[w * T + 2, y][:3], INK, 0.35) + (255,)
        else:
            y0 = w * T
            fl = floor_near((a + b) // 2, y0 + FACE + 8)
            for x in range(a, b):
                for y in range(y0, y0 + 5 + FACE):
                    fill(x, y, fl)
            for y in range(y0, y0 + 5 + FACE):
                px[a - 1, y] = px[b, y] = INK + (255,)
            c, r = (a + b - 1) / 2, (b - a) / 2
            for x in range(a, b):
                k = 1 - ((x - c) / r) ** 2
                spring = y0 + 5 + round(7 * (1 - max(k, 0) ** 0.5))
                for y in range(y0, spring + 1):
                    px[x, y] = (OAK[0] if y < spring - 1 else OAK[2]) + (255,)
                px[x, spring + 1] = GILT[1] + (255,)
            for x in range(a, b):                              # its threshold
                y = y0 + 5 + FACE - 1
                px[x, y] = mix(px[x, y][:3], INK, 0.35) + (255,)

    objects = load("CosyCabin_Objects.png")
    for kind, *a in WINDOWS[floor]:
        if kind in ("tall", "stained"):
            x, y, w = a
            img.alpha_composite(tall_glass(objects, w) if kind == "tall" else stained(w, seed=x), (x, y))
        else:
            wall, t0, t1 = a
            jewel = ground and (wall, t0) in STAINED_STRIPS
            for t in range(t0, t1):
                for i in range(5):
                    q = (wall * T + i, t) if kind == "v" else (t, wall * T + i)
                    u = t - t0
                    if i in (0, 4):
                        c = INK
                    elif u < 2 or u >= t1 - t0 - 2:
                        c = SHUTTER[1] if i != 2 else SHUTTER[2]   # painted shutter ends
                    elif (u + i) % 4 == 0 or (u - i) % 4 == 0:
                        c = LEAD
                    elif jewel:
                        c = mix(JEWELS[(u // 4) % 4], PANE[0], 0.2)
                    else:
                        c = PANE[1] if i == 1 else PANE[2]
                    px[q] = c + (255,)

    hy = ROOMS["hall"][1][3] * T
    if ground:
        fx, fy0, fy1 = CAT_FLAP
        for y in range(fy0, fy1):
            for i in range(5):
                px[fx + i, y] = (OAK[2] if y in (fy0, fy1 - 1) else OAK[1]) + (255,)
        for x in range(*FRONT_DOOR):
            for y in range(hy, hy + 5):
                fill(x, y, "flags")
        facade(img, walls)
        steps(img, tex)
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
                    px[x, y] = (WOOD[0] if d in (0, 3) else WOOD[3 if post else 2]) + (255,)
        # the attic ladder, where the old cats go to nap: a hatch and rungs in the landing's south-east corner
        lx, ly = box_px(LANDING)[2] - 5 - 28, hy - 44
        for x in range(lx, lx + 18):
            for y in range(ly, ly + 34):
                edge = x in (lx, lx + 17) or y in (ly, ly + 33)
                rungs = x in (lx + 3, lx + 4, lx + 13, lx + 14) or (y - ly) % 6 == 3
                px[x, y] = (WOOD[0] if edge else WOOD[2] if rungs else (50, 30, 26)) + (255,)
    # the house casts a soft shadow to the south-east, so it sits on the ground; the upper floor, higher, casts it
    # further
    off = 4 if ground else 8
    alpha = img.getchannel("A").point(lambda a: 255 if a else 0)
    shade = Image.new("RGBA", SIZE, (28, 44, 20, 110))
    under = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    under.paste(shade, (off, off), alpha)
    under.alpha_composite(img)
    return under


def facade_px(x, v, walls, glass):
    """One pixel of the south facade, v rows below the wall (0..FACADE-1): cornice, render with pilasters, a
    string course, then a stone plinth. glass=True: the conservatory's glazed face instead of render."""
    if v < 2:
        return STUCCO[v]
    if v == 2:
        return STUCCO[2]
    if v == 23:
        return STUCCO[1]
    if v == 24:
        return STUCCO[2]
    if v >= 25:                                                # the plinth: Cainos's dressed stone, a dark foot
        if v == FACADE - 1:
            return INK
        w = walls["stone_hall"]
        return mix(w.getpixel((x % w.width, v - 25 + 9))[:3], STONE[1], 0.2)
    if glass:
        if x % 12 in (0, 1):
            return STUCCO[0] if x % 12 == 0 else STUCCO[2]
        return PANE[0] if (x % 12) - (v - 3) // 2 in (3, 4) else PANE[1] if v < 13 else PANE[2]
    u = x % 48
    if u < 5:                                                  # a stucco pilaster, lit on its left
        return STUCCO[0] if u == 0 else STUCCO[2] if u == 4 else STUCCO[1]
    if v == 3:
        return OCHRE[2]                                        # the cornice's shadow
    return mix(OCHRE[1], OCHRE[0], 0.45) if noise(x, v) == 0 else OCHRE[1]


def window_px(dx, v):
    """An arched window with green shutters, dx = -9..9 from its centre, v = rows below the wall. None: render."""
    a = abs(dx)
    if not (6 <= v <= 20) or a > 9:
        return None
    if a >= 6:                                                 # shutters, 3 px, slatted
        if v < 9:
            return None
        return SHUTTER[2] if a == 9 or v == 20 else SHUTTER[0] if v % 2 else SHUTTER[1]
    top = 6 + (a >= 3) + (a >= 5)                              # the arch
    if v < top:
        return None
    if v == top or a == 5 or v == 20:
        return STUCCO[0] if v != 20 else STUCCO[2]             # stucco surround and sill
    if a == 0 or v == 13:
        return LEAD
    return PANE[2] if v > 13 or dx > 0 else PANE[1]


def facade(img, walls):
    """The south face of every ground-floor outside wall, in 3/4 below it: drawn only on open ground, never on a
    room, the bay or the catio. Nearer walls are drawn last, so they overlap the ones behind. The terrace and the
    bay are glazed; the rest are render with arched, shuttered windows."""
    px = img.load()
    door_c = sum(FRONT_DOOR) // 2
    faces = [(k, box) for k, (f, box, _, _) in ROOMS.items() if f == "ground"] + [("bay", BAY)]
    for name, box in sorted(faces, key=lambda r: r[1][3]):
        X0, Y0, X1, Y1 = box_px(box)
        glass = name in ("sunroom", "bay")
        spots = [x for x in range(X0, X1) if x % 48 == 24 and all(outdoors(x + d, Y1 + 10) for d in (-10, 10))]
        for x in range(X0, X1):
            for v in range(FACADE):
                y = Y1 + v
                if not outdoors(x, y):
                    continue
                c = facade_px(x, v, walls, glass)
                if not glass:
                    for s in spots:
                        if name == "hall" and abs(s - door_c) < 30:
                            continue
                        w = window_px(x - s, v)
                        if w:
                            c = w
                px[x, y] = c + (255,)
    front_door(img)


def front_door(img):
    """An arched double door in the entrance hall's facade, under a pediment, with a stained-glass fanlight and a
    pot of red geraniums either side."""
    px = img.load()
    c = (FRONT_DOOR[0] + FRONT_DOOR[1] - 1) / 2
    top = ROOMS["hall"][1][3] * T + 5                          # the facade's first row
    for v in range(FACADE - 1):
        y = top + v
        for x in range(FRONT_DOOR[0] - 8, FRONT_DOOR[1] + 8):
            d = x - c
            a = abs(d)
            col = None
            if v <= 6 and a <= 4 + v * 2.4:                    # the pediment, over the cornice
                col = INK if a > 3 + v * 2.4 or v == 6 else STUCCO[0] if d < 0 else STUCCO[1]
            elif 7 <= v <= 24 and a <= 14:
                arch = 14 * (1 - min(1, ((v - 7) / 7) ** 2) ** 0.5) if v < 14 else 0
                inner = 12 * (1 - min(1, ((v - 8) / 6) ** 2) ** 0.5) if v < 14 else 0
                if a > 14 - arch:
                    col = None
                elif a > 12 - inner or v == 7:
                    col = STUCCO[0] if d < 0 else STUCCO[2]    # the stucco surround
                elif v < 14:                                   # the fanlight: a sunburst of lead and colour
                    ray = int((d + 12) // 4)
                    col = LEAD if v == 13 or (d + 12) % 4 == 0 else mix(JEWELS[ray % 4], PANE[0], 0.15)
                else:                                          # two oak leaves with iron studs
                    col = INK if a < 0.6 or a > 11.4 else OAK[0] if (x % 4) else OAK[1]
                    if v in (17, 21) and a in (3.5, 8.5):
                        col = IRON
            elif 18 <= v <= 24 and 16 <= a <= 21:              # geraniums in stone pots
                if v >= 22:
                    col = STONE[1] if v < 24 else STONE[2]
                elif (x + v) % 3 == 0:
                    col = (104, 136, 84)
                else:
                    col = (196, 72, 72) if (x * 3 + v) % 4 else (226, 118, 112)
            if col:
                px[x, y] = col + (255,)


def steps(img, tex):
    """Two stone treads down from the front door, at the foot of the facade, with wrought-iron scroll rails."""
    px = img.load()
    hy = ROOMS["hall"][1][3] * T + 5 + FACADE
    for i, inset in enumerate((0, 4)):
        for x in range(FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 6 + inset):
            for y in range(hy + i * 5, hy + 5 + i * 5):
                t = tex["flags"]
                c = t.getpixel((x % t.width, y % t.height))[:3]
                if y == hy + 4 + i * 5 or x in (FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 5 + inset):
                    c = STONE[2]
                elif y == hy + i * 5:
                    c = STONE[0]
                px[x, y] = c + (255,)
    for side in (-1, 1):
        rx = FRONT_DOOR[0] - 12 if side < 0 else FRONT_DOOR[1] + 11
        for y in range(hy - 6, hy + 10):
            px[rx, y] = IRON + (255,)
        for dx, dy in ((0, 10), (side * -1, 11), (side * -2, 10), (side * -2, 9), (side * -1, 8)):   # the scroll
            px[rx + dx, hy + dy] = IRON + (255,)
        px[rx, hy - 7] = GILT[1] + (255,)


def grounds(sheet, wood, props, struct, more):
    """Outdoors, from the licensed packs (never committed): the catio's deck and fence, the drive with its lamps,
    the fountain beside it, a parterre before the craft room's bay, the arch gate, a pond, a well, a spruce forest
    round the edges like the woods behind Peles, and flowers, grass and mushrooms scattered on the lawn.
    sheet: Heosphorus's garden (already greened by build-art's spring()); wood(name): a Wood Garden piece;
    props, struct: Cainos's sheets (drawn on a 32 px grid, so they read large: garden stonework only);
    more: "nature", "exterior" and "floor" from Little Dreamyland, "biome" from Sprout Lands Sprites, "plant"
    (Cainos's, greened)."""
    import random
    from PIL import ImageDraw
    g = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    busy = Image.new("1", SIZE, 0)                     # where nothing more may go
    rnd = random.Random(29)                            # the same grounds on every build
    cut = lambda im, x, y, w, h: im.crop((x, y, x + w, y + h))
    crop = lambda x, y, w, h: cut(sheet, x, y, w, h)
    stone = lambda x, y, w, h: cut(props, x, y, w, h)
    nat, ext = (lambda *b: cut(more["nature"], *b)), (lambda *b: cut(more["exterior"], *b))

    def block(x0, y0, x1, y1):
        ImageDraw.Draw(busy).rectangle([x0, y0, x1, y1], fill=1)

    def stamp(im, x, y, keep=True):
        g.alpha_composite(im, (x, y))
        if keep:
            block(x - 2, y - 2, x + im.width + 1, y + im.height + 1)

    def free(x, y, w, h):
        return 0 <= x and x + w <= SIZE[0] and 0 <= y and y + h <= SIZE[1] and not busy.crop((x, y, x + w, y + h)).getbbox()

    cx = (FRONT_DOOR[0] + FRONT_DOOR[1]) // 2          # the drive's axis
    hy = ROOMS["hall"][1][3] * T + 5 + FACADE + 10      # the foot of the front steps, below the facade
    ay = SIZE[1] - 64                                   # the arch gate
    # the house, its facade and shadow, the bay, the catio, the drive and the gate stay clear
    for _, box, _, _ in ROOMS.values():
        X0, Y0, X1, Y1 = box_px(box)
        block(X0 - 4, Y0 - 4, X1 + 6, Y1 + FACADE + 8)
    X0, Y0, X1, Y1 = box_px(BAY)
    block(X0 - 4, Y0, X1 + 6, Y1 + FACADE + 8)
    block(CATIO[0] * T - 16, CATIO[1] * T - 20, CATIO[2] * T + 8, CATIO[3] * T + 10)
    block(cx - 24, hy - 14, cx + 24, ay)
    block(cx - 64, ay - 4, cx + 64, SIZE[1])

    # the catio, at the bottom right: decking against the cat lounge and the terrace, fenced where it meets the
    # garden, with a rose-arch gate on its south side and a shade tree over the fence
    X0, Y0, X1, Y1 = CATIO[0] * T + 8, CATIO[1] * T + 16, CATIO[2] * T, CATIO[3] * T
    deck = wood("Floor/Brown-floor-1.png")
    for x in range(X0 - 4, X1, 32):
        for y in range(Y0, Y1, 32):
            stamp(deck.crop((0, 0, min(32, X1 - x), min(32, Y1 - y))), x, y)
    for x in range(X0 - 2, X1 - 28, 32):
        stamp(wood("White fence/White-fence-2.png"), x, Y0 - 14)
    for y in range(Y0 - 8, Y1 - 20, 36):
        stamp(wood("White fence/White-fence-4.png"), X1 - 4, y)
    wall_end = ROOMS["sunroom"][1][3] * T + 5 + FACADE   # below the terrace's facade, the catio's west side is garden
    for y in range(wall_end - 4, Y1 - 20, 36):
        stamp(wood("White fence/White-fence-4.png"), X0 - 12, y)
    gx = X0 + 40
    for x in range(X0 - 12, gx - 4, 28):
        stamp(wood("White fence/White-fence-2.png"), x, Y1 - 8)
    stamp(wood("White gate/White-red-flower-gate-1.png"), gx, Y1 - 29)
    for x in range(gx + 42, X1 - 24, 28):
        stamp(wood("White fence/White-fence-2.png"), x, Y1 - 8)
    stamp(wood("White fence/White-fence-5.png"), X1 - 4, Y1 - 31)
    stamp(stone(99, 160, 27, 32), X0 + 4, Y1 + 10)                        # a signpost to the catio gate

    # the drive: stepping stones straight from the front steps to the arch gate, lamps along it
    for i, y in enumerate(range(hy + 4, ay - 8, 16)):
        for dx in (-17, 2):
            stamp(crop(64 + 16 * ((i + (dx > 0)) % 4), 49, 15, 15), cx + dx, y)
    stamp(stone(29, 166, 9, 53), cx - 16, ay + 8)                        # the gate's wooden doors, swung open
    stamp(stone(57, 166, 9, 53), cx + 10, ay + 8)
    stamp(struct.crop((408, 27, 488, 91)), cx - 40, ay)                  # the stone archway
    stamp(stone(165, 217, 21, 34), cx - 60, ay + 30)                     # vases either side
    stamp(stone(165, 348, 21, 32), cx + 40, ay + 32)
    stamp(stone(453, 118, 22, 37), FRONT_DOOR[0] - 38, hy - 10)          # lanterns by the front steps
    stamp(stone(453, 118, 22, 37), FRONT_DOOR[1] + 16, hy - 10)
    for y in (hy + 34,):                                                 # lamp posts along the stones
        stamp(ext(227, 17, 10, 31), cx - 32, y)
        stamp(ext(227, 17, 10, 31), cx + 22, y)

    # east of the drive: the fountain with its praying statue, and a bench facing it
    fx, fy = cx + 70, hy + 16
    stamp(stone(353, 269, 94, 72), fx, fy)
    stamp(stone(445, 21, 37, 72), fx + 29, fy - 22)
    stamp(stone(292, 19, 56, 41), fx + 110, fy + 44)
    # west of the drive: a parterre before the craft room's bay (its shop window looks onto it), and the well
    bx = box_px(BAY)
    stamp(crop(150, 6, 102, 86), bx[0] - 20, bx[3] + FACADE + 8)
    stamp(ext(166, 17, 21, 29), cx - 110, hy + 60)
    stamp(ext(305, 61, 15, 19), cx - 86, hy + 72)

    # a pond with lily pads, bushes and rocks
    stamp(crop(64, 84, 64, 56), 18, SIZE[1] - 110)
    stamp(nat(224, 112, 16, 15), 32, SIZE[1] - 96, keep=False)
    stamp(nat(241, 114, 14, 13), 52, SIZE[1] - 84, keep=False)
    for x, y, b in [(40, 404, (49, 424, 34, 30)), (300, 520, (16, 427, 26, 23)), (626, 470, (49, 424, 34, 30)),
                    (18, 36, (49, 424, 34, 30)), (900, 40, (16, 427, 26, 23))]:
        stamp(crop(*b), x, y)
    for x, y, b in [(126, 540, (99, 251, 24, 23)), (760, 530, (41, 258, 23, 16)), (60, 20, (71, 252, 22, 22))]:
        stamp(crop(*b), x, y)
    stamp(nat(227, 20, 24, 24), 88, SIZE[1] - 64)                         # mossy rocks by the pond
    stamp(nat(273, 22, 11, 8), 120, SIZE[1] - 40)

    # the trees: a spruce forest round the edges, as behind Peles, with the old round trees among them.
    # Drawn last, back to front, so nearer trunks stand in front of farther ones.
    trees = [(crop(113, 293, 81, 121), X1 - 16, Y0 - 58), (crop(19, 295, 93, 125), -40, 150)]
    kinds = [nat(53, 32, 22, 32)] * 5 + [nat(104, 67, 47, 41)] * 3 + [nat(17, 27, 30, 36)] * 2

    def forest(xs, ys, n):
        for _ in range(n):
            im = rnd.choice(kinds)
            x, y = rnd.randint(*xs) - im.width // 2, rnd.randint(*ys) - im.height
            if not busy.crop((x + im.width // 3, y + im.height - 6, x + im.width * 2 // 3, y + im.height)).getbbox():
                trees.append((im, x, y))
    forest((-10, 970), (18, 50), 70)          # north, behind the house
    forest((-10, 80), (60, 400), 26)          # west
    forest((915, 975), (70, 520), 16)         # east, beyond the catio
    for im, x, y in trees:                    # their trunks keep the scatter off
        block(x + 2, y + im.height // 3, x + im.width - 2, y + im.height)
    for b in ((20, 108, 24, 19), (57, 115, 15, 14), (51, 145, 26, 14), (101, 150, 22, 20)):   # stumps and logs
        for _ in range(12):
            x, y = rnd.choice([(rnd.randint(0, 80), rnd.randint(60, 400)), (rnd.randint(40, 900), rnd.randint(36, 46))])
            if free(x, y, b[2], b[3]):
                stamp(nat(*b), x, y)
                break

    # the lawn: flowers, grass tufts, pebbles, fallen leaves and a few mushrooms, scattered where nothing is
    floor, biome, plant = more["floor"], more["biome"], more["plant"]
    bits = ([cut(floor, x, y, 16, 16) for x, y in ((16, 16), (32, 16), (16, 32), (32, 32), (16, 48), (32, 48))] * 2 +
            [cut(floor, x, y, 16, 16) for x, y in ((96, 16), (112, 16), (128, 16), (96, 32), (128, 32))] +
            [cut(plant, *b) for b in ((8, 394, 17, 9), (41, 394, 16, 10), (73, 394, 15, 10), (102, 394, 15, 11),
                                     (9, 426, 12, 10), (43, 427, 13, 9), (74, 427, 13, 9), (41, 458, 12, 10))] * 2 +
            [cut(biome, *b) for b in ((82, 2, 13, 12), (100, 4, 10, 10), (115, 3, 7, 7), (129, 7, 7, 7), (136, 3, 7, 7),
                                      (52, 36, 8, 10), (67, 36, 10, 10), (83, 50, 11, 11))])
    placed = 0
    for _ in range(4000):
        if placed >= 110:
            break
        im = rnd.choice(bits)
        bb = im.getbbox()
        if not bb:
            continue
        x, y = rnd.randint(0, SIZE[0] - im.width), rnd.randint(40, SIZE[1] - im.height)
        if free(x + bb[0], y + bb[1], bb[2] - bb[0], bb[3] - bb[1]):
            stamp(im, x, y)
            placed += 1

    for im, x, y in sorted(trees, key=lambda t: t[2] + t[0].height):
        dx, dy = max(0, -x), max(0, -y)                              # a tree hanging off the edge is cut there
        g.alpha_composite(im.crop((dx, dy, im.width, im.height)), (x + dx, y + dy))
    return g
