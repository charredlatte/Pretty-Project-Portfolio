---
name: catio
description: Set up or refresh someone's own Catio — a page where every Claude Code session is a cat living in a room of a two-floor pixel-art manor, with a queen in each room who keeps what matters in it. Use this whenever someone wants to see their Claude Code sessions as something other than a list: a dashboard of what's running, what's blocked and what's waiting on them; a "catio", cat café, cat house or session zoo; or when they ask to install, set up, rebuild, refresh or republish the Catio, add a room, or point a room at one of their repositories.
---

# The Catio

One page where every Claude Code session is a cat. It plays while it works, sleeps when it's done,
and meows with a speech bubble when it's waiting on its human. Each room of the manor is a kind of
work, and a session's git repository decides which room its cat lives in.

Every room also has a **queen**: a cat who is not a session, never leaves, and keeps the things
that matter about that room. You give her something to hold, and she hands it back — in her menu,
or said out loud in her room until you take it off her.

The page is one private artifact per person. Sessions come live from the Claude Code Remote
connector; rooms, renames, adopted chats and what the queens keep live in the artifact's own
database, so they follow the person between phone and computer.

## Say this first: the art is theirs to bring

**The cats are not in the repository and cannot be, and nor is the interface.** Eight of the ten
art packs the page is built from forbid redistributing their files (and a ninth came with no licence at
all), so `catio/art/licensed/` is gitignored. A fresh clone draws only the Cosy Cabin furniture, its
menus on plain colour: no house and no cats.

Tell the person this before anything else, because it decides whether the rest is worth their time.
The page says it too — the sign reads *"The cat art isn't here"* with the three steps — but hearing
it from a wall of pixels after twenty minutes of setup is a poor way to find out.

What they need, from `catio/art/CREDITS.md`:

| Pack | Artist | Gives |
|---|---|---|
| [Cosy Cabin](https://marie-pepo.itch.io/cosy-cabin) | Marie Pepo | most of the furniture (**already committed**: this one allows it) and, with the others, the manor's floors and walls |
| [Cat Pack Mochi](https://toffeecraft.itch.io/cat-pack) + [Pochi](https://toffeecraft.itch.io/cat-retro), Cat UI | ToffeeCraft | every cat, the logo, the cat tree and the bowls |
| [Top Down Garden Castle](https://heosphorus.itch.io/) | Heosphorus | the meadow, pond, rocks and trees |
| [Wood Garden](https://rowdy41.itch.io/wood-garden) | rowdy41 | the catio decking, fence and gate, bookcases and chests |
| [Pixel Art Top Down – Basic](https://cainos.itch.io/pixel-art-top-down-basic) | Cainos | the stone stair, the arch gate, lanterns and fountain |
| [Sprout Lands UI Pack – Basic](https://cupnooble.itch.io/) | Cup Nooble | the whole interface: panels, buttons, speech bubbles, mood faces, the cat-paw pointer and the pixel font |
| plants.zip | (unknown) | the terrace's plants |
| [Sprout Lands Sprites – Basic](https://cupnooble.itch.io/) | Cup Nooble | flowers on the lawn |
| [Little Dreamyland](https://starmixu.itch.io/little-dreamyland-asset-pack) | Starmixu & Utaskuas | glazed tiles and the spruce forest |
| Game UI Pack – Pastel Edition | SC_siosio | the map panel and the controls' icons. Credit it as "Game UI Pack created by SC_siosio" |

Most have a free tier. Without the ToffeeCraft pack in particular there are no cats, which is most
of the point; without Sprout Lands the menus still work, on plain colour.

## Setting one up

Work through these with the person. Stop and ask whenever a step needs something only they have.

### 1. Get the page

```bash
git clone https://github.com/charredlatte/Pretty-Project-Portfolio
cd Pretty-Project-Portfolio
```

`catio/index.html` is the whole page: no build step, no dependencies. `catio/CLAUDE.md` at the repo
root is the operating brief — read it before changing the page itself.

### 2. Their art

They put their own zips wherever they like and name them on the command line, in this order (the
names don't matter, the order does):

```bash
pip install pillow fonttools
python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip "Top down garden castle.zip" \
    "Wood Garden Asset Pack.zip" "Pixel Art Top Down - Basic v1.2.3.zip" \
    "Sprout Lands - UI Pack - Basic pack.zip" plants.zip \
    "Sprout Lands - Sprites - Basic pack.zip" "Little Dreamyland - Free Pack.zip" Game_UI_Pack_Pastel.zip
```

Given only the Sprout Lands UI zip (and, optionally, Game UI Pastel's after it), it builds just the
interface.

That writes `catio/art/licensed/`, which stays gitignored. Never commit what it produces, and never
put it in anything you share — that is the whole reason it is separate.

### 3. Their rooms

`catio/data/rooms.json` maps repositories to rooms. Each key is a room of the manor; `repos` takes
repository names or `owner/repo`, and exactly one room should have `"catchAll": true` — new cats
arrive there when nothing else claims them.

```json
"kitchen": { "name": "Kitchen", "blurb": "Weekly meals", "repos": ["my-recipe-app"], "catchAll": false }
```

The room keys are fixed by the picture — they are places in a drawing, not a list you can extend.
Downstairs: `dining` (the café), `kitchen`, `living` (the cat lounge), `study` (the craft room), `hall`
(the entrance hall), `sunroom` (the terrace) and `garden` (the catio, outside). Upstairs: `brain` (the
library), `bedroom` and `bath` (the ensuite). Names and
blurbs are theirs to change, here or from the page's own "Edit rooms".

Ask what they actually work on and fill this in with them. A manor where everything lands in the
cat lounge is a worse dashboard than a list.

### 4. Their sessions

The page reads its cats live from Claude Code Remote. It also keeps a saved copy for when that read
is blocked, and that copy is the only source when the page runs off a folder:

1. Call `list_sessions` (limit 50) and save the result to a file.
2. `python3 catio/tools/save-sessions.py list_sessions.json` → `catio/data/sessions.json`.

That output is gitignored, and it should stay that way: it carries their session titles.

### 5. Their page

Publish `catio/index.html` as **their own** private artifact — never republish someone else's.
The URL in this repo's `artifacts.json` is Charlotte's, and her rooms and her queens live in its
database; publishing over it would take her page away from her. Their first publish creates a new
artifact, and they record that URL in their own copy of `artifacts.json`, republishing to it
afterwards with `url` so nothing they have done on the page is lost.

On the first publish it needs these capabilities:

```
capabilities: { mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions", "create_session",
  "set_session_title", "archive_session", "unarchive_session", "interrupt_session"] }] },
  db: {}, assets: {}, sample: {} }
```

The `mcp` grant is what lets the page read and manage their sessions as them, and only ever on their
click; `db` is where rooms, renames, adopted chats and the queens' notes are kept; `assets` holds files
dropped on a cat; `sample` lets the page ask Claude which cat a file is for. On a republish, omit
`capabilities` to keep what is stored: passing it replaces the whole set, so naming only some revokes
the rest.

If the sign says claude.ai won't let the page read sessions live, there is nothing for them to
switch: Claude Code Remote is built into claude.ai and has no entry in their Connectors list. The
page falls back to the saved copy from step 4, so refresh that copy instead.

### 6. Off a USB stick, if they want it

```bash
python3 catio/tools/bundle.py     # -> catio/dist/catio-local/ and a zip
```

A folder that runs from any local web server with no claude.ai at all. It also carries the Catio's own
MCP server (`harness/mcp/catio_mcp.py --serve . --port 8791`), through which agents that aren't Claude
Code sessions (Codex, Gemini CLI, Cursor) join as cats. It contains their licensed
art and their session list, so it is for them alone — never share the folder or commit it.

## Adopting the things that aren't sessions

Chats on claude.ai — a business plan, a legal question — can't be read by any connector. They are
adopted by hand from a room's menu: title, link, project, mood and a note. Whatever is typed there
is stored in the artifact database and visible to anyone the page is shared with, which the form
says on its face. Keep anything sensitive in the chat itself and give the cat a bland name.

## Queens, and what they're for

Each room's queen holds what matters about that room — the thing you'd otherwise have to remember,
or go and look up. A note she is *saying* shows as her line in the menus and a bubble in her room
until it is taken back; the rest she just keeps.

She is deliberately not a task: she never joins the count of cats needing you, because a sign that
says "3 need you" has to mean three real pieces of work. If you change how she works, keep her out
of those counts.

## Changing the page

- `sh catio/test/run.sh` runs the end-to-end suite in headless Chromium, against a stand-in for the
  artifact runtime and against the local bundle on a real server. Run it after every change; it
  builds the bundle as part of the run, so a broken bundler fails the suite.
- Look before you touch a test: `sh catio/test/run.sh look <room>` screenshots the page in a few seconds.
  Hold each one against what was asked; then run the suite unchanged, and rewrite only the checks the ask
  meant to break, from the ask's words rather than the code's.
- `catio/tools/manor.py` is the floor plan (two floors on one grid) and `catio/tools/furniture.py`
  places the furniture and the cats' stations and writes the page's `MANOR` block, from which `GEOM`
  comes. Change them together, re-run `furniture.py`, and check that `furniture.check()` is empty — a cat
  standing in a bathtub is a geometry bug, not a styling one.
- Each room holds back one seat for its queen (`GEOM[room].queen`). Giving a room another cat seat
  means taking one out of `spots`, not inventing a coordinate, because the seats are positions on a
  drawing that was checked against the art.

Read `CLAUDE.md` in the repository root before anything structural. It carries the decisions this
page has already paid for.
