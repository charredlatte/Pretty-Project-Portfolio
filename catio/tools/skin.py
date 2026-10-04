#!/usr/bin/env python3
"""List her own art for the page: art/skin/ in, art/skin.json out.

    python3 catio/tools/skin.py           ->  catio/art/skin.json, and what each file fills or why it can't

Every piece of the café is a slot (ART in catio/index.html, named as docs/drawing-plan.md names her files).
Drop a drawing in catio/art/skin/ under its slot's name (panel.png, cat-meow.png, font.ttf...), run this, and
the page draws with it: no code changes. It reads each PNG's size and checks it as the page does: the house,
the grounds, the furniture and the cursors must be their exact size, a sheet the same shape, and a cat's
frames must split its width. A 9-slice drawn at another size than the pack's needs its border, and a cat
its frames when they aren't square: say so in art/skin.json ("slice": [top, right, bottom, left],
"frames": 6, "secs": 0.6; a paw its tip, "hot": [x, y]), which this keeps on every run. Entries for files that have
gone are dropped; one pointed by hand at art elsewhere under art/ (another pack's) is kept while its file is there.

The rest of the design system is tokens, kept here in two modes, as Figma keeps a variable per mode:
"tokens": {"--ink": "#3F2A20", "--px-size": "16px"} for light and "dark": {...} for what differs at night (TOKENS in
the page lists them: colours as six hex digits, sizes in px or rem). Drop a design tokens file in art/skin/ too (the
W3C format Figma's variables export, or The look's own export: *.tokens.json, "dark" in its name for the dark mode)
and its tokens are read into that mode; a token is matched by its own name (ink, go, px-size...) wherever it sits,
and one the same as it would be anyway (the cafe's own in light, light's in dark) is left out, as The look does.
A mode with a tokens file in art/skin/ is rebuilt from its files alone on every run, so a token taken out of the file
goes; a mode with no file keeps the tokens written in skin.json by hand. A drawing's settings (its border, frames...)
are kept while it stays the size they were given for ("w" and "h" in its entry); redrawn at another size, they go,
and this says so.

The page also takes art from The look in its House menu; that wins over this file. Needs nothing but Python.
"""
import functools
import json
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
SKIN = ROOT / "art" / "skin"
OUT = ROOT / "art" / "skin.json"
FONTS = {".ttf", ".otf", ".woff", ".woff2"}


@functools.cache
def page():
    """The page's text, read once."""
    return PAGE.read_text(encoding="utf-8")


@functools.cache
def defaults():
    """Each token's own value in the page's :root, as the page's TOKENS0 reads it."""
    text = page()
    root = text[text.index(":root {"):text.index("color-scheme: light;")]
    return {n: v.strip() for n, v in re.findall(r"(--[\w-]+):\s*([^;]+);", root)}


def file_of(entry):
    """An entry's file, as the page reads it: "file" or "src", or the entry itself when it is a path."""
    return (entry.get("src") or entry.get("file")) if isinstance(entry, dict) else entry if isinstance(entry, str) else None   # src first, as skinEntry()


def slots():
    """The slot table, read from the page itself so the two can't disagree."""
    text = page()
    block = text[text.index("const ART = {"):text.index("const SPR0")]
    atlases = json.loads(re.search(r'"atlases":(\{[^}]*\})', text).group(1))   # MANOR's, which furniture.py writes
    out = {}
    for line in block.splitlines():
        m = re.match(r'\s+"([\w-]+)":\s*\{.*kind: "(\w+)"', line)
        if not m:
            continue
        a = {"kind": m.group(2)}
        for key in ("size", "slice"):
            v = re.search(key + r": \[([\d, ]+)\]", line)
            if v:
                a[key] = [int(n) for n in v.group(1).split(",")]
        v = re.search(r'atlas: "(\w+)"', line)
        if v:
            a["size"] = atlases[v.group(1)]
        if re.search(r"smooth: true", line):
            a["smooth"] = True
        v = re.search(r'fam: "(\w+)"', line)
        if v:
            a["fam"] = v.group(1)
        v = re.search(r"frames: (\d+)", line)
        if v:
            a["frames"] = int(v.group(1))
        v = re.search(r"scale: ([\d.]+)(?: / ([\d.]+))?", line)
        if v:
            a["scale"] = float(v.group(1)) / (float(v.group(2)) if v.group(2) else 1)
        out[m.group(1)] = a
    # every slot is one line of ART; a line this can't read is a change of shape to bring here, never a slot to drop
    keys = re.findall(r'^\s+"([\w-]+)":\s*\{', block, re.M)
    if sorted(keys) != sorted(out):
        sys.exit(f"skin.py can't read these slots in catio/index.html's ART: {', '.join(sorted(set(keys) - set(out)))}. "
                 "Keep each on one line with its kind, or teach slots() the new shape.")
    return out


