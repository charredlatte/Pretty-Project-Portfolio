# Loose ends

## Questions waiting on Charlotte

- **Licences:**
  - `Furnitures.png`, `FreeSprites.png`, `free.png`, `Idle.png` and `Box3.png` turned out to be ToffeeCraft's,
    from inside CatMegaFree: settled.
  - `plants.zip` is used, as she asked, and treated as licensed. **Who made it**, for the credits and the
    footer?
  - `Game_UI_Pack_Pastel.zip` (12.5 MB): whose is it, and does its licence allow use in the artifact?
  - Until then Game UI Pastel stays out of the build.
- **"download", "download (1)" and "download (2)"** in the Drive folder look like macOS `.DS_Store` files.
  Safe to delete?
- **Her MCPmarket plugin zip** (`mcpmarket-plugin-me-claude.zip`, the Game UI / UX skill) has her live API
  token in `.mcp.json`. It must never be committed. Since it has been passed around, she may want to rotate
  it at mcpmarket.com. Its hooks sync with and report skill use to mcpmarket.com, so it wasn't installed here:
  its `ui` skill was only read.
- **Should "Rename" on a session's cat rename the real session?** It doesn't: the cat's name and the
  session's title are two different fields on the card.
- **Should a filing cabinet ever leave its room** in renovation mode?

## Ideas not built yet

- **The concierge.** A small session plus an hourly Routine that reads `outbox/` with `ArtifactData` and
  delivers each post with `create_trigger`/`fire_trigger`. It's needed only if claude.ai refuses the page's
  own calls. Hourly is the Routine minimum, so this is slower than a direct push.
- **Seed `rules/*` from `harness/rules.json`** with `ArtifactData` at the next publish, with an `order` field
  set from the list position.
- **`save-sessions.py`** should keep `environment_id` and the model fields. Then the saved copy shows breeds,
  and New cat can pick an environment when the live read is blocked.
- **`bundle.py`** should put `catio_mcp.py` and `rules.json` in the localhost folder, with `HOW-TO-RUN.txt`
  covering `--serve`.
- **The marketplace** could list PR #5's `catio-plugin/` next to `kittychat-house-rules`.
- **Audits.** The page shows `audits/<repo>` in filing cabinets; nothing writes them until the plugin is on.

## Facts learned the hard way

- `host:` MCP servers work only in the Claude desktop app, and only for the artifact's owner.
- Write-tool failures that come back as `server_unavailable` or `upstream_error` are ambiguous: the tool may
  have run anyway. The page queues these rather than retrying.
- `ArtifactData` `where` on a nested field (`target.id`) may not be supported. Brain documents keep a flat
  `cat` field for queries.
- The e2e stub only includes agent cats with `?agents=1`, so the older checks' counts stay as they were.

- The Drive connector *can* hand over the zips: an oversized result lands in a tool-results JSON file, and
  base64-decoding its `content` field gives the zip. Checked with all nine packs, up to 2.6 MB.
- Little Dreamyland is by **Starmixu & Utaskuas**. Its licence: modifying allowed, non-commercial only, no
  redistribution or resale even modified, and no NFTs or AI training. Credit: "Assets from Little Dreamyland by
  Starmixu & Utaskuas."

## From the manor build

- CLAUDE.md says `art/house.png` is committed and gives the six-zip build command. Since the retexture the house is
  `art/licensed/house.png` (never committed) and `build-art.py` takes nine zips; its publish list needs the new path.
- CLAUDE.md's publish list still names `emblems.png`, and its `projects` row still has `emblem`. Emblems are gone
  (29 September): the page no longer uses them, `build-art.py` no longer makes them, and the next publish drops
  `art/licensed/emblems.png`.
- CLAUDE.md still describes the cabin: its publish file list, "The cabin is a floor plan", and the old
  capabilities. Claude can't edit CLAUDE.md (it's refused as self-modification). `docs/plan.md` has the new
  file list, and the MANOR block is described in `catio/tools/furniture.py`'s docstring.
- The rooms keep her own names from the database. With the two-floor manor, the names that no longer fit
  ("Dining room", "Living room", "Sunroom", "Hall", "Bathroom") are renamed at publish, with only `name`
  changed, to Café, Cat lounge, Terrace, Entrance hall and Ensuite. She can rename them back in Edit rooms.

## Merging version 11 into the two-floor manor (in progress, 30 September)

Version 11 (branch `claude/amazing-bohr-1sfkqi`: Baroque retexture, walking cats, project maps, livened
grounds) is merged into `ccr-bfc398ff-3gh5wb`. Her choice: keep both, in the Storybook Baroque look, on the
two-floor grid; fold the outdoor KittyChat Cafe into the indoor café and terrace. The plan is the "Merge
with the live version 11" section of this session's plan; each step is pushed as it lands:

- [x] 1. Merge commit: conflicts resolved to this branch's side (page, tests, manor, furniture, build-art,
  README, docs/plan.md). Their harness, docs and litterbox came in as they were.
- [x] 2. manor.py: the Baroque look on the grid (ochre and quoins, plaster and oak inside, stained glass,
  facade and pediment door on the ground floor), and their grounds (forest, lamps, fountain, well, scatter).
- [x] 3. build-art.py: nine zips; both floors go to art/licensed/ (no longer committed).
- [x] 4. furniture.py: doors() for both floors, the stair's upstairs stations.
- [x] 5. index.html: walking cats (with floors), project maps, emblems gone, credits.
- [x] 6. Tests: their map check and walking section, adapted.
- [x] 7. Docs.
- [ ] 8. Verify, screenshots.
- [ ] 9. Publish (read the artifact first; it was version 11).

Loose ends from the merge:

- Version 11's hover-steal checks (its test section 6d: a menu following a resting pointer to the next
  room) are dropped. Menus open on a click now, so there is nothing to steal; the walking checks are 6d.
- The outdoor KittyChat Cafe terrace is gone from the grounds: the café is indoors now, with the glazed
  terrace beside the lounge. A parterre stands before the bay instead.
- The parallel session that made version 11 still exists. Its branch is merged here, so a publish from
  that session would overwrite this one with the one-floor house. Publish from this branch only.
- A cat's walk used to start before its element was in the page and gave up on the first step, so a cat
  brought back from the attic stayed "walking" for ever. Fixed; the test for it is in 6d.
