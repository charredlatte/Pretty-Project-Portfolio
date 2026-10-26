---
date: 2026-10-25
---

# 25 October 2026: the artifact is out of the code

From "maybe get rid of the artifact", which you settled as *clean it out of the code* — strip the retired
machinery from the repo, leave the published page alone.

## Waiting on Charlotte

- [x] ~~**Three pull requests, and they have to merge in order.**~~ All merged on 25 and 26 October, #153 with them. [#152](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/152) (the `audit` tool) first, then [#155](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/155), which is stacked on it; [#154](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/154) is independent and can go any time. [#153](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/153) is still waiting too, unrelated to these. All of them touch `harness/` or are held for you anyway, so none could self-merge.

- [x] ~~**A file you drop on a reporting session's cat never reaches it, and the artifact is why.**~~ Still true, and still waiting on you: moved to the 26 October note so it is said once. The mechanism, for the record: `catio/index.html` still has the artifact's URL hardcoded (`CATIO_URL`, line 4737) and `deliveryText()` is not gated by `VIA_GATEWAY`, so in the café on your own address a delivery is announced as *"in the Catio at `https://claude.ai/artifact/KH…`. Fetch it with Artifact read (path = the asset id)"* — a page the session cannot read the asset out of. Meanwhile the file itself is in the gateway, and the session cannot reach it there either: `sendFile()` only calls `drop_file` when `cat.kind === "agent"`, and `pick_up` reads the gateway's `files` table, which only `drop_file` writes. So the note arrives and the file does not. Dropping on an *agent* cat has always worked; so has dropping on a cat with no gateway session. It is the common case — a Claude Code session reporting through the hook — that is broken.

  **What the fix looks like, and why it is not in these three.** `tell()` already routes by `cat.agentId` rather than `cat.kind`, so `sendFile()` should too: a reporting session cat has both, and routing on `agentId` sends it down the `drop_file` path that `report.py pick` already knows how to fetch. That is one condition. But `drop_file` caps a file at 1 MiB where the brain does not, so the big-file case needs an answer rather than a silent refusal, and it changes how files reach sessions, which is yours to say. It also needs the e2e suite, and a run in a cloud container is not a verdict: `art/licensed/` is gitignored, so the art-dependent checks go red for want of the packs. Say the word and I will do it in a session that has the art.

## Findings

- **The artifact is worth keeping, and not for sentiment.** It holds `art/licensed/`, and a session cannot get that art from the gateway: `PUT /api/art/*` takes the agents' key, but `GET /art/*` wants your own signed-in cookie, and licensed art is served to the first house only (`harness/gateway/src/cafe.js`). So reading it back out of the artifact is still the quick way for a fresh clone, which is the one job `CLAUDE.md`'s old "Republishing" section was still doing — it is now "The licensed art, and the two ways back to it". Your four project maps are also only there. Nothing was deleted; `artifacts.json` says read-only.

- **The same defect was in three places, not one.** The audit was the one found on 23 October. The project map had it too, and worse: `graphs/<repo>` had **no gateway tool at all**, so every map a session has digested since the café moved went into the artifact, and your filing cabinets have been empty of maps with nothing to say so. #155 adds a `graph` tool beside `audit`, on the same project key. And the `catio` skill itself read the artifact **first** and treated the gateway as the fallback — so its catch-up queried `brain` and `notes` in a database frozen weeks ago, which would have had a session acting on files long since dealt with.

- **`harness/rules.json`'s `catio` was still the artifact link**, which is what the skill passed as `url` and what the session-start preamble names as your own café. Changing it turned up a second thing: with `CATIO_URL` set to your own café the preamble printed the same link twice, the second time as *"her own is at <this very link>, which isn't theirs unless they are her"* — a warning about your own café. It now says that only for a session reporting somewhere else.

- **Two checks were rewritten, and both deserve naming.** They asserted the session-start preamble contains a literal `claude.ai/artifact/` — the thing your ask contradicts. They now assert that the link is the one `rules.json` carries rather than a host written into the hook, which is the reason the old link survived you asking twice: nothing was checking where it came from.

- **The public setup skill keeps the publish path on purpose.** `catio-plugin/skills/catio/SKILL.md` sets a café up for someone who is not you and has no gateway, and for them publishing an artifact is the only route. It no longer leans on your brief for the capability set (written out there now), and the `ArtifactData` steps the `catio` skill used to lead with now live in a last section of that skill for the same audience, with an explicit "their own URL, never Charlotte's".
