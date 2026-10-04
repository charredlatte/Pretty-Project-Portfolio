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

The rest of the design system is tokens, also kept here: "tokens": {"--ink": "#3F2A20", "--px-size": "16px"}
(TOKENS in the page lists them: colours as six hex digits, sizes in px or rem). This keeps them as they are.

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
    for p in files:
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
    tokens = old.get("tokens") if isinstance(old.get("tokens"), dict) else {}
    if tokens:
        skin["tokens"] = tokens
        said.append(f"  tokens: {len(tokens)} kept ({', '.join(sorted(tokens))})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(skin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT.parent)}: {len(skin) - ('tokens' in skin)} of {len(art)} slots are hers")
    print("\n".join(said) if said else f"  (nothing in {SKIN.relative_to(ROOT.parent)} yet)")


if __name__ == "__main__":
    sys.exit(main())
