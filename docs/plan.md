# The KittyChat Cafe: the plan and where it stands

Issue #3: "An AI harness that presents itself as a cat cafe." The Catio (`catio/index.html`, one private
artifact) becomes the harness. Every Claude Code session and every other agent is a cat in a refurbished
manor. Files dropped on the page go to the right cat, and cats can be talked to and managed.

Last updated 29 September 2026. What she has asked for, all in one place: [`requests.md`](requests.md).

## Done (on `main`)

| Part | Where | Checked by |
|---|---|---|
| House-rules plugin: preflight before any browser, a read-only ponytail audit to open a session, a nudge to ship unpushed work, and the `catio` skill | `harness/` | `python3 -m unittest discover harness/test` (15) |
| Catio MCP server for other agents and models (stdio, plus `--serve` with `/api/*` and wake commands) | `harness/mcp/catio_mcp.py` | the same tests |
| The brain: drop on a cat, a room or the house; sorted by target, link, words, then the sorter model; the tray and "File under" | `catio/index.html` | `sh catio/test/run.sh` (97) |
| Posting into sessions: a poke-only Routine per session (`create_trigger`), then `fire_trigger`. Refused posts wait in `outbox/` | page | e2e |
| Talking to a cat (`notes/`, live replies) and managing it (title, pause, wrap up, archive, New cat on a chosen model) | page | e2e |
| Breeds (the model's letter), agent cats through `host:catio`, the house-rules panel, and dragging cats between rooms | page | e2e |
| PR #5 (Sprout Lands interface, queens, rooms redesign) merged | `main` | |

## Blocked on Charlotte

1. **Turn the plugin on.** Add the settings block from `harness/README.md` to `.claude/settings.json`. The
   permission checks refused Claude's own write to it.
2. **Point CLAUDE.md at `docs/`.** Its harness section should link `docs/renovation-mode.md` and this plan.
   CLAUDE.md edits are refused as self-modification, so the links wait for her.
3. **Licences for the new packs** before any of them go in the build: `plants.zip`, `Furnitures.png`,
   `FreeSprites.png`, `free.png`, and `Game_UI_Pack_Pastel.zip`. Sprout Lands Sprites and Little Dreamyland
   are known: non-commercial, credit needed, no redistribution.
4. **The UX spec for renovation mode** from the rooms-redesign session.

## The manor: done (on `main`)

- **The shell**, drawn from Cosy Cabin alone (`catio/tools/manor.py`), and committed as `art/house.png`. It has:
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

## Next

- **Renovation mode**, following `docs/renovation-mode.md` and the rooms-redesign session's UX spec. Layouts
  per room go in `layouts/<room>`, and the default comes from `MANOR.layout`.
- **Upstairs:** cats napping upstairs could sit on the stairs' `upstairs` stations instead of being
  hidden. The older e2e checks expect them hidden, so this is a decision for Charlotte.

## Published

Version 8 went live on 29 September 2026, with the manor, the brain, posting into sessions, the house rules
panel, breeds and cats placed by state. The capabilities are Claude Code Remote (9 tools), `db`, `assets` and
`sample`. `host:catio` can only be declared from the Claude desktop app, so agent cats won't show until it's
published from there. `rooms/brain` and the eight `rules/*` are seeded.

## Publishing again

Files: `art/house.png`, `art/furniture.png`, `art/licensed/furniture.png`, `art/licensed/decor.png`, and the
rest of CLAUDE.md's list. `art/licensed/` now also holds `furniture.png`.

1. Re-read the live artifact.
2. Republish to `artifacts.json`'s URL with the full capabilities listed in CLAUDE.md.
3. Seed `rooms/brain` and `rules/*` with `ArtifactData`.
4. Probe one `brain` document.
5. With her OK, push one test file into a session.
6. Set up the concierge Routine that delivers `outbox/` when claude.ai refuses the page's own posts.
7. Send her `catio-local.zip`.

## Known limits

- **claude.ai may refuse the page's Claude Code Remote calls.** PR #5 found that this built-in connector has
  no switch in her Connectors list. If so, posts queue, and the concierge (still to build) delivers them.
- **The Drive connector returns files inline as base64,** so big zips must be attached in the chat instead.
- **Only the Artifact's owner can reach `host:catio`,** and only in the Claude desktop app.
