# The KittyChat Café: the plan

Issue #3: "An AI harness that presents itself as a cat cafe." The KittyChat Café (`catio/index.html`, one
private artifact) is the harness. Every Claude Code session and every other agent is a cat in a two-floor
manor. Files dropped on the page go to the right cat, and cats can be talked to and managed.

Last revised 5 October 2026. How it got here, version by version, is in `docs/history.md`; what she has asked
for, in `docs/requests.md`; the audit behind phase 0, in `docs/audit-2026-10-01.md`.

## Where it stands

Updated 4 October 2026.

- **Live:** the café's artifact (`kittychat-cafe` in `artifacts.json`), republished on her say-so, so it can trail `main` until the next
  publish.
- **`main`** has, beyond phase 0's honest café:
  - the house rules, on in all seven repos, with no Claude attribution on her public repos, and semi-automatic
    merging where a repo opts in;
  - the gateway, set up on 2 October (her `CATIO` connector): live cats, the café on its own address behind her
    password, and accounts phase 1 (`docs/accounts.md`);
  - the queen of the house and her runner, her routines, and the quest log: homework, the litter box and decisions
    as cards in her card;
  - the decider, logging beside the sorter (`docs/delegation.md`);
  - onboarding (phase 7), Project maps, and outlines on hover;
  - the open-source licence (AGPL-3.0), the shop's wireframes and plans, and the Buy Me a Coffee and Ulule kit
    (`docs/kittychat-shop/`);
  - plug-and-play design: every colour, font and size a token and every piece of art a slot, changed from The look
    or `art/skin.json` (`CLAUDE.md`);
  - the engine under the café, for builders (`docs/engine.md`);
  - the C++ phone app, whose core draws the manor (`docs/mobile-app.md`).
- **Tests:** the commands are in the README's Files section. The page's suite needs the licensed art
  (`CLAUDE.md`, "Checking a change").

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
- **The queen is the third road:** her runner (`harness/runner/queen.py`) waits on the house in a held request,
  runs one Claude Code turn per note or routine, and streams her words back. Every hop, and the design against
  scale, speed, extensibility, security, debugging and tests: `docs/delivery.md`.
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
That part is built (3 and 4 October, "Allow all assets to be plug-n-plays", "the entire design system"): every piece
is a slot and every colour, font and size a token, changed from The look in the House menu or `art/skin.json`, with
no code change (`CLAUDE.md`, "Plug-and-play design").

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
   - its secrets (`harness/gateway/README.md`);
   - `CATIO_URL` and `CATIO_TOKEN` in each Claude environment, with the Worker allowed in the network policy;
   - the `CATIO` connector in claude.ai, its tools set to Always allow.
2. **The page reads the gateway. Done (2 October):**
   - it declares her `CATIO` connector (`list_agents`, `comment`, `comments`, `manage`, `drop_file`): a page may
     name any of her claude.ai connectors by its display name. Without it, `host:catio`, as before;
   - its cats are read every 30 s, next to the sessions;
   - a gateway cat (`via: claude-code`, `session`) is the session it reports for, matched after the id's prefix
     (`cse_…` there, `session_…` in the list), so no session shows twice, and it wears the newer of the two moods;
   - what she writes or drops on it goes through the gateway, not the outbox, so a running session gets it at its
     next Stop; its answers there (`report.py say`) show in its conversation;
   - when CATIO asks before every call or needs signing in again, the House menu says so.
3. **Later:**
   - agents the gateway runs itself: phase 6; small cats on Haiku and Sonnet for the easy work, and the queen
     delegating to them: `docs/delegation.md`;
   - a Telegram channel;
   - agent cats through `host:catio` (only the Claude desktop app can declare it). Agents that report to the
     gateway show up anywhere, through the `CATIO` connector;
   - ~~`catio-plugin/` listed in the marketplace beside `kittychat-house-rules`~~: done
     (`.claude-plugin/marketplace.json`).
   - accounts, one café per person: the recommendation is `docs/accounts.md`.

### Phase 6: the Catio as the UI for all her sessions, in OpenClaw's shape

