# Bringing a change

Thank you for driving the café. Two kinds of change, and they go to different places.

## Your own café stays on your fork

Your café is your car: paint it on your fork. Its name, rooms, colours, art, your gateway's Worker name and your
own secrets are yours, and they stay on your fork's branches. A pull request carrying them to this repository
can't be merged: this repository's `main` is Charlotte's café, and her gateway redeploys from it on every merge.

Most of it needs no code at all:

- **The café's name**: the first step of the wizard, or *Set up again…* in the House menu.
- **Rooms**: *Edit rooms* in the House menu (name, open or closed, which repositories live there).
- **Colours, fonts, sizes and art**: *The look* in the House menu, or `catio/art/skin.json` with your own drawings
  in `catio/art/skin/` (`python3 catio/tools/skin.py` checks them). `CLAUDE.md`, "Plug-and-play design", says what
  every slot takes.
- **Your gateway's name**: name the Worker what you like in Cloudflare, and set `name` in
  `harness/gateway/wrangler.jsonc` to the same on your fork. Workers Builds refuses a build when the two differ. A new
  name makes a new Worker, with a new address and none of your secrets: add them all to it before you open its address.

## A fix to the car itself comes back here

A bug, a missing step, a confusing message, a test that fails on your computer: those help everyone, so send them
here.

1. **Start from today's `main`, Charlotte's.** A copy a day behind can be missing the very fix you need, and your
   fork's own `main` (`origin`) may carry your café. Once: `git remote add upstream
   https://github.com/charredlatte/Pretty-Project-Portfolio`. Then, each time: `git fetch upstream`.
2. **One branch per change**, made from that `main`, not from your café's branch:
   `git switch -c fix/what-it-fixes upstream/main`, and push it to your fork (`git push -u origin fix/what-it-fixes`).
3. **Run the checks** that touch what you changed (*The pieces* in the README lists them, and *Running the tests*
   below says what to set up), on your own computer. CI runs the harness on Linux and Windows.
4. **Save files as UTF-8.** Windows tools and some AI edits save in another encoding, and `Café` turns into
   `CafÃ©`. `.editorconfig` asks your editor for UTF-8; look at the diff before you push.
5. **Keep `.claude/` out of it.** Opening this folder in Claude Code offers Charlotte's house rules
   (`.claude/settings.json`), which stop every edit until skills you may not have, such as `ponytail-audit`, have run.
   Decline them, or turn them off for your clone alone with
   `claude plugin disable kittychat-house-rules@kittychat --scope local`. Don't switch a rule off in
   `.claude/catio-rules.json` on your branch: a change there waits for Charlotte, like the next step says.
6. **Open the pull request** against `charredlatte/Pretty-Project-Portfolio` `main`, saying what was wrong and how
   you checked the fix. Changes under `harness/` and `.claude/` are the house rules themselves, and `.github/` holds the
   workflows that run with the repo's token: they always wait for Charlotte.

## Running the tests

```
sh catio/test/run.sh                                   # the page, about seven minutes
python3 -m unittest discover harness/test               # the hooks, the runner, the rules
(cd harness/gateway && npm install && npm test)         # the gateway, on workerd
python3 -m unittest litterbox/test_sort.py litterbox/test_quiz.py
```

The page's suite and its screenshots (`sh catio/test/run.sh look kitchen study`, which writes
`catio/test/.look/`) drive a headless Chromium through Playwright. `run.sh` is set up for the copies
preinstalled in Charlotte's cloud sessions. Elsewhere it needs `sh`, `python3` and Node, plus:

- `PLAYWRIGHT`, the absolute path of a `playwright` package folder. After `npm i -g playwright`, that is
  `$(npm root -g)/playwright`;
- either `CHROMIUM`, a Chromium executable, or `node "$PLAYWRIGHT/cli.js" install chromium` so Playwright has its
  own;
- `PORT`, if something else (such as `catio_mcp.py --serve`) holds 127.0.0.1:8791. `run.sh` doesn't notice a
  busy port.

Each run starts a fresh temporary profile with no logins or saved passwords, and the page loads only local files,
Google Fonts and, for the test alone, its own server on that port.

**A run without the licensed art is not a verdict.** The art packs are gitignored, so a fresh clone has none, and
three things then go red for want of it rather than a fault: the check that wants no warning sign, and the checks
of The look and a skin, which stand in for a café owner's own drawings. **A failure outside those is a real one.**
`run.sh` says so when it starts, and again at the end if the run went red. A run that ends in `CRASH` stopped
early, so its list is partial: the totals line is the only proof it reached the end.

**Never rewrite a test because it fails.** A failing check means the page is wrong, not the check. The only checks
that change are the ones a new ask contradicts, and then from the words of the ask, not from which class names went
away.

## Something isn't working?

Open an issue with **Something isn't working**. It asks for the words on the screen, copied as text. A screenshot is
welcome too, but text can be searched, and it's what tells us which version you are on. Never paste a password, a key or a
secret, in an issue or anywhere else.
