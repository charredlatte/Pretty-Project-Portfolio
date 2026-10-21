---
project: Pretty-Project-Portfolio  # a guess by litterbox/sort.py: check it, then delete this comment to file these notes
---

# 7 to 21 October 2026: what the café's sessions left

## Waiting on Charlotte

- **The 90s Barbie kit still has to be uploaded to the gateway.** #132 (the gateway serves the kit) merged on 21 October, but the café on https://catio-gateway.charlotte-badot.workers.dev shows the queen's new card in the packs' tan until the kit's files are uploaded once: `CATIO_URL=… CATIO_TOKEN=… python3 harness/gateway/cafe/move-in.py` (it needs both), or `PUT /api/art/skin/<name>.png` with `CATIO_TOKEN`. The queen chat redesign session will do it when she says. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **#121 is hers to close.** Main already carries six of its seven fixes; the seventh (the rename-based lock takeover) was dropped, as its test passes on main's unlink too. The explanation is on #121. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **#115, her friend's audit of 5 October, went red only because main was broken that night.** "Update branch" on the pull request should turn it green. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **#123 ("Error") is a screenshot only, and sessions can't open GitHub's image attachments.** Paste the error's words into the issue and a session can pick it up. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **#122: Discussions is a switch only she can turn on.** Settings → General → Features → Discussions, then Set up discussions, in a browser (the GitHub app has no Settings page). The steps are on the issue. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **#23: her five Aseprite drawings aren't exported yet.** Her Drive folder for them holds five Aseprite sources from 2 October (a plain cat and Snow, two or three angles each), none exported. The café reads PNGs only: File → Export (or Export Sprite Sheet for a walk), one row of frames, each file named after its slot (`cat-work`, `cat-review`, `cat-meow`, `cat-cry`, `cat-sleep`, `cat-walk-side`; `docs/drawing-plan.md` lists them). *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Merged branches pile up on GitHub, and sessions can't delete them** (the git proxy refuses branch deletes). After a `git fetch --prune origin`, `git branch -r --merged origin/main` lists the ones that can go, besides `origin/main` and `origin/HEAD`, which it lists too, today's included (`claude/amazing-dirac-harden-gates`, `claude/gateway-skin-g8znsr`, `claude/queen-chat-redesign-g8znsr`…). Not `claude/allow-bash-in-the-review`: it holds #133's follow-up, unmerged (below). Also `claude/litterbox-oct-7-21` and `claude/litterbox-7-to-21-october`, two unmerged drafts of this pile, closed as #134 and #135. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Six cats in the café still ask for things that are done.** On the gateway: "main is broken… PR #117" (merged 5 October), "Window usability: PR #64" (merged 4 October), the landing page's PR #82 (merged 4 October), "Merge #83 (Opus by default)" (merged 5 October) with the business plan questions, the RPG mockups on PR #58 (merged 3 October, since replaced by the 20 October scenes), and "The queen chat redesign" asking about #130 (merged 21 October) and #131 (closed unmerged, replaced by #132, merged the same day). They count in "N need you" until she lets each go from its menu. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

## Findings

- **#133's follow-up hasn't merged.** #133 (the code review reaches the diff) merged on 21 October, and its own review then found two faults: the `pull-requests: write` grant bought nothing, and the pull request reference it passes (`<repo>/pull/<n>`) is not a form `gh pr diff` accepts. The fixes (`9ed6cc6`) are on `claude/allow-bash-in-the-review`, not on `main`, so the next pull request's `claude-review` runs the workflow as merged. They are #137, open. The action can't be tested before it merges, since it refuses to run on a pull request that edits its own workflow file. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **The decider fails on every call.** On 21 October the gateway's `decide` tool answered `the decider failed: 5006: Error: required properties at '/' are 'model,state,questions'` twice, the second time with `model: "@cf/cloudflare/clef-flash"` named on the call. The first call named no model, so `main` used `DECIDE_MODEL` (or the default), and `decide.js` puts `model` in the body it sends `env.AI.run` only for a Clef id (`const model = …` and the `env.AI.run(model, { ...(cf ? { model: cf[1] } : {}), ...body })` call): check what `DECIDE_MODEL` is set to first. The second named Clef, which `main` sends with its `model`, so if that still fails, compare the deployed Worker with `main`. Until it is fixed the house rule "The decider makes the judgement calls" can't be kept: sessions fall back to their own judgement and say so. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **A failed Skill call still counts as the skill having run.** `skill_calls()` in `harness/hooks/common.py` reads every Skill tool use without checking whether it errored, so one failed invocation disarms the browser preflight, the opening audit and the merge gate's audit and review. Still open on main after #126. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **A git command with any global flag slips past the opening audit's write block** (`git -C .`, `git -c k=v`, `git --no-pager`): exit 0, silent. Still open on main after #126. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **The hall can show two piles of cats** (its own, and the front-door line's overflow), and the page names only the last one. The page and the app (`catio-app/`) have to change together. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Three pull requests merged with their last commit unreviewed:** #129 (the app; its thirteenth review was cut off by the session limit; merged as `25c84d9`, last commit `061a336`), #126 (the gates) and #130 (the queen's card, worked on by Sonnet). Their holds said the code review hadn't run since the last commit; she merged them on 20 and 21 October. A review of each final commit is still owed. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **One gateway test (the hook's repo name) fails in a checkout cloned as lowercase `pretty-project-portfolio`,** and passes in CI. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

## Facts learned

- **A container's local `main` can be days stale** (one was at PR #27): base work on `origin/main`, never on the local branch. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Drive tags an uploaded `.aseprite` file as plain text** (the sprites session's sheets, 20 October). The bytes are intact and the editor opens it. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Long review loops run into the session limit.** #129 took thirteen review rounds and the last was cut off; the sprite uploads to Drive were cut off twice on 20 October. Ask for fewer, larger rounds. *— litterbox/2026-10-21-sessions-7-to-21-october.md*
