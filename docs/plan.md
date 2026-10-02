# The KittyChat Café: the plan

Issue #3: "An AI harness that presents itself as a cat cafe." The KittyChat Café (`catio/index.html`, one
private artifact) is the harness. Every Claude Code session and every other agent is a cat in a two-floor
manor. Files dropped on the page go to the right cat, and cats can be talked to and managed.

Last revised 2 October 2026. How it got here, version by version, is in `docs/history.md`; what she has asked
for, in `docs/requests.md`; the audit behind phase 0, in `docs/audit-2026-10-01.md`.

## Where it stands

- **Live:** version 18 (1 October): the KittyChat Café, made honest.
  - The brand is the House button; quiet maps and short menus; the Game UI Pastel map panel and minimap.
  - Posts go to the outbox: the page tries `send_message`, claude.ai refuses it, and the page says so.
  - Counts show only what really waits on her.
- **`main`** has everything live, plus:
  - the house rules, on in all seven repos, with the rule against Claude attribution in commits on her public
    repos and forks (PR #18);
  - the gateway, built and tested, waiting for her setup (PR #19);
  - the litter box's sifter;
  - the digest of her sessions;
  - the drawing plan.
- **Tests:**
  - e2e: 158 passed;
  - harness: 34 passed;
  - the gateway in workerd, with the real hook: 9 passed;
  - the sifter: 12 passed;
  - `furniture.check()` empty.

## How what she sends reaches a session

- **The page can't post into a session.**
  - A Routine bound to the session started a stray new session (30 September).
  - `send_message` from the page is refused, `blocked_by_policy` (1 October, version 18). The page still
    calls it first, so it works the day claude.ai allows it.
- **So everything is saved first, then waits in `outbox/`:** the file in `brain/`, the message in `notes/`,
  the request on `sessions/<id>`. The session collects it at its next start: the house-rules plugin's
  `catio` skill handles it, answers on the cat and marks it delivered.
- **The gateway (phase 5) makes it sooner and the cats live:**
  - a running session gets her message when its turn ends, from a hook;
  - every session reports its state to the gateway, so the page needn't ask claude.ai for the list.
- **What nothing can do: wake an idle session.** Only claude.ai can. Why is in `harness/README.md`.

## The roadmap, in order

Each phase ends with:
- the tests green;
- screenshots at 1440×900 and 390×844, in light and dark;
- a pull request;
- a publish by the checklist below, when she says so.

### Phase 0: make what's there honest. Done (versions 17 and 18)

From the audit:
- no stray sessions;
- honest counts (old review-ready cats nap in the attic; the warm-start session isn't a cat);
- errors that stay until dismissed;
- a sorter with a time limit;
- bubbles out of the Tab order;
- a Still cats switch;
- darker placeholders;
- the credits on phones;
- the plugin and the READMEs brought up to the manor;
- the old branches deleted;
- the `send_message` trial.

Left: the small Nunito text (10 to 12.8 px), which waits for her own art (phase 4).

### Phase 1: the map panel and minimap. Done (version 15)

`docs/camera-and-minimap.md`, iteration 1.

### Phase 2: the camera

The Sims build-mode camera, `docs/camera-and-minimap.md` iteration 2:
- WASD and the arrow keys pan, with acceleration (after a Tab, the arrows still walk between rooms);
- zoom settles on crisp steps;
- a flick glides;
- `F` frames the selection, and `Home` shows the whole house;
- a switch in the House menu turns off the letter keys.

It comes before renovation mode, where a drag moves furniture and the keys are how she pans.

### Phase 3: renovation mode

Move the furniture, add and remove the decorative pieces, and choose what each room's filing cabinet looks
like. The spec is `docs/renovation-mode.md`. In short:

- **Getting in and out:** a Live / Build switch on the map panel. Each change is saved when it is made.
- **While it's on:**
  - cats step aside, and menus and bubbles are off;
  - a 16 px grid shows;
  - Game UI Pastel's catalogue bar runs along the bottom.
- **Moving:**
  - drag and snap;
  - or select a piece and use the arrows, or Move to… (WCAG 2.5.7);
  - nothing lands on another piece, off its floor, or across a doorway.
- **What may move, by kind (`furniture.py`):**
  - essential pieces never move;
  - connected pieces (they carry a cat's station) move but can't be stored;
  - decor moves, and can be stored and brought back.
- **The filing cabinet** stays in its room, and she picks its look from any floor piece. It keeps its Files
  and its review spot.
- **Undo, redo and Reset room.** Cats and queens follow the furniture.
- **Data:** `layouts/<room>`, in the database, the stub, `localRuntime()` and `data/`.
- **Steps:**
  1. layouts as data, read only;
  2. moving;
  3. the catalogue and the cabinet's look;
  4. phones.

### Phase 4: her own art

She draws every asset herself in Aseprite, replacing the downloaded packs, before the working project is
published (1 October). `docs/drawing-plan.md` is the list:
- the scale: 1×, on a 16 px tile;
- every piece with its size and the file it replaces;
- the new pieces: a litter box, café tables and more;
- the order to draw in.

Each piece drops in where its pack's piece was. As the packs go, so do their licences and credits.

- Sounds, once she has found them (`docs/from-the-litterbox.md`).
- The small text raised to 14 px with the new bubbles.

### Phase 5: the gateway, and the rest of the harness

The gateway is built and merged (PR #19, 2 October): `harness/gateway/`, with `harness/hooks/report.py`. It is
OpenClaw's always-on hub, as:
- a Cloudflare Worker on the free plan, needing no server or domain of her own;
- the Catio server's tools at `/mcp`;
- her sign-in by password, through claude.ai's connector (OAuth, Claude's connectors only);
- an agents' key for the hooks, which can't write as her.

Every session reports itself through `report.py`, and its Stop hook hands in her notes, requests and files when
its turn ends. It does nothing until `CATIO_URL` and `CATIO_TOKEN` are set. Workers Builds deploys it on every
merge to `main`.

1. **She sets it up once** (`harness/gateway/README.md`):
   - deploy the Worker from this repo;
   - two secrets;
   - `CATIO_URL` and `CATIO_TOKEN` in each Claude environment, with the Worker allowed in the network policy;
   - the `Catio` connector in claude.ai, its tools set to Always allow.
2. **The page reads the gateway.**
   - Declare the `Catio` connector (`list_agents`, `comment`, `comments`, `manage`, `drop_file`) beside
     `host:catio`. First check that an artifact may name a custom connector.
   - Show its cats next to the sessions, live.
   - Match a gateway cat (`via: claude-code`, `session`) to the session it is, so no session shows twice.
     Compare the ids after their prefix, in case one is `cse_…` and the other `session_…`.
   - Send to a gateway cat through the gateway, not the outbox, so a running session gets it at its next Stop.
3. **Later:**
   - agents the gateway runs itself (the rest of OpenClaw), which would need a machine;
   - a Telegram channel;
   - agent cats through `host:catio` (only the Claude desktop app can declare it). Agents that report to the
     gateway show up anywhere, through the `Catio` connector;
   - `catio-plugin/` listed in the marketplace beside `kittychat-house-rules`.

## Waiting on Charlotte

1. **Set up the gateway:** the five steps in `harness/gateway/README.md`.
2. **Which comes first:** phase 2 (the camera) or the page reading the gateway (phase 5).
3. **The posts waiting since 30 September**, which a session collects only when it next runs:
   - two messages to Clafoutis;
   - one to Matcha;
   - Nougat's "yes";
   - an archive request for another Nougat session, which Claude can do on her word.
4. **Rotate the MCPmarket token** in her plugin zip's `.mcp.json`.
5. **Small questions:**
   - who made `plants.zip`;
   - whether Rename should rename the real session;
   - whether attic cats should sit on the stairs;
   - whether to delete the Drive folder's `download` files.
6. **Branches she may delete:**
   - `claude/digest-moves`;
   - `claude/elegant-edison-cnmcq7`;
   - `claude/exciting-bardeen-9vehk0`;
   - `claude/friendly-shannon-ykj7u1`;
   - `claude/kittychat-digest`;
   - `claude/openexecutive-repo-eval-lbilmm`;
   - `claude/cool-cannon-wh25u6` and `claude/eloquent-thompson-e9b2uh` (merged 2 October);
   - `claude/catio-gateway-plan`, the gateway's first draft (it needed a server and a domain). Not merged:
     `harness/gateway/` replaces it.

   This session's git access can't delete them.

## Publishing

1. CLAUDE.md's "Checking a change": looked at against her words, then `sh catio/test/run.sh`, everything passing.
2. Read the live artifact in full (`Artifact` read, then every line of the saved file), and compare it with
   the branch's page. If the live one is newer, merge it first; never overwrite it.
3. Publish `catio/index.html` to `artifacts.json`'s URL with only the files that changed, and **omit
   `capabilities`** to keep the stored set:
   - Claude Code Remote's eight tools: `list_sessions`, `send_message`, `delete_trigger`, `create_session`,
     `set_session_title`, `archive_session`, `unarchive_session` and `interrupt_session`;
   - `db`, `assets` and `sample`.

   Pass `capabilities` only to add something on purpose (the `Catio` connector, in phase 5), and then pass
   the whole set.
4. Afterwards: list the files, read back and look at any art that changed, list `rooms`, and create, update
   and delete one probe in `cats`.
5. Add a line to `docs/history.md`.

## Rules worth repeating

- **No Claude attribution lines** (`Co-Authored-By: Claude`, `Claude-Session:`) in commits on her public
  repos or forks: this one, the grocery app, Snail-Mail-Trail and the LibreSprite fork. She asked on
  1 October; the gate hook enforces it (`harness/rules.json`).
- The gateway's two secrets (`CATIO_TOKEN`, `CATIO_PASSWORD`) live only in Cloudflare and her Claude
  environments: never in the repo, the chat or a test.
- Never commit `art/licensed/`, `catio/data/sessions.json`, `catio/dist/` or anything from her sessions.

## Known limits

- **claude.ai refuses the page's Claude Code Remote calls**, except reading sessions, and sometimes that too.
  It is built in, so her Connectors list has no switch for it.
- **Nothing outside claude.ai can wake an idle session.** Messages to one wait for its next turn.
- **The Drive connector hands over files up to about 10 MB.** Bigger zips are attached in the chat.
- **`host:catio` works only in the Claude desktop app**, and only for the artifact's owner.
- **A write tool that fails with `server_unavailable` or `upstream_error` may have run anyway.** The page
  queues these rather than retrying.
