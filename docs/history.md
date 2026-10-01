# The KittyChat Café: how it got here

The version-by-version record that used to sit in `docs/plan.md`, moved here word for word on 1 October 2026
so the plan can be a roadmap. Newest decisions win: where this file and `docs/plan.md` or CLAUDE.md disagree,
they are right. The test counts are the ones at the time.

## The harness (29 September)

| Part | Where | Checked by |
|---|---|---|
| House-rules plugin: preflight before any browser, a read-only ponytail audit to open a session, a nudge to ship unpushed work, and the `catio` skill | `harness/` | `python3 -m unittest discover harness/test` (15) |
| Catio MCP server for other agents and models (stdio, plus `--serve` with `/api/*` and wake commands) | `harness/mcp/catio_mcp.py` | the same tests |
| The brain: drop on a cat, a room or the house; sorted by target, link, words, then the sorter model; the tray and "File under" | `catio/index.html` | `sh catio/test/run.sh` (97) |
| Posting into sessions: a poke-only Routine per session (`create_trigger`), then `fire_trigger`. Refused posts wait in `outbox/` | page | e2e |
| Talking to a cat (`notes/`, live replies) and managing it (title, pause, wrap up, archive, New cat on a chosen model) | page | e2e |
| Breeds (the model's letter), agent cats through `host:catio`, the house-rules panel, and dragging cats between rooms | page | e2e |
| PR #5 (Sprout Lands interface, queens, rooms redesign) merged | `main` | |

## The manor: done (on `main`)

- **The shell**, drawn from Cosy Cabin alone (`catio/tools/manor.py`), and committed as `art/house.png`
  (superseded: see the two floors and the merge below). It had:
  - grey stone outside walls and warm stone inside;
  - stone flags in the Great hall;
  - a panelled Library (the brain) behind the hall;
  - a glass conservatory;
  - front steps.
- **Every room furnished, one per commit**, in `catio/tools/furniture.py`:
  1. Great hall: a double stone staircase to the Library door.
  2. Library.
  3. Drawing room.
  4. Kitchen.
  5. Dining room.
  6. Conservatory: plants from plants.zip.
  7. Studio.
  8. Bedroom.
  9. Bathroom.
  10. The catio.

  Each piece has a kind (`essential`, `connected` or `decor`), a layer, a footprint, and **stations**.
  `check()` proves that no station is in furniture or off the floor.
- **The grounds** (`manor.grounds()`, licensed): the drive round a fountain, parterres, the arch gate, the
  pond and trees.
- **The page** draws it from a generated `MANOR` block (`python3 catio/tools/furniture.py`):
  - furniture as atlas cells in the cats' z-space;
  - cats at their state's station, else the nearest free floor;
  - the Library in the room order.

  e2e: 97 passed.

## The manor, two floors (30 September)

Charlotte asked for the copied cabin layout to be scrapped: a manor on two levels, the terrace and cat café on
the ground floor, her own rooms upstairs, the catio at the bottom right, and the Shopify craft room at the
bottom left with a bay window. Then: "the walls don't make any sense", and "it's hideous right now" (the menus).

- **One grid for both floors** (`catio/tools/manor.py`): columns 6, 17, 32, 43; rows 3, 13, 24. Every
  upstairs wall stands on a ground-floor wall, except the ensuite's partition inside the bedroom's bay.
  - Ground: café, kitchen and counter, cat lounge; craft room (with a canted bay), entrance hall (the
    stair, the front door), glazed terrace; the catio outside.
  - Upstairs (her choice, "over the back"): library over the café, an open landing over the kitchen and
    hall with the stairwell and the attic ladder, and the bedroom over the lounge with the ensuite. The
    craft room and the terrace are single-storey wings.
  - Doorways are clean cuts. `art/house-upper.png` is new. `cabin.py` is gone.
- **One floor at a time** on the page. The stair, the floor buttons and Page Up / Page Down switch floors
  without moving the camera. The stair's sign and the floor button carry a badge when the other floor needs
  her. Old and archived cats nap in the attic (hidden, as before).
- **A free camera**: drag to pan (left, right or middle button), wheel or pinch to zoom, + / − / 0,
  Shift+arrows. Zoomed into one room, you're in it and bubbles speak. A controls cluster sits bottom right.
- **Menus**: hover names, a click opens and pins. Each menu has a header with chips, what matters, one
  primary action, and a grid of the rest. House-wide things moved to a House menu, top right. CLAUDE.md's
  "no toolbar" and "hover opens a menu" rules are lifted at her request.
- Rooms' default names follow the house: Café, Cat lounge, Terrace, Entrance hall, Ensuite. e2e: 115 passed.

## Versions 9 to 11 merged into the two floors (30 September)

Versions 9 to 11 went live from a parallel session's branch (`claude/amazing-bohr-1sfkqi`), on the old
one-floor house. Her choice: merge and keep both, in the Baroque look, on the two-floor grid.

- **Version 9, the storybook Transylvanian Baroque manor**, redrawn on the grid. Ochre limewash with stucco
  quoins outside; plaster either side of an oak beam inside; carved oak lintels over back-wall doorways; a south
  facade with a pediment front door and steps on the ground floor only; stained glass in the library, the
  lounge and the hall's south strips. It mixes every pack, so both floors are licensed art now
  (`art/licensed/house.png`, `house-upper.png`), never committed. `build-art.py` takes nine zips.
- **Version 10, project maps**: each filing cabinet shows the project's graphify map from `graphs/<repo>`,
  and its questions ask a cat.
- **Version 11, walking cats and livened grounds.** Cats walk through the doorways (`MANOR.doors`, with the
  landing as a node upstairs), up the hall's stair to the attic and down it again, to the landing's ladder
  when they're upstairs, and in by the front door. The spruce forest, lamp posts along the drive, the
  fountain, the well and the pond came across. Emblems are gone: coats alone tell projects apart.
- **Not carried over:** the outdoor KittyChat Café terrace (the café is indoors now, with the glazed terrace;
  a parterre stands before the bay instead), and version 11's hover-steal delay (a click opens a menu now).

## Version 13: the KittyChat Café, quieter (30 September)

Charlotte: "Take everything about the UI and make it better… make the menus less bloated and minimize noise.
Redesign the UI using the licensed packs too", and "I hate the signs on every room and the large The Catio
name when really the harness and UI SaaS that I am making here is called the KittyChat Café."

- **The name**: the page is the KittyChat Café. The brand, top left, is ToffeeCraft's Cat UI cat-face bubble
  and the name on the pack's cream button; it is the House button and carries the badge. The big title panel
  and the separate House button are gone.
- **No signs on the map**: no room names, badges, stair sign or Files tag. Rooms are named on hover; a cat that
  needs her shows its face; the other floor's button carries its badge. Breeds and file counts show only
  inside a room.
- **Controls**: the pack's square buttons with its icons (new `icons.png`: its white icons in its outline
  brown), no panel and no words.
