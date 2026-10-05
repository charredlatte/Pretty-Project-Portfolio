---
project: montfortoise-shopify  # a guess by litterbox/sort.py: check it, then delete this comment to file these notes
---

# 3 to 5 October 2026: what the café's sessions left (sifted)

## Ideas not built

- **A public alias for the shop's email.** The address will be public anyway: French law (LCEN) requires a contact email in an online shop's mentions légales. A free Google Workspace alias such as bonjour@montfortoise.com would land in the same inbox and could be filtered or retired later; Claude offered to swap it in on the link page. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

## Facts learned

- **The onboarding and shop Figma files predate the car and Ninine.** The car analogy and the rename are in the page, the repo's wireframes and the plans, but the Figma files weren't redrawn, since each redraw uses one of her monthly Figma calls. *— litterbox/2026-10-05-sessions-3-to-5-october.md*

## Findings

- **The shipping nudge raises false alarms about montfortoise-shopify.** In at least three café sessions (4 and 5 October) the Stop hook said montfortoise-shopify's branch had commits that weren't pushed, though nothing had changed there and the branch matched `main` once fetched. `ship_check.py` counts commits ahead of the container's local `origin/main` when the branch has no upstream, and that ref can be out of date. Fetching before comparing would quieten it; the change is under `harness/`, so hers to approve. *— litterbox/2026-10-05-sessions-3-to-5-october.md*
