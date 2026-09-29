"""The manor's floor plan: a refurbished stone manor, drawn from Cosy Cabin alone (committable).

Layout, in 16 px tiles (the page's GEOM mirrors these numbers, doubled):

    north   kitchen | dining room | library (the brain) | drawing room | conservatory (glass, off the drawing room)
    south   bath | bedroom |        great hall        | studio            walled catio east of the conservatory
                             front door, drive, parterre

Public rooms face north onto the garden; the great hall runs from the front door to the library behind it;
the family rooms and the studio sit either side of the hall. Old stone outside (grey), warm stone inside,
the rooms themselves refurbished: pale boards, tiles and wallpaper.

This module is the shell only: floors, back walls, walls, doorways and glass. Furniture is not drawn here:
it is placed as pieces by the page (see furniture.py and docs/renovation-mode.md).
"""
from PIL import Image

import cabin

T = 16
FACE = 32                       # a back wall, ceiling to floor
SIZE = (60 * T, 34 * T)         # the whole grounds, native pixels

# walls: 5 px bands, outer to inner. Outside walls are the pack's grey stone, inside ones its warm stone.
STONE_OUT = [(65, 9, 9), (121, 101, 98), (152, 134, 129), (165, 149, 143), (121, 101, 98)]
STONE_IN = [(65, 9, 9), (102, 63, 57), (134, 98, 86), (151, 115, 100), (102, 63, 57)]
MORTAR_OUT, MORTAR_IN = (105, 86, 83), (88, 52, 46)
GLASS = cabin.GLASS

# key: tile box (x0, y0, x1, y1), floor, back wall
ROOMS = {
    "kitchen": ((5, 4, 14, 13), "pink", "paper16"),          # terracotta-pink tiles, poppy paper
    "dining":  ((14, 4, 22, 13), "wood", "paper32"),         # pale boards, blue stripes
    "brain":   ((22, 4, 31, 13), "dark", "panel_dark"),      # the library: dark boards, panelled
    "living":  ((31, 4, 41, 13), "wood", "paper64"),         # the drawing room: pale boards, damask
    "sunroom": ((41, 6, 47, 13), "sand", None),              # the conservatory: glass all round, sandstone
    "bath":    ((5, 13, 10, 20), "blue", "paper0"),
    "bedroom": ((10, 13, 19, 21), "wood", "paper48"),        # vines
    "hall":    ((19, 13, 34, 24), "stone", "stone_white"),   # stone flags, the old white stone left bare
    "study":   ((34, 13, 43, 22), "wood", "stone_brown"),    # the studio: exposed brick, refurbished
}
# the catio is outdoors: decking fenced against the conservatory's east wall
CATIO = (47, 4, 56, 20)

# doorways: ("v", wall tile x, y from, y to) through a side wall; ("h", wall tile y, x from, x to) through a back wall
DOORS = [
    ("v", 14, 144, 198),            # kitchen <-> dining (the servery)
    ("v", 22, 150, 198),            # dining <-> library
    ("v", 31, 150, 198),            # library <-> drawing room
    ("v", 41, 150, 198),            # drawing room <-> conservatory
    ("h", 13, 392, 440),            # hall -> library (the hall's back wall, under the stairs' landing)
    ("v", 19, 280, 330),            # bedroom <-> hall
    ("v", 10, 280, 316),            # bath <-> bedroom (the ensuite)
    ("v", 34, 280, 330),            # hall <-> studio
]
FRONT_DOOR = (400, 432)             # x span in the hall's south wall

# glass: ("tall", x, y, w) floor-to-ceiling on a back wall; ("v", wall x, y0, y1) and ("h", wall y, x0, x1) strips
WINDOWS = [
    ("tall", 100, 85, 40),                                  # kitchen, over the sink run
    ("tall", 250, 85, 60),                                  # dining room
    ("tall", 530, 85, 40), ("tall", 600, 85, 40),           # drawing room, either side of the fireplace
    ("tall", 668, 101, 76),                                 # conservatory
    ("v", 5, 112, 176),                                     # kitchen west
    ("v", 47, 104, 172), ("v", 47, 196, 206),               # conservatory east, broken by the cat flap
    ("h", 13, 690, 750),                                    # conservatory south, past the studio
    ("v", 5, 240, 304),                                     # bath west
    ("h", 21, 180, 290),                                    # bedroom south
    ("h", 24, 330, 390), ("h", 24, 442, 510),               # hall south, either side of the front door
    ("h", 22, 580, 680),                                    # studio south
    ("v", 43, 240, 330),                                    # studio east
]
CAT_FLAP = (752, 176, 192)          # x of the conservatory's east wall, y span


def box_px(box):
    x0, y0, x1, y1 = box
    return x0 * T, y0 * T, x1 * T + 5, y1 * T + 5


