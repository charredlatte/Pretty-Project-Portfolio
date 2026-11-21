---
date: 2026-10-26
---

# 25–26 October 2026: the decider in the docs, and the artifact out of the code

One session, eight pull requests, all merged. It started with two questions about Clef and ended with the
retired artifact gone from everything that tells a session what to do. This is the record; the 23 and 25
October notes are its working papers and their open items have moved here.

## Waiting on Charlotte

- [ ] **A file you drop on a reporting session's cat never reaches it.** The note arrives, the file does not.
  `catio/index.html` has the artifact's URL hardcoded (`CATIO_URL`) and `deliveryText()` is not gated by
  `VIA_GATEWAY`, so on your own address a delivery is announced as *"in the Catio at
  `https://claude.ai/artifact/KH…`. Fetch it with Artifact read"* — a page that session cannot read the asset
  out of. The file is in the gateway, and it cannot reach it there either: `sendFile()` only calls `drop_file`
  when `cat.kind === "agent"`, and `pick_up` reads the gateway's `files` table, which only `drop_file` writes.
  Dropping on an *agent* cat has always worked, and so has dropping on a cat with no gateway session; it is the
  common case — a Claude Code session reporting through the hook — that is broken.

  **The fix is one condition.** `tell()` already routes by `cat.agentId` rather than `cat.kind`; `sendFile()`
  should too, since a reporting session cat has both, and that sends it down the `drop_file` path `report.py
  pick` already knows. Two things stop me doing it unasked: `drop_file` caps a file at 1 MiB where the brain
  does not, so the big-file case needs an answer rather than a silent refusal, and it changes how files reach
  sessions, which is yours to say. It also needs the e2e suite, and a cloud run is not a verdict without
  `art/licensed/`. Say the word and I will do it where I can look at it.

- [ ] **#121 and #115 are the only pull requests left open, and I have reviewed neither.** #121 (Tosh's audit
  fixes, 5 October) conflicts in **all thirteen files it touches** — `CLAUDE.md`, six gateway sources,
  `catio_mcp.py`, `queen.py` and three test files — against a `main` three weeks ahead of it. Resolving thirteen
  stale conflicts is probably the wrong move; rebuilding it from its findings and checking what `main` already
  carries is probably the right one. #115 is the audit document itself, from `ohwellwhy10-jpg`'s fork.

- [ ] **GitHub's Claude integration still appends its footer to every new pull request here**, and it still has
  to be edited off by hand: it happened on both of this session's pull requests, and the house-rules hook caught
  both. Carried from the 23 October note, and observed twice since. The hook makes it safe, not quiet.

- [ ] **The repo's own over-engineering audit was last run on 22 October**, said the 23 October note; I have not
  re-run it, so that is its word rather than mine.

- [ ] **`fix/the-skill-reads-the-cafe` is back on the remote, and it is my fault.** I checked #155's state, found
  it stale, pushed a merge — and it had already been merged and the branch deleted, so the push recreated it. Its
  content is byte-identical to `main` (zero diff; the only commit on it is an empty merge), so nothing is wrong
  in the repo, but the house-rules gate will not delete it, because that commit is not an ancestor of `main`, and
  forcing past a guardrail for tidiness is not worth it. One click on GitHub.

## What was done

