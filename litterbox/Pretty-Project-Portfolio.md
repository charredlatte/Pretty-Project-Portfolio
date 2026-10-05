---
project: Pretty-Project-Portfolio  # a guess by litterbox/sort.py: check it, then delete this comment to file these notes
---

# 2 October 2026: the Catio's local copy, republishing, and her AI Gateway (sifted)

## Facts learned

- **Unzipping the Catio's local copy on her PC.** Windows' "Extract all" is greyed out for a zip on her Google
  Drive drive (G:), even one marked available offline, so give her PowerShell instead: in File Explorer, type
  `powershell` in the folder's address bar, then `Expand-Archive -Path 'catio-local.zip' -DestinationPath . -Force`.
  A second download arrives as `catio-local (1).zip`: keep the quotes, or PowerShell reads `(1)` as an
  expression and fails with "A positional parameter cannot be found". `-Force` writes over the old folder. *— litterbox/2026-10-02-catio-local-copy-and-ai-gateway.md*

- **Republishing the Catio from a session that didn't publish the live version** is refused until the session
  has read every line of the live source the refusal saves (about 3,100 lines, in chunks under 25,000 tokens).
  Diff that saved source against `git show origin/main:catio/index.html` first: if they match, nothing is lost,
  and the same publish, sent again unchanged, goes through. *— litterbox/2026-10-02-catio-local-copy-and-ai-gateway.md*

## Questions waiting on Charlotte

- **Which project is her new Cloudflare AI Gateway for?** She set one up on 2 October with rate limiting
  (50 requests a minute), an authenticated gateway, and spend limits on. Suggested spend-limit rules: $2 a day
  (sliding), $10 a month (fixed), and optionally $5 a month per app, split by an `app` metadata key that each
  project's requests would need to send. Its token belongs in a secret, never in a repo: her repos are public.
  Once she names the repo, wire the app to the gateway and send the `app` metadata. *— litterbox/2026-10-02-catio-local-copy-and-ai-gateway.md*

# 3 to 5 October 2026: what the café's sessions left (sifted)

## Waiting on Charlotte

