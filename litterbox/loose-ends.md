# Loose ends

## Questions waiting on Charlotte

- **Licences:**
  - `plants.zip`, `Furnitures.png`, `FreeSprites.png` and `free.png` came with no licence file. Who made
    them, and what does the licence say?
  - `Game_UI_Pack_Pastel.zip` (12.5 MB): whose is it, and does its licence allow use in the artifact?
  - Until then none of them go into the build.
- **`Idle.png` and `Box3.png`** in Drive look like ToffeeCraft's Mochi. Are they the same as the ones in
  CatMegaFree?
- **"download", "download (1)" and "download (2)"** in the Drive folder look like macOS `.DS_Store` files.
  Safe to delete?
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
