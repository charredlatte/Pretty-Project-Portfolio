---
project: Pretty-Project-Portfolio
date: 2026-10-25
---
# Held for review: charredlatte/Pretty-Project-Portfolio#157

## Waiting on Charlotte

- [ ] [charredlatte/Pretty-Project-Portfolio#157](https://github.com/charredlatte/Pretty-Project-Portfolio/pull/157) is held for your review before it merges: it changes harness, which always waits for her.
  Two follow-ups to #156: the last of the blurbs you quoted leaves the test fixtures, and the café's address is never written into the download. The page no longer carries your artifact's link and `harness/rules.json` no longer carries your gateway; a session is told the café in its `CATIO_URL` or that it isn't connected. On the gateway a session now gets its file the way an agent does (`drop_file`, then its hook's `pick_up`), which also fixes a note that pointed sessions at an artifact the file was never in. `artifacts.json` keeps your published pages on purpose.
  Merge it on GitHub if it's right, or say what to change.
