# Delegating the easy work to smaller models

**Status (3 October 2026): the café has no automatic delegation, to sub agents or to anything else.** Every cat runs on
the model it was started with, chosen by hand, and no house rule or agent definition makes a session hand its easy
steps to a sub agent on a smaller model. Phase A below is that piece; B and C go further. This is the plan to add it, cheapest step first, each one useful on its own.

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

A strong session hands its mechanical steps to a small sub agent. Half a day. Reviewed on 3 October against the
open-source tools that do this (below); the review changed it in four places, marked *changed*.

0. **The one-line version first** (*changed*). Claude Code resolves a sub agent's model from the call, then the
   agent file, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the session's model, and the built-in Explore and
   general-purpose agents run on the **session's** model by default, so today every Explore in her Opus session
   costs Opus. Setting `CLAUDE_CODE_SUBAGENT_MODEL=haiku` in her Claude environments puts every unpinned sub agent on
   Haiku with no file in the repo. Try that for a week before anything below: it also moves graphify's extraction
   sub agents to Haiku, so watch the map's quality; if it drops, pin graphify's agents to `sonnet` and keep the
   variable.
1. **Two agent definitions** in `catio-plugin/agents/`, each with `model`, `tools`, `maxTurns` and `omitClaudeMd:
   true` in its frontmatter (the built-in Explore skips CLAUDE.md for the same reason; hers is long):
   - `scout` (haiku): Glob, Grep, Read, and the graphify query preloaded with `skills:`. Finds where things are and
     reports paths and lines, nothing else.
   - `tester` (haiku): Bash, Read. Runs the repo's checks and reports what failed, with the failing lines.

   No `scribe` (*changed*): a PR description or a changelog line needs the diff the parent already holds, and a sub
   agent that must be handed that context costs more than it saves. Anthropic's own finding is that splitting by
   job title (planning, implementing, testing, reviewing) spent more on coordination than on the work; what pays is
   splitting along information boundaries: a self-contained job with verbose output and a short answer. Scout and
   tester are that. Prose stays with the parent, in Sonnet's or Opus's hands, where the French is better anyway.

   Neither gets Edit or Write. A small model that only reads, runs and reports can't weaken "a strong model did the
   work", so the merge gate's promise holds without a new rule.
2. **A nudge, not only a rule** (*changed*). The soft rule `delegate` goes in `harness/rules.json` ("Send the small
   stuff to a smaller cat"), with its switch on the page like the other soft rules. But the tools that work don't
   rely on prose: cc-router's scout guard watches the main session for an unbounded search and suggests the Scout,
   twice a session, then stays quiet. `graph_first.py` already does exactly this shape for the map; the same hook
   gets a second line: a `Grep` or `Glob` across the repo, or a `Bash` test run, in the main session on a strong
   model, is answered once with "scout/tester would do this for a tenth of the price". No block.
3. **The gate check moves to the moment of the edit** (*changed*). The plan said: refuse a commit when a small
   sidechain touched a tracked file, read from the transcript. Two facts against it: sub agent transcripts live
   in their own files (`subagents/agent-<id>.jsonl`), not in the sidechain entries `models()` reads, and hooks run
   *inside* sub agents, with the agent's name as `agent_type`. So `gates.py` refuses `Edit`, `Write` and
   `NotebookEdit` when `agent_type` is `scout` or `tester`, or when the running model is not strong and the file is
   tracked. Belt and braces over the frontmatter allowlist, a few lines, and it fires before anything is written
   instead of at the commit. A test beside the "sonnet worked on it" one.
4. **Escalation is "do it yourself"**. claude-router escalates a failed Sonnet job to Opus with the error attached;
   oh-my-opencode keeps `explore` and `explore-medium` on two sizes. Neither for the café: when scout or tester
   comes back empty or wrong, the rule says the session does that step itself, once. No bigger scout, no retry
   loop.

Done when: a session in this repo runs `tester` on Haiku and merges its own PR; `sh catio/test/run.sh` and the
harness tests pass unchanged.

**Later, from the same review, if A earns it:**
- An `implementer` on Sonnet that may edit code, the way every other tool allows (cc-router's Worker,
  claude-router's Implementer, oh-my-opencode's executor; aider's architect/editor split is the same idea and set
  records on its own benchmark). In the café the gate would then count its sidechain as Sonnet work, so its PRs are
  held for her, which is the right default. Not in A: the point of A is that nothing small writes code.
- cc-router's **quota step-down**: at 85 % of her plan's window, every tier drops one (strong stays strong for
  merging, which the gate wants anyway). Needs the usage reading from the status line; later.

### Reviewed against

- Claude Code's sub agent reference: the frontmatter (`model` incl. `fable`, `tools`, `disallowedTools`,
  `maxTurns`, `omitClaudeMd`, `skills`, `memory`, `background`, `isolation: worktree`), the model resolution order,
  `CLAUDE_CODE_SUBAGENT_MODEL` and `_FORCE`, Explore and general-purpose on the session's model by default, hooks
  running inside sub agents, separate transcript files, and "use a sub agent when the output is verbose, the work is
  self-contained and returns a summary".
- **cc-router** (theBlackEndDev): Scout and Scribe on Haiku, Worker, Researcher, Reviewer and Planner on Sonnet,
  Plan on Opus; the tier comes from which helper is started, enforced by hooks at `SubagentStart`; "no upgrades";
  the scout guard; quota step-down at 85 %. No measured savings published.
- **claude-router** (vimoxshah): Explorer on Haiku, Implementer on Sonnet, Hard-implementer and Reviewer on Opus,
  Advisor on Fable; "cheap models for volume, premium where a mistake compounds"; only the two implementers write;
  escalation with error context; a validation script before dispatch. No measured results.
- **wshobson/agents**: four tiers over about two hundred agents: Opus for architecture, security, all review and
  production code; Sonnet for docs, testing and debugging; Haiku for operational chores and simple docs. Note that
  it puts testing on Sonnet: that is writing tests; running them is Haiku work.
- **oh-my-opencode / oh-my-claudecode**: explore and librarian on the cheapest models "because they do not need
  deep reasoning", oracle on the strongest "because its outputs gate execution", three sizes of executor.
- **aider's architect/editor mode**: a strong model plans, a cheap one edits; state of the art on its own
  benchmark. The opposite split from A, and the argument for the later `implementer`.
- **RouteLLM** (LMSYS): a learned router between a cheap and a strong model, 85 % cost cut at 95 % of quality on
  MT-Bench. Overkill here: in Claude Code the session itself is the router, by which helper it starts.
- **Anthropic on multi-agent systems**: Opus lead with Sonnet sub agents beat a single Opus by 90 % on its research
  eval; divide by information boundary, not by job title; isolate a subtask when it produces over about a thousand
  tokens of which little matters to the parent; write the sub agent a precise objective, output format and
  boundaries.

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

A0, then A1 to A4, then C1 (routines on a small model), then B, then C2 to C4. A and C1 need no new secrets, no deploy and
no change to the page's stored capabilities (A0 is one variable in her Claude environments). B changes the gateway (deployed by Workers Builds on merge) and the
runner (she restarts it), so it waits for a quiet day.
