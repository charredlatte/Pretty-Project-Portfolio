#!/usr/bin/env python3
"""Turn a graphify graph into the Catio's project map: the `graphs/<repo>` document a filing cabinet shows.

    python3 graph_doc.py [graphify-out] [--by <session id>]

Reads graph.json and GRAPH_REPORT.md from graphify's output folder (default ./graphify-out), prints the
document id on the first line and the document as JSON after it, and saves the JSON beside the graph as
catio-graph.json for `ArtifactData` (`set`, `file_path`). Standard library only.
"""
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

TOP = 40     # ideas drawn on the map
W, H = 300, 160


def repo_name(root):
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True).stdout.strip()
    except OSError:
        url = ""
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else Path(root).resolve().name


def slug(name):
    return re.sub(r"[^a-z0-9_-]+", "-", name.split("/")[-1].lower()).strip("-")[:80] or "none"


def section(report, title):
    m = re.search(r"^## " + re.escape(title) + r"[^\n]*\n(.*?)(?=^## |\Z)", report, re.M | re.S)
    return m.group(1) if m else ""


def clip(s, n=80):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def layout(groups):
    """Each neighbourhood on an ellipse round the middle, its ideas spiralled out from its spot, busiest first."""
    xy, k = {}, len(groups)
    for j, members in enumerate(groups):
        a = 2 * math.pi * j / k - math.pi / 2
        cx, cy = (W / 2 + 108 * math.cos(a), H / 2 + 52 * math.sin(a)) if k > 1 else (W / 2, H / 2)
        for i, m in enumerate(members):
            r, t = 7 * math.sqrt(i), i * 2.39996
            xy[m] = (min(W - 6, max(6, round(cx + r * math.cos(t)))), min(H - 6, max(6, round(cy + r * math.sin(t)))))
    return xy


def build(out, by=""):
    out = Path(out)
    g = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    rp = out / "GRAPH_REPORT.md"
    report = rp.read_text(encoding="utf-8") if rp.exists() else ""
    root = (out / ".graphify_root").read_text(encoding="utf-8").strip() if (out / ".graphify_root").exists() else str(out.resolve().parent)
    nodes = [n for n in g["nodes"] if n.get("type") != "external"]
    ids = {n["id"] for n in nodes}
    links = g.get("links") or g.get("edges") or []
    deg = {}
    for l in links:
        for e in (l["source"], l["target"]):
            deg[e] = deg.get(e, 0) + 1

    sizes = {}
    for n in nodes:
        c = n.get("community")
        if c is not None:
            sizes.setdefault(c, [n.get("community_name") or "Group " + str(c), 0])[1] += 1
    order = sorted(sizes, key=lambda c: -sizes[c][1])
    groups = [{"name": clip(sizes[c][0], 48), "size": sizes[c][1]} for c in order[:8]]
    gi = {c: i for i, c in enumerate(order[:8])}

    gods = []
    for m in re.finditer(r"^\d+\.\s+`(.+?)`\s+-\s+(\d+)\s+edges", section(report, "God Nodes"), re.M):
        same = [n for n in nodes if n.get("label") == m.group(1)]
        f = max(same, key=lambda n: deg.get(n["id"], 0)).get("source_file", "") if same else ""
        gods.append({"label": clip(m.group(1), 60), "degree": int(m.group(2)), "file": f})
    if not gods:
        for n in sorted(nodes, key=lambda n: -deg.get(n["id"], 0))[:8]:
            gods.append({"label": clip(n["label"], 60), "degree": deg.get(n["id"], 0), "file": n.get("source_file", "")})
    gods = gods[:8]

    surprises = []
    for m in re.finditer(r"^- `(.+?)` --(\w+)--> `(.+?)`\s+\[(\w+)\]\s*\n\s+(.+?)\s*$", section(report, "Surprising Connections"), re.M):
        surprises.append({"a": clip(m.group(1), 60), "rel": m.group(2), "b": clip(m.group(3), 60), "how": m.group(4), "where": clip(m.group(5), 120)})
    questions = [clip(re.sub(r"[`*]", "", q), 200) for q in re.findall(r"^- \*\*(.+?)\*\*\s*$", section(report, "Suggested Questions"), re.M)]

    top = sorted(nodes, key=lambda n: (-deg.get(n["id"], 0), n["label"]))[:TOP]
    at = {n["id"]: i for i, n in enumerate(top)}
    pairs = sorted({tuple(sorted((at[l["source"]], at[l["target"]]))) for l in links
                    if l["source"] in at and l["target"] in at and l["source"] != l["target"]})
    by_group = {}
    for i, n in enumerate(top):
        by_group.setdefault(n.get("community"), []).append(i)
    xy = layout(sorted(by_group.values(), key=lambda m: (-len(m), m[0])))
    name = repo_name(root)
    doc = {
        "repo": name, "at": int(time.time() * 1000), "by": by, "commit": (g.get("built_at_commit") or "")[:12],
        "nodes": len(nodes), "edges": sum(1 for l in links if l["source"] in ids and l["target"] in ids), "communities": len(sizes),
        "gods": gods, "groups": groups, "surprises": surprises[:5], "questions": questions[:5],
        # objects and a flat list: the Catio's database takes no arrays inside arrays
        "map": {"n": [{"t": clip(n["label"], 48), "g": gi.get(n.get("community"), -1), "d": deg.get(n["id"], 0), "x": xy[i][0], "y": xy[i][1]}
                      for i, n in enumerate(top)],
                "l": [i for p in pairs for i in p]},
    }
    return slug(name), doc


def main(argv):
    # The doc keeps its non-ASCII (ensure_ascii=False), and graph reports carry arrows, so stdout
    # must not fall back to the console's codepage: cp1252 cannot encode them and the run dies.
    sys.stdout.reconfigure(encoding="utf-8")
    by = argv[argv.index("--by") + 1] if "--by" in argv else ""
    rest = [a for i, a in enumerate(argv) if a != "--by" and (i == 0 or argv[i - 1] != "--by")]
    out = Path(rest[0] if rest else "graphify-out")
    if not (out / "graph.json").exists():
        sys.exit(f"No graph at {out / 'graph.json'}. Build it first: graphify update . (code) or /graphify . (everything).")
    key, doc = build(out, by)
    (out / "catio-graph.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print("graphs/" + key)
    print(json.dumps(doc, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