- **Menus**: a name and one line, what matters now, then a list of actions with the pack's cream triangle
  (new `pointer.png`) as the cursor. Captions, chips and the green primary grid are gone; the House menu
  opens with whether the cats are live.
- **Cards**: a cat's card leads with the conversation, and folds its facts, management, name and title
  under Manage. A queen's notes save as they change (the UI audit's data-loss finding). Shorter explainers.
- **The status sign** only shows when something is wrong, and when Claude's saved copy stands in it is one
  line ("Saved copy · 17:02") with the why on hover or focus.
- `build-art.py` cuts `icons.png`, `pointer.png` and `logo.png` (the logo from CatMegaFree, so the full
  nine-zip build writes it). e2e: 125 passed, updated for the quiet map and the folded card.
- Published as version 13 from `claude/great-gauss-pgs8nq`, after reading version 12 in full. Capabilities
  carried over. Checked after: the ten `rooms` intact; a probe cat created, updated and deleted.

## Version 14: the Game UI Pastel pack (30 September)

"Use the Game UI Pastel pack anyway." Its licence was inside the zip after all: SC_siosio's Game UI Pack – Pastel
Edition, personal and commercial use, the credit "Game UI Pack created by SC_siosio" required, no redistribution
even modified. It is smooth 500 px art, so `build-art.py` pixelates the icons it needs onto the page's grid
(`pastel.png`) instead of mixing two styles: the corner controls (floor arrows, zoom, and Sprout Lands' house
recoloured to match, replacing version 13's `icons.png`), a cat's Pause, Resume, Wrap up, Archive and Unarchive,
and the lock on enforced house rules. The footer carries the credit. The zip is 12.5 MB, over the Drive
connector's limit, so she attached it in the chat. e2e 125 passed.

## What went live, version by version

**Version 18** went live on 1 October 2026: the `send_message` trial. `postToSession()` calls Claude Code
Remote's `send_message` (argument names from its schema), and what it can't post waits in `outbox/` with the
error. The declaration was passed in full for the first time since version 8: Claude Code Remote's
`list_sessions`, `send_message`, `delete_trigger`, `create_session`, `set_session_title`, `archive_session`,
`unarchive_session` and `interrupt_session` (the Routine tools dropped), `db`, `assets` and `sample`. A dialog
redrawn while its note shows now keeps the note. e2e 158 passed. Checked after publishing: a probe in `cats`
created, updated and deleted. A test session, "KittyChat test cat", was started for the trial, and
`snapshot/sessions` refreshed so it shows.

**Version 17** went live on 1 October 2026: phase 0 of `docs/plan.md`. Posts into a session no longer bind a
Routine (which started a stray session and never delivered): they wait in `outbox/` and the page says so. Old
review-ready cats nap in the attic, and the warm-start session is not a cat. Errors stay until dismissed, the
sorter times out, there is a Still cats switch, and the credits sit at the foot of the House menu. The live
page was version 16, read in full first; only `index.html` changed, and the stored capabilities carried over.
e2e 154 passed. Checked after publishing: 41 files, the 10 `rooms`, and a probe in `cats` created, updated and
deleted.

**Version 16** went live on 1 October 2026: the page renamed KittyChat Café, with its accent (the title, the
brand, the tab and the notes; `artifacts.json`'s key is now `kittychat-cafe`). The Drive folder keeps its name,
"KittyChat Cafe Assets".

**Version 15** went live on 30 September 2026 (21:58 UTC). It is version 13/14's KittyChat Café with iteration 1's map
panel and minimap in place of the corner row (`docs/camera-and-minimap.md`), and the seven cut pieces in
`art/licensed/pastel/`. The stored capabilities carried over. Checked after publishing: 41 files, the 10 `rooms`, and
a probe in `cats` created, updated and deleted.

Version 8 went live on 29 September 2026, with the manor, the brain, posting into sessions, the house rules
panel, breeds and cats placed by state. The capabilities are Claude Code Remote (9 tools), `db`, `assets` and
`sample`. `host:catio` can only be declared from the Claude desktop app, so agent cats won't show until it's
published from there. `rooms/brain` and the eight `rules/*` are seeded.

Versions 9 (the Baroque manor), 10 (project maps, with `graphs/pretty-project-portfolio` and
`rules/graph_first` seeded) and 11 (walking cats, the forest, coats without emblems) went live on
29 September from `claude/amazing-bohr-1sfkqi`, each checked afterwards: the ten `rooms` intact, and a probe
cat created, updated and deleted. That branch is merged here now.

Version 12 went live on 30 September 2026 from `ccr-bfc398ff-3gh5wb`: the two-floor manor merged with
versions 9 to 11 (the Baroque look on the grid, project maps, walking cats up the stair and to the attic
ladder, the forest). The live page was version 11, read in full before publishing. New file:
`art/licensed/house-upper.png`. The capabilities were carried over unchanged. e2e 125 passed. Checked
after publishing: the ten `rooms` intact; `dining`, `living`, `sunroom`, `hall` and `bath` renamed (name
only) to Café, Cat lounge, Terrace, Entrance hall and Ensuite; a probe cat created, updated and deleted.
