#!/usr/bin/env python3
"""The fireside scene for the KittyChat Café landing page, drawn in code.

Our own pixels, no pack: every colour and shape is here, so the page may be sold. It writes the layers the
page composites (480 × 270 native; the page scales them by whole numbers) and `scene.json`, which says
where the animated pieces go.

    python3 landing/tools/scene.py            # writes landing/art/
    python3 landing/tools/scene.py --preview  # also landing/art/preview.png, the whole scene at 2×, to look at

Layers, back to front:
    sky.png          the night, the milky way and the still stars (the twinkling ones are in scene.json)
    far.png          two mountain ranges and the far pines
    mid-0/1/2.png    the campsite in firelight at three flicker levels: ground, logs, bench, tent, near pines
    cats-0/1/2.png   the two cats on the bench, five frames each, at the same three levels
    tent-glow.png    the tent's inside light, drawn over the midground at a pulsing opacity
    fire.png         eight flame frames
And the page's own pieces: panel-tan.png and panel-night.png (9-slice boxes, 8-pixel corners), paw.png (the
pointer), portrait-0/1.png (the cats' faces for the dialogue box), scene.js (scene.json as a script).
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 480, 270
HORIZON = 160                       # where the ground meets the forest
FIRE = (268, 205)                   # the centre of the fire pit, on the ground
SEED = 20261004

# ---- the palette: one ramp per thing -------------------------------------------------------------------------
SKY = ["#070A1E", "#0B1030", "#111A44", "#182552", "#223160", "#2C3D6C"]      # zenith to horizon
MW_HAZE, MW_DUST, MW_LANE = "#34437A", "#4E5E99", "#0E1538"                 # the milky way's band, its dust, its dark lanes
STAR_DIM, STAR_MID, STAR_BRIGHT, STAR_WARM = "#6F7BB8", "#B4BDEA", "#FFFFFF", "#FFE9B3"
MTN_FAR, MTN_SNOW, MTN_NEAR = "#1E2A58", "#4A5A8E", "#141C40"
PINE_FAR, PINE_MID, PINE_NEAR, TRUNK = "#0E1A30", "#0A1324", "#070D1A", "#050910"
GROUND, GRASS_L, GRASS_D, EARTH = "#1A2420", "#24342A", "#121A17", "#2A2420"
STONE, STONE_D, ASH = "#4A4A52", "#2E2E36", "#15120F"
LOG, LOG_L, LOG_D, LOG_END, LOG_RING = "#3A2A1E", "#55412F", "#241910", "#6B5338", "#4A3826"
F_WHITE, F_YELLOW, F_ORANGE, F_RED, F_DEEP, EMBER = "#FFF8D6", "#FFD35A", "#FF8E2B", "#E0441E", "#8A2415", "#FF6A1C"
TENT, TENT_D, TENT_RIDGE, TENT_IN = "#5A4A3E", "#3E322A", "#7A6756", "#1A120E"
TENT_LIT, TENT_LIT2, TENT_SPILL = "#E8A24A", "#FFD27A", "#FFE9B3"
POLE, ROPE, PEG = "#2A1E16", "#8A7A66", "#5A4A3E"
CAT_A = dict(base="#B86A32", light="#E09A58", dark="#7A4320", stripe="#8E4E24", ear="#D98A7C", eye="#E6F27A", nose="#5A2A1A")
CAT_B = dict(base="#6E6E80", light="#A8A8BA", dark="#45455A", stripe="#5C5C70", ear="#C9A3A3", eye="#9CE8A0", nose="#3A3A4A", chest="#D8D2C8")


def rgb(h: str) -> tuple[int, int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255


class Layer:
    """A transparent 480 × 270 picture with pixel-exact drawing (PIL draws with no anti-aliasing)."""

    def __init__(self, w: int = W, h: int = H):
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.px = self.im.load()

    def put(self, x: int, y: int, c: str) -> None:
        if 0 <= x < self.im.width and 0 <= y < self.im.height:
            self.px[x, y] = rgb(c)

    def rect(self, x: int, y: int, w: int, h: int, c: str) -> None:
        if w > 0 and h > 0:
            self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgb(c))

    def hline(self, x0: int, x1: int, y: int, c: str) -> None:
        self.d.line([x0, y, x1, y], fill=rgb(c))

    def vline(self, x: int, y0: int, y1: int, c: str) -> None:
        self.d.line([x, y0, x, y1], fill=rgb(c))

    def line(self, x0: int, y0: int, x1: int, y1: int, c: str) -> None:
        self.d.line([x0, y0, x1, y1], fill=rgb(c))

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c: str) -> None:
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=rgb(c))

    def poly(self, pts, c: str) -> None:
        self.d.polygon(pts, fill=rgb(c))

    def dither(self, x: int, y: int, w: int, h: int, c: str, parity: int = 0) -> None:
        """Every other pixel, checkerboard: the pixel-art way to blend two colours."""
        col = rgb(c)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx + yy + parity) % 2 == 0 and 0 <= xx < W and 0 <= yy < H:
                    self.px[xx, yy] = col

    def over(self, other: "Layer") -> None:
        self.im.alpha_composite(other.im)

    def save(self, path: Path) -> None:
        self.im.save(path, optimize=True)


# ---- the sky ---------------------------------------------------------------------------------------------------
def sky(rnd: random.Random) -> tuple[Layer, list]:
    L = Layer()
    bands = len(SKY)
    span = HORIZON + 30                               # the sky runs a little under the horizon, behind the pines
    for y in range(span):
        t = y / span * (bands - 1)
        i = int(t)
        L.hline(0, W - 1, y, SKY[min(i, bands - 1)])
        frac = t - i
        if i + 1 < bands and 0.55 < frac:            # dither the lower part of each band into the next
            parity = y % 2
            for x in range(parity, W, 2):
                L.put(x, y, SKY[i + 1])
    # The milky way: a faint band from the top left down to the right. Never a solid stripe: a haze of
    # scattered pixels, densest along its middle, with brighter dust and a crowd of tiny stars in it.
    def band_centre(x: float) -> float:
        return 14 + x * 0.22 + 7 * math.sin(x / 70)
    for x in range(W):
        c = band_centre(x)
        half = 24 + 7 * math.sin(x / 45 + 1.3)
        for y in range(int(c - half), int(c + half) + 1):
            if not (0 <= y < HORIZON):
                continue
            d = abs(y - c) / half
            wobble = math.sin(x / 9 + y / 5) * 0.12         # so the edge isn't a straight rule
            if d + wobble < 0.35 and (x + y) % 2 == 0:
                L.put(x, y, MW_HAZE)
            elif d + wobble < 0.65 and (x * 3 + y) % 4 == 0:
                L.put(x, y, MW_HAZE)
            elif d + wobble < 1.0 and (x + y * 5) % 8 == 0:
                L.put(x, y, MW_HAZE)
    for _ in range(320):                               # the band's dust: a brighter speckle along its middle
        x = rnd.randrange(W)
        y = int(rnd.gauss(band_centre(x), 7))
        if 0 <= y < HORIZON and rnd.random() < 0.8:
            L.put(x, y, MW_DUST)
    for _ in range(240):                               # and the crowd of faint stars that is the milky way
        x = rnd.randrange(W)
        y = int(rnd.gauss(band_centre(x), 11))
        if 0 <= y < HORIZON:
            L.put(x, y, STAR_DIM if rnd.random() < 0.75 else STAR_MID)
    # Stars: many dim ones, fewer middling, a few bright crosses; the brightest twinkle on the page.
    stars = []
    for _ in range(170):
        x, y = rnd.randrange(W), rnd.randrange(0, HORIZON - 10)
        r = rnd.random()
        if r < 0.62:
            L.put(x, y, STAR_DIM)
        elif r < 0.9:
            L.put(x, y, STAR_MID)
            if rnd.random() < 0.5:
                stars.append([x, y, 1])
        else:
            c = STAR_WARM if rnd.random() < 0.3 else STAR_BRIGHT
            L.put(x, y, c)
            if rnd.random() < 0.6:                     # a cross
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    L.put(x + dx, y + dy, STAR_DIM)
            stars.append([x, y, 2])
    return L, stars


# ---- the mountains and the far forest ------------------------------------------------------------------------
def ridge(rnd: random.Random, base: int, lo: int, hi: int, step: int) -> list:
    """A jagged ridgeline across the picture, as a polygon down to the base."""
    pts, x, y = [], -10, rnd.randrange(lo, hi)
    while x < W + 10:
        pts.append((x, y))
        x += step + rnd.randrange(-3, 4)
        y = max(lo, min(hi, y + rnd.choice([-9, -6, -4, -2, 2, 4, 6, 9])))
    pts.append((W + 10, base))
    pts.append((-10, base))
    return pts


def pine(L: Layer, x: int, base: int, h: int, c: str, trunk: str = TRUNK) -> None:
    """A spruce: three tiers of triangle, each wider, and a stub of trunk."""
    w = max(6, h // 2)
    tiers = 3
    for i in range(tiers):
        top = base - h + i * (h // tiers) * 0.72
        bottom = base - h + (i + 1) * (h // tiers) + 2
        half = int(w * (0.35 + 0.33 * i))
        L.poly([(x, top), (x - half, bottom), (x + half, bottom)], c)
    L.rect(x - 1, base - 3, 2 if h < 30 else 3, 4, trunk)


def far(rnd: random.Random) -> Layer:
    L = Layer()
    L.poly(ridge(rnd, HORIZON, 78, 108, 14), MTN_FAR)
    for _ in range(18):                                 # snow on the far peaks: a pixel or two at the top
        x = rnd.randrange(W)
        for y in range(70, 120):
            if L.px[x, y][3]:
                L.put(x, y, MTN_SNOW); L.put(x, y + 1, MTN_SNOW)
                if rnd.random() < 0.5:
                    L.put(x + 1, y + 1, MTN_SNOW)
                break
    L.poly(ridge(rnd, HORIZON, 104, 128, 11), MTN_NEAR)
    # Two rows of far pines on the horizon; the campsite's clearing stays open in the middle of the nearer row.
    x = -4
    while x < W + 6:
        pine(L, x, HORIZON - 14, rnd.randrange(16, 28), PINE_FAR)
        x += rnd.randrange(6, 10)
    x = -4
    while x < W + 6:
        if not 150 < x < 390 or rnd.random() < 0.25:
            pine(L, x, HORIZON - 5, rnd.randrange(22, 40), PINE_MID)
        x += rnd.randrange(7, 12)
    return L


# ---- the campsite ----------------------------------------------------------------------------------------------
def ground(L: Layer, rnd: random.Random) -> None:
    L.rect(0, HORIZON - 6, W, H - HORIZON + 6, GROUND)
    for x in range(W):                                  # the edge of the clearing, dithered into the pines
        if (x + HORIZON) % 2:
            L.put(x, HORIZON - 7, GROUND)
        if x % 3 == 0:
            L.put(x, HORIZON - 8, GROUND)
    for _ in range(210):                                # grass tufts: little v's, light and dark
        x, y = rnd.randrange(W), rnd.randrange(HORIZON - 2, H)
        c = GRASS_L if rnd.random() < 0.55 else GRASS_D
        L.put(x, y, c); L.put(x - 1, y - 1, c); L.put(x + 1, y - 1, c)
        if rnd.random() < 0.3:
            L.put(x, y - 1, c)
    for _ in range(14):                                 # a few stones in the grass
        x, y = rnd.randrange(W), rnd.randrange(HORIZON + 4, H)
        L.rect(x, y, rnd.randrange(2, 4), 2, STONE_D)
    # Trodden earth round the fire, in an ellipse, its edge dithered.
    fx, fy = FIRE
    L.ellipse(fx, fy + 2, 44, 17, EARTH)
    for yy in range(fy - 20, fy + 24):
        for xx in range(fx - 50, fx + 51):
            dx, dy = (xx - fx) / 50, (yy - fy - 2) / 20
            if 0.78 < dx * dx + dy * dy < 1.0 and (xx + yy) % 2 == 0:
                L.put(xx, yy, EARTH)


def log(L: Layer, x: int, y: int, w: int, h: int, end: str = "right") -> None:
    """A log lying across: the bark, a highlight along the top, and the grain at one end."""
    L.rect(x, y, w, h, LOG)
    L.hline(x + 1, x + w - 2, y, LOG_L)
    L.hline(x + 2, x + w - 3, y + 1, LOG_L)
    L.hline(x, x + w - 1, y + h - 1, LOG_D)
    for k in range(x + 5, x + w - 4, 9):                # bark cracks
        L.vline(k, y + 2, y + h - 3, LOG_D)
    ex = x + w - h // 2 - 1 if end == "right" else x
    L.ellipse(ex + h // 4, y + h // 2 - 0.5, h // 2, h // 2 - 0.5, LOG_END)
    L.ellipse(ex + h // 4, y + h // 2 - 0.5, h // 4, max(1, h // 4 - 1), LOG_RING)


def firepit(L: Layer) -> None:
    fx, fy = FIRE
    L.ellipse(fx, fy, 22, 8, ASH)
    for i in range(14):                                 # a ring of stones
        a = i / 14 * math.tau
        x, y = fx + 23 * math.cos(a), fy + 9 * math.sin(a)
        c = STONE if math.sin(a) > -0.3 else STONE_D
        L.rect(int(x) - 2, int(y) - 1, 5, 3, c)
        L.hline(int(x) - 1, int(x) + 1, int(y) - 1, STONE if c == STONE_D else "#5C5C66")
    # the logs in the pit, crossed, their ends glowing
    L.poly([(fx - 14, fy + 3), (fx + 12, fy - 5), (fx + 13, fy - 2), (fx - 13, fy + 6)], LOG_D)
    L.poly([(fx - 12, fy - 5), (fx + 14, fy + 3), (fx + 13, fy + 6), (fx - 13, fy - 2)], LOG)
    for x, y in ((fx - 13, fy + 4), (fx + 12, fy - 3), (fx - 11, fy - 3), (fx + 13, fy + 4)):
        L.rect(x, y, 2, 2, EMBER)
    L.rect(fx - 4, fy - 1, 8, 2, F_DEEP)


def bench(L: Layer) -> None:
    """The log bench to the left of the fire: a long log on two stumps."""
    L.rect(158, 198, 8, 12, LOG_D); L.rect(210, 198, 8, 12, LOG_D)   # stumps
    L.rect(159, 198, 2, 11, LOG); L.rect(211, 198, 2, 11, LOG)
    log(L, 150, 190, 78, 10, "right")


def tent(L: Layer, lit: bool) -> None:
    """An A-frame tent at the back right, its door toward the fire. `lit` draws the glow layer only."""
    x0, base, h = 364, 191, 44                          # the front pole's foot, the ground line, the height
    apex = (x0 + 16, base - h)
    front = [(x0 - 6, base), apex, (x0 + 38, base)]     # the front face, a triangle, its door toward the fire
    side = [apex, (x0 + 38, base), (x0 + 66, base - 5), (x0 + 42, base - h + 2)]   # the side, receding right
    door = [(x0 + 16, base - 1), (x0 + 10, base - 22), (x0 + 22, base - 22), (x0 + 23, base - 1)]
    flap = [(x0 + 9, base - 20), (x0 + 16, base - 1), (x0 + 5, base + 1), (x0 - 2, base - 1)]
    if lit:
        # Only the fabric glows: the two faces, brighter low down where the lantern stands, the door a
        # bright gap, the flap lit through, and a pool of light on the grass in front.
        L.poly(front, TENT_LIT)
        L.poly(side, TENT_LIT)
        for y in range(base - h, base + 1):
            for x in range(x0 - 6, x0 + 67):
                if L.px[x, y][3] and y > base - h * 0.55 and (x + y) % 2 == 0:
                    L.put(x, y, TENT_LIT2)
        L.poly(door, TENT_LIT2)
        L.poly(flap, TENT_LIT)
        L.ellipse(x0 + 17, base + 3, 14, 3, TENT_SPILL)
        L.dither(x0 + 2, base - 1, 30, 8, TENT_SPILL, 1)
        return
    L.poly(front, TENT)
    L.poly(side, TENT_D)
    L.line(apex[0], apex[1], x0 + 42, base - h + 2, TENT_RIDGE)
    L.line(x0 - 6, base, apex[0], apex[1], TENT_RIDGE)
    L.poly(door, TENT_IN)                                # the open door
    L.poly(flap, TENT_D)                                 # the flap, pulled aside
    L.vline(apex[0], apex[1] - 3, base, POLE)
    L.line(x0 - 6, base, x0 - 15, base + 4, ROPE); L.rect(x0 - 16, base + 3, 2, 3, PEG)                        # guy ropes
    L.line(x0 + 38, base, x0 + 47, base + 4, ROPE); L.rect(x0 + 47, base + 3, 2, 3, PEG)
    L.line(x0 + 66, base - 5, x0 + 74, base - 2, ROPE); L.rect(x0 + 74, base - 3, 2, 3, PEG)
    L.rect(x0 - 9, base - 5, 3, 5, STONE_D); L.rect(x0 + 46, base - 4, 4, 4, STONE_D)                           # a pack by the door, a stone


def cat(L: Layer, x: int, y: int, k: dict, frame: int, mirror_tail: bool = False) -> None:
    """A cat sitting, seen from its left, facing right toward the fire. (x, y) is where its feet meet the bench.

    Frames: 0 idle, 1 breathing (a pixel taller), 2 blink, 3 an ear flicks, 4 the tail's tip lifts.
    The face side is lit (its light colour), the back is in shade (dark): the fire is to the right.
    """
    breath = 1 if frame == 1 else 0
    # tail: curled round the near side, lying on the bench to the left
    tip = -1 if frame == 4 else 0
    L.rect(x - 7, y - 3 + tip, 9, 3, k["dark"]); L.rect(x - 9, y - 5 + tip, 4, 3, k["dark"]); L.put(x - 9, y - 6 + tip, k["base"])
    # body: a rounded mass, taller at the back, chest toward the fire
    L.ellipse(x + 7, y - 9 - breath, 8, 9 + breath, k["base"])
    L.rect(x + 1, y - 7 - breath, 13, 7 + breath, k["base"])
    L.rect(x - 1, y - 11 - breath, 7, 11 + breath, k["dark"])              # the back, in shade
    L.ellipse(x + 11, y - 7 - breath, 5, 7 + breath, k["light"])            # the chest, lit
    if "chest" in k:
        L.ellipse(x + 11, y - 5, 3, 4, k["chest"])
    for i in range(3):                                                      # stripes down the back
        L.hline(x + 1 + i * 2, x + 2 + i * 2, y - 12 - breath + i * 3, k["stripe"])
    # legs: two front paws together, pointing right
    L.rect(x + 9, y - 2, 3, 2, k["light"]); L.rect(x + 13, y - 2, 3, 2, k["light"]); L.put(x + 15, y - 1, k["dark"])
    # head: slightly forward, lit on the fire side
    hx, hy = x + 12, y - 19 - breath
    L.ellipse(hx, hy, 6, 5, k["base"])
    L.rect(hx - 6, hy - 3, 6, 7, k["dark"])                                 # back of the head
    L.rect(hx - 2, hy - 4, 8, 8, k["base"])
    L.ellipse(hx + 2, hy + 1, 5, 4, k["light"])                            # the muzzle and cheek, lit
    # ears
    ear_l = (hx - 4, hy - 5)
    L.poly([(ear_l[0] - 1, ear_l[1] + 2), (ear_l[0] + 1, ear_l[1] - 4), (ear_l[0] + 4, ear_l[1] + 1)], k["dark"])
    if frame == 3:                                                          # the near ear flicks flat
        L.poly([(hx + 1, hy - 4), (hx + 6, hy - 5), (hx + 5, hy - 2)], k["base"])
        L.put(hx + 4, hy - 4, k["ear"])
    else:
        L.poly([(hx + 1, hy - 3), (hx + 3, hy - 9), (hx + 6, hy - 3)], k["base"])
        L.put(hx + 3, hy - 6, k["ear"]); L.put(hx + 3, hy - 5, k["ear"]); L.put(hx + 4, hy - 4, k["ear"])
    # face: the eye, a glint of firelight, closed when blinking; the nose; whiskers as a lit pixel
    if frame == 2:
        L.hline(hx + 2, hx + 4, hy - 1, k["dark"])
    else:
        L.rect(hx + 2, hy - 2, 2, 2, k["eye"]); L.put(hx + 3, hy - 2, F_WHITE)
    L.put(hx + 6, hy + 1, k["nose"])
    L.put(hx + 7, hy, F_WHITE)                                              # the rim of light on the nose


def cats(frame: int) -> Layer:
    """Both cats at the same frame: the page draws each cat from its own frame of the sheet (split at x 36 of the
    cell), on its own clocks, so they never blink together."""
    L = Layer()
    cat(L, 166, 190, CAT_A, frame)
    cat(L, 194, 190, CAT_B, frame)
    return L


def near_pines(L: Layer, rnd: random.Random) -> None:
    """The front row: tall spruces at the edges of the clearing, catching the firelight."""
    for x in (-2, 14, 30, 48, 66):
        pine(L, x, HORIZON + 14 + (x % 7), rnd.randrange(44, 66), PINE_NEAR)
    for x in (438, 454, 470, 486):
        pine(L, x, HORIZON + 12 + (x % 5), rnd.randrange(42, 62), PINE_NEAR)
    for x in (92, 112):
        pine(L, x, HORIZON + 2, rnd.randrange(30, 40), PINE_MID)


def midground(rnd: random.Random) -> Layer:
    L = Layer()
    ground(L, rnd)
    near_pines(L, rnd)
    tent(L, lit=False)
    firepit(L)
    bench(L)
    log(L, 300, 206, 54, 10, "left")                   # the log to the right of the fire
    log(L, 236, 226, 64, 9, "right")                   # the log in front
    return L


# ---- the firelight: warm bands by distance, dithered at their edges, at three flicker levels ---------------
WARMTH = [0.0, 0.22, 0.42, 0.62, 0.82]                  # how far each band moves toward the fire's colour
RADII = [30, 58, 92, 136]                               # the bands' outer edges, before flicker


def warm(c, k: float):
    r, g, b, a = c
    tr, tg, tb = min(255, r * 1.18 + 44), min(255, g * 0.98 + 20), b * 0.68
    return (int(r + (tr - r) * k), int(g + (tg - g) * k), int(b + (tb - b) * k), a)


def light(L: Layer, flicker: float) -> Layer:
    out = Layer(L.im.width, L.im.height)
    src, dst = L.px, out.px
    fx, fy = FIRE
    radii = [r * flicker for r in RADII]
    for y in range(L.im.height):
        for x in range(L.im.width):
            c = src[x, y]
            if not c[3]:
                continue
            dx, dy = x - fx, (y - fy) * 1.45                           # the pool of light is an ellipse on the ground
            if y < fy:
                dy *= 0.85                                               # light reaches a little further up than down
            d = math.hypot(dx, dy)
            level = 4
            for i, r in enumerate(radii):
                if d > r:
                    level = 3 - i
                else:
                    edge = r - d
                    if edge < 5 and (x + y) % 2 == 0:                    # dither the band's edge
                        level = max(0, level - 1)
                    break
            dst[x, y] = warm(c, WARMTH[max(0, level)]) if level > 0 else c
    return out


# ---- the fire --------------------------------------------------------------------------------------------------
FIRE_W, FIRE_H, FIRE_FRAMES = 40, 56, 8


def flames(rnd: random.Random) -> Layer:
    """Eight frames side by side. Each is a tongue of fire from a wide base, in four colours, with sparks."""
    sheet = Layer(FIRE_W * FIRE_FRAMES, FIRE_H)
    for f in range(FIRE_FRAMES):
        ox = f * FIRE_W
        cx, base = ox + FIRE_W // 2, FIRE_H - 4
        ph = f / FIRE_FRAMES * math.tau
        lean = int(3 * math.sin(ph)) + rnd.randrange(-1, 2)
        h = 34 + int(5 * math.sin(ph * 2 + 1)) + rnd.randrange(-2, 3)
        for colour, shrink, lift in ((F_RED, 0, 0), (F_ORANGE, 3, 3), (F_YELLOW, 7, 6), (F_WHITE, 11, 8)):
            hw = 13 - shrink
            hh = h - lift - shrink
            if hw <= 1 or hh <= 2:
                continue
            tip = (cx + lean * (1 + shrink / 8), base - hh)
            pts = [(cx - hw, base), (cx - hw + 2, base - hh * 0.45 + rnd.randrange(-2, 3)),
                   (tip[0] - 2 + rnd.randrange(-1, 2), tip[1] + 4), tip,
                   (tip[0] + 3, tip[1] + 6 + rnd.randrange(0, 3)), (cx + hw - 1, base - hh * 0.4 + rnd.randrange(-2, 3)), (cx + hw, base)]
            sheet.poly(pts, colour)
        for _ in range(rnd.randrange(2, 4)):                               # tongues that have let go
            tx, ty = cx + rnd.randrange(-9, 10), base - h - rnd.randrange(2, 9)
            sheet.ellipse(tx, ty, rnd.randrange(1, 3), rnd.randrange(2, 4), F_ORANGE if rnd.random() < 0.6 else F_RED)
        for _ in range(rnd.randrange(3, 6)):                               # sparks
            sx, sy = cx + rnd.randrange(-14, 15), base - rnd.randrange(h - 6, FIRE_H - 2)
            sheet.put(sx, sy, F_YELLOW if rnd.random() < 0.6 else EMBER)
        sheet.ellipse(cx, base, 13, 2, F_DEEP)                             # the glow at the roots
        sheet.ellipse(cx, base, 9, 1, F_ORANGE)
    return sheet


# ---- the page's own pieces: two panels, a button, a paw, a portrait -------------------------------------------
TAN, TAN_D, TAN_L, INK = "#DCB98A", "#B8905E", "#F3E5C2", "#3F2A20"          # the café's own panel colours
NIGHT, NIGHT_L, CREAM = "#121A34", "#2A3A66", "#F3E5C2"


def panel(face: str, edge: str, inner: str, size: int = 24) -> Layer:
    """A 9-slice box, 24 × 24 with 8-pixel corners: a two-pixel outline, one pixel of inner line, the face.
    The corner pixel is cut, the way the games' boxes are."""
    L = Layer(size, size)
    L.rect(0, 0, size, size, edge)
    L.rect(2, 2, size - 4, size - 4, inner)
    L.rect(3, 3, size - 6, size - 6, face)
    for x, y in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
        L.px[x, y] = (0, 0, 0, 0)
    for x, y in ((1, 0), (0, 1), (size - 2, 0), (size - 1, 1), (1, size - 1), (0, size - 2), (size - 2, size - 1), (size - 1, size - 2)):
        L.put(x, y, edge)
    return L