def textures(tm, ex):
    """Floors and back walls, all from the Cosy Cabin sheets."""
    t = cabin.floors(tm, ex)
    t.update({
        "stone": tm.crop((336, 112, 352, 128)), "brownstone": tm.crop((400, 112, 416, 128)), "cobble": tm.crop((464, 112, 480, 128)),
    })
    walls = {f"paper{c}": tm.crop((c, 32, c + 16, 52)) for c in (0, 16, 32, 48, 64)}
    walls.update({
        "panel_light": tm.crop((0, 112, 32, 132)), "panel_dark": tm.crop((32, 112, 64, 132)),
        "stone_brown": tm.crop((0, 176, 16, 196)), "stone_white": tm.crop((16, 176, 32, 196)),
    })
    return t, walls, tm.crop((0, 68, 16, 80))


def inside(x, y):
    """Is this native pixel inside some room's box (walls included)?"""
    for box, _, _ in ROOMS.values():
        X0, Y0, X1, Y1 = box_px(box)
        if X0 <= x < X1 and Y0 <= y < Y1:
            return True
    return False


def shell(tm, objects, ex):
    img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    px = img.load()
    tex, walls, rail = textures(tm, ex)
    floor_at = {}

    def fill(x, y, name):
        t = tex[name]
        px[x, y] = t.getpixel((x % t.width, y % t.height))

    # floors, and each room's back wall: paper (20 px) over a rail (12 px), or panelling/stone the full height
    for name, (box, fl, wall) in ROOMS.items():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0 + 5, X1 - 5):
            for y in range(Y0 + 5, Y1 - 5):
                fy = y - (Y0 + 5)
                if wall and fy < FACE:
                    w = walls[wall]
                    if not wall.startswith("stone"):   # paper or panelling above the rail
                        px[x, y] = w.getpixel((x % 16, fy)) if fy < 20 else rail.getpixel((x % 16, fy - 20))
                    else:
                        px[x, y] = w.getpixel((x % w.width, fy % w.height))
                else:
                    fill(x, y, fl)
                    floor_at[(x // T, y // T)] = fl
    # walls: a mitred 5 px band round each room, grey stone where the other side is outdoors
    for box, _, _ in ROOMS.values():
        X0, Y0, X1, Y1 = box_px(box)
        for x in range(X0, X1):
            for y in range(Y0, Y1):
                d = min(x - X0, X1 - 1 - x, y - Y0, Y1 - 1 - y)
                if d >= 5:
                    continue
                # which side is this pixel on, and what's beyond it?
                side = [(x - X0, (-6, 0)), (X1 - 1 - x, (6, 0)), (y - Y0, (0, -6)), (Y1 - 1 - y, (0, 6))]
                _, (dx, dy) = min(side, key=lambda s: s[0])
                out = not inside(x + dx, y + dy)
                band, mortar = (STONE_OUT, MORTAR_OUT) if out else (STONE_IN, MORTAR_IN)
                along = y if dx else x
                px[x, y] = mortar if 1 <= d <= 3 and along % 9 == 0 else band[d]

    def floor_near(x, y):
        for dx in (8, -8, 0):
            for dy in (0, 8, 40):
                f = floor_at.get(((x + dx) // T, (y + dy) // T))
                if f:
                    return f
        return "wood"

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
                    px[a - 5 + i, y] = STONE_IN[4 - i]
                    px[b + i, y] = STONE_IN[i]
    hy = ROOMS["hall"][0][3] * T
    for x in range(*FRONT_DOOR):
        for y in range(hy, hy + 5):
            fill(x, y, "stone")
    for kind, *a in WINDOWS:
        if kind == "tall":
            x, y, w = a
            img.alpha_composite(cabin.tall_glass(objects, w), (x, y))
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
    fx, fy0, fy1 = CAT_FLAP
    for y in range(fy0, fy1):
        for i in range(5):
            px[fx + i, y] = (65, 9, 9) if y in (fy0, fy1 - 1) else (88, 26, 17)
    # front steps: two stone treads down from the front door
    for i, (inset, dark) in enumerate(((0, (121, 101, 98)), (4, (102, 84, 80)))):
        for x in range(FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 6 + inset):
            for y in range(hy + 5 + i * 5, hy + 10 + i * 5):
                fill(x, y, "stone")
                if y == hy + 9 + i * 5 or x in (FRONT_DOOR[0] - 6 - inset, FRONT_DOOR[1] + 5 + inset):
                    px[x, y] = dark
    # the house casts a soft shadow to the south-east, so it sits on the ground
    alpha = img.getchannel("A").point(lambda a: 255 if a else 0)
    shade = Image.new("RGBA", SIZE, (28, 44, 20, 110))
    under = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    under.paste(shade, (4, 4), alpha)
    under.alpha_composite(img)
    return under
