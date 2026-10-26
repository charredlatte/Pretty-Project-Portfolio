#!/usr/bin/env python3
"""The demo page's own pixels.

The café's real art comes from six licensed packs that may not be redistributed, so the public
demo (demo/index.html) cannot ship one pixel of them. These are drawn here from nothing instead,
in the café's own skin palette (catio/art/skin.json), to the slots docs/drawing-plan.md asks for:
cat-work, cat-review, cat-meow, cat-cry, cat-sleep, cat-walk-side, owner and a crown, plus the
furniture a room needs to read as that room.

Nothing here comes from a pack, so demo/art/ is committed, as landing/art/ and catio/art/skin/ are.

    python3 demo/tools/sprites.py [--out demo/art] [--sheet]

--sheet also writes demo/art/.preview.png, every sprite scaled up on one strip, to look at.
Drawn the way landing/tools/scene.py draws: a Layer of pixels, with rects, ellipses and polygons.
"""

import argparse, json, pathlib, sys

try:
    from PIL import Image
except ImportError:
    sys.exit("needs pillow: pip install -r dependencies/requirements.txt")

ROOT = pathlib.Path(__file__).resolve().parents[2]

# ---- the palette ------------------------------------------------------------------------------
# The café's own skin (catio/art/skin.json): lavender and pink, nothing beige.
INK = "#4B1C5E"        # --ink: every outline
ACCENT = "#FF3FA4"     # --accent: the nose, the inner ear
WHITE = "#FFF6FC"      # --outline: the muzzle, the chest, the paws
LAV = "#DCC8FF"        # --tan
LAV_LIT = "#F3E8FF"    # --well
LAV_DIM = "#8A6C94"    # --placeholder
PINK = "#FFB0DB"       # --cream
TEAL = "#5FD6D0"       # --go
GOLD = "#FFDD6E"       # the crown's gilding, a lit window

# One fur ramp, used nowhere else, so the eight coats can one day be palette swaps of it rather
# than the CSS filters the page uses today (docs/drawing-plan.md).
FUR = {"light": "#F7E6CC", "base": "#EBD2AE", "dark": "#C9A87E", "deep": "#9A7B57"}

W, H = 30, 30          # every cat frame; its feet are on row 27

# Where the cat stands in its frame. The proportions are landing/tools/scene.py's cat, which
# already reads as a cat at this size; the palette and the moods are this file's.
FX, FY = 10, 28


def rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


