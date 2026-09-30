# The Catio: operating brief

`README.md` says what the page is. This file is how to work on it.

## Republishing

The page is **one** private artifact. Its URL is in `artifacts.json`. Always republish to that
URL (`Artifact` publish with `url`, after reading it back), never a new one: the database with
her rooms, renames and adopted chats belongs to that artifact.

Publish `catio/index.html` with:

- `files`: every file the page references: `art/furniture.png`, `art/licensed/*.png` (`house.png`,
  `house-upper.png`, `decor.png`, `furniture.png`, `meadow.png`, `mochi-idle.png`, `mochi-box.png`,
  `pochi.png`) and the interface
  in `art/licensed/ui/` (`panel`, `button`, `button-hover`, `button-down`, `button-green`,
  `button-pink`, `field`, `arrow`, `frame`, `divider`, `bubble`, `bubble-tail`, `corners`,
  `toggle`, `status`, `faces`, `crown`, `stars`, `cursor`, `cursor-point`, `icons`, `pointer`, `logo` `.png`,
  and `sprout.ttf`);
- `capabilities`: omit it on a republish to keep what's stored. The declaration is
  `{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions"] }] }, db: {} }`.

`catio/data/` is **not** published: it is for the localhost copy (below).

`art/licensed/` is not in git (licences below). In a fresh session, get it back one of two ways:

1. `Artifact` read with `path: "art/licensed/<file>"` on the published URL, for each file; or
2. get the nine zips from her Drive folder "KittyChat Cafe Assets" (or ask her for them) and run
   `python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip "Top down garden castle.zip" "Wood Garden Asset Pack.zip" "Pixel Art Top Down - Basic v1.2.3.zip" "Sprout Lands - UI Pack - Basic pack.zip" plants.zip "Sprout Lands - Sprites - Basic pack.zip" "Little Dreamyland - Free Pack.zip"`
   (needs `pip install pillow fonttools`; the order matters, not the names). Given only the Sprout Lands zip, it rebuilds just the
   interface.

## Licences: what may be committed

- **Cosy Cabin** (Marie Pepo): copying and modifying allowed, with credit. `art/furniture.png` is
  committed. The house itself is not: it mixes every pack now.
- **ToffeeCraft cats** (free version): personal use only, **no redistribution**. Never commit.
- **Top Down Garden Castle** (Heosphorus): **no distribution, even modified**. Never commit.
- **Wood Garden** (rowdy41): no resale. It is baked into `decor.png` with Heosphorus's
  pieces, so that file stays uncommitted too.
- **Pixel Art Top Down – Basic** (Cainos): free for any project, **no redistribution**. Its
  stonework is also in `decor.png`. It is drawn on a 32 px grid, twice the cabin's, so its
  pieces read large: use it for garden stonework, not indoor furniture.
- **Sprout Lands UI Pack – Basic** (Cup Nooble): modifying allowed, **no redistribution or resale,
  even modified**, non-commercial use only. The whole interface (`art/licensed/ui/`). Never commit.
- **Sprout Lands Sprites – Basic** (Cup Nooble): the same terms. Flowers on the lawn. Never commit.
- **Little Dreamyland** (Starmixu & Utaskuas): changes allowed, non-commercial only, **no
  redistribution or resale, even modified**, no AI training. Glazed tiles and the forest. Never commit.
- **plants.zip**: no licence came with it, so it is treated as licensed. Never commit.

`catio/art/CREDITS.md` says which pack drew what. The footer credits them all. Keep it.

## The manor is a floor plan, on two floors

`catio/tools/manor.py` is the plan. It holds rooms as tile boxes with their floor (`ground` or `upper`),
floor texture and back wall; the landing; the craft room's bay; doorways; glass; the stair; and the
grounds. `shell(floor)` draws each floor, in the Storybook Baroque look, from every pack, into
`art/licensed/house.png` and `art/licensed/house-upper.png`: never committed. `grounds()` draws the catio,
the drive, the forest and the garden (`decor.png`). `catio/tools/furniture.py` places every piece of furniture and its stations, and writes
the page's `MANOR` block. The page's `GEOM` comes from that block, so change the plan and the furniture
together, re-run `build-art.py` (or `furniture.py`), and check that `furniture.check()` is empty and no cat
stands on furniture.

**Both floors stand on one grid** (columns 6, 17, 32, 43; rows 3, 13, 24): every upstairs wall stands on a
ground-floor wall, except the ensuite's light partition inside the bedroom's bay. Keep it that way. A wall
off the grid is what made the first draft's walls "not make any sense". Outside walls are ochre limewash
with stucco quoins; inside walls are plaster either side of an oak beam. A doorway is a clean cut: through
a back wall it has a carved oak lintel, through a side wall a darkened threshold. Every room has a back
wall, so a doorway never meets a bare edge. The ground floor alone has the south facade, the pediment
front door and the steps; the library, the lounge and the hall's south strips have stained glass.

