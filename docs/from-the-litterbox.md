# From the litter box

Notes filed here from the KittyChat Café's litter box by `litterbox/sort.py`. Each ends with the file it came
from. Edit them freely: the sorter only adds, and never files a note that is already here.

## Waiting on Charlotte

### Loose ends › Questions waiting on Charlotte

- **Licences:**
  - `Furnitures.png`, `FreeSprites.png`, `free.png`, `Idle.png` and `Box3.png` turned out to be ToffeeCraft's,
    from inside CatMegaFree: settled.
  - `plants.zip` is used, as she asked, and treated as licensed. **Who made it**, for the credits and the
    footer? *— litterbox/loose-ends.md*

- **"download", "download (1)" and "download (2)"** in the Drive folder look like macOS `.DS_Store` files.
  Safe to delete? *— litterbox/loose-ends.md*

- **Her MCPmarket plugin zip** (`mcpmarket-plugin-me-claude.zip`, the Game UI / UX skill) has her live API
  token in `.mcp.json`. It must never be committed. Since it has been passed around, she may want to rotate
  it at mcpmarket.com. Its hooks sync with and report skill use to mcpmarket.com, so it wasn't installed here:
  its `ui` skill was only read. *— litterbox/loose-ends.md*

- **Should "Rename" on a session's cat rename the real session?** It doesn't: the cat's name and the
  session's title are two different fields on the card. *— litterbox/loose-ends.md*

- **Should a filing cabinet ever leave its room** in renovation mode? Settled 30 September: never, but she
  picks its look in each room (`docs/renovation-mode.md`). *— litterbox/loose-ends.md*

### 1 October 2026: branches that never reached main

- **`claude/catio-gateway-plan`** is the next job's plan. Before landing it, update step 1 for the server's
  localhost-only API. *— litterbox/2026-10-01-branches-cafe.md*

### 2 October 2026: issue #24's round, sifted

- **Four sessions still wait on questions that are settled.** Each can be archived from its cat:
  - the attribution rule's session, which asks about PR #18 (merged);
  - the compress-compile-sort audit, which asks about PR #9 (merged) and which branches to merge (the list is in
    `docs/plan.md`);
  - the MCP integration plan, which waits for a go-ahead on `claude/catio-gateway-plan` (the gateway replaced
    it);
  - the manor retexture, which asks which UI bug to fix next (29 September). *— litterbox/2026-10-02-issue-24-report.md*

- **Her "yes" to letting the adopted chat go was marked delivered, but nothing happened.** The adopted chat still
  points to the same conversation as a session, so it shows as two cats. Her answer stands: Claude deletes the
  adopted chat's `cats` document once she confirms. *— litterbox/2026-10-02-issue-24-report.md*

- **"Which comes first" in `docs/plan.md`'s list is settled.** Issue #24 chose the page reading the gateway, and
  version 21 did it. By the plan's order, phase 2 (the camera) is next. *— litterbox/2026-10-02-issue-24-report.md*

### 2 October 2026: the chat that set up the gateway, moved the café onto it and planned the queen

- **A paid voice for the queen?** The free browser voice is what's built (Chrome or Edge's en-GB voices,
  `speechSynthesis`). A paid one (ElevenLabs or OpenAI) would go through a gateway proxy keyed by a secret;
  the page's `speak()` is one function so it can be a second branch. Her call, later. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Where the runner lives after her PC,** with October 2026 prices (also in `docs/plan.md`, phase 6):
  - Cloudflare Containers next to the gateway: $5/month for Workers Paid plus about 7¢ a working hour; sleeps
    when idle, and its disk empties when it sleeps. Cloudflare's own Claude Code guide uses an API key, so
    her plan's sign-in must be checked there first. Recommended.
  - Hetzner CAX11: €5.99 + €0.50 a month, keeps its files, near her in France.
  - Oracle Always Free ARM: free, 2 cores and 12 GB since June 2026; needs a card, and idle machines are
    reclaimed.
  - A Raspberry Pi: €80–100 once.

  Claude Code needs 4 GB. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Set the CATIO connector's tools to Always allow** (claude.ai → Customize → Connectors) if not done yet:
  otherwise the artifact page's live read asks before every call, and the House menu says so. A session can't
  check it. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Three old messages in the gateway café still carry a "queued" label.** The seven outbox posts were
  delivered from a session after the café's data was copied in, and the agents' key can't edit her data, on
  purpose. Harmless. *— litterbox/2026-10-02-gateway-cafe-queen.md*

### 3 October 2026: owner on the wire, shipped, and what it left

