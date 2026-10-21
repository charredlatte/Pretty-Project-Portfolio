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

- **#23: her five Aseprite drawings aren't exported yet.** Her Drive folder for them holds five Aseprite sources from 2 October (a plain cat and Snow, two or three angles each), none exported. The café reads PNGs only: File → Export (or Export Sprite Sheet for a walk), one row of frames, each file named after a slot the café has (`cat-work`, `cat-review`, `cat-meow`, `cat-cry`, `cat-sleep`, `cat-walk-side`; The look in the House menu lists them). *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Merged branches pile up on GitHub, and sessions can't delete them** (the git proxy refuses branch deletes). Turn on Settings → General → Pull Requests → *Automatically delete head branches*, as `harness/README.md` asks: a session that pushes to a branch again after its merge simply recreates it. For the ones already there, `git fetch --prune origin` then `git branch -r --merged origin/main` lists the merged ones, though not a branch pushed to again after its merge or merged by squash (leave out `origin/main`, `origin/HEAD -> origin/main` where it shows, and any branch an open session is still on: the café shows the branch of each session that reports one). Also `claude/litterbox-oct-7-21` and `claude/litterbox-7-to-21-october`, from #134 and #135, closed unmerged. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Six cats on the gateway still ask her about pull requests that are done:** #117, #64, #82, #83, #58 and #130 with #131 (all merged, or closed and replaced, between 3 and 21 October). They count in "N need you" until she lets each go from its menu. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

## Findings

- **The decider failed both times it was asked on 21 October.** The gateway's `decide` tool answered `the decider failed: 5006: Error: required properties at '/' are 'model,state,questions'` twice, the second time with `model: "@cf/cloudflare/clef-flash"` named on the call. On `main`, both calls should have carried `model`: the default model is Clef, and `decide.js` puts Clef's short name in the body it sends `env.AI.run` (`const model = …` and the `env.AI.run(model, { ...(cf ? { model: cf[1] } : {}), ...body })` call). The second call named Clef itself, so `DECIDE_MODEL` can't explain it: check whether the deployed Worker matches `main` (Workers Builds) and whether Clef's input schema or name changed. Until it is fixed the house rule "The decider makes the judgement calls" can't be kept: sessions fall back to their own judgement and say so. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **The merge gate refuses a short `expectedHeadSha` with a message that reads as a mismatch.** `harness/hooks/ship_gate.py` compares it with `git rev-parse HEAD` by `head != sha`, so `c4515aa` never equals `c4515aa95fda…`, and the refusal says "check out and review what's on #N" about the very commit under review (it happened to #130 on 21 October). When the short one is a prefix of HEAD, the message should simply ask for the full SHA, which it already prints; on a pull request that is held anyway, the same misleading line lands in her hold note too. Whether GitHub's merge call would take a short one wasn't checked; never accept a bare prefix in the gate, which would let `c` pass. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **A failed Skill call still counts as the skill having run.** `skill_calls()` in `harness/hooks/common.py` reads every Skill tool use without checking whether it errored, so one failed invocation disarms the browser preflight, the opening audit and the merge gate's audit and review. Still open on main after #126. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **The opening audit's write block misses more than it catches in git.** `WRITE_CMD` in `harness/hooks/gates.py` matches `git commit`, `push`, `merge`, `rebase`, `reset`, `revert`, `cherry-pick`, `am`, `apply` and `stash` straight after `git`: any global flag (`git -C .`, `git -c k=v`, `git --no-pager`) slips past, and so do `git checkout`, `restore`, `switch`, `add`, `clean`, `pull`, `tag` and `branch -D` with none. Its other patterns (`rm`, `mv`, `cp`, `sed -i`, `tee`, `truncate`, `patch`, redirections, `--write` and `--commit`) have gaps of their own (and `rm`, `mv`, `cp` match after any space, so a read like `grep rm f` is blocked too, while `/bin/rm f` and `\rm f` pass): `1> f`, `2> f`, `&> f`, `>| f`, a leading `>f` and `sed -E -i` all pass. Test the regex against each form before trusting it. Exit 0, silent. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **The hall can show two piles of cats** (its own, and the front-door line's overflow), and the page names only the last one. The page and the app (`catio-app/`) have to change together. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **A review of #129's last commit (`061a336`) is still owed.** The app's thirteenth review was cut off by the session limit, and #129 merged as `25c84d9` on 20 October. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **One gateway test (the hook's repo name) fails in a checkout cloned as lowercase `pretty-project-portfolio`,** and passes in CI. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

## Facts learned

- **A container's local `main` can be days stale** (one was at PR #27): base work on `origin/main`, never on the local branch. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Drive tags an uploaded `.aseprite` file as plain text** (the sprites session's sheets, 20 October). The bytes are intact and the editor opens it. *— litterbox/2026-10-21-sessions-7-to-21-october.md*

- **Long review loops run into the session limit.** #129 took thirteen review rounds and the last was cut off; the sprite uploads to Drive were cut off twice on 20 October. Ask for fewer, larger rounds. *— litterbox/2026-10-21-sessions-7-to-21-october.md*