`furniture.doors()` lists the doorways as the cats' routes (`MANOR.doors`): each floor's doorways, the
terrace's cat flap, the front door, and the stair as one link from the hall (its foot) to the landing (its
top). The stair piece's `upstairs` stations are its steps.

The layout runs from public to private, the way houses and game levels both do:

- **Downstairs is the cat café.** Café, kitchen and counter, and cat lounge sit across the back. The craft
  room (the shop, its bay window its shop window on the drive, bottom left), the entrance hall (the stair
  and the front door) and the glazed terrace sit across the front. The catio is fenced at the bottom right,
  reached by the terrace's cat flap.
- **Upstairs are her own rooms,** over the back of the house: the library over the café, an open landing
  over the kitchen and hall (the stairwell and the attic ladder), and the bedroom and ensuite over the
  lounge. The craft room and the terrace are single-storey wings.

The stair is in the same place on both floors, so changing floor never moves the camera.

## The UI is made of the packs

The manor fills the screen and is the page, **one floor at a time**. The ground floor stays faded under
the upper one: `S.floor`, `data-floor` on everything, upper pieces lifted by `ZUP`.

- **The page is the KittyChat Cafe** (September 2026: "the harness and UI SaaS that I am making here is
  called the KittyChat Cafe"). The Catio is the page's old name and the code's; the catio is still the
  fenced deck outside.
- **No signs on the map** (she hates them): no room names, badges or stair sign on the art. A room is
  named on hover (`#tip`); a cat that needs her shows its face over its head; the other floor's button
  carries its badge; the brand carries the house's.
- **Floors**: the stair, the floor buttons and Page Up / Page Down go between them. The tally counts both
  floors.
- **Controls**: two sets sit on screen, and nothing else should:
  - the brand (`#houseBtn`, top left: ToffeeCraft's cat-face bubble, the name and a badge when cats need
    her), which is the House button: its menu holds what belongs to the whole house (whether the cats are
    live, the brain, house rules, Edit rooms, the attic, Check now and sound);
  - the corner row (`#controls`: the floor arrows, zoom in and out, whole house), the pack's square
    buttons with its icons, no panel and no words.
- **The status sign** under the brand shows only when something is wrong. When Claude's saved copy fills
  in for a blocked live read, it is one line ("Saved copy · 17:02") and the why shows on hover or focus.
- **Breeds and file counts** on cats show only inside a room (`.stage.inroom`).
- **Room controls**: a control for one room or cat goes in its menu.
- **The camera is free**: drag to pan (left, right or middle button, or Space), wheel or pinch to zoom,
  + / − / 0 and Shift+arrows. `S.focus` is the room that fills the view, and bubbles speak there.
- **Hover names a thing** in a line (`#tip`). **A click opens its menu** beside it, pinned until a click
  elsewhere or Escape (`toggleMenu`); a tap does the same. Keyboard focus opens a menu only when
  `:focus-visible`, and a click never closes a menu keyboard focus opened.
- **Every menu has the same shape, as short as it can be** ("make the menus less bloated and minimize
  noise", September 2026):
  - the name, with a badge when cats need her, and one line under it (no captions, no chips);
  - what matters now, if anything does: the cats that need her (three at most), a queen's said note, a
    cat's ask;
  - the actions as a list (`mi()` in `list()`), the first the default (`.primary`), the pack's triangle
    (`pointer.png`) beside the one under the pointer or focus.

  Keep to that: a new action is a list item, and only if it earns its place. A card (dialog) puts what she
  came for first and folds the rest (a cat's facts, management, name and title under Manage).
- Hover means the pointer really moved onto the thing (`moved()`). When the camera moves or a dialog
  closes, the room that slides under a still pointer isn't named until she moves.
- **Cats walk** when their place changes: through the doorways to a new room, up the stair to nap in the
  attic (to the landing's ladder when they're upstairs), down it when they come back, and in by the front
  door when they're new. A journey that changes floor starts at the stair on the floor they're going to.
  Working cats wander a little. A cat's element must be in the page before `walk()` starts. With reduced
  motion, and for four seconds after the page opens, cats are simply in their places.

The interface is Cup Nooble's Sprout Lands UI pack, cut by `build-art.py` into
`art/licensed/ui/`. Menus, dialogs, the sign and the screen's frame are its tan panel; buttons are
its cream square button (white on hover, pressed in when held; `green` and `pink` are recoloured
copies); inputs are its grey pressed-in button; speech bubbles and a cat's ask are its grey bubble;
a filing cabinet's project sits in its pressed cream well; rooms and cabinets light up with its
white selection brackets (on a room they stay one size on screen at any zoom), and so does the
chosen room on the Edit rooms plan, which sits in its picture frame with its arrow, on its white
button, pointing into the room new cats come in to. Each is a 9-slice `border-image`. The mood faces are its cat emoji
(`faces.png`, in `MOODS` order, then a queen's heart eyes), the sound control is its toggle, the
sign's tick and cross are its own, a queen's crown is its crown icon gilded, what she keeps is
starred with its stars, and the pointer is its cat paw. Keep it that way: a new control should
reuse one of these pieces rather than a CSS border or gradient. The controls' icons are its white icons
recoloured to its outline brown (`icons.png`: plus, minus, house, chat, gear, check, cross), the menus'
cursor is its cream triangle (`pointer.png`), and the logo is ToffeeCraft's Cat UI cat-face bubble
(`logo.png`). `--u` is one art pixel on screen
(2px, or 1px on phones); the scene's overlay (room tags, bubbles) is drawn at one art pixel a
pixel.

Titles, labels, buttons and names use the pack's pixel font (`--pixel`, `sprout.ttf`) at **18px**,
where one font pixel is one screen pixel (36px for a cat's name on its card); anything else blurs.
It has capitals only (small letters draw as capitals), so body text stays in Nunito.
`build-art.py` adds the accents French names need (à â ä ç é è ê ë î ï ô ö ù û ü ÿ, a middle
dot, an ellipsis, curly quotes); other symbols fall back to Fredoka.

## Data

The artifact database, written by the page and seeded with `ArtifactData`:

| Collection | Document | Holds |
|---|---|---|
| `rooms` | one per room key (`garden` (the catio), `kitchen`, `dining`, `living`, `sunroom`, `study`, `bedroom`, `bath`, `hall`) | `name`, `blurb`, `repos[]` (repo names or `owner/repo`), `catchAll` |
| `sessions` | the Claude Code session id | `name`, `room`: her rename or move of one session's cat |
| `cats` | generated id | an adopted chat: `title`, `link`, `project`, `room`, `mood` (`needs` / `busy` / `done`), `note`, `name` |
| `projects` | the project's slug (repo name, or an adopted chat's project) | `name`, `coat`: the look every cat of that project shares, set from a filing cabinet |
| `graphs` | the repo's slug | its project map from graphify, saved by the catio skill's `graph_doc.py`: counts, the map, hubs, groups, surprises and questions a cat can be asked; shown in the filing cabinet |
| `queens` | the room key | the room's queen: `name`, `notes[]` of `{text, pinned, at}`. A pinned note is one she says out loud in her room |
| `snapshot` | `sessions` | `{at, savedBy, sessions[]}`: Claude's saved copy of `list_sessions`, shown when the live read is blocked. Written only by Claude, with `ArtifactData` |

Room **geometry** (where each room is on the art and where its cats sit) is code, in `GEOM` in
the page, because it is tied to the picture. Room **names and which projects live where** are
data. Don't hardcode those.

**Every room has a queen** — one cat who is not a session, never leaves, and keeps what matters
in that room. She sits on `GEOM[room].queen`, the seat held back from `spots` for her, so adding
one to a room means taking a seat out of `spots`, not inventing a coordinate. She is deliberately
outside `allCats()`: she is never in `VIEW.cats`, never in a pile, never in the filing cabinets
and never counted by the sign, because she is not work to be done. What she keeps is hers alone;
a note she is *saying* (`pinned`) becomes her line in the menus and a bubble in her room. Keep her
out of the counts if you touch this — a queen that inflates "3 need you" makes the sign a liar.

Adopted chats can hold anything she types, including legal matters. They live only in the
artifact database, never in this repo. The adopt form says so. The same goes for what a queen
keeps: her card carries the same warning.

## The harness (KittyChat)

`harness/` is the harness behind the page (see `harness/README.md`): the `kittychat-house-rules`
plugin (hooks: preflight before any browser, a read-only ponytail audit to open a session, a nudge to
ship unpushed work; the `catio` skill) and `harness/mcp/catio_mcp.py`, the Catio MCP server other
agents join through. The rules are `harness/rules.json`; Claude seeds them into the `rules` collection.

The page now **writes** through Claude Code Remote, always on an explicit action:

- **The brain**: files dropped on a cat, a room or the house go to `assets.upload` and a `brain/<id>`
  document (`name, type, size, asset, url, cat, kind, project, room, how, reason, note, status`
  `unsorted | waiting | pushed | picked`). `route()` sorts: the cat dropped on, a session/chat link in
  the file, a keyword score, then the sorter (`sample.json` in claude.ai; an OpenAI-compatible endpoint
  on localhost, `localStorage` `catio.sorter`), else the tray.
- **Posting into a session**: `create_trigger` (poke-only, `persistent_session_id`, kept in
  `sessions/<id>.trigger`) then `fire_trigger` with the text. `[Catio] Delivery…`, `[Catio] Charlotte
  says: …`, `[Catio] Request: wrap_up`. Refused calls go to `outbox/<id>` (`status: queued`, `why`)
  for the concierge to deliver; the session's own catch-up (catio skill) also finds them.
- **Talking**: `notes/<id>` `{cat, text, author: charlotte|session|agent, at, via}`; replies show live.
- **Managing**: `set_session_title`, `interrupt_session`, `archive_session` (+ `delete_trigger`),
  `unarchive_session`, `create_session` (New cat, model from `rooms/<k>.model`).
- **Agents**: `host:catio` `list_agents`, `comment`, `drop_file`, `manage` (on localhost, `/api/*` when
  served by `catio_mcp.py --serve`). Breeds: the model's letter on each cat.
- `audits/<repo slug>` `{repo, at, by, summary}` shows in the filing cabinet.

Capabilities for the next publish (full set, replacing the stored one):
`{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions","create_trigger","fire_trigger","delete_trigger","create_session","set_session_title","archive_session","unarchive_session","interrupt_session"] }, { server: "host:catio", tools: ["list_agents","drop_file","comment","comments","manage"] }] }, db: {}, assets: {}, sample: {} }`

Still to do: the refurbished-manor art (needs the CosyCabin, Garden Castle, Wood Garden and
CatMegaFree zips), furniture as sprites with a renovation mode, and cats placed by state at stations.

## Live sessions

The page calls `list_sessions` (limit 50) through the `mcp` capability as the viewer. Its write
tools are the harness's, above, and only ever run on her click or drop. Don't add `mine: true`: a page has no calling session, and that flag can
error without one. Every connector error code has its own message in `problem()`.

claude.ai can refuse the page's read (`approval_required`: the tool asks before every call,
which a page can't do; `blocked_by_policy`). Claude Code Remote is a built-in connector: it is
**not** in her Customize → Connectors list, so there is no `list_sessions` switch for her to set
(checked against her settings, September 2026). Don't send her looking for one. The page shows
`snapshot/sessions`. To refresh it, call `list_sessions` (limit 50) from a session, save the
result, run
`python3 catio/tools/save-sessions.py <result>.json`, and write `catio/data/sessions.json`'s
object to `snapshot/sessions` with `ArtifactData` (`set`, pinned with `if_version`). The script
keeps only what the page reads, and accepts the result as the tool returns it
(wrapped in `ccr`).

A Routine, "Refresh the catio", does this every two hours from 07:59 to 19:59 Paris time. It fires
into the Claude Code session it was created from, not a fresh one: a fresh routine session has
neither `list_sessions` nor `ArtifactData`, so it can't refresh anything (tried September 2026).

## Running on localhost

`python3 catio/tools/bundle.py` builds `catio/dist/catio-local/` and `catio-local.zip`: the page
wrapped in a complete HTML document, all the art (licensed included), `data/rooms.json` and
`data/sessions.json`, with a `HOW-TO-RUN.txt`. Any static server runs it (VS Code Live Server,
`python -m http.server`, `php -S localhost:8000`); there is no PHP and no server code. Send her
the zip with `SendUserFile`; Claude can't reach her USB stick.

With no `window.claude` the page uses `localRuntime()`: a database in `localStorage`
(`catio.local.db`), seeded with the rooms from `data/rooms.json` on first run, and
`snapshot/sessions` from `data/sessions.json` on every load. There is no mcp there, so the cats
are the saved copy.

- `catio/data/rooms.json` mirrors the artifact's `rooms`; keep it in step when rooms change.
- `catio/data/sessions.json` and `catio/dist/` are gitignored. Her session titles and the
  licensed art are in them: **never commit either**.

## Checking a change

Run the end-to-end test before every publish:

```bash
sh catio/test/run.sh
```

It loads the page in the same skeleton the Artifact tool publishes, against `runtime-stub.js`
(an in-memory db with live snapshots and the real path rules, plus a sessions feed the test
changes as it runs), and walks: adopting a chat, through in progress and done, to letting it
go; a session going blocked, working, finished, archived and failed; renaming and moving a
cat; a filing cabinet and a project's look; renaming rooms; the room and cat menus by hover,
keyboard and touch; the saved copy when settings block the live read; the no-connector,
no-storage, view-only and phone cases; a copy with none of the licensed art (`.page-noart.html`,
as anyone else's clone is, whether or not this checkout has the packs); and the localhost bundle,
served on port 8791 with its own `data/`. All checks must pass.

Its example data is invented. Never paste her real session list into the stub or the page.

After publishing, check the real database with `ArtifactData`: list `rooms`, and create,
update and delete one probe document in `cats` the way the page does.