Her ask (2 October): "I want to be able to use the catio as a UI for all of my Claude sessions", not an artifact,
and "Open session" not sending her back into claude.ai. OpenClaw's gateway serves its Control UI from its own
address and runs the sessions itself, so the UI is where you chat (`chat.send`, `chat.history`, `chat.abort`); a
coding agent such as Claude Code runs on "the machine that runs the coding agent", which dials out to the gateway.
Claude Code sessions in claude.ai stay claude.ai's: their full conversation opens only there.

1. **The café on the gateway's address.** Built (this branch): sign-in, the page with `cafe/runtime.js`, her data
   in the house with live pushes over a WebSocket, art and brain files in KV, `cafe/move-in.py` to move in.
   Go-live: she merges, Workers Builds deploys, Claude runs `move-in.py` with the artifact's database.
2. **Chat in the café.** Built (2 October): one queen of the house, in the entrance hall, that she talks to like an
   NPC. Her words: "Merge the queen cats to make one main character queen cat that you chat with that does
   everything for you"; voice to text; a character she can customise, with routines; cats with handoffs visibly
   passing things to her; a proper Elizabethan manner; a voice that turns on and off. The gateway keeps her
   conversation (the cat `queen`), streams her answer to every open café, and Stop ends her turn. Her voice and
   ears are the browser's own (free; Chrome or Edge); a paid voice (ElevenLabs, OpenAI) through the gateway is a
   later option, behind the same switch. Homework (her ask the same evening): the queen sets quizzes to unblock
   cats, answered by tapping in her card; the answers reach the cat as Charlotte's words.
3. **The runner.** Built (2 October): `harness/runner/queen.py`, on her Windows PC (her choice: free, while it's
   on), signed in with her Claude plan, holding the queen's own key (`CATIO_QUEEN`). It waits on the gateway, runs
   one `claude -p` turn per thing she says or routine due, with the Catio's tools and nothing that edits files,
   and streams the answer back. Routines run while it runs. Go-live needs her: the secret on the Worker, the two
   variables on the PC, `python harness\runner\queen.py` (`harness/runner/README.md`).
   Always-on homes, if she wants one later (prices of October 2026): Cloudflare Containers next to the gateway
   ($5/month Workers Paid, sleeps when idle, about 7¢ a working hour at 4 GB), Hetzner CAX11 (€5.99 + €0.50 a month),
   Oracle's Always Free ARM machine (2 cores, 12 GB since June 2026), a Raspberry Pi. Claude Code needs 4 GB.

### Phase 7: onboarding. Built

A café with no rooms opens a seven-step wizard (`docs/onboarding/`): name, rooms (the rest closed), repositories
through `list_repos`, sessions, the litter box, how it works, done. The public `catio` skill asks the same
questions. Closed rooms are dimmed, queenless and get no cats. CLAUDE.md, "Onboarding".

3 October: the wording went plain (`docs/onboarding/README.md`, "Decided 3 October"). The wizard's Welcome and How it
works steps use the café's words, not MCP, API or hooks, in `openSetup()` and in the wireframes alike, and the
README opens with "In plain words". The steps that instruct still name the real tools. Still to do: republish the
page. A hosted café is planned, not open: the onboarding offers running your own.

## The first player: a friend's run, 4 and 5 October

@ohwellwhy10-jpg is the first person outside the house to run the café. He is on Windows, at home in GitHub and Cloudflare,
works through Claude Code, and isn't a developer by trade: the second of the two audiences (docs/requests.md, 3 October),
on the harder road of running his own. His run is the café's first user test. Each step below is what he did, what it
cost him, and what changed so the next player doesn't pay it. Everything he wrote is in charredlatte/Pretty-Project-Portfolio#80, #81, #99, #100
and #102, and in his fork (ohwellwhy10-jpg/Pretty-Project-Portfolio, `main` and `theme/dog-den`).