def token_names():
    text = page()
    block = text[text.index("const TOKENS = {"):text.index("const tokenOk")]
    return dict(re.findall(r'"(--[\w-]+)": \["([^"]+)"', block))


@functools.cache
def sizes():
    """The page's SIZES, each size token's range in px, read from the page so the two can't disagree."""
    text = page()
    block = text[text.index("const SIZES = {"):text.index("function sizeOk")]
    return {n: (float(lo), float(hi)) for n, lo, hi in re.findall(r'"(--[\w-]+)": \[([\d.]+), ([\d.]+)\]', block)}


@functools.cache
def whole():
    """The page's WHOLE_PX: the sizes kept to whole screen pixels."""
    return set(re.findall(r'"(--[\w-]+)"', re.search(r"const WHOLE_PX = \[([^\]]*)\]", page()).group(1)))


@functools.cache
def pixelish():
    """The page's PIXELISH: drawn at most this much of the width a map piece is shown, or of a sheet's pack width, a smooth
    slot's piece starts as pixel art."""
    return tuple(float(n) for n in re.search(r"const PIXELISH = \[([\d.]+), ([\d.]+)\]", page()).groups())


def token_ok(groups, name, v):
    if name not in groups or not isinstance(v, str):
        return False
    if groups[name] != "Type":
        return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", v))
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3})?)(px|rem)", v)
    if m and name in whole() and (m.group(2) != "px" or not float(m.group(1)).is_integer()):
        return False   # the page's WHOLE_PX: whole screen pixels, or the pixel art blurs
    lo, hi = sizes().get(name, (0, 0))
    return bool(m) and lo <= float(m.group(1)) * (16 if m.group(2) == "rem" else 1) <= hi


def from_dtcg(doc, groups):
    """The page's fromDTCG(): the café's tokens in a design tokens file, how many weren't the café's, and how many were
    but with a value it can't take."""
    flat, found, foreign = {}, {}, 0

    def walk(node, path):   # as the page's walk: objects and lists alike
        if isinstance(node, list):
            node = {str(i): v for i, v in enumerate(node)}
        if not isinstance(node, dict):
            return
        if "$value" in node:
            flat[".".join(path)] = node["$value"]
            return
        for k, v in node.items():
            if not k.startswith("$"):
                walk(v, path + [k])
    walk(doc, [])

    def resolve(v, depth=0):
        if isinstance(v, str) and re.fullmatch(r"\{[^}]+\}", v) and depth < 10:
            return resolve(flat.get(v[1:-1]), depth + 1)
        return v
    own, refused = {}, 0   # as the page: the café's own group wins a name; a value it can't take is refused, not foreign
    for path, raw in flat.items():
        name, v, css = "--" + re.sub(r"[\s_]+", "-", path.split(".")[-1].strip().lower()), resolve(raw), None   # Figma's "Px size" is px-size
        if name not in groups:
            foreign += 1
            continue
        hexa = v if isinstance(v, str) else v.get("hex") if isinstance(v, dict) and isinstance(v.get("hex"), str) else ""
        clear = bool(re.fullmatch(r"#[0-9a-fA-F]{6}(?![fF]{2})[0-9a-fA-F]{2}", hexa)) or (isinstance(v, dict) and number(v.get("alpha"), float("-inf"), float("inf")) and v["alpha"] < 1)
        try:
            css = to_css(v) if not (number(v, 0, 999) and groups.get(name) == "Type") else f"{round(v, 3):g}px"   # Figma's number variable
        except (TypeError, ValueError):   # numbers that aren't: refused, as the page does
            css = None
        if clear or not token_ok(groups, name, css):
            refused += 1
            continue
        mine = path.split(".")[0] == re.sub(r"[^a-z0-9]+", "-", groups[name].lower())   # the page's groupKey()
        if name in found and (own[name] or not mine):
            continue
        found[name], own[name] = css, mine
    return found, foreign, refused


