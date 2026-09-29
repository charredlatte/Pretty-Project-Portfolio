# The Catio: operating brief

`README.md` says what the page is. This file is how to work on it.

## Republishing

The page is **one** private artifact. Its URL is in `artifacts.json`. Always republish to that
URL (`Artifact` publish with `url`, after reading it back), never a new one: the database with
her rooms, renames and adopted chats belongs to that artifact.

Publish `catio/index.html` with:

- `files`: every file the page references: `art/house.png`, `art/licensed/*.png` (`decor.png`,
  `meadow.png`, `emblems.png`, `mochi-idle.png`, `mochi-box.png`, `pochi.png`) and the interface
  in `art/licensed/ui/` (`panel`, `button`, `button-hover`, `button-down`, `button-green`,
  `button-pink`, `field`, `arrow`, `frame`, `divider`, `bubble`, `bubble-tail`, `corners`,
  `toggle`, `status`, `faces`, `crown`, `stars`, `cursor`, `cursor-point` `.png`, and `sprout.ttf`);
- `capabilities`: omit it on a republish to keep what's stored. The declaration is
  `{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions"] }] }, db: {} }`.

`catio/data/` is **not** published: it is for the localhost copy (below).

`art/licensed/` is not in git (licences below). In a fresh session, get it back one of two ways:

1. `Artifact` read with `path: "art/licensed/<file>"` on the published URL, for each file; or
2. ask Charlotte for the six zips and run
   `python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip Top_down_garden_castle.zip Wood_Garden_Asset_Pack.zip "Pixel_Art_Top_Down_-_Basic_v1.2.3.zip" "Sprout_Lands_-_UI_Pack_-_Basic_pack.zip"`
   (needs `pip install pillow fonttools`). Given only the Sprout Lands zip, it rebuilds just the
   interface.

## Licences: what may be committed

- **Cosy Cabin** (Marie Pepo): copying and modifying allowed, with credit. `art/house.png` is
  committed.
- **ToffeeCraft cats** (free version): personal use only, **no redistribution**. Never commit.
- **Top Down Garden Castle** (Heosphorus): **no distribution, even modified**. Never commit.
- **Wood Garden** (rowdy41): no resale. It is baked into `decor.png` with Heosphorus's
  pieces, so that file stays uncommitted too.
- **Pixel Art Top Down – Basic** (Cainos): free for any project, **no redistribution**. Its
  stonework is also in `decor.png`. It is drawn on a 32 px grid, twice the cabin's, so its
  pieces read large: use it for garden stonework, not indoor furniture.
- **Sprout Lands UI Pack – Basic** (Cup Nooble): modifying allowed, **no redistribution or resale,
  even modified**, non-commercial use only. The whole interface (`art/licensed/ui/`). Never commit.

The footer credits all six. Keep it.

## The cabin is a floor plan

`catio/tools/cabin.py` is the plan: rooms as tile boxes with their floors and wallpapers,
doorways, glass (floor-to-ceiling on back walls, strips on outside walls), and furniture as
`(sprite, x, y)`. `house()` draws it from Cosy Cabin alone (committed as `art/house.png`);
`decor()` adds the catio, the garden and indoor pieces from the other packs (`decor.png`).
The page's `GEOM` (room boxes, cat spots and filing-cabinet boxes) and `WORLD` must match the plan. Change both
together, then re-render and check that no cat stands on furniture.

The layout follows ordinary small-cabin planning: kitchen, dining and living as one open run
facing the light; the sunroom off the living room; bedroom, ensuite and craft room behind; the
bathroom backing onto the kitchen's plumbing; the catio fenced against the sunroom's outside
wall, reached by a cat flap, with shade, shelves to climb and seats for people.

## The UI is made of the packs

The cabin fills the screen and is the page. There is no toolbar or side list: every control
lives in a menu that opens on **hover** over a room (`roomMenu`) or a cat (`catMenu`, `pileMenu`),
placed beside it so it never covers what the pointer is on. Keyboard focus opens a menu only when
`:focus-visible`; on touch the first tap opens the menu and the second acts (`armed()`). A new
control goes into one of these menus, not onto the screen.

Hover means the pointer really moved onto the thing (`moved()`): when the camera moves or a dialog
closes, the room that slides under a still pointer gets no menu until she moves. Without that, a
neighbour's menu opens over the room she just looked into.

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
reuse one of these pieces rather than a CSS border or gradient. `--u` is one art pixel on screen
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
| `projects` | the project's slug (repo name, or an adopted chat's project) | `name`, `emblem`, `coat`: the look every cat of that project shares, set from a filing cabinet |
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
