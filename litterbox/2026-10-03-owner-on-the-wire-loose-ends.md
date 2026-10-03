---
project: Pretty-Project-Portfolio
date: 2026-10-03
---

# 3 October 2026: owner on the wire, shipped, and what it left

## Waiting on Charlotte

- **A second Worker, `pretty-project-portfolio`, serves `catio/` to anyone.** It appeared at 07:04 UTC and every
  merge to `main` redeploys it, so Cloudflare's Workers Builds looks connected to this repo with no config of its
  own (there is no wrangler file at the root). At its workers.dev address, with no sign-in, it serves the café page
  (`main`'s `catio/index.html`), `art/furniture.png` and `data/rooms.json`. The licensed art, `data/sessions.json`
  and the gateway's routes all answer 404, so everything it serves is already public in this repo, and the page
  there runs on its localhost fallback with nothing in it. Delete it, keep it, or put it behind the sign-in: in her
  homework.

- **"Don't touch the artifact"** (her rule, 3 October: "I don't want you touching the artifact again. Run
  everything through the cafe's deployed address and the repo"). The artifact stays at version 32. Open: whether
  CLAUDE.md records the rule (its Republishing section and post-publish checks still tell sessions to publish),
  whether the catio skill, audits and project maps move off the artifact's database onto the gateway, and whether
  the litter box quiz and decisions quiz count as artifacts too. In her homework.

- **No line from her has reached the café on its own address since the rename deployed.** The gateway's tests
  cover a note written as `owner`; one real line to the queen from the café would show it end to end. In her
  homework.

## Facts learned

- **The rename reached her real house.** After PR #50 deployed, every note in the queen's conversation reads
  `owner` or `queen`, including ones written as `charlotte` two hours earlier: the House's one-time migration ran.

- **GitHub won't change the base of a stacked pull request** ("Cannot change the base branch because the pull
  request is part of a stack") once the one under it has closed. Open a new pull request from the same branch:
  that is how #42 became #50.

## Findings

- **The review of 3 October found six bugs in the café's gateway mode and the queen's key** (filed from
  `2026-10-03-review.md`). Whether a cat fixes them now is in her homework.
