---
project: Pretty-Project-Portfolio
---

# 4 October 2026: the queen's card, held for her

## Waiting on Charlotte

- **PR #64 is ready and held for her, not merged.** "Make this window useable" — her card's words were a
  column a third of the card wide with a sideways scrollbar under them. The width fix merged as #62; #64 is
  the height, which #62 got wrong, plus the faults the fix itself introduced before it settled. It is green
  (catio 265, harness 63, gateway 33) and the card is measured at eleven window sizes from 1440x900 to
  320x480, with homework and with Settings open. It is held because the change needed **seven review rounds**,
  and three of those rounds found faults that a green suite had not: Send on screen but painted over and
  unclickable; her homework clamped to nothing with an open quiz behind it; a 330 KB generated page committed
  by accident. The checks that should have caught them were themselves passing on live bugs — one measured
  from the stage's border box while it clips at the content box, two read constants from the stylesheet. All
  are fixed and each is now verified to fail on the fault it names, but a change with that history is worth
  her eyes rather than a self-merge. https://github.com/charredlatte/Pretty-Project-Portfolio/pull/64

- **The café still shows the old card until the page is republished.** Both #62 and #64 only change the
  repository: the artifact at `artifacts.json`'s `kittychat-cafe` keeps the page it was last published with.
  A session with the licensed art (read it back from the artifact, per CLAUDE.md "Republishing") needs to
  publish `catio/index.html` to that URL for any of this to reach her.

## Facts learned

- **The e2e suite had not parsed since the quest-log merge.** The merge that brought in #58 dropped the two
  lines closing the scene's test block, so `catio/test/run.sh` died with `SyntaxError: Unexpected end of
  input` before a single check ran. Both branches fixed it independently within the hour. Worth knowing that
  a merge can silently take a suite to zero: nothing reported a failure, because nothing ran.

- **`max-height: <percentage>` resolves to `none` against an indefinite height.** Two separate bugs in the
  queen's card came from this: `.homework { max-height: 46% }` in a grid row sized `auto` (so homework took
  the whole talk and the conversation had no height at all), and `.owner svg { max-height: 100% }` on an
  auto-height grid item (so the owner was never capped and her head was clipped). `fit-content()` on the
  track is what actually caps a grid row.
