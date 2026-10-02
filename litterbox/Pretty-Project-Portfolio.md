---
project: Pretty-Project-Portfolio  # a guess by litterbox/sort.py: check it, then delete this comment to file these notes
---

# 28 September 2026: the chat that built the first Catio (sifted)

## Facts learned

- **The Catio artifact's wake subscription never registered** for the session that built it (`mint_failed`).
  A session can't count on being woken by her comments or edits on the page: read the page's database with
  `ArtifactData`, or ask her. *— litterbox/2026-10-02-catio-first-build.md*

- **A full `list_sessions` is too big to read inline**: about 83,000 characters for 46 sessions, 115,000 for 50. The tool
  saves it to a tool-results file, with the list under its `ccr` key; pass that object to
  `catio/tools/save-sessions.py` to refresh the Catio's saved copy. *— litterbox/2026-10-02-catio-first-build.md*

- **Testing the Catio's menus in Playwright:**
  - A menu laid over its target steals the hover, so menus open beside what they belong to, and a test
    points at a clear patch of floor (found with `elementFromPoint`).
  - The first Escape only closes a menu; zooming out takes a second one.
  - A tap focuses the cat, so focus may open a menu only when `:focus-visible`. Otherwise the tap's click
    lands on the stage and closes the menu. *— litterbox/2026-10-02-catio-first-build.md*

- **The Catio's localhost copy goes in her Google Drive**, in My Drive › Claude › KittyChat Cafe (local copy),
  not on her USB stick: it was never on the stick. The Drive connector can't upload a zip that size, so Claude
  sends `catio-local.zip` in the chat and she saves it in that folder. *— litterbox/2026-10-02-catio-first-build.md*

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
