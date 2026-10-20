#!/usr/bin/env python3
"""Make a folder (and a zip) that runs the Catio from any local web server, e.g. off a USB stick.

    python3 catio/tools/bundle.py            ->  catio/dist/catio-local/  and  catio/dist/catio-local.zip

It holds the page as a complete HTML document, all the art (licensed art included: this copy is for
Charlotte's own use, never for sharing or committing), data/rooms.json, and data/sessions.json if
Claude has saved one, and the Catio MCP server (harness/mcp/catio_mcp.py with its rules.json) so agents
that aren't Claude Code sessions can join as cats. Run it with VS Code's Live Server, `python -m http.server`, or `php -S localhost:8000`.
"""
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT.parent / "harness"
DIST = ROOT / "dist"
OUT = DIST / "catio-local"

HOWTO = """THE KITTYCHAT CAFÉ, ON YOUR OWN COMPUTER

1. Copy this folder onto your USB stick (or anywhere).
2. Open the folder in VS Code (File > Open Folder).
3. Start a local web server in it, any one of these:
   - VS Code: install the "Live Server" extension, then right-click index.html > Open with Live Server
   - a terminal in this folder: python -m http.server 8000   then open http://localhost:8000
   - or, if you have PHP: php -S localhost:8000             then open http://localhost:8000
   (Opening index.html by double-clicking won't load the cats: browsers block reading the data
   folder from a file:// page. It needs one of the servers above.)

To let other agents in too (Codex, Gemini CLI, Cursor, any MCP client), serve the folder with the
Catio's own server instead, which needs only Python:
   python3 harness/mcp/catio_mcp.py --serve . --port 8791   then open http://localhost:8791
Agents join it as an MCP server: python3 harness/mcp/catio_mcp.py (over stdio). It keeps its
state in a .catio folder in your home folder, and its house rules in harness/rules.json.

What you'll see: the manor, with a cat for every Claude Code session in data/sessions.json, the
copy Claude saved. Adopted cats, room names and project looks are saved in this browser.
To get newer cats, ask Claude to refresh data/sessions.json and copy the new file into data/.

The art belongs to Marie Pepo, ToffeeCraft, Heosphorus, rowdy41, Cainos, Cup Nooble,
Starmixu & Utaskuas (Little Dreamyland) and SC_siosio (Game UI Pack created by SC_siosio). It's licensed for
your own use: please don't share this folder.
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        "<style>[hidden]{display:none!important}img{max-width:100%}</style></head><body>\n"
        + page + "\n</body></html>\n", encoding="utf-8")
    shutil.copytree(ROOT / "art", OUT / "art", ignore=shutil.ignore_patterns("CREDITS.md"))
    shutil.copy(ROOT / "art" / "CREDITS.md", OUT / "CREDITS.md")
    for name in ("rooms.json", "sessions.json"):
        if (ROOT / "data" / name).exists():
            shutil.copy(ROOT / "data" / name, OUT / "data" / name)
    (OUT / "harness" / "mcp").mkdir(parents=True)
    for name in ("catio_mcp.py", "design_tokens.py"):   # the server imports design_tokens from beside itself
        shutil.copy(HARNESS / "mcp" / name, OUT / "harness" / "mcp" / name)
    shutil.copy(HARNESS / "rules.json", OUT / "harness" / "rules.json")  # where catio_mcp.py looks for it
    (OUT / "HOW-TO-RUN.txt").write_text(HOWTO, encoding="utf-8")
    zpath = DIST / "catio-local.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                z.write(f, Path("catio-local") / f.relative_to(OUT))
    print("wrote", OUT, "and", zpath, f"({zpath.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