def paw(c: str = INK, pad: str = CREAM) -> Layer:
    """A 16 × 16 cat paw for the pointer, its tip at the top left, outlined so it reads on anything."""
    L = Layer(16, 16)
    for cx, cy in ((4, 3), (8, 2), (12, 4)):
        L.ellipse(cx, cy, 2, 2, c)
    L.ellipse(8, 9, 5, 4, c)
    for cx, cy in ((4, 3), (8, 2), (12, 4)):
        L.put(cx, cy, pad)
    L.ellipse(8, 9, 3, 2, pad)
    return L


def portrait(cats_sheet: Image.Image, which: int) -> Image.Image:
    """A cat's head and shoulders for the dialogue box, cut from the lit sheet's idle frame."""
    x = 6 if which == 0 else 34
    return cats_sheet.crop((x, 0, x + 34, 34))


# ---- putting it together ---------------------------------------------------------------------------------------
def main(argv: list[str]) -> None:
    here = Path(__file__).resolve().parent
    out = (here.parent / "art") if here.name == "tools" else here / "art"
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(SEED)
    sky_layer, stars = sky(rnd)
    sky_layer.save(out / "sky.png")
    far(random.Random(SEED + 1)).save(out / "far.png")
    mid = midground(random.Random(SEED + 2))
    levels = [0.9, 1.0, 1.1]
    for i, fl in enumerate(levels):
        light(mid, fl).save(out / f"mid-{i}.png")
    cat_frames = [cats(f) for f in range(5)]
    CX, CY, CW, CH = 150, 160, 80, 34                                       # the cats' box in the world
    for i, fl in enumerate(levels):
        sheet = Layer(CW * 5, CH)
        for f, frame in enumerate(cat_frames):
            lit = light(frame, fl)
            sheet.im.alpha_composite(lit.im.crop((CX, CY, CX + CW, CY + CH)), (f * CW, 0))
        sheet.save(out / f"cats-{i}.png")
    glow = Layer(); tent(glow, lit=True)
    glow.im = glow.im.crop((350, 140, 450, 200)); glow.save(out / "tent-glow.png")
    fire = flames(random.Random(SEED + 3)); fire.save(out / "fire.png")
    panel(TAN, INK, TAN_D).save(out / "panel-tan.png")
    panel(NIGHT, CREAM, NIGHT_L).save(out / "panel-night.png")
    paw().save(out / "paw.png")
    lit_cats = Image.open(out / "cats-1.png")
    portrait(lit_cats, 0).save(out / "portrait-0.png")
    portrait(lit_cats, 1).save(out / "portrait-1.png")
    scene = {
        "w": W, "h": H, "horizon": HORIZON,
        "fire": {"x": FIRE[0] - FIRE_W // 2, "y": FIRE[1] + 4 - FIRE_H, "fw": FIRE_W, "fh": FIRE_H, "frames": FIRE_FRAMES, "fps": 10},
        "smoke": {"x": FIRE[0], "y": FIRE[1] - 36},
        "cats": {"x": CX, "y": CY, "fw": CW, "fh": CH, "frames": 5},
        "tentGlow": {"x": 350, "y": 140},
        "light": {"levels": len(levels)},
        "stars": stars,
        "safe": [48, 432],
    }
    (out / "scene.json").write_text(json.dumps(scene, separators=(",", ":")) + "\n")
    # The page reads it as a script, so it runs from a double-clicked file too (fetch() can't, from file://).
    (out / "scene.js").write_text("window.SCENE = " + json.dumps(scene, separators=(",", ":")) + ";\n")
    if "--preview" in argv:
        comp = Layer()
        comp.over(sky_layer); comp.over(far(random.Random(SEED + 1)))
        comp.over(light(mid, 1.0))
        comp.im.alpha_composite(Image.open(out / "cats-1.png").crop((0, 0, CW, CH)), (CX, CY))
        comp.over(glow_full(glow))
        comp.im.alpha_composite(fire.im.crop((0, 0, FIRE_W, FIRE_H)), (scene["fire"]["x"], scene["fire"]["y"]))
        comp.im.resize((W * 2, H * 2), Image.NEAREST).save(out / "preview.png")
    print(f"wrote {out}: sky, far, mid-0..2, cats-0..2, tent-glow, fire, the panels, the paw, two portraits, "
          f"scene.json and scene.js ({len(stars)} twinkling stars)")


def glow_full(glow: Layer) -> Layer:
    L = Layer()
    faint = glow.im.copy()
    faint.putalpha(faint.getchannel("A").point(lambda a: a * 7 // 10))   # the page shows it at about this opacity
    L.im.alpha_composite(faint, (350, 140))
    return L


if __name__ == "__main__":
    main(sys.argv[1:])
