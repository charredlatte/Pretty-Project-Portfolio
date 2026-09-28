# The Catio: operating brief

`README.md` says what the page is. This file is how to work on it.

## Republishing

The page is **one** private artifact. Its URL is in `artifacts.json`. Always republish to that
URL (`Artifact` publish with `url`, after reading it back), never a new one: the database with
her rooms, renames and adopted chats belongs to that artifact.

Publish `catio/index.html` with:

- `files`: every file the page references: `art/house.png`, `art/ui/*.png` (frames, plaques,
  wallpaper, rail, bar, slot, door) and `art/licensed/*.png` (`decor.png`, `meadow.png`,
  `mochi-idle.png`, `mochi-box.png`, `pochi.png`, `cat-ui.png`);
- `capabilities`: omit it on a republish to keep what's stored. The declaration is
  `{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions"] }] }, db: {} }`.

`art/licensed/` is not in git (licences below). In a fresh session, get it back one of two ways:

1. `Artifact` read with `path: "art/licensed/<file>"` on the published URL, for each file; or
2. ask Charlotte for the four zips and run
   `python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip Top_down_garden_castle.zip Wood_Garden_Asset_Pack.zip`
   (needs `pip install pillow`).

## Licences: what may be committed

- **Cosy Cabin** (Marie Pepo): copying and modifying allowed, with credit. `art/house.png` and
  `art/ui/` (every frame, plaque and wallpaper on the page) are committed.
- **ToffeeCraft cats** (free version): personal use only, **no redistribution**. Never commit.
- **Top Down Garden Castle** (Heosphorus): **no distribution, even modified**. Never commit.
- **Wood Garden** (rowdy41): no resale. It is baked into `decor.png` with Heosphorus's
  pieces, so that file stays uncommitted too.

The footer credits all four. Keep it.

## The cabin is a floor plan

`catio/tools/cabin.py` is the plan: rooms as tile boxes with their floors and wallpapers,
doorways, glass (floor-to-ceiling on back walls, strips on outside walls), and furniture as
`(sprite, x, y)`. `house()` draws it from Cosy Cabin alone (committed as `art/house.png`);
`decor()` adds the catio, the garden and indoor pieces from the other packs (`decor.png`).
The page's `GEOM` (room boxes and cat spots) and `WORLD` must match the plan. Change both
together, then re-render and check that no cat stands on furniture.

The layout follows ordinary small-cabin planning: kitchen, dining and living as one open run
facing the light; the sunroom off the living room; bedroom, ensuite and study behind; the
bathroom backing onto the kitchen's plumbing; the catio fenced against the sunroom's outside
wall, reached by a cat flap, with shade, shelves to climb and seats for people.

## The UI is made of the packs

Frames, panels, buttons, chips, slots and dividers are 9-slice `border-image`s cut from the
Cosy Cabin tile sheet (`art/ui/`). The hotbar icons, mood faces and paw come from ToffeeCraft's
cat UI sheet. Keep it that way: a new control should reuse one of these pieces rather than a
CSS border or gradient. `--u` is one art pixel on screen (2px, or 1px on phones).

## Data

The artifact database, written by the page and seeded with `ArtifactData`:

| Collection | Document | Holds |
|---|---|---|
| `rooms` | one per room key (`garden` (the catio), `kitchen`, `dining`, `living`, `sunroom`, `study`, `bedroom`, `bath`, `hall`) | `name`, `blurb`, `repos[]` (repo names or `owner/repo`), `catchAll` |
| `sessions` | the Claude Code session id | `name`, `room`: her rename or move of one session's cat |
| `cats` | generated id | an adopted chat: `title`, `link`, `room`, `mood` (`needs` / `busy` / `done`), `note`, `name` |

Room **geometry** (where each room is on the art and where its cats sit) is code, in `GEOM` in
the page, because it is tied to the picture. Room **names and which projects live where** are
data. Don't hardcode those.

Adopted chats can hold anything she types, including legal matters. They live only in the
artifact database, never in this repo. The adopt form says so.

## Live sessions

The page calls `list_sessions` (limit 50) through the `mcp` capability as the viewer. It never
calls a write tool. Don't add `mine: true`: a page has no calling session, and that flag can
error without one. Every connector error code has its own message in `problem()`.

## Checking a change

There is no test suite. Render the page before publishing: wrap `catio/index.html` in the
publish skeleton with a stub `window.claude` that returns example sessions, then screenshot it
at 390 px and 1280 px in light and dark. Chromium is at `/opt/pw-browsers`. Keep the stub and
its example data out of the repo, and never paste her real session list into the page.
