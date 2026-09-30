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
- **Should "Rename" on a session's cat rename the real session?** It doesn't: the cat's name and the
  session's title are two different fields on the card.
- **Should a filing cabinet ever leave its room** in renovation mode?

## Ideas not built yet

- **Routines are paused (2026-09-30), at Charlotte's request: not enough usage to run them daily.** "Refresh
  the catio" and "Catio: hourly audit and queens pass" are both disabled. Refresh `snapshot/sessions` by hand
  when she asks. Don't re-enable either or add new scheduled ones.
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
- **Posting into a session through a bound Routine doesn't reach it** (tried 2026-09-30): `create_trigger` with
  `persistent_session_id` set to an existing session, then `fire_trigger`, started a *new* session titled
  "⚡ <routine name>" with no repo, and the target session never saw the text. `postToSession()` and the
  concierge idea both rest on this, so posts stay queued in `outbox/` until another way is found. Deleting the
  Routine deletes the stray session with it.
- Review-ready cats never go upstairs: `STALE_DAYS` only moves sleeping ones. Month-old Remote Control
  sessions keep the sign's "need you" count high.
- The warm-start placeholder session (`__warming__`, tag `cowork-warm-start`) shows up as a cat to review.

## From the manor build

- CLAUDE.md still describes the cabin: its publish file list, "The cabin is a floor plan", and the old
  capabilities. Claude can't edit CLAUDE.md (it's refused as self-modification). `docs/plan.md` has the new
  file list, and the MANOR block is described in `catio/tools/furniture.py`'s docstring.
- `catio/tools/cabin.py` is no longer used by the build. It stays for now as the old plan; delete it when
  nothing needs it.
- The rooms keep her own names from the database ("Living room", "Sunroom", "Craft room", "Hall"). The manor's
  defaults ("Drawing room", "Conservatory", "Studio", "Great hall") only show when a room has no saved name.
  She may want to rename them in Edit rooms.
