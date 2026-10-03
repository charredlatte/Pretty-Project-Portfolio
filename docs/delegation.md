# Delegating the easy work to smaller models

**Status (3 October 2026): the café has no automatic delegation.** Every cat runs on the model it was started with,
chosen by hand. This is the plan to add it, cheapest step first, each one useful on its own.

## What exists today

- **A breed per room.** `rooms/<k>.model` is the model a New cat gets in that room (`MODELS` in the page: Fable 5.1,
  Opus 5.5, Sonnet 5.5, Haiku 4.5; Opus by default). Charlotte picks it per room, or per cat, in the New cat form.
  Nothing picks it for her.
- **The merge gate knows who worked.** `models()` in `harness/hooks/common.py` reads every model that answered in a
  session, and the merging rule (`rules.json`, `merging.strong`: opus, fable) merges only when a strong one did. A
  Sonnet or Haiku cat's pull request is **held for her**, with a note in the litter box. A subagent's sidechain
  doesn't count: a strong session that sends a Haiku helper to search or run tests still merges.
- **The queen can't start anything.** Her runner is `claude -p --restricted --allowedTools mcp__catio`, with no file
  tools and no `create_session`. Her brief says so: starting a session is "what only claude.ai can do".
- **Claude Code already delegates**, inside a session: the `Agent` tool takes `model: haiku | sonnet`, and
  `.claude/agents/*.md` can pin a model and a tool list. The graphify skill uses it for extraction. No house rule
  asks sessions to use it, and no agent definition in `catio-plugin/` does.
