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
