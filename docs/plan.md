# The KittyChat Cafe: the plan and where it stands

Issue #3: "An AI harness that presents itself as a cat cafe." The Catio (`catio/index.html`, one private
artifact) becomes the harness. Every Claude Code session and every other agent is a cat in a refurbished
manor. Files dropped on the page go to the right cat, and cats can be talked to and managed.

Last updated 29 September 2026.

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

## Next: the manor, one room at a time

Every room is its own small step. Each step:

1. Plan the room in `cabin.py`: floor, wallpaper, glass, doorways.
2. Place its furniture as pieces (with a kind: `essential`, `connected` or `decor`) and its **stations**.
3. Render the room alone, look at it, and adjust.
4. Commit.

A room is only done when it reads right at 1x and 2x, and no station sits on a footprint.

- **A. Inventory: done.** Every pack is unpacked and has numbered contact sheets. Cosy Cabin alone has
  stone walls, stone facings, panelling and stone floors, so the shell can be committed. ToffeeCraft's
  `Furnitures.png` (cat beds, posts, bowls) supplies the stations.
- **B. The shell: done** (`catio/tools/manor.py`, `shell()`): a stone shell (Cainos walls) around a
  Cosy Cabin interior.
  - The existing room keys stay the same, so her renames, moves and filing carry over.
  - One room is new: `brain`, the Library.
  - The rest become the Great hall (`hall`), Kitchen, Dining room, Drawing room (`living`), Conservatory
    (`sunroom`), Studio (`study`), Bedroom, Bathroom, and the Walled catio (`garden`).
- **C. Rooms, one per step, in this order:**
  1. Great hall: the front door, the grand stairs (where cats nap upstairs), the house rules on the wall.
  2. Library, the brain: bookcases, the big desk, the drop tray.
  3. Drawing room.
  4. Kitchen.
  5. Dining room.
  6. Conservatory.
  7. Studio.
  8. Bedroom.
  9. Bathroom.
  10. Walled catio.
  11. Grounds: the drive, the parterre, the fountain, the gate.
- **D. Wire it into the page.**
  - `WORLD` and `GEOM` (room boxes only) come from the plan.
  - Furniture becomes sprites drawn from atlases, in the cats' z-space.
  - **Stations**: a cat's place shows its state:
    - working at a desk or table;
    - needs you at the door mat;
    - to review by its filing cabinet;
    - failed on the rug;
    - asleep in a basket or on the sofa;
    - archived up the stairs.
  - Queen seats and cabinets come from the layout.
- **E. Renovation mode**, after the UX spec, following `docs/renovation-mode.md`.

## Then: publish

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