| # | What he did | What it cost | What changed |
|---|---|---|---|
| 1 | Served `catio/` with `python -m http.server` | A dead page: no charset, so the script never ran | #80, his own fix: `<meta charset>` |
| 2 | Ran the harness tests on Windows | cp1252 crashes, and a real `claude` answering instead of the stub | #81 (through #90), his own fix, and CI on Linux and Windows |
| 3 | Sent #81 from a branch that wasn't from `main` | A round trip: "you're on the wrong branch" | `CONTRIBUTING.md`: one branch per change, from a synced `main` |
| 4 | Joined Charlotte's gateway by invite | No cats: the invite page never said the plugin does the reporting | #98, #99 |
| 5 | Forked to run his own café, the Dog Den, and rebranded it by editing `index.html` and `rooms.json` by hand | Two art paths outside the slots, and `Café` saved as `CafÃ©` | `CONTRIBUTING.md` and the README's "Make it yours without touching the code" (the wizard's name, Edit rooms, The look, `art/skin/`); `.editorconfig` asks for UTF-8 |
| 6 | Renamed the Worker in `wrangler.jsonc` | A build Workers Builds refuses unless the dashboard's name matches | The README's step 4 and the gateway's README say so; `docs/self-hosting.md` lists `name` |
| 7 | Opened his gateway: "The gateway has no account yet", from the first load, though the secrets "exist" | The worst of it: the reason was a second sentence on the same red line, under a sign-in form that could never work, so he kept retrying `charlotte` and asked whether to reset everything | #103 (the handle, once only), then #104: until there is an account the page shows one warning light per secret as this Worker sees it, the handle it will have, and no form |
| 8 | Sent his Dog Den changes here, titled "Maybe will fix Log-in?" | A pull request that would have renamed her gateway on merge; closed | `CONTRIBUTING.md`: your café stays on your fork |
| 9 | Reported with a screenshot alone | Text we couldn't read or search, and no way to tell his fork was a day behind | The issue form, "Something isn't working": which café, the words as text, the fork's last sync |
| 10 | Hardened the gateway on his fork (his fork's pull request #1) | His Sync fork would conflict in three files with the day's fixes | His two commits brought here, merged with `main`, so the sync is clean |
| 11 | Signed in to his own gateway at last (18:42), then asked his Gemini to connect | The repositories step can't work on a café's own address, and the café's automatic check-ins exist only as a Claude Code plugin | #113: no Connect GitHub button there; Gemini joins through the café's MCP address and reports when asked (#100) |
| 12 | Connected his "Gemini": Antigravity, Google's agent editor, which only starts MCP servers as local programs | Our answer was Gemini CLI's address-and-key settings, which Antigravity can't take, and the harness README's local server (`catio_mcp.py`) keeps its cats on the computer it runs on, where his gateway never sees them | He wrote `catio_bridge.py` (his fork's PR 4), a local program that passes everything on to the gateway; brought here, and the harness README now says which server goes with which café |
| 13 | Made an agents' key for it | No button: he pasted a `fetch` into the browser's console | Keys in the House menu of a café on its own address (`openKeys()`): a key made from a name, shown once beside `CATIO_URL` and `CATIO_TOKEN` with Copy, and deleted after it asks; the console line is only for a café from before it |
| 14 | Audited the gateway and the MCP server again, fixed what he found (his fork's PR 5) and wrote it up (#115) | His docs-only pull request went red, through nothing he changed: `main` was broken (#114) | #114 restores `main`; his PR 5 and PR 4 brought here, with the same 500 found in sign-up and invites, which his fork doesn't have |

**What the decider guessed** (5 October, `decide` with kind `ux-test-1` in the house's log; Clef answered, as Jev had no
AI Gateway credits). Asked about the run above, it put the lights page far ahead as the fix that would have let him
through step 7 alone (0.97, against 0.03 for a longer guide), and step 7 as where a player at his level most likely
gives up (0.85). Its likeliest causes for step 7 were a build variable (0.43) or the secrets sitting on another Worker
(0.36), with little confidence (0.20): the lights were built to tell them apart instead of guessing. It expects
encoding damage on Windows again (0.89), thinks he edited code because the no-code ways weren't where he looked first
(0.86), that an issue form saves a round trip (0.91), and that a "where does my change go" note would have spared steps
3 and 8 (0.75). Keeping the fork synced it gave even odds (0.48): it is in the README all the same, since step 7's
clearer messages were a day old.

**What players at his level can do, and where they trip.** They follow copy-paste steps, find their way around GitHub's
and Cloudflare's dashboards, run a test suite, and even fix the café (steps 1 and 2 were his own pull requests, and his
fork's `main` carries a hardening pass of the gateway, with an adversarial suite). They trip on:

- **State they can't see.** The first account is made once, by the first request; a variable in one Cloudflare tab works
  and the same name in the next doesn't. A page that shows what the Worker sees beats any paragraph saying what it should
  see.
- **Two homes for one change.** Fork and upstream, their café's branch and a fix's branch. Say where each change goes
  before they make it.
- **Windows.** Encodings, `python` for `python3`, no shebangs. CI on Windows catches the code; `.editorconfig` and the
  diff catch their files.
- **Errors inside pictures.** Ask for the words as text, and make the words on screen say exactly what to do.

**The walkthrough after him** (5 October, evening). Six players walked the docs as he would have (an invitee, a Windows
self-hoster, a claude.ai-only owner, a Mac contributor, a localhost user, and someone waking the queen), the
recent changes were sifted for docs they made wrong, and a sceptic refuted every friction point: 130 survived, 10
blockers, 43 majors and 77 minors. The blockers are fixed in #110 (the wizard crashed without the art for every
guest, a sign-up gave no key, the bundle's server died on start) and 40 majors in #113 (the README's fork, the invitee's
path, the CATIO name, the hooks on Windows). Left: the 77 minors (the walkthrough's output, re-run it to list them),
and the two below that are hers. **Players use other assistants:** he reached for Gemini first, so a café that only
Claude Code can check in to automatically will lose the second audience; a check-in for other agents as easy as the
plugin is worth a place on the roadmap. And "Gemini" may be the CLI, Antigravity or the app, each joining differently
(step 12): ask which, and lead with the bridge, which works for any client that can start a local program. A red check
they didn't cause reads as their fault (step 14): say so on their pull request straight away.

**What it means for the shop** (`docs/kittychat-shop/`). Running your own gateway took him more than a day and is
still not done. For the second audience the invite to a hosted café is the door, and running your own is the
developers' door, as the README already says; the Set up for you plan sells exactly the afternoon he spent. Every new
player's run gets a row here, and anything worse than step 7 is fixed before the hosted café opens.

## Waiting on Charlotte

The decisions below are dealt as decision cards in the queen's quest log (her card in the café on the gateway's
address, and in claude.ai once a publish passes the whole stored set, which now has `quizzes` and `answer`; the
decisions quiz page is retired). The small facts (who made `plants.zip`) stay here.

1. **The gateway is set up** (2 October): the Worker, the two secrets of the time (the queen's key came later, below), `CATIO_URL` and `CATIO_TOKEN` in her
   environment, the setup script that installs the plugin, and the connector, signed in. A session reported
   through the hook and showed in `list_agents`, once PR #26 gave the hook its own User-Agent (Cloudflare refuses
   Python's). Left for her: set the connector's tools to Always allow, if she hasn't.
2. ~~Which comes first: phase 2 (the camera) or the page reading the gateway (phase 5)~~: the page reads the
   gateway (2 October).
3. ~~The posts waiting since 30 September~~: delivered from a session on 2 October with Claude Code Remote's
   `send_message` (four messages, one archive; two were already done) and marked delivered.
4. **Rotate the MCPmarket token** in her plugin zip's `.mcp.json`.
5. **Small questions:**
   - who made `plants.zip`;
   - ~~whether Rename should rename the real session~~: yes (3 October). Renaming a session's cat retitles the
     session in claude.ai too, unless she types a title of her own in the same save;
   - ~~whether attic cats should sit on the stairs~~: no, they stay out of sight (3 October);
   - whether to delete the Drive folder's `download` files.
6. ~~Turn the house rules on in the cloud~~: done 2 October, the two lines are in the environment's setup script
   and a restarted session had the rules on.
10. **The queen's key and her runner** (after the queen's pull request merges): the secret `CATIO_QUEEN` on the
    Worker, then on her PC `setx CATIO_URL`, `setx CATIO_QUEEN` and `python harness\runner\queen.py`
    (`harness/runner/README.md`). Then open the café in Chrome, click the queen in the hall, turn her voice on,
    and talk to her.
7. **Turn on *Automatically delete head branches*** in each repo (Settings → General → Pull Requests), so a
   merge deletes its branch.
8. **Opt the other repos in to semi-automatic merging**: she said yes for all of them (3 October). A session's
   attempt was refused by Claude Code's own permission check, as a session widening its own merge rights, so the
   change is hers to make: `{"merge": true}` in each repo's `.claude/catio-rules.json`. For montfortoise-shopify the
   suggestion is `{"merge": true, "hold": ["components/"]}`, since `components/` is what gets installed on the live
   theme.
9. **Branches she may delete:**
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
11. ~~**The first player's fixes** (PR #104, above)~~: merged 5 October; he signed in to his own gateway at 18:42.
12. ~~**His hardening pass**~~ (his fork's PR 1, brought here with his commits as they are): merged 5 October (#105).
13. **Jev for the decider**: `typesafe/jev` answers only with AI Gateway credits ("Insufficient AI Gateway credits",
    5 October). Until they are topped up, Clef answers, free.
14. **A guest's café draws no art.** The packs' licences are personal, so only her own café is given them, and an
    invited player's café is plain panels with no house or cats. Hers to decide: her own drawings as the guests' art
    (`docs/drawing-plan.md`), or a plain café on purpose and said so on the invite.
15. **`plants.zip`'s source.** It reached her with no artist or licence; until it is credited, or its four plants
    are drawn from another pack, nobody else can run the full art build.
16. **His audit fixes** (#115 describes them): his fork's PR 5 and the Antigravity bridge under it, brought here like
    item 12 and merged with `main`, with the same fix for sign-up and invites. It touches `harness/`:
    hers to merge.
17. **In flight on 5 October, late** (her tokens were running out, so each lands as soon as it passes): #112's
    improvements ported onto delegate-first (what #114's description lists: no guessing a task's ease from its words,
    a typo in a repo's cap reported, the gates failing closed, one transcript reader), and a Keys item in the House
    menu of a café on its own address (step 13 above). Both are pushed; the port's review was still to come.

## Publishing

1. CLAUDE.md's "Checking a change": looked at against her words, then `sh catio/test/run.sh`, everything passing.
2. Read the live artifact in full (`Artifact` read, then every line of the saved file), and compare it with
   the branch's page. If the live one is newer, merge it first; never overwrite it.
3. Publish `catio/index.html` to the café's URL (`kittychat-cafe` in `artifacts.json`) with `files` and
   `capabilities` as CLAUDE.md's "Republishing" says: leave `capabilities` out to keep the stored set, unless CLAUDE.md's
   "The stored capabilities" says a tool joined since the last publish, or to add one on purpose, and then pass the
   whole set it gives.
4. Afterwards: list the files, read back and look at any art that changed, list `rooms`, and create, update
   and delete one probe in `cats`.
5. Add a line to `docs/history.md`.

## Rules worth repeating

- **No Claude attribution lines** (`Co-Authored-By: Claude`, `Claude-Session:`) in commits on her public
  repos or forks: this one, the grocery app, Snail-Mail-Trail and the LibreSprite fork. She asked on
  1 October; the gate hook enforces it (`harness/rules.json`).
- The gateway's three secrets live only in Cloudflare and one other place each: `CATIO_TOKEN` in her Claude
  environments, `CATIO_PASSWORD` nowhere but her password manager, `CATIO_QUEEN` on the queen's runner. Never in the repo,
  the chat or a test.
- Never commit `art/licensed/`, `catio/data/sessions.json`, `catio/dist/` or anything from her sessions.

## Known limits

- **claude.ai refuses the page's Claude Code Remote calls**, except reading sessions, and sometimes that too.
  It is built in, so her Connectors list has no switch for it.
- **Nothing outside claude.ai can wake an idle session.** Messages to one wait for its next turn.
- **The Drive connector hands over files up to about 10 MB.** Bigger zips are attached in the chat.
- **`host:catio` works only in the Claude desktop app**, and only for the artifact's owner.
- **A write tool that fails with `server_unavailable` or `upstream_error` may have run anyway.** The page
  queues these rather than retrying.