class Layer:
    """A frame of pixels. Every call clips, so a shape may run off the edge."""

    def __init__(self, w=W, h=H):
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.im.load()
        self.w, self.h = w, h

    def put(self, x, y, c):
        if 0 <= int(x) < self.w and 0 <= int(y) < self.h:
            self.px[int(x), int(y)] = rgb(c)

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.put(xx, yy, c)

    def hline(self, x0, x1, y, c):
        for x in range(int(x0), int(x1) + 1):
            self.put(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(int(y0), int(y1) + 1):
            self.put(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.put(x, y, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(round(xs[i]), round(xs[i + 1]), y, c)

    def outline(self, c=INK):
        """One pixel traced round everything drawn so far, as the pack's own sprites have."""
        edge = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[x, y][3]:
                    continue
                if any(0 <= x + dx < self.w and 0 <= y + dy < self.h and self.px[x + dx, y + dy][3]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    edge.append((x, y))
        for x, y in edge:
            self.put(x, y, c)

    def save(self, path):
        self.im.save(path)


# ---- the cat ----------------------------------------------------------------------------------
# Sitting, seen from its left, facing right, so cat-walk-side mirrors cleanly for a cat going left.
# Every sitting mood shares one feet line, so a cat changing mood doesn't jump.


def tail(L, tip=0, x=FX, y=FY):
    """Curled round the near side and lying to the left. Drawn first: the body overlaps it."""
    L.rect(x - 7, y - 4 + tip, 9, 3, FUR["deep"])
    L.rect(x - 9, y - 6 + tip, 4, 3, FUR["deep"])
    L.put(x - 9, y - 7 + tip, FUR["dark"])


def sitting(L, breath=0, drop=0, x=FX, y=FY):
    """The body of a sitting cat: haunch, shaded back, lit chest, two front paws."""
    y += drop
    L.ellipse(x + 7, y - 9 - breath, 8, 9 + breath, FUR["base"])
    L.rect(x + 1, y - 7 - breath, 13, 7 + breath, FUR["base"])
    L.rect(x - 1, y - 11 - breath, 7, 11 + breath, FUR["dark"])        # the back, in shade
    L.ellipse(x + 11, y - 7 - breath, 5, 7 + breath, FUR["light"])     # the chest, lit
    L.rect(x + 9, y - 2, 3, 2, WHITE)                                  # the front paws
    L.rect(x + 13, y - 2, 3, 2, WHITE)
    L.put(x + 15, y - 1, FUR["dark"])


def face(L, hx, hy, ears="up", eye="open", mouth="shut", tear=False):
    """The head, at (hx, hy). Ears up for a cat that is listening, flat for one that is not."""
    if ears == "up":
        L.poly([(hx - 5, hy - 2), (hx - 3, hy - 8), (hx - 0.5, hy - 3)], FUR["dark"])
        L.poly([(hx + 1, hy - 3), (hx + 3, hy - 9), (hx + 6, hy - 3)], FUR["base"])
        L.put(hx + 3, hy - 5, ACCENT); L.put(hx + 4, hy - 4, ACCENT)
        L.put(hx - 3, hy - 4, ACCENT)
    else:
        L.poly([(hx + 1, hy - 4), (hx + 7, hy - 5), (hx + 5, hy - 1)], FUR["base"])
        L.poly([(hx - 6, hy - 5), (hx - 1, hy - 4), (hx - 2, hy - 1)], FUR["dark"])
        L.put(hx + 4, hy - 4, ACCENT)
    L.ellipse(hx, hy, 6, 5, FUR["base"])
    L.rect(hx - 6, hy - 3, 6, 7, FUR["dark"])                          # the back of the head
    L.rect(hx - 2, hy - 4, 8, 8, FUR["base"])
    L.ellipse(hx + 2, hy + 1, 5, 4, FUR["light"])                      # the cheek and muzzle, lit
    if eye == "open":
        L.rect(hx + 2, hy - 2, 2, 2, TEAL)
        L.put(hx + 3, hy - 2, WHITE)
        L.put(hx + 2, hy - 3, INK)
    elif eye == "shut":
        L.hline(hx + 2, hx + 4, hy - 1, INK)
    else:                                                              # squeezed shut: upset
        L.hline(hx + 2, hx + 4, hy - 1, INK)
        L.put(hx + 2, hy - 2, INK); L.put(hx + 4, hy - 2, INK)
    L.put(hx + 6, hy + 1, ACCENT)                                      # the nose
    L.put(hx + 7, hy, WHITE)
    if mouth == "open":
        L.rect(hx + 5, hy + 2, 2, 2, ACCENT)
        L.put(hx + 6, hy + 3, INK)
    else:
        L.put(hx + 5, hy + 2, FUR["dark"])
    if tear:
        L.put(hx + 4, hy + 1, TEAL); L.put(hx + 4, hy + 2, TEAL)


def frame_work(i):
    """Busy: sitting at a ball of yarn, one paw on it. The tail flicks, an ear blinks."""
    L = Layer()
    tail(L, tip=-1 if i in (1, 2) else 0)
    sitting(L, breath=1 if i == 1 else 0)
    face(L, FX + 12, FY - 19 - (1 if i == 1 else 0), eye="shut" if i == 3 else "open")
    L.ellipse(5, FY - 4, 4, 4, PINK)                                   # the ball of yarn
    L.put(3, FY - 6, LAV_LIT); L.put(6, FY - 2, LAV_LIT); L.put(7, FY - 5, LAV_LIT)
    L.put(4, FY - 7, LAV_LIT)
    paw = FY - 8 - (1 if i in (1, 2) else 0)                           # a paw resting on it
    L.rect(4, paw, 4, 3, WHITE); L.put(7, paw + 3, WHITE)
    L.put(4, paw + 1, FUR["dark"]); L.put(6, paw + 1, FUR["dark"])     # two toes
    L.outline()
    return L


def frame_review(i):
    """Brought something to review: sitting beside a parcel, tied with a bow."""
    L = Layer()
    tail(L)
    sitting(L, breath=1 if i == 1 else 0)
    face(L, FX + 12, FY - 19 - (1 if i == 1 else 0))
    L.rect(1, FY - 10, 10, 10, LAV)                                    # the parcel
    L.rect(1, FY - 10, 10, 3, LAV_LIT)
    L.vline(5, FY - 10, FY - 1, ACCENT)
    L.hline(1, 10, FY - 6, ACCENT)
    L.rect(2, FY - 13, 3, 3, PINK)                                     # the bow: two loops
    L.rect(6, FY - 13, 3, 3, PINK)
    L.put(3, FY - 12, LAV_LIT); L.put(7, FY - 12, LAV_LIT)
    L.rect(5, FY - 12, 1, 2, ACCENT)                                   # and its knot
    L.outline()
    return L


def frame_meow(i):
    """Needs you: sitting up tall, head back, mouth open."""
    L = Layer()
    tail(L, tip=-1 if i else 0)
    sitting(L, breath=1 if i else 0)
    face(L, FX + 12, FY - 20 - (1 if i else 0), mouth="open" if i else "shut")
    if i:                                                              # the breath of a meow
        L.put(FX + 21, FY - 23, PINK); L.put(FX + 22, FY - 25, PINK)
    L.outline()
    return L


def frame_cry(i):
    """Upset: hunched down, ears flat, eyes squeezed shut, a tear."""
    L = Layer()
    tail(L, tip=3)
    sitting(L, drop=3)
    L.rect(FX + 1, FY - 13, 10, 4, FUR["dark"])                        # the shoulders come up
    face(L, FX + 12, FY - 13, ears="flat", eye="squeezed", tear=i in (1, 2))
    L.outline()
    return L


def frame_sleep(i):
    """Asleep: curled up, the tail round the nose, breathing."""
    L = Layer()
    b = 1 if i in (1, 2) else 0
    L.ellipse(15, FY - 6 - b, 11, 6 + b, FUR["base"])                  # the curl
    L.ellipse(11, FY - 7 - b, 8, 5 + b, FUR["dark"])                   # the back, in shade
    L.ellipse(20, FY - 5, 6, 4, FUR["light"])                          # the flank, lit
    L.poly([(16, FY - 10 - b), (17, FY - 16 - b), (21, FY - 11 - b)], FUR["base"])
    L.poly([(12, FY - 10 - b), (12, FY - 15 - b), (16, FY - 11 - b)], FUR["dark"])
    L.put(18, FY - 13 - b, ACCENT)
    L.ellipse(19, FY - 8 - b, 5, 4, FUR["light"])                      # the face, tucked down
    L.hline(19, 21, FY - 9 - b, INK)                                   # the eye, shut
    L.put(23, FY - 7 - b, ACCENT)                                      # the nose
    L.rect(2, FY - 7 - b, 11, 3, FUR["deep"])                          # the tail, round to the nose
    L.put(2, FY - 8 - b, FUR["dark"])
    L.outline()
    return L


def frame_walk(i):
    """Walking, facing right. Four frames; the page mirrors them for a cat going left."""
    L = Layer()
    bob = (0, 1, 0, 1)[i]
    y = FY - 2 + bob
    L.rect(3, y - 13, 4, 4, FUR["deep"])                               # the tail, up behind
    L.rect(2, y - 16, 3, 4, FUR["deep"])
    L.put(2, y - 17, FUR["dark"])
    L.ellipse(12, y - 7, 8, 5, FUR["base"])                            # the body, level
    L.rect(8, y - 9, 11, 7, FUR["base"])
    L.ellipse(9, y - 8, 5, 4, FUR["dark"])
    L.ellipse(17, y - 6, 5, 4, FUR["light"])
    face(L, 20, y - 14, eye="open")
    # a front and a back leg each side, out of step: the far pair in shade, the near pair lit
    far_f, near_f, far_b, near_b = ((17, 14, 7, 10), (14, 17, 10, 7),
                                    (16, 15, 8, 9), (15, 16, 9, 8))[i]
    for x, c in ((far_f, FUR["dark"]), (far_b, FUR["dark"])):
        L.rect(x, y - 2, 2, 4, c)
    for x, c in ((near_f, FUR["light"]), (near_b, FUR["base"])):
        L.rect(x, y - 2, 3, 4, c); L.put(x + 1, y + 1, WHITE)
    L.outline()
    return L


MOODS = {
    "cat-work": (frame_work, 4),
    "cat-review": (frame_review, 2),
    "cat-meow": (frame_meow, 2),
    "cat-cry": (frame_cry, 3),
    "cat-sleep": (frame_sleep, 3),
    "cat-walk-side": (frame_walk, 4),
}


def sheet(fn, n):
    """A sheet of n frames in a row, as every cat slot in docs/drawing-plan.md is."""
    out = Image.new("RGBA", (W * n, H), (0, 0, 0, 0))
    for i in range(n):
        out.paste(fn(i).im, (W * i, 0))
    return out


# ---- the rest ----------------------------------------------------------------------------------


def crown():
    """The queen's, shown in her menu and her card. Never on the map (CLAUDE.md, "No signs")."""
    L = Layer(16, 9)
    L.poly([(1, 8), (1, 3), (4, 6), (8, 1), (12, 6), (14, 3), (14, 8)], GOLD)
    L.rect(1, 7, 14, 2, "#E8B93C")
    for x in (4, 8, 11):
        L.put(x, 7, ACCENT)
    L.put(8, 0, PINK)
    L.outline()
    return L


def owner():
    """You, from behind: the left of the queen's scene. The page draws its own in code."""
    L = Layer(20, 30)
    L.ellipse(10, 8, 6, 7, "#6B4A86")                             # the hair, from behind
    L.rect(4, 8, 13, 7, "#6B4A86")
    L.ellipse(10, 14, 5, 3, "#5A3C73")                            # where it falls past the collar
    L.poly([(5, 17), (15, 17), (17, 24), (3, 24)], PINK)          # the shoulders and back
    L.rect(2, 18, 3, 6, PINK); L.rect(15, 18, 3, 6, PINK)         # the arms
    L.put(2, 24, "#E8A0B8"); L.put(17, 24, "#E8A0B8")             # the hands
    L.rect(4, 24, 12, 5, LAV)                                     # and below the shirt
    L.hline(6, 13, 17, LAV_LIT)                                   # the collar
    L.outline()
    return L


def furniture():
    """One piece a room: enough for a room on the demo's plan to read as itself, no more."""
    out = {}

    def L(w=18, h=12):
        return Layer(w, h)

    # the café: a counter, two cups
    f = L()
    f.rect(0, 4, 18, 7, LAV); f.rect(0, 4, 18, 2, LAV_LIT)
    f.hline(0, 17, 8, LAV_DIM)
    for x in (3, 9):
        f.rect(x, 1, 3, 3, WHITE); f.put(x + 3, 2, WHITE); f.put(x + 1, 0, LAV_LIT)
    f.outline(); out["counter"] = f

    # the kitchen: a stove, a pot on it
    f = L()
    f.rect(0, 4, 18, 7, LAV)
    f.rect(2, 6, 6, 4, LAV_DIM); f.rect(10, 6, 6, 4, LAV_DIM)
    f.rect(3, 7, 4, 2, GOLD)
    f.rect(5, 1, 7, 3, WHITE); f.hline(4, 12, 1, LAV_LIT)
    f.outline(); out["stove"] = f

    # the cat lounge: a cushioned bench
    f = L()
    f.rect(1, 3, 16, 5, PINK); f.rect(2, 4, 14, 2, LAV_LIT)
    f.rect(0, 8, 18, 2, LAV)
    f.rect(2, 10, 2, 2, LAV_DIM); f.rect(14, 10, 2, 2, LAV_DIM)
    f.outline(); out["bench"] = f

    # the craft room: a workbench, a lamp over it
    f = L()
    f.rect(0, 6, 18, 3, LAV)
    f.rect(2, 9, 2, 3, LAV_DIM); f.rect(14, 9, 2, 3, LAV_DIM)
    f.rect(4, 4, 3, 2, ACCENT); f.rect(8, 4, 4, 2, PINK)          # the work on it
    f.poly([(12, 3), (17, 3), (15, 0), (14, 0)], GOLD)            # the lamp
    f.outline(); out["workbench"] = f

    # the entrance hall: the front door, under its pediment
    f = L()
    f.poly([(1, 4), (9, 0), (17, 4)], GOLD)
    f.rect(3, 4, 12, 8, LAV)
    f.rect(5, 6, 8, 6, LAV_LIT)
    f.hline(5, 12, 8, LAV_DIM); f.vline(9, 6, 11, LAV_DIM)
    f.put(12, 9, ACCENT)                                          # the handle
    f.outline(); out["door"] = f

    # the terrace: glass, and the cat flap in it
    f = L()
    f.rect(0, 0, 18, 9, LAV_LIT)
    for x in (6, 12):
        f.vline(x, 0, 8, LAV)
    f.hline(0, 17, 4, LAV)
    f.rect(7, 9, 5, 3, PINK)                                      # the flap
    f.outline(); out["glass"] = f

    # the catio: the fence, a tuft of grass
    f = L()
    for x in (1, 6, 11, 16):
        f.vline(x, 2, 11, LAV)
    f.hline(0, 17, 4, LAV); f.hline(0, 17, 9, LAV)
    f.poly([(8, 11), (9, 6), (10, 11)], TEAL)
    f.poly([(12, 11), (14, 7), (15, 11)], TEAL)
    f.outline(); out["fence"] = f

    # the library: shelves of books, and the chest that is the litter box
    f = L()
    f.rect(0, 0, 18, 12, LAV)
    for row in (1, 5, 9):
        f.hline(0, 17, row + 3, LAV_DIM)
        for i, c in enumerate((ACCENT, PINK, TEAL, LAV_LIT, ACCENT, PINK)):
            f.rect(1 + i * 3, row, 2, 3, c)
    f.outline(); out["shelf"] = f

    # the bedroom: a bed, a quilt on it
    f = L()
    f.rect(0, 3, 18, 7, LAV)
    f.rect(0, 2, 5, 4, WHITE)                                     # the pillow
    f.rect(5, 4, 13, 5, PINK)
    for i in range(3):
        f.vline(8 + i * 4, 4, 8, LAV_LIT)
    f.rect(1, 10, 2, 2, LAV_DIM); f.rect(15, 10, 2, 2, LAV_DIM)
    f.outline(); out["bed"] = f

    # the ensuite: the tub
    f = L()
    f.ellipse(9, 8, 8, 4, LAV_LIT)
    f.rect(1, 4, 16, 4, LAV_LIT)
    f.ellipse(9, 6, 7, 2.5, TEAL)
    f.vline(16, 0, 4, LAV); f.hline(13, 16, 0, LAV)
    f.rect(2, 11, 2, 1, LAV_DIM); f.rect(14, 11, 2, 1, LAV_DIM)
    f.outline(); out["tub"] = f

    # a filing cabinet: one a room, where the project lives
    f = Layer(14, 16)
    f.rect(0, 0, 14, 16, LAV)
    for y in (1, 6, 11):
        f.rect(1, y, 12, 4, LAV_LIT)
        f.rect(5, y + 1, 4, 1, LAV_DIM)
    f.outline(); out["cabinet"] = f

    # the litter box: the library's chest, where her quest log's notes wait
    f = Layer(16, 13)
    f.rect(0, 4, 16, 9, LAV)
    f.poly([(0, 4), (8, 0), (15, 4)], PINK)
    f.hline(0, 15, 7, LAV_DIM)
    f.rect(6, 6, 4, 4, GOLD); f.put(8, 8, INK)                    # the lock
    f.outline(); out["chest"] = f
    return out


def chrome():
    """The one interface piece the page can't draw in CSS: the triangle beside a menu item.

    The real café's interface pieces are catio/art/skin/, its owner's own drawings, and they stay
    there; the demo draws what it needs so demo/ carries no copy of another folder's binaries.
    """
    out = {}

    # the triangle beside the item under the pointer, as the pack's own menus have
    f = Layer(7, 10)
    f.poly([(1, 0), (6, 5), (1, 9)], PINK)
    f.poly([(2, 2), (5, 5), (2, 7)], LAV_LIT)
    f.outline()
    out["pointer"] = f
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "demo" / "art"))
    ap.add_argument("--sheet", action="store_true", help="also write .preview.png, to look at")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    made, meta = {}, {}
    for name, (fn, n) in MOODS.items():
        made[name] = sheet(fn, n)
        meta[name] = {"w": W, "h": H, "frames": n}
    extra = dict(furniture(), **chrome())
    for name, layer in [("crown", crown()), ("owner", owner())] + sorted(extra.items()):
        made[name] = layer.im
        meta[name] = {"w": layer.w, "h": layer.h, "frames": 1}

    for name, im in sorted(made.items()):
        im.save(out / (name + ".png"))
    (out / "sprites.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    print("%d sprites -> %s" % (len(made), out))

    if a.sheet:
        scale, pad = 4, 12
        w = sum(im.width * scale + pad for im in made.values()) + pad
        h = max(im.height for im in made.values()) * scale + 2 * pad
        strip = Image.new("RGBA", (w, h), rgb(LAV_LIT))
        x = pad
        for name, im in sorted(made.items()):
            big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
            strip.paste(big, (x, pad), big)
            x += big.width + pad
        strip.save(out / ".preview.png")
        print("look at %s" % (out / ".preview.png"))
        print("  " + "  ".join(sorted(made)))


if __name__ == "__main__":
    main()