- **The sorter** (the brain's `route()`) is the one place a small model is used on purpose, and only to file files.

So the ingredients are there. What's missing is a rule saying when, a way for the queen to start small cats, and a
rubric for "easy".

## What counts as easy

A task goes to a smaller model when all of these hold. The queen's brief and the house rule carry the same list.

| | |
|---|---|
| **Spelled out** | the ask names the file, the test or the output; no design judgment, no "make it better" |
| **Checkable** | a test, a build or a diff shows whether it is done |
| **Small** | one file, or read-only across many |
| **Not held** | nothing under `harness/`, `.claude/`, the merging rule's `hold` paths, or a public repo's rules |
| **Not private** | none of her legal, money or health matters (the `private` rule) |
| **No browser** | no preflight needed |

Haiku: read, search, run and report (a test run and its failures in three lines; a summary of a doc; a graphify
extraction; alt text from a filename list). Sonnet: a one-file fix with a test that shows it, a docstring pass, a
rename across a package. Everything else stays Opus or Fable, and the merge gate stays as it is: **a small model's
pull request is always hers to merge.** That is the safety net, and it is already built.

## Phase A: inside a session (no new infrastructure)

A strong session hands its mechanical steps to a small subagent. Half a day.

1. **Three agent definitions** in `catio-plugin/agents/`, each with `model:` and `tools:` in its frontmatter:
   - `scout` (haiku): Glob, Grep, Read, the graphify query. Finds where things are, reports paths and lines.
   - `tester` (haiku): Bash, Read. Runs the repo's checks and reports what failed, with the failing lines, nothing
     else.
   - `scribe` (sonnet): Read, Write to `docs/` and `*.md` only. Drafts a doc, a changelog line, a PR description.

   None of them gets Edit on code. A small model that only reads, runs and writes prose can't weaken "a strong model
   did the work", so the merge gate needs no change.
2. **A soft house rule** `delegate` in `harness/rules.json` ("Send the small stuff to a smaller cat": search, test
   runs and summaries go to `scout`, `tester` and `scribe`; code stays with you), `enforced: false`, with its switch
   on the page like the other soft rules. The plugin's SessionStart hook prints it with the rest.
3. **One check in the gate**, so the promise holds: `ship_gate.py` refuses a commit when a sidechain on a non-strong
   model touched a tracked file (the transcript records tool calls per sidechain; `models()` already separates
   them). A test in `harness/test/test_hooks.py` beside the "sonnet worked on it" one.

Done when: a session in this repo runs `tester` on Haiku and merges its own PR; `sh catio/test/run.sh` and the
harness tests pass unchanged.

## Phase B: the queen starts small cats

"Agents the gateway runs itself" (plan, phase 5, later). The runner on her PC already runs `claude`; it can run a
worker too. A day or two.

1. **A `delegate` tool** on the gateway and in `catio_mcp.py` (same name, arguments, result in both): `repo`,
   `task`, `model` (`haiku` or `sonnet`, nothing bigger: a strong cat is started in claude.ai, by her), `room`.
   Only the queen's key and Charlotte may call it. It writes `jobs/<id>` (`status: queued`) and wakes a waiting
   runner.
2. **The runner picks jobs up** from `/api/runner/wait` beside her notes and routines, and runs
   `claude -p --model <model> --max-turns N` in `~/.catio/work/<repo>` (cloned or fetched first), **with**
   `CATIO_URL` and `CATIO_TOKEN` in the environment this time, so the worker reports itself as a cat through
   `report.py`, lands in `room`, and its `said` comes back to the queen as a handoff. One job at a time, the queen's
   own turns first. The job's `status` goes `running`, then `done` or `failed` with the last lines.
3. **The queen's brief** (`queen.md`) gets the rubric above and the tool: when Charlotte says "have a small cat do
   X", or a cat's `ask` is something a Haiku can answer by reading the repo, she delegates and says so in a line.
   She never delegates a held path or a private matter, and she never delegates when the rubric doesn't hold: she
   tells Charlotte to start a cat in claude.ai instead.
4. **On the page**, a delegated cat is a cat like any other (`via: runner`, breed Haiku or Sonnet), and the
   queen's menu says "N small cats working". Nothing drawn on the sprite.

Done when: she tells the queen "have a small cat run the grocery app's tests", a Haiku cat appears in the kitchen,
reports, and its line lands in the queen's thread; `harness/test/test_queen.py` runs a job against the fake
`claude` and the stand-in gateway.

## Phase C: automatic

With B in place, delegation needs no asking. Small steps, each a few hours.

1. **Routines on a small model.** `routines/<id>.model`, a select in her Routines card (Fable off the list), and
   `--model` in the runner's turn. Most routines are easy by nature (a morning report, a test run): the cheapest
   win, and it needs no job queue, so it can ship before B.
2. **The queen triages asks.** Each `refreshAgents` cycle she already sees every `needs` cat. A new line in her
   brief: when an `ask` passes the rubric (a fact about the repo, a test to run), delegate it to a scout and post
   the answer to the cat as a comment from the queen, instead of setting Charlotte homework. Homework stays for
   choices only she can make.
3. **A Chores room.** A room with `model: claude-haiku-4-5-20251001` and a blurb that says what goes there. New
   cats she starts there are Haiku already; a delegated cat's `room` defaults to it.
4. **The brain's tray.** A file dropped with a note that reads like a task ("summarise this", "check these
   against the catalogue") is offered to the queen for delegation, with her confirmation, not before.

## What never delegates

- Merging, pushing to a default branch, anything under `hold`: the gates refuse these whoever the model is.
- Changes under `harness/` or `.claude/`: the rules themselves.
- Anything needing a browser, or a key.
- Her private matters.
- The queen herself: she stays on the runner's default model. A cheaper queen would be a cheaper assistant.

## Cost, roughly

Haiku is an order of magnitude cheaper than Opus a token, Sonnet a few times cheaper (check the current price list before quoting her a number). A test run, a search or a summary is a
few thousand tokens either way, so phase A pays for itself on the first day of a session that greps a lot. Phase B
spends her PC's time, not money: the runner is signed in with her plan.

## Order

A1 to A3, then C1 (routines on a small model), then B, then C2 to C4. A and C1 need no new secrets, no deploy and
no change to the page's stored capabilities. B changes the gateway (deployed by Workers Builds on merge) and the
runner (she restarts it), so it waits for a quiet day.
