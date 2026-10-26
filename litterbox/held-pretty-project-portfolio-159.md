---
project: Pretty-Project-Portfolio
date: 2026-10-26
---
# Held for review: charredlatte/Pretty-Project-Portfolio#159

## Waiting on Charlotte

- [ ] [charredlatte/Pretty-Project-Portfolio#159](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/159),
  the public demo page, is green and held for you to merge.
  Merge it on GitHub if it's right, or say what to change.

The merging rule held it, twice over, and only one of the two was a judgement call:

- The merge commit's `Guesses:` block said "none" and then wrote a paragraph of caveats, which the
  gate reads as guesses. That was a mistake in how it was written, not a thing left unchecked.
- The review had not run since the last commit. It was then run, found four more defects, and those
  were fixed — which left the review one commit behind again. That loop is why this stopped rather
  than trying a third time.

**Why it is worth looking at rather than merging on trust.** Seven review rounds each found something
real, and three of them found the same class of bug twice over: something drawn on top of the floor
plan quietly eating the hover and click events the rooms need, which every screenshot shows as
perfect. It happened with the cat layer, then the furniture and filing cabinets, then the hover line.
Two rounds found defects introduced by the previous round's fix — once an `aria-hidden` that turned
seven new room buttons into tab stops no screen reader can see, once a menu moved out of the stage so
a phone would not clip it, which then let a click on its own title dismiss it.

The pattern was fixing the instance and not the class, then writing a check that encoded the
incomplete fix. `demo/test/check.mjs` is the correction and is now the strongest part of the change:
it sweeps every room's interior as a grid at four widths with the map panel folded and open, reads
the room boxes off the drawn SVG rather than keeping a copy, checks what assistive tech is told, and
re-checks everything with motion turned off. Each fix was verified by breaking it again and watching
the check go red.

What a reviewer might reasonably still want:

- The suite is **not** wired into `.github/workflows/tests.yml` — a held path — so nothing re-runs it
  when the page changes. That step is yours, and without it the checks only run when someone
  remembers.
- The manor's room boxes are copied from `catio-app/generated/manor.json` rather than generated into
  the page, and the doorway rectangles were measured by eye. `demo/README.md` says so. Both drift if
  the plan moves.
- `demo/tools/sprites.py` duplicates about seventy lines of `landing/tools/scene.py`'s drawing
  primitives. They bound ellipses differently, so sharing them means redrawing every sprite and
  re-checking the landing scene.

Everything else in the change is green: the four CI jobs on `e175c76`, the whole browser suite, and
`demo/tools/sprites.py` regenerating `demo/art/` byte-identical.
