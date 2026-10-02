#!/usr/bin/env python3
"""Move the café into the gateway: upload the art from this checkout (catio/art, the licensed packs included, never
committed), and import the café's data once.

    CATIO_URL=https://catio-gateway.<name>.workers.dev CATIO_TOKEN=... python3 harness/gateway/cafe/move-in.py [docs.json]

docs.json is {"<collection>/<id>": {...}}: the claude.ai artifact's database, as Claude exports it with ArtifactData.
The gateway takes an import only while the café's database is empty. Run it again after rebuilding the art.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CATIO = Path(__file__).resolve().parents[3] / "catio"


def send(method, path, body, content_type):
    url = os.environ["CATIO_URL"].rstrip("/") + path
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": "Bearer " + os.environ["CATIO_TOKEN"].strip(), "Content-Type": content_type,
        "User-Agent": "kittychat-move-in/1"})   # Cloudflare refuses Python's own User-Agent
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    art = [CATIO / "art" / "furniture.png"] + sorted(p for p in (CATIO / "art" / "licensed").rglob("*") if p.suffix in (".png", ".ttf"))
    if len(art) < 2:
        sys.exit("No licensed art in catio/art/licensed: read it back from the artifact first (CLAUDE.md, Republishing).")
    bad = []
    for p in art:
        rel = p.relative_to(CATIO).as_posix()
        status, text = send("PUT", "/api/" + rel, p.read_bytes(), "application/octet-stream")
        if status != 200:
            bad.append(f"{rel}: {status} {text[:120]}")
    print(f"art: {len(art) - len(bad)} of {len(art)} uploaded")
    for b in bad:
        print("  " + b)
    if len(sys.argv) > 1:
        docs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        status, text = send("POST", "/api/import", json.dumps({"docs": docs}).encode(), "application/json")
        print(f"import: {status} {text[:200]}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
