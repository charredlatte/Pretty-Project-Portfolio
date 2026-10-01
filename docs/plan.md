# The KittyChat Café: the plan

Issue #3: "An AI harness that presents itself as a cat cafe." The KittyChat Café (`catio/index.html`, one
private artifact) is the harness. Every Claude Code session and every other agent is a cat in a two-floor
manor. Files dropped on the page go to the right cat, and cats can be talked to and managed.

Last revised 1 October 2026, after the audit in `docs/audit-2026-10-01.md`. How it got here, version by
version, is in `docs/history.md`. What she has asked for is in `docs/requests.md`.

## Where it stands

- **Live:** version 17, published 1 October from `claude/dreamy-goldberg-iu6w6l`: phase 0 on top of the
  KittyChat Café:
  - the brand is the House button;
  - quiet maps and short menus;
  - Game UI Pastel pixel icons;
  - the map panel and minimap.
- **Tests:** e2e 154 passed; harness 18 passed; `furniture.check()` empty.
- **`main`** has version 16 (PR #7) and the digest of her sessions (`catio/tools/digest.py`, PR #8). Phase 0
  is on `claude/dreamy-goldberg-iu6w6l`, with `main` merged in, waiting for its pull request.
- **Phase 0** is done and live (version 17), except what waits on her: the `send_message` trial and deleting
  the old branches.

## The roadmap, in order

Each phase ends with the e2e test green, screenshots at 1440×900 and 390×844 in light and dark, a commit, and
(when she says so) a publish by the checklist below.

### Phase 0: make what's there honest (from the audit). Done, live in version 17

The page shouldn't say "Sent." when nothing arrived, or "3 need you" when they don't. This comes before
anything new.

1. **Posting into sessions** (audit finding 1). Today it creates stray sessions and never delivers.
   - Done: Routines are no longer bound. Every post goes to `outbox/` with `why: "no_route"`, and the
     toast says it's waiting.
   - Declare Claude Code Remote's `send_message` and, with her OK, try it once on a test session. If it
     posts into the session, `postToSession()` uses it, and the outbox is only for refusals.
   - Done: the e2e checks expect the outbox.
2. **Honest counts** (finding 2). Done.
   - Review-ready cats older than `STALE_DAYS` nap in the attic.
   - Sessions tagged `cowork-warm-start` are not cats.
3. **The UI audit's leftovers** (finding 3). Done, except the small Nunito text, which waits for phase 4's
   look at the bubbles.
   - Errors and "queued" messages stay until dismissed (`role="alert"`).
   - The sorter times out after about 8 s, Send turns on as soon as the keyword guesses are in, and skipped
     files are named.
   - Bubbles leave the Tab order.
   - A "Still cats" switch in the House menu.
   - Darker placeholders.
   - The credits line also at the foot of the House menu, so phones show it (finding 6).
4. **Housekeeping** (findings 4, 5, 10). Done, except deleting the old branches.
   - A pull request from this branch to `main` (versions 13 to 16 went in with PR #7). Then, with her OK,
     delete the 14 old branches, so none can publish over the live page again.
   - Bring `catio-plugin/` and the README up to the manor (ten zips, no `cabin.py`).
   - Small fixes:
     - add graphify's `LICENSE-MIT`;
     - `save-sessions.py` keeps `environment_id` and the model;
     - `bundle.py` ships the Catio MCP server;
     - put the litter box with the missing art (`docs/from-the-litterbox.md`).

### Phase 1: the map panel and minimap. Done (version 15)

The smooth Game UI Pastel panel, top right: zoom, whole house, the fold (M), the minimap (click, drag,
double-click, wheel) and the floor tabs. See `docs/camera-and-minimap.md`, iteration 1.

### Phase 2: the camera

The Sims build-mode camera, from `docs/camera-and-minimap.md`, iteration 2:
- WASD and the arrow keys pan, with acceleration (the arrows still walk between rooms after a Tab);
- zoom settles on crisp steps;
- a flick glides;
- `F` frames the selection and `Home` shows the whole house;
- a switch in the House menu turns off the letter keys.

It comes before renovation mode, which needs it: in renovation mode a drag moves furniture, so the keys are
how she pans.

### Phase 3: renovation mode

Move the furniture, add and remove the decorative pieces, and choose what each room's filing cabinet looks
like. The full spec is **`docs/renovation-mode.md`**. In short:

- **Getting in and out.** A Live / Build switch on the map panel, or Renovate in the House menu. Leaving
  Build saves nothing new; every change was saved when it was made.
- **While it's on:**
  - cats step aside and menus and bubbles are off;
  - a 16 px grid shows;
  - Game UI Pastel's catalogue bar runs along the bottom.
- **Moving furniture.** Drag a piece; it snaps to the grid and is saved on the drop.
  - Without dragging: select a piece, move it with the arrows, or choose Move to… (WCAG 2.5.7).
  - A piece can't be dropped on another piece's footprint, outside its room's floor, or where it would
    cover a doorway.
- **What can move, by kind** (`furniture.py`):
  - **essential** pieces never move: the stair, the front door mat, the brain's desk;
  - **connected** pieces (those with a station: desks, cushions, armchairs, rugs) move but can't be removed;
  - **decor** pieces move, and can be stored in the catalogue and brought back.
- **Filing cabinets** (her decision): one per room. It moves only within its room, and she picks what it
  looks like from any floor piece. It keeps its Files and its review spot whatever it looks like.
- **Undo and redo** for the session in Build; **Reset room** puts back `MANOR.layout`.
- **Cats follow the furniture.** Stations and free floor are worked out again from the new layout, so no
  cat sits in furniture. Queens keep their seat's piece.
- **Data:** `layouts/<room>` in the database (`{pieces: [[key, x, y], …], cabinet: {look, x, y}}`), in the
  stub, in `localRuntime()` and in `data/`. No document means `MANOR.layout`.
- **Steps:**
  1. Layouts as data, read from the database (no editing yet).
  2. The mode with move, snap, undo and the keyboard.
  3. The catalogue with store and bring back, and the cabinet's "Looks like…".
  4. Phones: editing inside a zoomed-in room only.

  Each step is its own commit with its checks.

### Phase 4: art and sound

From `docs/from-the-litterbox.md` (Ideas not built), as she buys, finds or approves:
- a walk cycle (ToffeeCraft's paid Pochi pack), which also brings real coat colours;
- a litter box;
- Baroque pieces (shutters, a balustrade, cobbles);
- café props (an espresso machine, cakes, a chalkboard);
- sounds once she has found them.

Each pack's licence is checked before it goes in, and credited in the footer and `CREDITS.md`.

### Phase 5: the rest of the harness

- **The house-rules plugin turned on** (her step). Then sessions write `audits/<repo>` and pick up the
  `outbox/` on catch-up.
- **The concierge**, only if `send_message` can't be called from the page: a session plus a Routine that
  delivers `outbox/` from Claude's side. The Routines are paused at her request, so this waits for her.
- **Agent cats in claude.ai** need `host:catio` declared, which only the Claude desktop app can do.
- **List `catio-plugin/` in the marketplace** next to `kittychat-house-rules`.

## Waiting on Charlotte

1. Rotate the MCPmarket token in her plugin zip's `.mcp.json`.
2. Turn the house-rules plugin on (`.claude/settings.json`, from `harness/README.md`).
3. OK a one-message test of `send_message` on a test session (phase 0). It needs a publish that declares it.
4. OK deleting the 14 old branches once `main` has version 15 (phase 0).
5. Who made `plants.zip`, for the credits.
6. Whether "Rename" should also rename the real session.
7. Whether cats napping in the attic should sit on the stairs instead.
8. Whether to delete the `download` files (`.DS_Store`) in the Drive folder.

## Publishing

1. `sh catio/test/run.sh`: everything passes.
2. Read the live artifact in full (`Artifact` read, then every line of the saved file), and compare it with
   the branch's page. If it's newer, merge it first, never overwrite it.
3. Publish `catio/index.html` to `artifacts.json`'s URL with only the files that changed, and **omit
   `capabilities`** to keep the stored set (Claude Code Remote's nine tools, `db`, `assets`, `sample`). Pass
   `capabilities` only to add a tool on purpose, as phase 0 will for `send_message`.
4. Afterwards: list the files, list `rooms`, and create, update and delete one probe in `cats`.
5. Add a line to `docs/history.md`.

## Known limits

- claude.ai may refuse the page's Claude Code Remote calls. Claude Code Remote is built in, so there is no
  switch in her Connectors list. Refused posts wait in `outbox/`.
- The Drive connector hands over files up to about 10 MB. Bigger zips (Game UI Pastel, 12.5 MB) are attached
  in the chat.
- `host:catio` works only in the Claude desktop app, and only for the artifact's owner.
- Write-tool failures that come back as `server_unavailable` or `upstream_error` may have run anyway. The page
  queues these rather than retrying.