- **A second Worker, `pretty-project-portfolio`, serves `catio/` to anyone.** It appeared at 07:04 UTC and every
  merge to `main` redeploys it, so Cloudflare's Workers Builds looks connected to this repo with no config of its
  own (there is no wrangler file at the root). At its workers.dev address, with no sign-in, it serves the café page
  (`main`'s `catio/index.html`), `art/furniture.png` and `data/rooms.json`. The licensed art, `data/sessions.json`
  and the gateway's routes all answer 404, so everything it serves is already public in this repo, and the page
  there runs on its localhost fallback with nothing in it. Delete it, keep it, or put it behind the sign-in: in her
  homework. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

- **"Don't touch the artifact"** (her rule, 3 October: "I don't want you touching the artifact again. Run
  everything through the cafe's deployed address and the repo"). ~~The artifact stays at version 32.~~: on 4 October she asked for republishes herself (version 33 added `quizzes` and `answer` to the stored capabilities, version 34 the decider-log fix), and later ones followed. Open: whether
  CLAUDE.md records the rule (its Republishing section and post-publish checks still tell sessions to publish),
  whether the catio skill, audits and project maps move off the artifact's database onto the gateway, and whether
  the litter box quiz and decisions quiz count as artifacts too. In her homework. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

- **No line from her has reached the café on its own address since the rename deployed.** The gateway's tests
  cover a note written as `owner`; one real line to the queen from the café would show it end to end. In her
  homework. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

### 4 October 2026: the queen's card, held for her

- ~~**PR #64 is ready and held for her, not merged.**~~: merged on 4 October ("Make this window useable": the queen's card's height). https://github.com/charredlatte/Pretty-Project-Portfolio/pull/64 *— litterbox/2026-10-04-queen-card-held-for-her.md*

- ~~**The café still shows the old card until the page is republished.**~~: folded into the round of 5 October's note on the claude.ai café trailing `main`. Both #62 and #64 only change the
  repository: the artifact at `artifacts.json`'s `kittychat-cafe` keeps the page it was last published with.
  A session with the licensed art (read it back from the artifact, per CLAUDE.md "Republishing") needs to
  publish `catio/index.html` to that URL for any of this to reach her. *— litterbox/2026-10-04-queen-card-held-for-her.md*

### Held for review: charredlatte/Pretty-Project-Portfolio#72

- [x] [charredlatte/Pretty-Project-Portfolio#72](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/72) merged on 4 October; it was held for her review: guesses: none. Left for later and not in this change: run.sh doesn't notice a taken port, and the test list doesn't include the catio-app header build.
  *— litterbox/held-pretty-project-portfolio-72.md, 2026-10-04*

## Ideas not built

### What's missing: art and sound for the Catio

Since 1 October Charlotte is drawing every asset herself: `docs/drawing-plan.md` is the list to work from.
The "buy first" section below is kept for reference only. *— litterbox/assets-wishlist.md*

Everything the Catio shows today, and what it would take to make it what you picture: what to buy, and what
to draw (or commission) because no pack has it. Checked against the packs' itch.io pages on 29 September 2026,
and brought up to date on 30 September (version 12, and the camera and minimap plan). *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › How to draw anything for it

So a piece drops straight in without scaling or blur: *— litterbox/assets-wishlist.md*

- **Tile grid:** 16 px, Cosy Cabin's. A back wall is 32 px tall, and a wall seen from above is a 5 px band. *— litterbox/assets-wishlist.md*

- **View:** three-quarter top-down. You see the tops of things and their south faces. *— litterbox/assets-wishlist.md*

- **Light:** from the top left. Highlights go on the top and left edges, shade on the bottom and right, and
  the drop shadow falls to the south-east. *— litterbox/assets-wishlist.md*

- **Cats:** 32 × 32 frames with the feet at the bottom middle (Mochi's size), or 64 × 64 (Pochi's size).
  Keep one size for every cat. *— litterbox/assets-wishlist.md*

- **Palette:** Sprout Lands' creams and tans for anything near the interface: `F3E5C2`, `E8CFA6`, `C49A6C`,
  `AA7959`, `90625D`, ink `3F2A20`. Keep the accents muted: gilt `D9B45A`, and soft jewel tones for glass. *— litterbox/assets-wishlist.md*

- **Format:** PNG with a transparent background, one piece per file, or a sheet on the 16 px grid. Tell me
  each piece's box. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › 1. Buy first: cheap, and each fixes something visible

| Pack | Price | What it fixes |
|---|---|---|
| [Cat Pack – Pochi](https://toffeecraft.itch.io/cat-retro), paid | $1.80+ | **The walk.** Its *Run* animation replaces today's hopping sitter. It also has **six real coat colours** (brown, white, black, grey, orange, grey-white). Coats are now the only way to tell projects apart, so real colours beat today's colour filters. It also adds Happy, Chilling, Surprised, Sleeping and Dance for the moods. |
| [Sprout Lands UI Pack](https://cupnooble.itch.io/sprout-lands-ui-pack), premium | $3.99+ | Emote bubbles for meowing cats, a bigger emoji set (more mood faces), and more expressions for its cat |
| [Sprout Lands Asset Pack](https://cupnooble.itch.io/sprout-lands-asset-pack), premium | $3.99+ | Doors, windows and roofs that could replace the facade I drew in code, plus interior furniture |

*— litterbox/assets-wishlist.md*

**Worth knowing before you buy:** *— litterbox/assets-wishlist.md*

- **Mochi has no walk cycle.** The paid [Cat Pack – Mochi](https://toffeecraft.itch.io/cat-pack) ($1.90+)
  has no walk or run; its own page says so. Buy it only for its colours and poses (eating, licking,
  bathing, dancing), not for walking. *— litterbox/assets-wishlist.md*

- **Sizes:** Pochi is 64 px and Mochi 32 px. If Pochi's Run becomes the walk, the working cat (today a
  32 px Mochi) should become Pochi too, so every cat is one size. *— litterbox/assets-wishlist.md*

- **Directions:** Pochi's Run is most likely side-on only. Walking up and down the screen, and climbing
  the stairs, would still need drawing (section 2). *— litterbox/assets-wishlist.md*

- **Catio furniture:** ToffeeCraft's [CatRoomPaid](https://toffeecraft.itch.io/cat-pack) ($1) adds cat
  furniture and decorations for the catio. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › The cats

| Piece | Where it goes | Frames |
|---|---|---|
| **Walk, 4 directions** (side, towards you, away) | Every walk between spots | 4–6 a direction |
| **Climbing stairs, from behind** | Going upstairs when archived | 4 |
| **Coming downstairs, from the front** | Coming back down | 4 |
| **Working**: at a laptop, a desk or yarn | A working cat's station | 4–8, looping |
| **Sitting on a step** | If napping cats ever sit on the stairs instead of vanishing | 2 |

*— litterbox/assets-wishlist.md*

The Pochi Run from section 1 covers "side". The rest match whichever cat you choose. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › The manor, after Peleș and Sinaia

Today these are drawn in code (`catio/tools/manor.py`). They work, but hand-drawn pieces would be richer. *— litterbox/assets-wishlist.md*

**Outside:** *— litterbox/assets-wishlist.md*

| Piece | Size |
|---|---|
| Limewashed wall, ochre and one or two pastels | 16 × 32 repeating |
| Stucco pilaster and cornice | 5 × 32, and a 16 × 3 cornice |
| Arched window with painted shutters, open and closed | about 18 × 16 |
| Baroque double door with a pediment and a stained-glass fanlight | about 36 × 32 |
| Stone plinth and corner quoins | 16 × 7, and 5 × 5 blocks |
| Wrought-iron stair rail with scrolls | 2 × 16 |
| Window box of red geraniums | 16 × 6 |

*— litterbox/assets-wishlist.md*

**Inside, walls and floors:** *— litterbox/assets-wishlist.md*

| Piece | Size |
|---|---|
| Gilt trellis panel on white (photo 3) | 16 × 32, and a 6 × 32 pilaster |
| Carved walnut panelling (library) | 32 × 32 repeating |
| Art Nouveau wallpapers (lily, iris, peacock) | 16 × 20 repeating |
| Stained-glass window, lily or fleur | 30, 40 and 76 wide × 32 |
| Parquet or herringbone floor (drawing room) | 16 × 16 |
| Marble chequer (orangery) | 16 × 16 |

*— litterbox/assets-wishlist.md*

**Inside, furniture** (each is a piece renovation mode can move): *— litterbox/assets-wishlist.md*

- **Library:** a carved walnut bookcase with an iron grille and gilt scalloped shelves, after photo 2. *— litterbox/assets-wishlist.md*

- **Great hall:** a marble bust on a pedestal (photo 3), a chandelier seen from above, a carved oak
  settle. *— litterbox/assets-wishlist.md*

- **Drawing room:** an ornate fireplace and a grand piano. *— litterbox/assets-wishlist.md*

- **Bedroom:** a four-poster bed. *— litterbox/assets-wishlist.md*

- **Bathroom:** a claw-foot bath. *— litterbox/assets-wishlist.md*

- **Kitchen:** a copper pan rack. *— litterbox/assets-wishlist.md*

- **Everywhere:** carved chairs. *— litterbox/assets-wishlist.md*

- **Catio:** a cat flap. Today it's a dark rectangle. *— litterbox/assets-wishlist.md*
- **A litter box:** a house full of cats has none, and no pack we have draws one. A top-down sprite on the
  16 px grid, about 16 × 12, for the catio or the bathroom. *— litterbox/missing-assets.md*

**Outdoors:** *— litterbox/assets-wishlist.md*

- Cobblestone paving, after photos 1 and 4. No pack has it. *— litterbox/assets-wishlist.md*

- A stone balustrade (photo 4). No pack has it. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › The cafe (KittyChat Cafe)

The outdoor terrace built on 29 September was not carried into version 12: the café is a room indoors now,
on the ground floor, beside the glazed terrace. For it to read as a café it still needs: *— litterbox/assets-wishlist.md*

- an espresso machine; *— litterbox/assets-wishlist.md*

- cups and cakes on the counter; *— litterbox/assets-wishlist.md*

- a chalkboard. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › The interface: gaps in the two UI packs

Game UI Pastel dresses the map panel, the minimap, the camera's buttons and Build mode
(`docs/camera-and-minimap.md`). Sprout Lands keeps everything else. Neither pack has these, so the plan fills
each one for now: *— litterbox/assets-wishlist.md*

| Missing | Filled for now with | Worth drawing |
|---|---|---|
| A house icon (for "whole house") | The page's own small house glyph on a Pastel button | A house or a map pin, in Pastel's style |
| A selection outline (the minimap's view) | A Pastel panel border with no fill | Four rounded corner brackets |
| A grid or build icon (the Live / Build switch) | The round slider knob on a button, with no icon | A hammer or a trowel |
| An undo icon | Pastel's `Reload`, mirrored | — |
| A floor or stairs icon | Words: "Ground" and "Upstairs" | A little stair |
| Outline panels | The Filled panels (the Outline panel folders in the zip are empty) | — |
| An "interrogation" icon | `Question` (its folder in the zip is empty) | — |
| Key caps for the `?` list of keys | Plain lettering | Rounded key caps |
| Furniture thumbnails for the catalogue and "Looks like…" | The atlas cells, drawn small | — |

*— litterbox/assets-wishlist.md*

"—" means what fills it is good enough. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › 3. Sound: nothing yet (Charlotte is finding some)

The meow is made in code (a filtered tone). Real sounds would be better: *— litterbox/assets-wishlist.md*

- a short meow; *— litterbox/assets-wishlist.md*

- a purr for a cat that finishes; *— litterbox/assets-wishlist.md*

- soft paw steps; *— litterbox/assets-wishlist.md*

- a door, for new cats coming in. *— litterbox/assets-wishlist.md*

For free sounds, search [freesound.org](https://freesound.org) filtered to the **CC0** licence, and keep
each under a second. *— litterbox/assets-wishlist.md*

### What's missing: art and sound for the Catio › 4. Licences to sort out

These aren't art to get, but they're open questions on what you already have: *— litterbox/assets-wishlist.md*

- **Unknown makers or terms:**
  - `plants.zip`: who made it? It's credited as unknown. *— litterbox/assets-wishlist.md*

- **If the Catio ever becomes commercial** (sold, or used for the shop), several free versions don't
  allow it:
  - ToffeeCraft free: personal use only.
  - Sprout Lands basic (UI and sprites): non-commercial.
  - Little Dreamyland free: non-commercial.
  - Top Down Garden Castle: no distribution at all. *— litterbox/assets-wishlist.md*

- **The premium Sprout Lands packs and the paid ToffeeCraft packs** all allow commercial use. *— litterbox/assets-wishlist.md*

### Loose ends › Ideas not built yet

- **Routines are paused (2026-09-30), at Charlotte's request: not enough usage to run them daily.** "Refresh
  the catio" and "Catio: hourly audit and queens pass" are both disabled. Refresh `snapshot/sessions` by hand
  when she asks. Don't re-enable either or add new scheduled ones. *— litterbox/loose-ends.md*

- **The concierge.** A small session plus an hourly Routine that reads `outbox/` with `ArtifactData` and
  delivers each post with `create_trigger`/`fire_trigger`. It's needed only if claude.ai refuses the page's
  own calls. Hourly is the Routine minimum, so this is slower than a direct push. *— litterbox/loose-ends.md*

- **Seed `rules/*` from `harness/rules.json`** with `ArtifactData` at the next publish, with an `order` field
  set from the list position. *— litterbox/loose-ends.md*

- **`save-sessions.py`** should keep `environment_id` and the model fields. Then the saved copy shows breeds,
  and New cat can pick an environment when the live read is blocked. *— litterbox/loose-ends.md*

- **`bundle.py`** should put `catio_mcp.py` and `rules.json` in the localhost folder, with `HOW-TO-RUN.txt`
  covering `--serve`. *— litterbox/loose-ends.md*

- **The marketplace** could list PR #5's `catio-plugin/` next to `kittychat-house-rules`. *— litterbox/loose-ends.md*

- **Audits.** The page shows `audits/<repo>` in filing cabinets; nothing writes them until the plugin is on. *— litterbox/loose-ends.md*

### 2 October 2026: the chat that set up the gateway, moved the café onto it and planned the queen

- **Managed Agents sessions** started and chatted with entirely from the café: separate from her claude.ai
  sessions and billed per use through an API key. Offered 2 October, not chosen. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **The file sorter and starting sessions from the café** (`harness/gateway/README.md`, "Not here (yet)");
  the runner brings the second. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Accounts** (`docs/accounts.md`): the queen's key is one more key for the Registry, with the role `queen`. *— litterbox/2026-10-02-gateway-cafe-queen.md*

## Facts learned

### Loose ends › Facts learned the hard way

- `host:` MCP servers work only in the Claude desktop app, and only for the artifact's owner. *— litterbox/loose-ends.md*

- Write-tool failures that come back as `server_unavailable` or `upstream_error` are ambiguous: the tool may
  have run anyway. The page queues these rather than retrying. *— litterbox/loose-ends.md*

- `ArtifactData` `where` on a nested field (`target.id`) may not be supported. Brain documents keep a flat
  `cat` field for queries. *— litterbox/loose-ends.md*

- The e2e stub only includes agent cats with `?agents=1`, so the older checks' counts stay as they were. *— litterbox/loose-ends.md*

- **Posting into a session through a bound Routine doesn't reach it** (tried 2026-09-30): `create_trigger` with
  `persistent_session_id` set to an existing session, then `fire_trigger`, started a *new* session titled
  "⚡ <routine name>" with no repo, and the target session never saw the text. `postToSession()` and the
  concierge idea both rest on this, so posts stay queued in `outbox/` until another way is found. Deleting the
  Routine deletes the stray session with it. *— litterbox/loose-ends.md*

- Review-ready cats never go upstairs: `STALE_DAYS` only moves sleeping ones. Month-old Remote Control
  sessions keep the sign's "need you" count high. *— litterbox/loose-ends.md*

- The warm-start placeholder session (`__warming__`, tag `cowork-warm-start`) shows up as a cat to review. *— litterbox/loose-ends.md*

- The Drive connector *can* hand over the zips: an oversized result lands in a tool-results JSON file, and
  base64-decoding its `content` field gives the zip. Checked with all nine packs, up to 2.6 MB. *— litterbox/loose-ends.md*

- Little Dreamyland is by **Starmixu & Utaskuas**. Its licence: modifying allowed, non-commercial only, no
  redistribution or resale even modified, and no NFTs or AI training. Credit: "Assets from Little Dreamyland by
  Starmixu & Utaskuas." *— litterbox/loose-ends.md*

### 2 October 2026: issue #24's round, sifted

- **A session can check the gateway without asking her:**
  - the Cloudflare connector's `workers_list` shows `catio-gateway`;
  - `ListConnectors` shows `CATIO`;
  - in a session that has the connector, the `CATIO` tools answer, `list_agents` included. *— litterbox/2026-10-02-issue-24-report.md*

- **Sifting sessions:** `list_events` with `kinds: ["result"]` returns each turn's closing message without the
  tool calls. A session's post-turn summary, in `list_sessions`'s `external_metadata`, gives its current ask in
  a line. *— litterbox/2026-10-02-issue-24-report.md*

- **Check `main` again before filing.** On 2 October, the gateway was set up and version 21 was written between
  the round's diagnosis (14:45 UTC) and its sift (19:50 UTC). Half of the round's report had gone stale. *— litterbox/2026-10-02-issue-24-report.md*

### 28 September 2026: the chat that built the first Catio

- **The Catio artifact's wake subscription never registered** for the session that built it (`mint_failed`).
  A session can't count on being woken by her comments or edits on the page: read the page's database with
  `ArtifactData`, or ask her. *— litterbox/2026-10-02-catio-first-build.md*

- **A full `list_sessions` is too big to read inline**: about 83,000 characters for 46 sessions, 115,000 for 50. The tool
  saves it to a tool-results file, with the list under its `ccr` key; pass that object to
  `catio/tools/save-sessions.py` to refresh the Catio's saved copy. *— litterbox/2026-10-02-catio-first-build.md*

- **Testing the Catio's menus in Playwright:**
  - A menu laid over its target steals the hover, so menus open beside what they belong to, and a test
    points at a clear patch of floor (found with `elementFromPoint`).
  - The first Escape only closes a menu; zooming out takes a second one.
  - A tap focuses the cat, so focus may open a menu only when `:focus-visible`. Otherwise the tap's click
    lands on the stage and closes the menu. *— litterbox/2026-10-02-catio-first-build.md*

- **The Catio's localhost copy goes in her Google Drive**, in My Drive › Claude › KittyChat Cafe (local copy),
  not on her USB stick: it was never on the stick. The Drive connector can't upload a zip that size, so Claude
  sends `catio-local.zip` in the chat and she saves it in that folder. *— litterbox/2026-10-02-catio-first-build.md*

### 2 October 2026: the chat that set up the gateway, moved the café onto it and planned the queen

- **Cloudflare's bot check (error 1010, `browser_signature_banned`) refuses Python's default User-Agent,** so
  every script that calls the gateway names itself (`kittychat-report/1`, `kittychat-move-in/1`, the runner
  `kittychat-queen/1`). The hook's reports were dropped silently until PR #26. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Cloudflare's "Import a repository" fills the Worker's name with the repo's.** It must be `catio-gateway`,
  to match `wrangler.jsonc`, or later deploys fail. A Worker under the wrong name is deleted and imported
  again (renaming is risky: the Durable Object is tied to the name), and its leftover KV namespace deleted
  too. Done 2 October. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **A Worker secret counts only as type Secret, under Production, and after Deploy** (saving a version isn't
  live). A 401 `invalid_token` on `/mcp` means the Worker's `CATIO_TOKEN` differs from the environment's:
  copy it with the password manager's copy button (selecting the text can pick up a space) and paste it
  again. That was the cause on 2 October. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **The gateway's old home page said one fixed line whatever the state,** so it told her nothing (now it is
  the café). Check a deploy from a session: the sign-in page's wording, `/mcp` with the key, `list_agents`.
  Never by trying a password: a wrong one from a check counts toward the five-try lock (one was spent on
  2 October). *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Cloud sessions don't install the plugin from the repo's `.claude/settings.json`.** It goes in the
  environment's setup script, with the full `https://…git` marketplace address (the short form hung).
  Verified 2 October: the session restarted with the rules on, and the audit and browser-preflight gates held
  until their skills ran. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Claude Code Remote's `send_message` works from a session** where the page's call is refused: the seven
  outbox posts of 30 September were delivered that way on 2 October (four messages, one archive, two already
  done) and marked delivered. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Secrets on her PC:** in PowerShell,
  `$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | % { $_.ToString('x2') })`;
  in a Codespace, `openssl rand -hex 32`. Chrome's password manager has an Add button at
  `chrome://password-manager/passwords`; passwords.google.com doesn't. Both entries are filed under the
  gateway's address. Her Codespace is "symmetrical space giggle"; VS Code's Chat panel sends what's typed to
  an AI, so secrets go in the terminal. Her PC's VS Code opens in `G:\My Drive\Claude`. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Claude Code headless, for the runner:**
  `claude -p --resume <id> --output-format stream-json --verbose --include-partial-messages --append-system-prompt-file … --mcp-config '{"mcpServers":{"catio":{"type":"http","url":"…/mcp","headers":{"Authorization":"Bearer …"}}}}' --allowedTools mcp__catio --permission-prompts none --max-turns 30`.
  `--bare` needs an API key, so it isn't used: she signs in with her plan. SIGINT ends a turn (on Windows,
  `CTRL_BREAK_EVENT` to a child started with `CREATE_NEW_PROCESS_GROUP`). Cross-session messaging needs a
  session connected to Remote Control to pass messages on: untested. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **A Worker holds a request as long as the client stays connected,** so the runner's 25-second long poll is
  fine on the free plan; a Durable Object alarm wakes it for a routine on time. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Voice in the browser:** `webkitSpeechRecognition` is Chrome and Edge only (voice to text);
  `speechSynthesis` has en-GB voices on Windows (Microsoft Hazel, Susan). Both free; hidden where the browser
  lacks them. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **The ship check reads the branch's upstream:** a feature branch tracking `main` reports every commit as
  unpushed. `git branch --set-upstream-to=origin/<branch>` fixes it. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **Her choices of 2 October:** the café on its own address (over talking in the cats' cards, or Managed
  Agents sessions billed per use through an API key); the runner on her PC for now; the free browser voice
  now. *— litterbox/2026-10-02-gateway-cafe-queen.md*

### 3 October 2026: owner on the wire, shipped, and what it left

- **The rename reached her real house.** After PR #50 deployed, every note in the queen's conversation reads
  `owner` or `queen`, including ones written as `charlotte` two hours earlier: the House's one-time migration ran. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

- **GitHub won't change the base of a stacked pull request** ("Cannot change the base branch because the pull
  request is part of a stack") once the one under it has closed. Open a new pull request from the same branch:
  that is how #42 became #50. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

### 4 October 2026: the queen's card, held for her

- **The e2e suite had not parsed since the quest-log merge.** The merge that brought in #58 dropped the two
  lines closing the scene's test block, so `catio/test/run.sh` died with `SyntaxError: Unexpected end of
  input` before a single check ran. Both branches fixed it independently within the hour. Worth knowing that
  a merge can silently take a suite to zero: nothing reported a failure, because nothing ran. *— litterbox/2026-10-04-queen-card-held-for-her.md*

- **`max-height: <percentage>` resolves to `none` against an indefinite height.** Two separate bugs in the
  queen's card came from this: `.homework { max-height: 46% }` in a grid row sized `auto` (so homework took
  the whole talk and the conversation had no height at all), and `.owner svg { max-height: 100% }` on an
  auto-height grid item (so the owner was never capped and her head was clipped). `fit-content()` on the
  track is what actually caps a grid row. *— litterbox/2026-10-04-queen-card-held-for-her.md*

## Findings

### 29 September 2026: building the KittyChat harness › What she asked for, in order

1. Issue #3: "An AI harness that presents itself as a cat cafe. The KittyChat Cafe." *— litterbox/2026-09-29-harness-chat.md*

2. Drag and drop chats, downloads and other files into "the brain", each filed to the right session or cat. *— litterbox/2026-09-29-harness-chat.md*

3. The house becomes a **refurbished manor**. There are **house rules** for the harness, starting with the
   preflight skill every time an agent uses a browser. Other models can connect. *— litterbox/2026-09-29-harness-chat.md*

4. After seeing the plan:
   - private matters must stay out of git repos, but may be saved to the Catio's own storage;
   - sessions can be managed and commented on from inside the harness and the MCP server;
   - "I would like for the page to push to a session. I want a true harness."
   - renovation mode: drag furniture around, and add or remove the non-essential and unconnected pieces;
   - a cat's **position** shows its state, not a mood face;
   - more rules: a read-only ponytail audit when a session opens; PRs and pushes happen automatically
     when reasonable ("semi-automatic auto mode");
   - she would add CatMegaFree. *— litterbox/2026-09-29-harness-chat.md*

5. Her answers to the questions:
   - she uploads the zips;
   - the rules ship as a plugin for every repo;
   - other models means Claude breeds, other models doing the sorting, other agents' sessions, and any
     MCP client. *— litterbox/2026-09-29-harness-chat.md*

6. "You're running out of tokens. Make sure you push to main and merge 5." *— litterbox/2026-09-29-harness-chat.md*

7. Add the renovation notes to the repo, build the manor a room at a time, revise the plan, compile and
   compress this chat, and put useful leftovers here. *— litterbox/2026-09-29-harness-chat.md*

### 29 September 2026: building the KittyChat harness › What was found

- **The live artifact wasn't `main`.** A Sprout Lands reskin with room queens and a rooms redesign was
  live from PR #5's branch (`claude/charming-dirac-f7g4pr`). This work was built on top of it, and PR #5
  was merged. *— litterbox/2026-09-29-harness-chat.md*

- **A page can post into a session.** It makes a Routine bound to that session (`create_trigger` with
  `persistent_session_id` and no schedule), then fires it (`fire_trigger` with text). The text arrives as
  a turn in that session. *— litterbox/2026-09-29-harness-chat.md*

- **claude.ai may refuse the page these calls.** PR #5's session found Claude Code Remote has no switch in
  her Connectors list. So every post falls back to `outbox/`. *— litterbox/2026-09-29-harness-chat.md*

- **The Drive connector can't hand over big files.** It returns each one inline as base64. The zips had to
  be attached in the chat. *— litterbox/2026-09-29-harness-chat.md*

- **Claude's own edits to `.claude/settings.json` and `CLAUDE.md` are refused** as self-modification.
  Those two changes are hers to make. *— litterbox/2026-09-29-harness-chat.md*

- **`list_sessions` gives each session a model and an environment:** `environment_id`,
  `session_context.model`, `configured_model` and `external_metadata.last_served_model`. *— litterbox/2026-09-29-harness-chat.md*

### 29 September 2026: building the KittyChat harness › What was built (all on `main`)

- **`harness/`: the `kittychat-house-rules` plugin and the MCP server.**
  - `rules.json` holds the three enforced rules and five soft ones.
  - Hooks:
    - `gates.py`: preflight before browsers; the audit before any edit, commit or push;
    - `ship_check.py`: a nudge when work is left unpushed;
    - `session_start.py`: prints the rules.
  - The `catio` skill handles deliveries, messages, requests and the catch-up.
  - `mcp/catio_mcp.py` is the MCP server for other agents: stdio, `--serve`, and wake commands.
  - 15 tests. *— litterbox/2026-09-29-harness-chat.md*

- **`catio/index.html`:**
  - the brain: drop, sort, the tray, "File under", throw away;
  - pushing into sessions, with the outbox as fallback;
  - conversations in `notes/`;
  - managing a cat: title, pause, wrap up, archive, New cat on a model;
  - breeds, agent cats, the house-rules panel, dragging cats between rooms;
  - on localhost, files are kept in IndexedDB and any OpenAI-compatible model can sort.
  - The e2e test grew from 72 to 97 checks. *— litterbox/2026-09-29-harness-chat.md*

- **`docs/renovation-mode.md`**: the rooms-redesign session's constraints. **`docs/plan.md`**: the revised plan. *— litterbox/2026-09-29-harness-chat.md*

### 29 September 2026: building the KittyChat harness › Left open

See `loose-ends.md` and `docs/plan.md` ("Blocked on Charlotte" and "Next"). *— litterbox/2026-09-29-harness-chat.md*

### Loose ends › From the manor build

- CLAUDE.md says `art/house.png` is committed and gives the six-zip build command. Since the retexture the house is
  `art/licensed/house.png` (never committed) and `build-art.py` takes nine zips; its publish list needs the new path. *— litterbox/loose-ends.md*

- CLAUDE.md's publish list still names `emblems.png`, and its `projects` row still has `emblem`. Emblems are gone
  (29 September): the page no longer uses them, `build-art.py` no longer makes them, and the next publish drops
  `art/licensed/emblems.png`. *— litterbox/loose-ends.md*

- CLAUDE.md still describes the cabin: its publish file list, "The cabin is a floor plan", and the old
  capabilities. Claude can't edit CLAUDE.md (it's refused as self-modification). `docs/plan.md` has the new
  file list, and the MANOR block is described in `catio/tools/furniture.py`'s docstring. *— litterbox/loose-ends.md*

- The rooms keep her own names from the database. With the two-floor manor, the names that no longer fit
  ("Dining room", "Living room", "Sunroom", "Hall", "Bathroom") were renamed at the version 12 publish, with
  only `name` changed, to Café, Cat lounge, Terrace, Entrance hall and Ensuite. She can rename them back in
  Edit rooms. `catio/data/rooms.json` already has the new names. *— litterbox/loose-ends.md*

### Loose ends › Merging version 11 into the two-floor manor (done, 30 September)

Version 11 (branch `claude/amazing-bohr-1sfkqi`: Baroque retexture, walking cats, project maps, livened
grounds) is merged into `ccr-bfc398ff-3gh5wb`. Her choice: keep both, in the Storybook Baroque look, on the
two-floor grid; fold the outdoor KittyChat Cafe into the indoor café and terrace. The plan is the "Merge
with the live version 11" section of this session's plan; each step is pushed as it lands: *— litterbox/loose-ends.md*

Loose ends from the merge: *— litterbox/loose-ends.md*

- Version 11's hover-steal checks (its test section 6d: a menu following a resting pointer to the next
  room) are dropped. Menus open on a click now, so there is nothing to steal; the walking checks are 6d. *— litterbox/loose-ends.md*

- The outdoor KittyChat Cafe terrace is gone from the grounds: the café is indoors now, with the glazed
  terrace beside the lounge. A parterre stands before the bay instead. *— litterbox/loose-ends.md*

- The parallel session that made version 11 still exists. Its branch is merged here, so a publish from
  that session would overwrite this one with the one-floor house. Publish from this branch only. *— litterbox/loose-ends.md*

- A cat's walk used to start before its element was in the page and gave up on the first step, so a cat
  brought back from the attic stayed "walking" for ever. Fixed; the test for it is in 6d. *— litterbox/loose-ends.md*

- `harness/skills/graphify/NOTICE` says the MIT licence for graphify's older parts is kept in `LICENSE-MIT`,
  but that file wasn't copied in with the skill; only the Apache `LICENSE` was. Copy upstream's
  `LICENSE-MIT` next to it. *— litterbox/loose-ends.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin

Run with her MCPmarket `ui` skill: role Game UI Designer, with UI Designer accessibility. References: `menu-systems`,
`game-ui-accessibility`, `game-ui-patterns`, `accessibility`, `usability-heuristics`, `interaction-patterns`. *— litterbox/ui-audit.md*

- **How it was checked:** the reviewer read `catio/index.html`, looked at laptop and phone screenshots, and
  moved a real mouse over the test copy of the page in a headless browser. *— litterbox/ui-audit.md*

- **What was left out:** gamepad guidance doesn't apply (no gamepad), so it was skipped. *— litterbox/ui-audit.md*

- **Status:** report only. Nothing has been changed yet. Pick what to fix. *— litterbox/ui-audit.md*

- **Line numbers:** they are for `catio/index.html` at commit `1d428ac`. *— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Summary

The pixel UI is consistent and legible, and several things are already done well: *— litterbox/ui-audit.md*

- dark ink on the tan panels reads at 7.3:1; *— litterbox/ui-audit.md*

- deletes ask twice; *— litterbox/ui-audit.md*

- empty states and connector errors are in plain language; *— litterbox/ui-audit.md*

- reduced motion is respected. *— litterbox/ui-audit.md*

The serious problem is hover. When you move the mouse from a room or a cat towards its menu, the pointer
passes over something else on the way, and that thing's menu replaces the one you wanted. On the phone,
the house is too small to use at the start. *— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Critical

**1. Moving the mouse to a menu opens a different menu.** **Fixed** (29 September): with a menu open,
another room or cat takes over only once the pointer rests on it for 240 ms; reaching the menu cancels the
switch. Seven new e2e checks glide the mouse in small steps. Tested by moving the mouse the way a person does
(25 small steps): *— litterbox/ui-audit.md*

- Kitchen → its menu turned into **Dining room**. *— litterbox/ui-audit.md*

- Dining → a queen's menu (**Philomène**). *— litterbox/ui-audit.md*

- Bedroom → **Hall**. *— litterbox/ui-audit.md*

- A cat → its own **room's** menu (Pomme → Kitchen, Caramel → Craft room). *— litterbox/ui-audit.md*

*Why:* *— litterbox/ui-audit.md*

- Each menu sits 12px beside the thing it belongs to (`g = 12`, lines 1063 and 1073–1074). *— litterbox/ui-audit.md*

- That 12px gap is covered by the next room, or by the room floor around a cat. *— litterbox/ui-audit.md*

- `hoverable()` (1020–1023) opens a new menu the moment the pointer enters something, with no delay. *— litterbox/ui-audit.md*

- A fast flick sometimes skips the gap, so it feels random. *— litterbox/ui-audit.md*

*Why it matters:* hover is the only way into the page's controls. Right now she has to "sneak" onto a menu. *— litterbox/ui-audit.md*

*Fix:* *— litterbox/ui-audit.md*

- In `hoverable`, when a different menu is already open, wait about 200ms before opening the new one, and
  cancel if the pointer reaches `#menu`. *— litterbox/ui-audit.md*

- Never let a cat's, pile's or queen's own room take over their menu while it is open. *— litterbox/ui-audit.md*

- Consider `g = -4`, so the menu overlaps its anchor and there is no gap at all. *— litterbox/ui-audit.md*

- Add a test that moves the mouse with `mouse.move(x, y, { steps: 20 })`. Playwright's `click()` jumps
  straight to the button, which is why the tests missed this. *— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Warning

**2. On a phone, the house is tiny, has no room names, and cats can't be tapped.** *— litterbox/ui-audit.md*

- At 390×844 the house fills about an eighth of the screen. The camera fits the whole grounds by width
  (`WHOLE`, 373; `layout()` 933–948). *— litterbox/ui-audit.md*

- Room names are hidden, because signs need `room >= 56` (1216). Only the badge shows. *— litterbox/ui-audit.md*

- Measured tap targets: cats 6–12px, rooms 38–92px (bathroom and sunroom are 38×44). *— litterbox/ui-audit.md*

- *Fix:*
  - on narrow portrait screens, open zoomed into the most urgent room (`labelRooms` already works out
    which one);
  - add a left/right swipe that follows the existing `NEXT` map;
  - fit the camera to the house (`PLAN`) rather than the whole grounds. *— litterbox/ui-audit.md*

**3. Buttons are too small to tap on a phone.** *— litterbox/ui-audit.md*

- `--u` is 1px on phones (line 31), so a `.btn` is 32px tall. The Sound switch is 22px (196–197). *— litterbox/ui-audit.md*

- *Fix:* add `@media (pointer: coarse) { .btn, .sound { min-height: 44px; } }` with padding to centre the
  text. The 9-slice art stretches to fit. *— litterbox/ui-audit.md*

**4. The live status can only be read by hovering.** *— litterbox/ui-audit.md*

- When all is well, the words ("Live · updated 14:02…", or the saved-copy date) are hidden unless the sign
  is hovered (92–93). *— litterbox/ui-audit.md*

- Keyboard focus never reaches the sign, and touch has no hover. *— litterbox/ui-audit.md*

- The tick has no text (1309), so a screen reader gets an empty status. *— litterbox/ui-audit.md*

- In the warning state, `renderStatus()` rebuilds the status on every data update and every minute
  (1406–1421, 2355), so the same long error can be announced again and again. *— litterbox/ui-audit.md*

- *Fix:*
  - give the tick a hidden label ("Live", "Saved copy");
  - make the sign focusable (`tabindex="0"`), or put a status line in the room menu's footer;
  - only update `#status` when its text actually changes. *— litterbox/ui-audit.md*

**5. Errors and long confirmations vanish after 3.2 seconds.** *— litterbox/ui-audit.md*

- `toast()` (2329) hides every message after 3.2s. That includes:
  - "Couldn't save…";
  - the 150-character "Queued: claude.ai won't let this page…" message (1878);
  - the brain's combined report for several files (2029). *— litterbox/ui-audit.md*

- *Fix:*
  - keep error and "queued" messages until dismissed, with a close button made from the pack;
  - use a separate `role="alert"` region for errors;
  - show the brain's per-file results inside the brain dialog. *— litterbox/ui-audit.md*

**6. The brain's Send button can stay disabled forever.** *— litterbox/ui-audit.md*

- Send turns on only after every file has been sorted (`Promise.all`, 2010–2017). *— litterbox/ui-audit.md*

- `endpointSort()` (1930–1939) and `S.sample.json` have no time limit, so a hung sorter leaves every row on
  "Sorting…" and she can only Cancel. *— litterbox/ui-audit.md*

- Files over 20 MB are skipped at Send (2022), with nothing about it in the result. *— litterbox/ui-audit.md*

- *Fix:*
  - time the sorter out with `AbortController` after about 8s, then fall back to "Nobody yet";
  - turn Send on as soon as the keyword guesses are ready;
  - list skipped files in the result. *— litterbox/ui-audit.md*

**7. A queen's notes are lost without warning.** *— litterbox/ui-audit.md*

- "Give it to her" and "Forget" only change a local list (1545–1564). Nothing is saved until **Save** (1577). *— litterbox/ui-audit.md*

- Close and Escape throw the changes away silently (1436), and "Give it to her" sounds like it already saved. *— litterbox/ui-audit.md*

- *Fix:* save straight away on Give, Forget and Say it, or ask "Keep your changes?" on close when the list
  has changed. *— litterbox/ui-audit.md*

**8. Speech bubbles are extra keyboard stops that swap the menu.** *— litterbox/ui-audit.md*

- Bubbles are buttons left in the tab order (1264). *— litterbox/ui-audit.md*

- On the whole-house view, Tab went from a room to Caramel's bubble, and landing on it replaced the room's
  menu with the cat's. *— litterbox/ui-audit.md*

- Inside a room, each meowing cat is reached twice: once on the cat, once on its bubble. *— litterbox/ui-audit.md*

- *Fix:* set `tabIndex = -1` on bubbles and the "Files" tag (1234). Both are already reachable from the cat
  and the room menu. This keeps the "one Tab stop for the map" rule. *— litterbox/ui-audit.md*

**9. The cats never stop moving, and there's no pause on the page.** *— litterbox/ui-audit.md*

- Every cat loops its animation forever (138–153), and busy cats wander every 6s (919–930). Only the
  operating system's reduced-motion setting stops this (308–311). *— litterbox/ui-audit.md*

- It's an all-day dashboard, and WCAG 2.2.2 asks for a way to pause motion that lasts more than 5 seconds. *— litterbox/ui-audit.md*

- *Fix:* add a "Still cats" switch next to Sound in the room menu's footer, with the same toggle art. Keep
  it in `localStorage`, and have `calm()` and the CSS read it (a `.still` class on `body`). *— litterbox/ui-audit.md*

**10. The brain and House rules are hidden in two rooms.** *— litterbox/ui-audit.md*

- They only appear in the Hall and Library menus (1119–1123), so she has to remember where they live. *— litterbox/ui-audit.md*

- *Fix:* put both in the footer of every room menu, as small buttons next to Sound. *— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Suggestion

**11. The room menu has too many choices.** *— litterbox/ui-audit.md*

- It can show up to 10 buttons plus a 3-control footer (1110–1134), all the same size. *— litterbox/ui-audit.md*

- *Fix:* put Look in, Ask the queen and Files on the first row. Put Give it files, New cat, Adopt and Edit
  rooms below the divider. *— litterbox/ui-audit.md*

**12. Some text is too small.** *— litterbox/ui-audit.md*

- Bubble text is 12.5px (168), model plaques 10px (283), counts 11px (118, 285), notes and captions
  12–12.8px (193, 238). *— litterbox/ui-audit.md*

- *Fix:* raise the Nunito text to at least 14px, and enlarge plaques and counts when a room is zoomed in. *— litterbox/ui-audit.md*

**13. Screen readers can't tell a menu has opened.** *— litterbox/ui-audit.md*

- `#menu` (328) is a plain div, and the room or cat has no `aria-expanded` / `aria-controls`. *— litterbox/ui-audit.md*

- *Fix:* add `role="group"` and an `aria-label` from its heading, and set `aria-expanded` on the anchor in
  `showMenu` and `hideMenu`. *— litterbox/ui-audit.md*

**14. Current names show only as faint placeholders.** *— litterbox/ui-audit.md*

- A cat's or queen's current name is shown only as placeholder text (1476, 1570), at 3.3:1 contrast
  (`#5F6A5E` on `#C1C8B9`, line 59). *— litterbox/ui-audit.md*

- *Fix:* show the current name as visible text under the field, and darken the placeholder to about
  `#4E574D`. *— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Assessment

| Criterion | Current state | Severity | Recommendation |
|---|---|---|---|
| Hover menus | Moving to a menu opens a neighbour's (tested) | Critical | 200ms delay before switching; own room can't take over a cat's menu; stepped-move test |
| Phone layout | House is about 1/8 of the screen; no names; cats 6–12px | Warning | Start zoomed into the urgent room; swipe between rooms |
| Touch targets | Buttons 32px, switch 22px | Warning | 44px minimum on touch screens |
| Status sign | Hover-only words; tick has no text; repeated announcements | Warning | Hidden label, a way to read it, update only on change |
| Error feedback | Toasts gone in 3.2s | Warning | Keep errors until dismissed; `role="alert"` |
| Brain drop flow | Can hang on "Sorting…"; >20 MB skipped silently | Warning | Sorter time limit, earlier Send, report skipped files |
| Data safety | Queen notes lost on close; deletes confirm twice (good) | Warning | Save straight away or warn on close |
| Keyboard | Arrow map, Enter and Escape are solid; bubbles add stops | Warning | Take bubbles out of the Tab order |
| Motion | Honours reduced motion; no pause on the page | Warning | "Still cats" switch |
| Contrast | Ink on tan 7.3:1, ink-soft 4.6:1; placeholders 3.3:1 | Suggestion | Darker placeholder |
| Text size | Pixel font kept at 18px (good); body text 10–12.8px | Suggestion | 14px minimum for Nunito text |
| Empty states | Clear and helpful everywhere | — | Keep |
| Consistency with the pack | Every control uses the pack's art | — | Keep |

*— litterbox/ui-audit.md*

### UI/UX audit of the Catio, with Charlotte's Game UI plugin › Recommended order

1. Fix hover switching (`hoverable` / `showMenu`) and add a stepped mouse-move test. *— litterbox/ui-audit.md*

2. Phone: start zoomed into the urgent room, add room swipes, and make touch targets at least 44px. *— litterbox/ui-audit.md*

3. Keep error and queued messages until dismissed, and show the brain's results in its dialog. *— litterbox/ui-audit.md*

4. Add the sorter time limit and an earlier Send, and report skipped files. *— litterbox/ui-audit.md*

5. Save queen notes straight away, or warn before closing with unsaved changes. *— litterbox/ui-audit.md*

6. Make the status sign readable without hover, and stop the repeated announcements. *— litterbox/ui-audit.md*

7. Take bubbles out of the Tab order. *— litterbox/ui-audit.md*

8. Add a "Still cats" switch, and put The brain and House rules in every room menu's footer. *— litterbox/ui-audit.md*

9. Group the room menu, raise small text to 14px, add `aria-expanded` to menus, and darken placeholders. *— litterbox/ui-audit.md*

### 1 October 2026: the litter box and an audit of the harness › What she asked for, in order

1. An audit of how the harness (the "OpenClaw framework") works, to run a first test of the litter box sifter. *— litterbox/2026-10-01-litter-box-chat.md*

2. "Fix them all": the seven problems the test found. *— litterbox/2026-10-01-litter-box-chat.md*

3. Every note needs a `project:` header, "but the sifter should give it the appropriate header"; and "it should
   semi-auto push" what it files. *— litterbox/2026-10-01-litter-box-chat.md*

4. "I prefer to keep guessing to a minimum before deletion. The litterbox is the back burner, it finds things
   that need to be dealt with and lumps them together with a header." Then: update the README to match. *— litterbox/2026-10-01-litter-box-chat.md*

5. With another agent turning the house rules on in every repo: fix the grocery app's merge clash "before you
   do anything else". *— litterbox/2026-10-01-litter-box-chat.md*

6. Before the gateway: triage the branches that never reached `main`, and compress this chat. *— litterbox/2026-10-01-litter-box-chat.md*

### 1 October 2026: the litter box and an audit of the harness › What was found

- **The harness never ran the sifter.** `litterbox/sort.py` was a script run by hand; nothing in the plugin,
  the `catio` skill or the server mentions it. *— litterbox/2026-10-01-litter-box-chat.md*

- **The first test** (invented notes, copies of all five repos) sent notes to the wrong repo on single words
  ("of course" to the grocery app, "basket", "pixel art"), deleted real notes (two notes one word apart, a
  struck-through correction), lost a Notepad file's header to its BOM, left what it filed in other repos
  uncommitted, and slipped past the audit gate, which blocked `rm` but not `sort.py --write`. *— litterbox/2026-10-01-litter-box-chat.md*

- **The Catio server's localhost API** answered tool calls by GET, so any web page could wake an agent with
  "[Catio] Charlotte says: …" (reproduced), and a site naming itself 127.0.0.1 passed the Origin check. *— litterbox/2026-10-01-litter-box-chat.md*

- **The shipping rule's "never merge"** contradicted the grocery app's own rule that every session ends with
  its pull request merged. *— litterbox/2026-10-01-litter-box-chat.md*

- The café and the grocery app are public repos: a note filed there is published at the next push. *— litterbox/2026-10-01-litter-box-chat.md*

### 1 October 2026: the litter box and an audit of the harness › What was built

- **PR #12:** the sifter's fixes; the server answers POST only, at localhost; the audit gate counts `--write`
  and `--commit`; in a cloud session the shipping nudge checks every repo in the container; the sifter
  commits and pushes what it files (never the default branch). *— litterbox/2026-10-01-litter-box-chat.md*

- **PR #13:** the back burner. Notes without a `project:` go on their project's pile, under a header marked as
  a guess; a pile is filed only after she deletes the guess comment. *— litterbox/2026-10-01-litter-box-chat.md*

- **PR #15**, and the grocery app's **#18:** a repo opts in to merging with `{"merge": true}` in
  `.claude/catio-rules.json`; the grocery app does. *— litterbox/2026-10-01-litter-box-chat.md*

### 1 October 2026: the litter box and an audit of the harness › Left open

- **The gateway** is next. Its plan, on `claude/catio-gateway-plan`, needs one change first: the server's API
  now answers only at localhost, so a remote endpoint needs a token and its own host. *— litterbox/2026-10-01-litter-box-chat.md*

- Nothing tells a session to drop its leftovers in the box, and a session in another repo reaches the box only
  when the café is checked out beside it. *— litterbox/2026-10-01-litter-box-chat.md*

### 2 October 2026: issue #24's round, sifted

- **The gateway's ponytail audit (2 October, before the café moved onto the gateway): lean.** Three small cuts,
  still there on `main` at 19:50 UTC:
  - `House.call` checks the tool name a second time, after `mcp.js` already has, and nothing reads its
    `unknown`;
  - the files table's `picked_by` is written and never read;
  - `package.json`'s `dev` and `deploy` scripts are never run.

  A fourth cut, moving `secret.js` into `signin.js`, no longer applies, because `cafe.js` uses it too.

  Kept on purpose:
  - one OAuth provider per address, because the library needs an absolute resource URI;
  - `wake`, `woke` and `waiting`, so the tools match `catio_mcp.py`;
  - the JSON-RPC batch, so the Stop hook reports and collects in one request.

  Not audited: `src/cafe.js` and `cafe/`, which came later. The summary is in the Catio, at
  `audits/pretty-project-portfolio`. *— litterbox/2026-10-02-issue-24-report.md*

- **One session can be in the gateway twice**, as `cse_…` and as `session_…`. Both were in `list_agents` at
  19:50 UTC: the `cse_…` one from the hook, with a link, and the `session_…` one with a title and no link.
  - The café's `allCats()` keys the gateway's cats by the id after its prefix. The gateway lists the newest
    first, so the older record wins: its mood and `agentId` go on the session's cat, and the other record shows
    as a second cat.
  - If the kept record is `session_…`, what she sends goes to an inbox the Stop hook never collects, because the
    hook asks for `cse_…`.
  - This was read from the code, not seen on the page.
  - Fix: let one record per session through, the newest, or have the gateway merge the two. *— litterbox/2026-10-02-issue-24-report.md*

- **Short-lived `cli-…` cats.** At 19:50 UTC, 10 of the gateway's 16 cats were `cli-…` ids on `main`.
  - Each started and finished within a second, in bursts, one per repo, at the moments cloud sessions started.
  - Something in a starting cloud session runs Claude Code briefly in each repo, without a claude.ai session id,
    and `report.py` reports it. The setup script's plugin install is the first suspect. This is not confirmed.
  - The café shows them as finished cats.
  - Fix: `report.py` skips a run that never had a prompt, or the café hides `cli-` cats that never had one. *— litterbox/2026-10-02-issue-24-report.md*

### 2 October 2026: the chat that set up the gateway, moved the café onto it and planned the queen

- **The serving model fell back to Opus 5.5 for one turn** during stage 1 ("Try again"); the work was
  re-checked and nothing was lost. *— litterbox/2026-10-02-gateway-cafe-queen.md*

- **The artifact's database and the gateway café's are two copies that don't share changes** (the "queued"
  labels above are one consequence); `CLAUDE.md` says so. *— litterbox/2026-10-02-gateway-cafe-queen.md*

### 3 October 2026: owner on the wire, shipped, and what it left

- **The review of 3 October found six bugs in the café's gateway mode and the queen's key** (filed from
  `2026-10-03-review.md`). Whether a cat fixes them now is in her homework. *— litterbox/2026-10-03-owner-on-the-wire-loose-ends.md*

### Review of 3 October, outside PR #37

- **In gateway mode the café can lose its reporting cats until reload.** `refreshAgents()` in `catio/index.html` keeps
  the claude.ai fallback: any `list_agents` error other than `server_unavailable` or `rate_limited` flips `S.host` to
  `host:catio`, `cafe/runtime.js` then throws `gateway_only`, which isn't in the reset list, so the gateway is never
  retried. Skip the fallback when `VIA_GATEWAY`. *— litterbox/2026-10-03-review.md*

- **The café's first sync is never retried.** In `harness/gateway/cafe/runtime.js`, if the first `GET /api/db` fails
  with anything but a 401, `loaded` stays false, no snapshot fires and the WebSocket's first `onopen` skips `sync()`:
  an empty café with no error until a reload. Retry the sync on `onopen`, or show the error. *— litterbox/2026-10-03-review.md*

- **A document pushed during the café's first sync is lost until it changes again.** `sync()` in
  `harness/gateway/cafe/runtime.js` replaces the whole store with the `GET /api/db` reply, so a `doc` push that lands
  while the GET is in flight (on reconnect) is overwritten. Apply pushes received during the sync after it. *— litterbox/2026-10-03-review.md*

- **The queen's seeded key dies on a password reset.** `setPassword` in `harness/gateway/src/registry.js` deletes the
  `CATIO_QUEEN`-seeded key, and `seedQueen` reruns only at isolate boot, so after an admin reset the runner gets 401
  until the Worker restarts. Reseed in `setPassword`, or on every `/api/runner/wait` 401. *— litterbox/2026-10-03-review.md*

- **`seedQueen` ignores `addKey` returning false.** An ordinary agent key named "queen" makes the secret silently never
  become a queen key. Fail loudly, or name the seeded key after the role. *— litterbox/2026-10-03-review.md*

- **A handed note can be lost.** `queenReady` in `harness/gateway/src/house.js` marks Charlotte's notes handed before
  the runner's response completes; a dropped response loses the message. Mark on the runner's ack. *— litterbox/2026-10-03-review.md*