- **The claude.ai café trails `main` by several features.** On the morning of 5 October it still ran the version published on 4 October (version 36, the hover outlines). Not in it yet: the minimisable map panel (#84, #86), the queen's loading strip (#76), the queen's card that fits the window (#64), the recent plug-and-play work on The look, and the car-analogy wording of the wizard's How it works. A republish waits for her say-so, and per CLAUDE.md it must pass the whole stored capability set so `downloads` joins it. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The queen's step tiles need her runner updated on her PC.** The loading strip's Sims-style steps come from the runner, which now tells the gateway when she wakes and each time she uses a tool. The gateway deploys itself on merge, but `harness/runner/queen.py` runs from her own copy of the repo: pull `main` there and restart the runner. Until then the strip shows only "Thinking" and the seconds, with no step tiles. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **A repo watch is still running.** On 5 October she asked a session to watch the repo: it subscribes to each open pull request and set a recurring check-in (about every four hours while quiet) to pick up new ones. It keeps going until she tells that session "stop watching". *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **Branches to tidy on GitHub, which sessions can't delete (their git access refuses it).** Merged, so they can go: `claude/great-bell-tc00ty` (PR #74) and `claude/eager-darwin-8a7t59` (PR #52). Never merged and with nothing worth keeping: `claude/compassionate-archimedes-56vo6o` (a held-PR-57 litter note and a wizard line since rewritten). Her call: `add-claude-github-actions-1791040441357`, made by GitHub's Claude app on 3 October with two workflows (Claude Code Review and the PR Assistant) and no pull request: keep it if she wants those workflows. Turning on *Automatically delete head branches* in the repo's settings would stop merged ones piling up. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The GitHub repository description still reads "Personal-use MCP framework … vibed by Charlotte Badot".** The README now sells the KittyChat Café, so the description no longer matches it. Only she can change it, in the repository's settings; a suggestion was "KittyChat Café: every Claude chat as a cat in a cozy pixel café". *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **Is "December 2027" the app or the hosted café?** The README now says the KittyChat Café app is planned for December 2027, as she asked, but the rest of the repo describes the app as an unfinished draft whose store release waits on her own art. She should say which launch the date belongs to. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **Check the art before filming.** The café's Sprout Lands and Little Dreamyland art is licensed for non-commercial use only. Showing it in a monetised Make n Break video or in the Ulule campaign could break those licences, so either check their terms or put her own art on screen. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The queen's runner still needs to learn she is Ninine.** The rename reached the claude.ai café's database and the default name, but the café on the gateway's address and her runner on her PC keep their own copy of the queen's settings. To fix it: open the queen's card in the gateway café, Settings, Her character, and save. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The decider's week of logging starts on 4 October, not 3 October.** The fixed log (PR #66) reached the gateway at about 12:00 UTC on 4 October and the claude.ai café at version 34. Entries before that lack the `floor` and `ref` fields and log a made-up "none" when the sorter timed out, so they cannot be judged. Decide whether to switch `house/main.decide` to "on" from about 11 October, on the new entries only. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **A stray Git repository sits on her whole Windows user folder.** Git Gui turned `C:\Users\Utilisateur` into an empty repository (branch master, no commits) and listed Claude Code's history files as changes. Nothing there should be committed: delete the hidden `.git` folder in that user folder (show hidden items in File Explorer), or tools may take the whole home folder for a repository. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The link page is merged but not live: GitHub Pages is off.** charredlatte.github.io still answers "Site not found" (checked 5 October). In the repo's Settings, Pages, set Source to "Deploy from a branch", branch main, folder / (root), and save; Claude can't switch it on. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The link page's "bientôt" strips wait on the real pages.** Buy Me a Coffee and Ulule show as coming soon until their addresses exist; other profiles (Instagram, LinkedIn) can be added the same way once she sends them. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

## Ideas not built

- **Two small minimap loose ends, left alone on purpose.** Hovering a room on the minimap names it only through the browser's slow native tooltip, not the café's own hover line (`#tip`). And while a cat is walking, the folded panel's pip counts it where it is heading rather than where it stands. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

## Facts learned

- **The harness now has CI, from a contributor's pull requests.** The Windows fixes for the harness suite came in as #80 and #81 (rebuilt as #90 with the conflict resolved, keeping the contributor's authorship). Since #90, `.github/workflows/tests.yml` runs the harness suite on Ubuntu and Windows for every push to `main` and every pull request. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The landing page's Figma wireframes are behind the repo.** The file "KittyChat Café · Landing page wireframes" in her Figma drafts was drawn before the last round of review changes to the landing page. The script in the repo that draws them is current, so a redraw (one of the month's Figma calls) brings it level. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The onboarding and shop Figma files predate the car and Ninine.** The wizard's car analogy and the queen's rename to Ninine are in the page, the repo's wireframes and the plans, but the café's Figma files weren't redrawn, since each redraw uses one of her monthly Figma calls. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The artifact moved past version 32 after all.** The litter box records her 3 October rule ("I don't want you touching the artifact again") and says the artifact stays at version 32, but on 4 October she asked for republishes herself: version 33 added `quizzes` and `answer` to the stored capabilities, and version 34 carried the decider-log fix. By that afternoon the claude.ai café was already behind `main` again (#71's hover outlines, then later merges), so whether it is kept current is still her call. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

## Findings

- **`catio/test/run.sh` can't find an ordinary local Playwright install.** The review of PR #72 found that outside Claude's cloud the script looks only where the cloud keeps its browser, so the page's tests won't run on her own machine without a fix. It was left out of #72 because a proper fix was more than a README change should carry. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The shipping nudge raises false alarms about montfortoise-shopify.** In at least three café sessions (4 and 5 October) the Stop hook said montfortoise-shopify's branch had commits that weren't pushed, though the branch matched its remote and, once `main` was fetched, `main` too. `harness/hooks/ship_check.py` counts commits against the container's local copy of `origin/main`, which can be out of date; fetching before comparing would quieten it. A change under `harness/`, so hers to approve. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

- **The Play Store may treat a personal developer account differently, unchecked.** Claude believed new personal accounts must run a closed test (about 12 testers for 14 days) before publishing, while company accounts skip it, and that a personal listing shows her own name and address. Check the current rule before opening the account for the Android app. *— litterbox/2026-10-05-sessions-3-to-5-october.md*
