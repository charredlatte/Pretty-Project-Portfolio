#!/usr/bin/env python3
"""List her own art for the page: art/skin/ in, art/skin.json out.

    python3 catio/tools/skin.py           ->  catio/art/skin.json, and what each file fills or why it can't

Every piece of the café is a slot (ART in catio/index.html, named as docs/drawing-plan.md names her files).
Drop a drawing in catio/art/skin/ under its slot's name (panel.png, cat-meow.png, font.ttf...), run this, and
the page draws with it: no code changes. It reads each PNG's size and checks it as the page does: the house,
the grounds, the furniture and the cursors must be their exact size, a sheet the same shape, and a cat's
frames must split its width. A 9-slice drawn at another size than the pack's needs its border, and a cat
its frames when they aren't square: say so in art/skin.json ("slice": [top, right, bottom, left],
"frames": 6, "secs": 0.6), which this keeps on every run. Entries for files that have gone are dropped.

The rest of the design system is tokens, kept here in two modes, as Figma keeps a variable per mode:
"tokens": {"--ink": "#3F2A20", "--px-size": "16px"} for light and "dark": {...} for what differs at night (TOKENS in
the page lists them: colours as six hex digits, sizes in px or rem). Drop a design tokens file in art/skin/ too (the
W3C format Figma's variables export, or The look's own export: *.tokens.json, "dark" in its name for the dark mode)
and its tokens are read into that mode; a token is matched by its own name (ink, go, px-size...) wherever it sits.
Tokens already in skin.json and not in a file are kept.

The page also takes art from The look in its House menu; that wins over this file. Needs nothing but Python.
"""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
SKIN = ROOT / "art" / "skin"
OUT = ROOT / "art" / "skin.json"
FONTS = {".ttf", ".otf", ".woff", ".woff2"}


def slots():
    """The slot table, read from the page itself so the two can't disagree."""
    text = PAGE.read_text(encoding="utf-8")
    block = text[text.index("const ART = {"):text.index("const SPR0")]
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
        v = re.search(r"frames: (\d+)", line)
        if v:
            a["frames"] = int(v.group(1))
        out[m.group(1)] = a
    return out


def token_names():
    text = PAGE.read_text(encoding="utf-8")
    block = text[text.index("const TOKENS = {"):text.index("const tokenOk")]
    return dict(re.findall(r'"(--[\w-]+)": \["([^"]+)"', block))


def token_ok(groups, name, v):
    if name not in groups or not isinstance(v, str):
        return False
    return bool(re.fullmatch(r"\d{1,3}(\.\d{1,3})?(px|rem)", v) if groups[name] == "Type" else re.fullmatch(r"#[0-9a-fA-F]{6}", v))


def from_dtcg(doc, groups):
    """The page's fromDTCG(): the café's tokens in a design tokens file, and how many weren't the café's."""
    flat, found, foreign = {}, {}, 0

    def walk(node, path):
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
    for path, raw in flat.items():
        name, v, css = "--" + path.split(".")[-1], resolve(raw), None
        if name not in groups:
            foreign += 1
            continue
        if isinstance(v, str):
            css = v[:7] if re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", v) else v
        elif isinstance(v, dict) and isinstance(v.get("hex"), str):
            css = v["hex"][:7]
        elif isinstance(v, dict) and isinstance(v.get("components"), list) and v.get("colorSpace", "srgb") == "srgb":
            css = "#" + "".join(f"{round(min(1, max(0, c)) * 255):02x}" for c in v["components"][:3])
        elif isinstance(v, dict) and isinstance(v.get("value"), (int, float)) and v.get("unit") in ("px", "rem"):
            css = f"{round(v['value'], 3):g}{v['unit']}"
        if token_ok(groups, name, css):
            found[name] = css
        else:
            foreign += 1
    return found, foreign


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def main():
    art = slots()
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    files = sorted(p for p in SKIN.iterdir() if p.is_file()) if SKIN.is_dir() else []
    skin, said = {}, []
    groups = token_names()
    modes = {m: {k: v for k, v in (old.get(key) or {}).items() if token_ok(groups, k, v)} if isinstance(old.get(key), dict) else {}
             for m, key in (("light", "tokens"), ("dark", "dark"))}
    for p in files:
        if p.name.endswith(".tokens.json"):
            mode = "dark" if "dark" in p.name.lower() else "light"
            try:
                found, foreign = from_dtcg(json.loads(p.read_text(encoding="utf-8")), groups)
            except (ValueError, UnicodeDecodeError):
                said.append(f"  {p.name}: not a tokens file (it isn't JSON)")
                continue
            modes[mode].update(found)
            said.append(f"  {p.name}: {len(found)} tokens into {mode}" + (f", {foreign} not the cafe's" if foreign else ""))
            continue
        key = p.stem
        if key not in art:
            said.append(f"  {p.name}: no slot is called {key} (the slots are in ART, catio/index.html)")
            continue
        a, was = art[key], old.get(key) if isinstance(old.get(key), dict) else {}
        entry = {k: v for k, v in was.items() if k in ("slice", "frames", "secs", "anchor", "scale", "pixel")}
        entry["file"] = "art/skin/" + p.name
        if a["kind"] == "font":
            if p.suffix.lower() not in FONTS:
                said.append(f"  {p.name}: the font slot takes .ttf, .otf or .woff")
                continue
            skin[key] = entry
            said.append(f"  {p.name}: the pixel font")
            continue
        size = png_size(p)
        if not size:
            said.append(f"  {p.name}: not a PNG")
            continue
        w, h = size
        want = a.get("size")
        if a["kind"] == "exact" and want and [w, h] != want:
            said.append(f"  {p.name}: {w} x {h}, but it must be {want[0]} x {want[1]}: left out")
            continue
        if a["kind"] == "sheet" and want and abs(w / h - want[0] / want[1]) > 0.02:
            said.append(f"  {p.name}: {w} x {h}, but it must be the shape of {want[0]} x {want[1]}: left out")
            continue
        note = ""
        if a["kind"] == "slice" and "slice" in a and want and [w, h] != want and "slice" not in entry:
            note = f" (another size than the pack's {want[0]} x {want[1]}: give its border, \"slice\": [t, r, b, l], or it keeps {a['slice']})"
        if a["kind"] == "cat":
            n = entry.get("frames") or (w // h if w % h == 0 else a.get("frames", 1))
            if w % n:
                said.append(f"  {p.name}: {w} px wide doesn't split into {n} frames: set \"frames\" in skin.json")
                continue
            entry["frames"] = n
            note = f" ({n} frames of {w // n} x {h})"
        skin[key] = entry
        said.append(f"  {p.name}: {key}{note}")
    for mode, key in (("light", "tokens"), ("dark", "dark")):
        if modes[mode]:
            skin[key] = dict(sorted(modes[mode].items()))
            said.append(f"  {key}: {len(modes[mode])} ({mode})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(skin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT.parent)}: {len(skin) - ('tokens' in skin) - ('dark' in skin)} of {len(art)} slots are hers")
    print("\n".join(said) if said else f"  (nothing in {SKIN.relative_to(ROOT.parent)} yet)")


if __name__ == "__main__":
    sys.exit(main())
