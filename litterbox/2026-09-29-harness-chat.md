# 29 September 2026: building the KittyChat harness (compressed)

## What she asked for, in order

1. Issue #3: "An AI harness that presents itself as a cat cafe. The KittyChat Cafe."
2. Drag and drop chats, downloads and other files into "the brain", each filed to the right session or cat.
3. The house becomes a **refurbished manor**. There are **house rules** for the harness, starting with the
   preflight skill every time an agent uses a browser. Other models can connect.
4. After seeing the plan:
   - private matters must stay out of git repos, but may be saved to the Catio's own storage;
   - sessions can be managed and commented on from inside the harness and the MCP server;
   - "I would like for the page to push to a session. I want a true harness."
   - renovation mode: drag furniture around, and add or remove the non-essential and unconnected pieces;
   - a cat's **position** shows its state, not a mood face;
   - more rules: a read-only ponytail audit when a session opens; PRs and pushes happen automatically
     when reasonable ("semi-automatic auto mode");
   - she would add CatMegaFree.
5. Her answers to the questions:
   - she uploads the zips;
   - the rules ship as a plugin for every repo;
   - other models means Claude breeds, other models doing the sorting, other agents' sessions, and any
     MCP client.
6. "You're running out of tokens. Make sure you push to main and merge 5."
7. Add the renovation notes to the repo, build the manor a room at a time, revise the plan, compile and
   compress this chat, and put useful leftovers here.

## What was found

- **The live artifact wasn't `main`.** A Sprout Lands reskin with room queens and a rooms redesign was
  live from PR #5's branch (`claude/charming-dirac-f7g4pr`). This work was built on top of it, and PR #5
  was merged.
- **A page can post into a session.** It makes a Routine bound to that session (`create_trigger` with
  `persistent_session_id` and no schedule), then fires it (`fire_trigger` with text). The text arrives as
  a turn in that session.
- **claude.ai may refuse the page these calls.** PR #5's session found Claude Code Remote has no switch in
  her Connectors list. So every post falls back to `outbox/`.
- **The Drive connector can't hand over big files.** It returns each one inline as base64. The zips had to
  be attached in the chat.
- **Claude's own edits to `.claude/settings.json` and `CLAUDE.md` are refused** as self-modification.
  Those two changes are hers to make.
- **`list_sessions` gives each session a model and an environment:** `environment_id`,
  `session_context.model`, `configured_model` and `external_metadata.last_served_model`.

## What was built (all on `main`)

- **`harness/`: the `kittychat-house-rules` plugin and the MCP server.**
  - `rules.json` holds the three enforced rules and five soft ones.
  - Hooks:
    - `gates.py`: preflight before browsers; the audit before any edit, commit or push;
    - `ship_check.py`: a nudge when work is left unpushed;
    - `session_start.py`: prints the rules.
  - The `catio` skill handles deliveries, messages, requests and the catch-up.
  - `mcp/catio_mcp.py` is the MCP server for other agents: stdio, `--serve`, and wake commands.
  - 15 tests.
- **`catio/index.html`:**
  - the brain: drop, sort, the tray, "File under", throw away;
  - pushing into sessions, with the outbox as fallback;
  - conversations in `notes/`;
  - managing a cat: title, pause, wrap up, archive, New cat on a model;
  - breeds, agent cats, the house-rules panel, dragging cats between rooms;
  - on localhost, files are kept in IndexedDB and any OpenAI-compatible model can sort.
  - The e2e test grew from 72 to 97 checks.
- **`docs/renovation-mode.md`**: the rooms-redesign session's constraints. **`docs/plan.md`**: the revised plan.

## Left open

See `loose-ends.md` and `docs/plan.md` ("Blocked on Charlotte" and "Next").
