---
project: Pretty-Project-Portfolio  # a guess by litterbox/sort.py: check it, then delete this comment to file these notes
---

# 28 September 2026: the chat that built the first Catio (sifted)

## Facts learned

- **The Catio artifact's wake subscription never registered** for the session that built it (`mint_failed`).
  A session can't count on being woken by her comments or edits on the page: read the page's database with
  `ArtifactData`, or ask her. *— litterbox/2026-10-02-catio-first-build.md*

- **A full `list_sessions` is too big to read inline**: about 83,000 characters for 46 sessions. The tool
  saves it to a tool-results file, with the list under its `ccr` key; pass that object to
  `catio/tools/save-sessions.py` to refresh the Catio's saved copy. *— litterbox/2026-10-02-catio-first-build.md*

- **Testing the Catio's hover menus in Playwright:**
  - A menu laid over its target steals the hover, so menus open beside what they belong to, and a test
    hovers a clear patch of floor (found with `elementFromPoint`).
  - The first Escape only closes a menu; zooming out takes a second one.
  - A tap focuses the cat, so focus may open a menu only when `:focus-visible`. Otherwise the tap's click
    lands on the stage and closes the menu. *— litterbox/2026-10-02-catio-first-build.md*

## Questions waiting on Charlotte

- **Is the Catio on your USB stick current?** The zip this chat sent on 28 September is the one-floor cabin,
  from before the manor. `python3 catio/tools/bundle.py` builds a new one. *— litterbox/2026-10-02-catio-first-build.md*
