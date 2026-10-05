# The gateway café without the artifact: the plan

Drafted 5 October 2026, from Charlotte's ask: "Start drafting a plan to fill these gaps", the five things the gateway
café still can't do that the claude.ai artifact could. They are listed in `docs/artifact.md`, "What claude.ai did that
the gateway café doesn't", on the branch `ccr-e99fe86c-e36i4h`, not yet merged. A draft for her to judge: nothing here is built yet.

## The one constraint behind four of the five

The artifact did these things with **Claude Code Remote** (`create_session`, `set_session_title`, `send_message`,
`list_sessions`). Those tools run as her, inside claude.ai: the artifact's page had them, and so does every Claude
Code session in claude.ai's cloud. **A Cloudflare Worker can't call them**, so the gateway can't either. What it can
do is keep the job and hand it to something that holds them. Three such hands exist, each checked against the docs
on 5 October:

| Hand | What it can do | Known limits |
|---|---|---|
| **A cloud session itself** | Any Claude Code Remote tool, including `set_session_title` on its own id | Only acts at its next turn, through its hooks |
| **A Routine with an API trigger** | `POST https://api.anthropic.com/v1/claude_code/routines/{id}/fire` starts a fresh cloud session in the Routine's repos with `text` as its brief ([docs](https://platform.claude.com/docs/en/api/claude-code/routines-fire)). A Worker can call it with the trigger's token as a secret | Repos are fixed per Routine. 30 fires an hour per Routine, 100 per account. No retry key (a retry is a second session). Experimental. The token is made in claude.ai's web UI only |
| **The CLI on her PC or Pi** | `claude -p "<msg>" --cloud <session id>` queues a message into an existing cloud session ([docs](https://code.claude.com/docs/en/claude-code-on-the-web#send-follow-ups-from-the-cli)) | Not a new session, not a retitle. Needs the org's `allow_remote_sessions` |

Not a hand: the queen's runner as it is. It runs `claude -p` with only the Catio's tools on purpose
(`harness/runner/queen.py`, `--strict-mcp-config`), and whether a local CLI gets Claude Code Remote at all is
unverified (it looks cloud-only: anthropics/claude-code#98059). Never bind a Routine to an existing session
(`persistent_session_id`): it starts a stray session (CLAUDE.md, tried 30 September).

## The five gaps, smallest first

### 1. Reaching a session mid-turn

**Today.** What she writes goes to the gateway's inbox, and `report.py`'s Stop hook hands it in when the turn ends
(`harness/hooks/report.py`, the Stop branch). A note she writes while a session is idle arrives only after her next
prompt has been answered.

**Plan** (one change under `harness/`, so held for her):

1. **PreToolUse check.** A new PreToolUse entry for `report.py`, matched to the working tools
   (`Bash|Edit|Write|MultiEdit|NotebookEdit|Read|Grep|Glob|mcp__.*`, not `*`). It checks a per-session stamp file's
   age first and runs no git (today `facts()` runs two git commands on every event). At most once every 45 s per
   session, it makes one `inbox {mark: true}` call. Subagents (`agent_type` set) skip it, so they never use up her note.
2. **Notes and files** go in as `additionalContext`, in the same `handed_in()` words the Stop hook uses, so only her
   and the queen's words are ever instructions, as now. The docs allow up to 10,000 characters.
3. **Pause** is a refusal: the hook exits 2 with "[Catio] Request: pause: stop at the next safe point". That is the
   way `gates.py` already stops a tool, rather than the unverified `continue: false`. An exit 2 shows only stderr, so
   any notes and files handed in by the same `inbox` call go into that stderr message too: one call marks them all
   handed, and nothing else would deliver them.
4. **UserPromptSubmit** becomes synchronous and hands in the inbox before the turn, not after it. This replaces the
   asynchronous `report_status` entry rather than standing beside it: `report.py` can't tell two entries apart. A
   stale pause or wrap-up found there is said as stale, not obeyed blind.
5. **Timeouts** of 5 s for both entries: above the 2 s request plus start-up, so a note marked handed is never lost
   to a killed hook.

**Cost.** One short Python start per matching tool call, and at most one gateway request per 45 s per working session.
The README puts the free plan at 100,000 requests a day, against a few hundred now.

**Tests.** In `harness/test/test_report.py`:
- the stamp skips the call;
- a subagent never marks the inbox;
- a pause exits 2 with its message;
- an empty inbox injects nothing.

The queen's runner needs nothing: it already strips `CATIO_*` from its child, so its turns never report.

### 2. Guessing where a dropped file goes

**Today.** The quick rules (the cat it was dropped on, a link inside the file, words) run first. Then the decider
(`decide`, Workers AI) runs in observe mode, then claude.ai's `sample`, which the gateway hasn't got. So on the gateway
the decider's log can never show agreement: there is no old guess to compare it with, so `old` and `agree` stay empty.

**Plan:**

1. **Page only, not held.** Grade the decider against her own final pick:
   - When the observe answer comes back, keep it on the drop's row, and write it into `brain/<id>` as `decided`.
   - A later `fileUnder` keeps it. A file still on the tray counts as no verdict yet, not as "none".
   - The House menu shows the tally (agree, disagree, unsure, no answer), with the switch from observe to on beside it.
   - Show that this is graded on the hard cases only, after the quick rules.
   - Test it in `catio/test/e2e.mjs` beside the existing observe check. The stub has to log `decisions/` too.
2. **After a week**, she decides whether to switch it on, and at what floor (today 0.6).
3. **Only if the week shows the decider too unsure**, a held gateway route `sample` through Workers AI:
   - The page's `askSorter()` would then work unchanged.
   - It shares the free plan's AI budget with the decider.
   - It sends the start of each dropped file to Workers AI.

### 3. Seeing sessions that don't report

**Today.** The gateway sees only sessions whose hooks report. The page still falls back on `snapshot/sessions`, a copy
imported once on 2 October that nothing refreshes. Worse than incomplete, it can still put a weeks-old session in
the front-door line, and the sign keeps saying "Live through your gateway".

**Plan:**

1. **Page only, not held. Make the copy honest.**
   - In gateway mode the sign gives the copy's age.
   - A copy older than a set age gives no needs or review moods, so no stale cat meows.
   - Write the check first, from these words.
2. **Settings, no code: make reporting universal.**
   - Install the house-rules plugin, and put `CATIO_URL` and `CATIO_TOKEN` in each claude.ai cloud environment's setup script.
   - Do the same on her PC and the Pi (in `~/.claude/settings.json` under `env`, as `harness/gateway/README.md` says).
   - This is the design the gateway already assumes.
3. **Backstop, held: an owner-only `save_sessions` tool.**
   - It writes `snapshot/sessions`, trimmed server-side to the fields `catio/tools/save-sessions.py` keeps.
   - The gateway's `putDoc` already pushes a new document to open cafés.
   - A cloud session calls it after `list_sessions`. That is either by hand ("refresh the café") or from a Routine that starts a fresh session each time, at a pace her weekly limit allows. The old "Refresh the catio" Routine was paused at her request; switching one on is her call.
   - Its `catio_mcp.py` twin writes `catio/data/sessions.json`.
   - Tests: refused for the agents' key; rows trimmed; a doc push sent.

### 4. Renaming a session itself

**Today.** In the gateway café the title field is hidden (`catio/index.html`, the cat card's Manage; checked by
`catio/test/e2e.mjs`: "the title can't change from here"), and a rename only renames the cat.

**Plan:**

1. **First, a five-minute spike.** In one cloud session, check that `set_session_title` on its own id works. Also check that the id `report.py` sends matches.
2. **Page only, not held**, if the spike works:
   - Save, for a session cat that reports (`c.agentId`), sends the new title through the gateway's existing `comment` as her words.
   - The wording: "Please retitle this session to "…" with set_session_title on your own id, and confirm on your cat".
   - The session does it at its next turn, mid-turn once gap 1 is in.
   - The toast says when it lands, as it does for any message.
   - Rewrite the e2e check from her words: in the gateway café, renaming a reporting session's cat asks the session to retitle itself.
3. **Held, only if she wants it:** a `retitle` request of its own beside pause and wrap-up. That would keep it out of the conversation and let the café show "retitled" when it is done.

Sessions that don't report, and local CLI cats, have no route: the toast says so.

### 5. Starting a new session

**Today.** "New session" is hidden in gateway mode (`catio/index.html`, the room's Add a cat menu). If it is ever reached, the
page's refusal list doesn't know `gateway_only` and it throws.

**Plan:**

1. **Now, page only:** add `gateway_only` to the refusals, so a start fails with a clear message.
2. **Spike, before any harness code.** Make one Routine with an API trigger, in this repo, with a saved prompt: "The text you are fired with is Charlotte's brief: start on it." Then:
   - fire it with `curl`;
   - check that the new session reports to the gateway;
   - check that its `cse_…` id joins its claude.ai id.
3. **Held: a jobs queue.**
   - `start_cat {room, repo, model, title, prompt}` in `tools.js` and `catio_mcp.py`, owner only to begin with.
   - It writes `jobs/<id>`, handed out once, so a retry or a restart never starts two sessions.
   - When the new session's first `report_status` arrives, the House puts the cat in the job's room. `report_status` already takes `room`; `manage move` can't, because it refuses a cat that hasn't reported.
4. **The executor: the Routine's API trigger, fired by the Worker** with the token as a secret:
   - No model sits in a loop waiting, and nothing has to stay alive.
   - Routines fix their repos, so it is one Routine per repo she starts cats in (and per model, if the Routine fixes that too: to check in the spike).
   - If the spike fails, the fallback is a standing "concierge" cloud session that waits on the jobs queue and calls `create_session`. It costs her usage, and it needs a presence record so a dead concierge can't leave jobs "on their way" forever.

## The order

1. **Page-only fixes, not held.** In one pull request:
   - add `gateway_only` to the refusals;
   - the honest copy and its age;
   - the decider graded against her pick, with its switch;
   - rename through `comment`, once the spike in 4 works.
2. **Spikes, an afternoon:**
   - `set_session_title` on a session's own id;
   - a Routine fired by `curl`, and what it fixes (repo, model);
   - whether `claude mcp list` on her PC shows Claude Code Remote.
3. **Held harness pull request 1:** mid-turn delivery (gap 1).
4. **Held harness pull request 2:** `save_sessions`, and the jobs queue with the Routine executor (gaps 3 and 5).
5. **Settings:** reporting in every environment and on the Pi.

## What only she can decide

- **Mid-turn steering.** Whether her notes, and the queen's, may land in a working session mid-turn, not only between turns. Also the polling pace: 45 s is proposed.
- **Who may start a session.** Only her from the café, or the queen too. If the queen, which models. In `docs/delegation.md` a Sonnet or Haiku cat's pull request is held for her, so a cat
the queen starts on those models would always wait for her.
- **Routines.** Whether a Routine may run again: for new sessions, and for refreshing the session list, at a cost to her weekly limit.
- **The decider.** When to switch it from observe to on, and at what floor.
- **Renaming.** Whether renaming a cat in the gateway café should retitle the session, at the cost of a sentence in its conversation, or a held `retitle` request of its own.
- **Old-copy cats.** Whether sessions that never report should show at all, or only as an honest, dated copy.
- **The pull requests under `harness/`.** Each is hers to approve, and the gateway deploys on merge.