**The decider, in the docs** (#146, #147, #149, #151). From "why isn't the queen's runner run by Clef?" The
answer is categorical, not a roadmap gap: the decider holds no tools and no session, so it can never *drive* a
cat the way `runner/queen.py` drives Claude Code. The docs had been teaching the opposite — `harness/README.md`
framed the choice as cost ("a cheaper Opus"), and `docs/engine.md` had the decider as a **row in the Driver
table**. Both now say what actually picks it: numbers to hold against a floor, rather than prose to parse.

**The two parked items** (#152, #153). The driver table got a column per fact instead of one `Status` meaning
three different things, and the opening audit got a gateway tool.

**The artifact, out of the code** (#154, #155). Your call of 20 and 21 October had not reached the repo:
`CLAUDE.md` still carried the whole publishing recipe, so a session reading it top to bottom still found
instructions for a page you never open. Gone: the `Republishing` section, the stored-capabilities block and its
three "until a republish" caveats, the post-publish checks, the `ArtifactData` write ending the saved-sessions
refresh, and `docs/plan.md`'s publishing procedure.

## Findings

- **The artifact is worth keeping read-only, and not for sentiment.** It holds `art/licensed/`, and a session
  cannot get that art from the gateway: `PUT /api/art/*` takes the agents' key, but `GET /art/*` wants your own
  signed-in cookie, and licensed art is served to the first house only (`harness/gateway/src/cafe.js`). Reading
  it back out of the artifact is still the quick way for a fresh clone — the one job the old "Republishing"
  section was still doing, now "The licensed art, and the two ways back to it". Your four project maps are also
  only there. Nothing was deleted; `artifacts.json` says read-only.

- **The same defect was in three places, not one.** The audit was the one found on 23 October. The **project
  map** had it worse: `graphs/<repo>` had *no gateway tool at all*, so every map digested since the café moved
  went into the artifact, and your filing cabinets have been empty of maps with nothing to say so. And the
  `catio` skill read the artifact **first**, treating the gateway as the fallback — its catch-up queried `brain`
  and `notes` in a database frozen weeks ago, which would have had a session acting on files long since dealt
  with. #155 adds a `graph` tool beside `audit`, on the same project key, and turns the skill round.

- **The gateway redeployed and the tools are live.** `audit` and `graph` appeared in a session's own tool list
  after the merges — direct evidence, not an inference, which closes the one guess #152 carried ("nothing here
  has watched a real filing cabinet draw a real audit").

- **The 21 October "decider outage" was never an outage.** The pile said `decide` answered `5006: required
  properties at '/' are 'model,state,questions'` both times. It was a caller error: every Clef question needs
  `instructions`, and the gateway dropped any other key, so a question written the natural way reached Clef as a
  bare `{type: "noul"}`, which it refuses by naming the *root* — which is why all three root properties were
  present and the message still read as the service being down. #149 reproduces it and makes both tools refuse a
  wordless question by name.

- **Clef's confidence is not its winning probability**, and the two can sit far apart (0.7276 against 0.2072 in
  a live sample). `confidence()` reads the `confidence` field, so the 0.6 floor applies to that, not to the
  winner. Worth knowing before reading any `decisions/` row.

- **`harness/rules.json`'s `catio` was still the artifact link** — the value the skill passed as `url` and the
  session-start preamble names as your own café. Changing it exposed a second thing: with `CATIO_URL` set to
  your own café the preamble printed the same link twice, the second time as *"her own is at <this very link>,
  which isn't theirs unless they are her"* — a warning about your own café. It now says that only for a session
  reporting somewhere else.

- **Four checks were rewritten across the session, every one named before the suite ran.** Two tool-name-set
  assertions (what those checks are *for*, and a new tool belongs in them), and two asserting the session-start
  preamble carries a literal `claude.ai/artifact/` — the thing your ask contradicts. The latter two now assert
  the stronger property: the link is the one `rules.json` carries, not a host written into the hook, which is
  how the old link survived you asking twice. Nothing was loosened, skipped or deleted.

## Where I was wrong

- **I advised a merge order from a trial that went stale under me.** I merged all four branches locally, in both
  orders, and reported no conflicts — true when I ran it, and false twenty minutes later when #156 landed from
  another session and put #154 into conflict. A local trial merge answers "do these conflict with each other",
  not "will they still merge after someone else pushes".

- **I checked #155's state, acted on it, and it had already been merged** — the push recreated a deleted branch
  (above).

- **I reported the harness README as needing nothing, early on, because it did not carry the *wrong* framing.**
  Not carrying the wrong framing is not the same as carrying the point; it took your "did you fix all of the
  readmes?" to find that out.

- **I let a false claim through into `docs/engine.md`** — that the runner's code has "one function per CLI" and a
  `Turn.args()`. I had verified the symbol did not exist and still passed the claim along. It is false:
  `Runner.turn()` parses Claude's stream-JSON, `mcp_file()` writes Claude's `mcpServers` shape, and `main()`
  resolves only `claude`. Corrected in the same PR.

## The public repository, and what was in it

Her ask on 26 October: *"make sure that no more personal information ends up in the public repo"*. A scan of
tracked files — not the working tree, which may hold her data under `catio/data` and `catio/dist`, both
gitignored — found three things, and cleared two of them.

- **Her own name was in the café's address, in the brief.** The gateway's host carries her full name, and
  `CLAUDE.md` printed it as the one link to give her. #157 had already taken that address out of
  `harness/rules.json`, `harness/hooks/session_start.py` and the page; the brief was the copy left behind, and
  an unfiled pile note had it too. Both now say `CATIO_URL`, which is where it belongs. **A check now enforces
  it** (`test_no_tracked_file_names_the_owner_s_own_cafe`): it walks every tracked file and fails on the host,
  and it was proved by planting the address and watching it go red, because a check nobody has seen fail is not
  a check. Its needle is built from parts so the file does not contain the thing it forbids.

- **Her benefits status was named in `docs/requests.md`.** The line's job was to record that the business plan
  is private and never in git — but it listed *which* private circumstances it covers, one of them ARE. The line
  now says the circumstances are private without naming them, which is what it was for.

- **Her full name beside "EI" in the shop and landing pages is deliberate, and stays.** `docs/kittychat-shop/`
  and `landing/index.html` carry "Charlotte Badot, EI" in mentions légales, a contact tile and a footer. French
  law requires an e-commerce site to publish exactly that, so these are drafts of pages whose purpose is to be
  public. Whoever drew them was careful: SIREN, RNE, address and email are all placeholders. Left alone, and
  named here so the next scan doesn't mistake it for a leak. The same goes for her name as author and copyright
  holder in `README.md` and the two plugin manifests.

- **The artifact URLs went too, on her word.** `artifacts.json` held three private claude.ai pages of hers;
  it is empty now, and the café artifact's link is `CATIO_ARTIFACT` in her environment, beside `CATIO_URL`.
  Two things actually read those values and both were changed with them: route 1 for the licensed art in
  `CLAUDE.md`, and the page's delivery fallback, which pointed a session at an `artifacts.json` entry that no
  longer exists and now says to ask the owner, because nothing in the repo knows the link any more. The file
  stays as the empty slot a fork records its own page in. The check grew a second needle for it: a full
  `claude.ai/artifact/<id>` link fails, while the bare path in prose does not, since the docs and this box
  discuss it as a thing and only a real link gives a real page away. Both halves were proved by planting
  each and watching the right one go red.

  The page change was held against a baseline rather than guessed at: the e2e suite ran on this branch and on
  `main`, and the two failure sets are **identical** — 329 passed, 30 failed, every one of them art-dependent,
  as a run without `art/licensed/` always is. The run is not a verdict on the page; the comparison is a verdict
  on the change.