def to_css(v):
    css = None
    if isinstance(v, str):
        css = v[:7] if re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", v) else v
    elif isinstance(v, dict) and isinstance(v.get("hex"), str):
        css = v["hex"][:7]
    elif isinstance(v, dict) and isinstance(v.get("components"), list) and (v.get("colorSpace") or "srgb") == "srgb":
        css = "#" + "".join(f"{math.floor(min(1, max(0, c)) * 255 + 0.5):02x}" for c in v["components"][:3])   # halves up, as Math.round
    elif isinstance(v, dict) and number(v.get("value"), 0, float("inf")) and v.get("unit") in ("px", "rem"):
        css = f"{round(v['value'], 3):g}{v['unit']}"
    return css


def ints(v, n, lo, hi):
    return isinstance(v, list) and len(v) == n and all(isinstance(x, int) and not isinstance(x, bool) and lo <= x <= hi for x in v)


def number(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


# the page's skinEntry(), for what a slot's entry may carry
SETTINGS = {
    "slice": lambda v: ints(v, 4, 0, 256),   # the page takes 64, or 256 for a smooth map piece (checked in check())
    "frames": lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 64,
    "secs": lambda v: number(v, 0.1, 20), "anchor": lambda v: isinstance(v, list) and len(v) == 2 and all(number(x, 0, 1024) for x in v),
    "scale": lambda v: number(v, 0.001, 64), "pixel": lambda v: isinstance(v, bool), "hot": lambda v: ints(v, 2, 0, 127),
    "w": lambda v: isinstance(v, int), "h": lambda v: isinstance(v, int),
}


def png_size(path):
    """A PNG's width and height from its header, or None when it isn't one (or is cut short, or has no size)."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            return None
        w, h = struct.unpack(">II", head[16:24])
    except (OSError, struct.error):
        return None
    return (w, h) if w and h else None


def check(art, key, rel, was, said, where="", filled=None):
    """One drawing for one slot, checked as the page checks it: its entry for skin.json, or None and why, said. What it
    fills is told through `filled` when given (a family member's, once its head is known), else said at once."""
    a, path, name = art[key], ROOT / rel, Path(rel).name
    # what this worked out itself last time, with the values it gave: worked out again, never "dropped" - unless she has
    # changed one since, which makes it hers
    auto = was.get("auto") if isinstance(was.get("auto"), dict) else {}
    entry = {k: v for k, v in was.items() if k in ("slice", "frames", "secs", "anchor", "scale", "pixel", "hot", "w", "h") and not (k in auto and auto[k] == v)}
    for k, ok in SETTINGS.items():   # what the page would drop, dropped here, and said
        if k in entry and not ok(entry[k]):
            said.append(f"  {name}: its \"{k}\" ({entry[k]!r}) isn't one the page can use, so it was dropped")
            del entry[k]
    entry["file"] = rel
    worked = []
    if a["kind"] == "font":
        if path.suffix.lower() not in FONTS:
            said.append(f"  {name}: a font slot takes .ttf, .otf, .woff or .woff2")
            return None
        said.append(f"  {name}: {key} (" + {"font": "the pixel font", "font-body": "the text", "font-display": "the round font"}.get(key, "a font") + f"){where}")
        return entry
    size = png_size(path)
    if not size:
        said.append(f"  {name}: not a PNG (pixel art is kept as PNG, here and in The look)")
        return None
    w, h = size
    entry.pop("w", None), entry.pop("h", None)
    sized = entry.keys() & {"slice", "frames", "anchor", "hot", "scale"}   # what depends on the drawing's size (not secs, not pixel)
    if sized and was.get("w") is not None and [was.get("w"), was.get("h")] != [w, h]:
        said.append(f"  {name}: redrawn at {w} x {h}, so its " + ", ".join(sorted(sized)) + " were dropped: give them again if it needs them")
        for k in sized:
            del entry[k]
    entry["w"], entry["h"] = w, h
    want = a.get("size")
    if a["kind"] == "exact" and want and [w, h] != want:
        said.append(f"  {name}: {w} x {h}, but it must be {want[0]} x {want[1]}: left out")
        return None
    if a["kind"] == "sheet" and want and abs(w / h - want[0] / want[1]) > 0.02:
        said.append(f"  {name}: {w} x {h}, but it must be the shape of {want[0]} x {want[1]}: left out")
        return None
    note = ""
    if a["kind"] == "slice" and "slice" in a and want and [w, h] != want and "slice" not in entry:
        if "scale" in a:   # as The look does: the pack's border, scaled to her drawing, pixel art or smooth
            entry["slice"] = [min(256, max(1, round(n * w / want[0]))) for n in a["slice"]]   # a smooth map piece: up to 256
            worked.append("slice")
            note = f" (border {' '.join(map(str, entry['slice']))}, scaled from the pack's; set \"slice\" if it isn't)"
        else:
            note = f" (another size than the pack's {want[0]} x {want[1]}: give its border, \"slice\": [t, r, b, l], or it keeps {a['slice']})"
    smooth = "scale" in a or a.get("smooth")
    # as The look starts it: drawn nearer the art pixel than the screen (a map piece), or at half the pack's width or
    # less (a sheet), it is pixel art
    if smooth and want and "pixel" not in entry and "scale" not in entry and w <= (want[0] * a["scale"] * pixelish()[0] if "scale" in a else want[0] * pixelish()[1]):
        entry["pixel"] = True
        worked.append("pixel")
        note += " (pixel art; \"pixel\": false if it is smooth)"
    if entry.get("pixel"):
        entry.pop("scale", None)   # pixel art is drawn at the art pixel: a scale has nothing to say
    if a["kind"] == "slice" and "scale" in a and want and w != want[0] and "scale" not in entry and not entry.get("pixel"):
        entry["scale"] = round(a["scale"] * want[0] / w, 4)   # drawn smooth, shown the pack's size
        worked.append("scale")
        note += f" (scale {entry['scale']}, smooth; \"pixel\": true instead if it is pixel art)"
    if entry.get("slice") and max(entry["slice"]) > (256 if "scale" in a else 64):
        said.append(f"  {name}: its border {entry['slice']} is over {256 if 'scale' in a else 64}, more than the page takes: left out")
        return None
    if entry.get("hot") and (entry["hot"][0] >= w or entry["hot"][1] >= h):
        said.append(f"  {name}: its tip {entry['hot']} is outside {w} x {h}, so it was dropped")
        del entry["hot"]
    sl = entry.get("slice") or a.get("slice")   # hers, or the pack's it would be cut with, in its own pixels
    if a["kind"] == "slice" and sl and (sl[1] + sl[3] > w or sl[0] + sl[2] > h or not any(sl)):
        said.append(f"  {name}: the border {' '.join(map(str, sl))} doesn't fit inside {w} x {h}: left out" + ("" if entry.get("slice") else " (give it its own, \"slice\")"))
        return None
    if a["kind"] == "cat":
        n = entry.get("frames") or (w // h if w % h == 0 and w // h <= 64 else a.get("frames", 1))
        if w % n:
            said.append(f"  {name}: {w} px wide doesn't split into {n} frames: set \"frames\" in skin.json")
            return None
        if "frames" not in entry:
            worked.append("frames")
        entry["frames"] = n
        note = f" ({n} frames of {w // n} x {h})"
    if worked:
        entry["auto"] = {k: entry[k] for k in worked}
    line = f"  {name}: {key}{note}{where}"
    if filled is not None:
        filled[key] = line
    else:
        said.append(line)
    return entry


def family(art, skin, said):
    """A family member is cut with its head's border, so it is the head's size: the head as it ended up (hers, wherever its
    file is, or the pack's when hers was left out). Those that aren't are left out, and said."""
    for key in [k for k in skin if k in art and art[k]["kind"] == "slice" and "slice" not in art[k] and art[k].get("fam")]:
        head = next(k for k, h in art.items() if h.get("fam") == art[key]["fam"] and "slice" in h)
        hf, mf = file_of(skin.get(head)), file_of(skin[key])
        if not (isinstance(mf, str) and mf.startswith("art/")) or (hf and not hf.startswith("art/")):
            continue   # not a file here: the page weighs it
        hw, hh = (png_size(ROOT / hf) if hf and (ROOT / hf).is_file() else None) or art[head]["size"]
        mw, mh = (png_size(ROOT / mf) if mf and (ROOT / mf).is_file() else None) or (0, 0)
        if [mw, mh] != [hw, hh]:
            said.append(f"  {key}: {mw} x {mh}, but it shares {head}'s border, so it must be {hw} x {hh}: left out")
            del skin[key]


def main():
    art = slots()
    try:
        old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    except ValueError as e:
        sys.exit(f"{OUT.relative_to(ROOT.parent)} isn't JSON any more ({e}): put it right, or delete it to start again.")
    if not isinstance(old, dict):
        sys.exit(f"{OUT.relative_to(ROOT.parent)} should be an object of slots and tokens: put it right, or delete it.")
    # hidden and system files (.DS_Store, desktop.ini, Thumbs.db) are nobody's drawing
    files = sorted(p for p in SKIN.iterdir() if p.is_file() and not p.name.startswith(".") and p.name.lower() not in ("desktop.ini", "thumbs.db")) if SKIN.is_dir() else []
    skin, said = {}, []
    groups = token_names()
    modes = {m: {k: v for k, v in (old.get(key) or {}).items() if token_ok(groups, k, v)} if isinstance(old.get(key), dict) else {}
             for m, key in (("light", "tokens"), ("dark", "dark"))}
    for key in ("tokens", "dark"):
        for k, v in (old.get(key) or {}).items() if isinstance(old.get(key), dict) else []:
            if not token_ok(groups, k, v):
                said.append(f"  {key}: {k} = {v!r} left out (a colour is #rrggbb; a size stays in its range, SIZES in the page)")
    # a mode that has its files is what the files say (so a token taken out of one goes), but only once a file of it
    # could be read: a half-saved one leaves the mode as it was
    from_files, broken = {}, set()
    for p in files:
        if p.name.endswith(".tokens.json"):
            mode = "dark" if "dark" in p.name.lower() else "light"
            try:
                found, foreign, refused = from_dtcg(json.loads(p.read_text(encoding="utf-8")), groups)
            except (ValueError, UnicodeDecodeError):
                said.append(f"  {p.name}: not a tokens file (it isn't JSON): {mode} kept as it was")
                broken.add(mode)
                continue
            from_files.setdefault(mode, {}).update(found)
            said.append(f"  {p.name}: {len(found)} tokens into {mode}" + (f", {foreign} not the cafe's" if foreign else "") + (f", {refused} with a value the cafe can't take (see-through, out of its range, or an alias to nothing in the file)" if refused else ""))
    base = defaults()
    tf = old.get("tokensFromFiles")   # modes built from files last time: with their files gone, so are they
    filed = {m for m in tf if m in ("light", "dark")} if isinstance(tf, list) else set()
    for mode in filed - set(from_files) - broken:
        said.append(f"  {mode}: its tokens files have gone, so its tokens were dropped")
        modes[mode] = {}
    if "light" in from_files:
        from_files["light"] = {t: v for t, v in from_files["light"].items() if v.lower() != base.get(t, "").lower()}
    if "light" in from_files and "light" not in broken:
        modes["light"] = from_files["light"]
    if "dark" in from_files and "dark" not in broken:   # what differs from light as it now stands (The look's export repeats it)
        modes["dark"] = {t: v for t, v in from_files["dark"].items() if v.lower() != (modes["light"].get(t) or base.get(t, "")).lower()}
    for key, was in old.items():   # a drawing of hers in art/skin/ that has gone
        f = file_of(was)
        if key in art and isinstance(f, str) and f.startswith("art/skin/") and Path(f).stem == key and not (ROOT / f).is_file():
            said.append(f"  {key}: {f} has gone, so the pack's is back")   # one under another name is said with the hand-pointed
    pointed = {file_of(w) for k, w in old.items() if k in art and isinstance(file_of(w), str)}   # files skin.json names by hand
    names, filled = {}, {}   # filled: what each slot's drawing fills, said once the family check has run
    for p in files:
        if not p.name.endswith(".tokens.json"):
            names.setdefault(p.stem, []).append(p.name)
    for stem, both in names.items():
        if len(both) > 1:
            said.append(f"  {', '.join(both)} all name {stem}: {both[-1]} is the one used, unless it is left out")
    for p in files:
        if p.name.endswith(".tokens.json"):
            continue
        if p.stem not in art:
            if "art/skin/" + p.name not in pointed:   # one skin.json points at a slot by hand is weighed there
                said.append(f"  {p.name}: no slot is called {p.stem} (the slots are in ART, catio/index.html)")
            continue
        was = old.get(p.stem)
        f = file_of(was)
        if isinstance(f, str) and f.startswith("art/skin/") and Path(f).stem == p.stem and (ROOT / f).is_file():
            was = was if f == "art/skin/" + p.name else {}   # one of two drawings of hers named after the slot: said with the names above
        elif isinstance(f, str) and f != "art/skin/" + p.name:   # skin.json named another file for it: the folder's drawing wins, with its own settings
            said.append(f"  {p.name}: takes {p.stem} over {f}, which skin.json named for it")
            was = {}
        entry = check(art, p.stem, "art/skin/" + p.name, was if isinstance(was, dict) else {}, said, filled=filled)
        if entry:
            skin[p.stem] = entry
    member = lambda k: art[k]["kind"] == "slice" and "slice" not in art[k] and art[k].get("fam")
    # a slot pointed by hand at art outside art/skin/ (another pack's), checked the same way: the heads first, so the
    # folder's members are weighed against the head that will be drawn; then the members, so one refused in the
    # folder leaves a hand-pointed one its chance
    for members in (False, True):
        if members:
            family(art, skin, said)
        for key, was in old.items():
            f = file_of(was)
            if key in skin or bool(key in art and member(key)) != members:
                continue
            if key not in art:
                if key not in ("tokens", "dark", "tokensFromFiles"):
                    said.append(f"  {key}: no slot is called that (the slots are in ART, catio/index.html): dropped")
                continue
            if isinstance(f, str) and re.fullmatch(r"(/_blob/[\w-]+|/files/[\w.-]+|local:[\w-]+)", f):
                skin[key] = was   # an asset, a gateway file or one in a browser: the page checks it, this can't
                said.append(f"  {key}: {f} kept as written (not a file here, so the page checks it)")
                continue
            if not isinstance(f, str) or not f.startswith("art/"):
                said.append(f"  {key}: {f!r} isn't a file the page can read: dropped")
                continue
            if f.startswith("art/skin/") and Path(f).stem == key:
                continue   # one named after its slot was weighed with the folder
            if not re.fullmatch(r"art/[^\"'()\\\x00-\x1f]+", f) or ".." in f:   # the page's safeSrc()
                said.append(f"  {key}: {f} is a path the page won't read (quotes, brackets, a backslash or ..): left out")
                continue
            if not (ROOT / f).is_file():
                said.append(f"  {key}: {f} has gone, so it was dropped")
                continue
            entry = check(art, key, f, was if isinstance(was, dict) else {}, said, " (named by hand)" if f.startswith("art/skin/") else " (outside art/skin/)", filled=filled)
            if entry:
                skin[key] = entry
    family(art, skin, said)
    still = (set(from_files) - broken) | (filed & broken)   # built from files now, or still waiting on one half-saved
    if still:
        skin["tokensFromFiles"] = sorted(still)
    said.extend(line for key, line in filled.items() if key in skin)
    for mode, key in (("light", "tokens"), ("dark", "dark")):
        if modes[mode]:
            skin[key] = dict(sorted(modes[mode].items()))
            said.append(f"  {key}: {len(modes[mode])} ({mode})")
    if not skin and not OUT.exists():   # nothing of hers, and no skin.json to empty: none is written
        print(f"  (nothing in {SKIN.relative_to(ROOT.parent)} yet, so no {OUT.relative_to(ROOT.parent)} was written)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(skin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT.parent)}: {sum(k in art for k in skin)} of {len(art)} slots are hers")
    print("\n".join(said) if said else f"  (nothing in {SKIN.relative_to(ROOT.parent)} yet)")


if __name__ == "__main__":
    sys.exit(main())
