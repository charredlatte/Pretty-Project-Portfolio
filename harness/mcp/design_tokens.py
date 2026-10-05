"""The café's design tokens as a design tokens file, for catio_mcp.py's tokens and set_tokens: the gateway's
src/tokens.js (and the page's toDTCG and fromDTCG) in Python, standard library only.

The token table, the size ranges and the café's own values are read from the page the server serves (its
index.html), never copied. harness/test/fixtures/tokens-figma.json is read by all four (the page, skin.py, the
gateway and this) and must come out the same everywhere.
"""
import json
import math
import re


class Page:
    """What the café's index.html says about its tokens."""

    def __init__(self, text):
        a = text.find("const TOKENS = {")
        block = text[a:text.find("};", a)] if a >= 0 else ""
        self.tokens = {n: json.loads(arr) for n, arr in re.findall(r'"(--[\w-]+)": (\[[^\]]*\])', block)}
        m = re.search(r"const SIZES = (\{[^}]*\})", text)
        self.sizes = json.loads(m.group(1)) if m else {}
        m = re.search(r"const WHOLE_PX = (\[[^\]]*\])", text)
        self.whole = json.loads(m.group(1)) if m else []
        a = text.find(":root {")
        root = text[a:text.find("color-scheme: light;", a)] if a >= 0 else ""
        self.defaults = {n: v.strip() for n, v in re.findall(r"(--[\w-]+):\s*([^;]+);", root) if n in self.tokens}
        if not self.tokens:
            raise ValueError("the café's page has no TOKENS table: is this the café's folder?")

    def size_ok(self, name, v):
        m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3})?)(px|rem)", v)
        lo, hi = self.sizes.get(name, (0, 0))
        if m and name in self.whole and (m.group(2) != "px" or not float(m.group(1)).is_integer()):
            return False
        return bool(m) and lo <= float(m.group(1)) * (16 if m.group(2) == "rem" else 1) <= hi

    def ok(self, name, v):
        if name not in self.tokens or not isinstance(v, str):
            return False
        return self.size_ok(name, v) if self.tokens[name][0] == "Type" else bool(re.fullmatch(r"#[0-9a-fA-F]{6}", v))

    def clean(self, t):
        return {k: v for k, v in (t.items() if isinstance(t, dict) else []) if self.ok(k, v)}

    def modes(self, theme):
        theme = theme if isinstance(theme, dict) else {}
        return {"light": self.clean(theme.get("tokens")), "dark": self.clean(theme.get("dark"))}


def group_key(g):
    return re.sub(r"[^a-z0-9]+", "-", g.lower())


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _value_in(t, page, mode, n):
    return t[mode].get(n) or t["light"].get(n) or page.defaults.get(n)


def to_dtcg(page, theme, mode):
    """The café's tokens in mode as a design tokens file: the page's toDTCG."""
    t = page.modes(theme)
    out = {"$description": "The KittyChat Café's design tokens, " + mode + " mode. Import into Figma's variables as a mode, or into The look."}
    for n, (g, name, what) in page.tokens.items():
        grp = out.setdefault(group_key(g), {"$type": "dimension" if g == "Type" else "color"})
        v = _value_in(t, page, mode, n) or ""
        tk = {"$description": name + (". " + what if what else "")}
        if g == "Type":
            m = re.fullmatch(r"([\d.]+)(px|rem)", v)
            num = float(m.group(1)) if m else 0
            tk["$value"] = {"value": int(num) if num.is_integer() else num, "unit": m.group(2) if m else "px"}
        else:
            h = v.lower()
            tk["$value"] = {"colorSpace": "srgb", "components": [float(f"{int(h[i:i + 2], 16) / 255:.4f}") for i in (1, 3, 5)], "hex": h}
        grp[n[2:]] = tk
    return out


def from_dtcg(page, doc):
    """A design tokens file read for the café: the page's fromDTCG. (found, foreign, refused)."""
    flat, found, own, bad, foreign = {}, {}, {}, set(), 0

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
        n, v = "--" + re.sub(r"[\s_]+", "-", path.split(".")[-1].strip().lower()), resolve(raw)
        if n not in page.tokens:
            foreign += 1
            continue
        hexa = v if isinstance(v, str) else v.get("hex") if isinstance(v, dict) and isinstance(v.get("hex"), str) else ""
        clear = bool(re.fullmatch(r"#[0-9a-fA-F]{6}(?![fF]{2})[0-9a-fA-F]{2}", hexa)) or (isinstance(v, dict) and _num(v.get("alpha")) and v["alpha"] < 1)
        css = None
        if isinstance(v, str):
            css = v[:7] if re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", v) else v
        elif isinstance(v, dict) and isinstance(v.get("hex"), str):
            css = v["hex"][:7]
        elif isinstance(v, dict) and isinstance(v.get("components"), list) and (v.get("colorSpace") or "srgb") == "srgb":
            try:   # halves up, as Math.round
                css = "#" + "".join(f"{math.floor(min(1, max(0, c)) * 255 + 0.5):02x}" for c in v["components"][:3])
            except TypeError:
                css = None
        elif isinstance(v, dict) and _num(v.get("value")) and v.get("unit") in ("px", "rem"):
            css = f"{round(v['value'], 3):g}{v['unit']}"
        elif _num(v) and page.tokens[n][0] == "Type":
            css = f"{round(v, 3):g}px"
        if clear or not page.ok(n, css):
            bad.add(n)
            continue
        mine = path.split(".")[0] == group_key(page.tokens[n][0])
        if n in found and (own[n] or not mine):
            continue
        found[n], own[n] = css, mine
    return found, foreign, len(bad - found.keys())


def import_into(page, theme, mode, doc, replace=False):
    """A file brought into mode of a theme ({tokens, dark}), as The look's Import tokens… does. (new modes, report)."""
    found, foreign, refused = from_dtcg(page, doc)
    was = page.modes(theme)
    nxt = {"light": dict(was["light"]), "dark": dict(was["dark"])}
    changed = sum(1 for n, v in found.items() if v.lower() != str(_value_in(was, page, mode, n)).lower())
    nxt[mode] = dict(found) if replace else {**nxt[mode], **found}

    def anyway(n):   # the same as it would be anyway: light's own is the café's, dark's is light's
        return (nxt["light"].get(n) or page.defaults.get(n)) if mode == "dark" else page.defaults.get(n)
    for n, v in list(nxt[mode].items()):
        if v != was[mode].get(n) and v.lower() == str(anyway(n)).lower():
            del nxt[mode][n]
    return nxt, {"mode": mode, "tokens": len(found), "changed": changed, "foreign": foreign, "refused": refused}
