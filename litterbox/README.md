# The litter box

The back burner. Useful things land here before they have a home: session notes, loose ends, findings,
wishlists. Drop a Markdown file in, and the sifter finds what needs dealing with, piles it up by project under
a header, and waits for you to check each pile before anything leaves the box. Nothing in here is read by the
page or the harness.

```bash
python3 litterbox/sort.py            # a dry run: what it would drop, pile and file
python3 litterbox/sort.py --write    # do it, then commit and push what it filed
```

## What a run does

The sifter reads every `*.md` here except this README, a note at a time (a top-level bullet with everything
indented under it, a paragraph, or a table), and:

- **compresses:** done checklist items (`- [x]`) and settled ones go, with what is indented under them. Settled
  means struck through whole (`- ~~An old idea~~`) or a struck label with a colon (`- ~~Lanterns~~: done`). A
  correction (`- ~~Tuesday~~ Wednesday: call the printer`) is still live, so it stays;
- **piles:** a note in a file without a `project:` goes on its project's pile, `litterbox/<project>.md`. The
  pile's header is the sifter's guess, and says so: `project: tiktok-saves  # a guess by litterbox/sort.py:
  check it, …`. The guess is the repo a note's words point at (`BELONGS` in `catio/tools/digest.py`, or the
  repo's own name), else the repo most of its file points at. Each note keeps its file's title and headings,
  and a tag naming the file (and date) it came from. A note that points nowhere stays in its own file;
- **waits:** a pile marked as a guess is never filed. New notes for that project join it, and the run ends by
  listing the piles waiting for a check;
- **dedupes:** a note that repeats another, or one already filed, goes. Case, accents, markdown and
  punctuation don't count. A repeat says nothing new: all its words appear, in order, in the other note, and
  the longer one stays. "Rename her Mochi" and "Rename her Pochi" are two notes;
- **files:** a file whose `project:` isn't a guess is emptied into **that project's own repo**, in
  `docs/from-the-litterbox.md` (montfortoise: `admin/from-the-litterbox.md`; `HOME` in `sort.py`), under
  *Waiting on Charlotte*, *Ideas not built*, *Facts learned* or *Findings*. Each note sits under its file's
  title and heading, and ends with the file it came from.

Filed and dropped notes leave the box, and a file left empty is deleted (git history keeps it). A note whose
repo isn't checked out beside this one stays here; pass `--checkout repo=path` for a repo kept elsewhere.

It drops only what is certainly done or repeated. A note that has gone stale is a judgement call, so it gets
filed, and you can delete it where it lands; the sifter never files the same note twice.

## Checking a pile

Open `litterbox/<project>.md` and read it. If the project is right, delete the `# a guess …` comment from its
header. If it's wrong, change the project and delete the comment. Move a note to another pile, or out to a
file of its own, if it belongs elsewhere. The next run files every checked pile.

To give a file its project yourself, so it skips the pile, start it with (a file saved by Notepad works too):

```
---
project: montfortoise-shopify
date: 2026-10-01
---
```

### Or in the café, as homework

The KittyChat Café's queen keeps a quest log of everything waiting on Charlotte, and the litter box is in it: one
note a card, which project it is for, or *Settled: drop it*. She takes it in the café, from the House menu's
Homework or the litter box on the map (the library's chest), a tap a card. The cards and her answers live in her
gateway (`quizzes/<id>`, kind `litterbox`), so the notes of private projects never enter this public repo.

1. **Deal the cards:** `python3 litterbox/quiz.py deal <dir>` writes one file per note on a pile still marked as a
   guess: the arguments of the gateway's `quiz` tool (the `CATIO` connector). Call `quiz` with each. A card is dealt
   once (its `ref` is the note's id): dealing again replaces the open ones and leaves the answered ones alone.
   Then save `quizzes` with `{kind: "litterbox"}` and run `python3 litterbox/quiz.py stale <that file>`: `forget` the
   cards it lists, whose notes no longer wait (a pile checked or rewritten since).
2. **When she says to file them:** save the result of `quizzes` with `{done: true, kind: "litterbox"}` as a `.json`
   file, then `python3 litterbox/quiz.py apply <that file>`. Settled notes go. The rest leave their piles for
   `<date>-sorted-<project>.md`, checked, which the next `sort.py --write` files. Unanswered notes stay put.
3. `forget` the cards `apply` lists as filed, so the next round starts clean.

Piles of private projects aren't committed here: pass `--box <dir>` to both commands where they are kept.
Tests: `python3 -m unittest litterbox/test_quiz.py`.

The decisions waiting on her are the same: one `quiz` call each, kind `decision`, the decision in `note`, the options
in its one question, Claude's recommendation in `hint`, a short key in `ref`.

A café with no gateway uses `quiz.html` instead, a page of its own: `quiz.py cards` deals into its database and
`apply` takes the directory its `answers` are saved into. The skill `catio-plugin/skills/litterbox-quiz/SKILL.md`
says how to deal and file both.

## Held pull requests

When the house rules hold a merge for her (semi-automatic merging, `harness/README.md`), they drop
`held-<repo>-<number>.md` in here: the pull request, and each reason it is held, under *Waiting on Charlotte*. Its
`project:` is the repo, not a guess, so the next run files it straight into that repo. Tick it there once the
pull request is merged or closed.

## Shipping

**It ships what it files**, as the house rule for semi-automatic shipping says (`harness/rules.json`): in each
repo it wrote into, it commits the files it wrote, and only those, and pushes them to the branch that repo is
on. Never the default branch (there it only writes, and says so), never a force-push, and not where a repo
switches the rule off (`.claude/catio-rules.json`, `{"ship": false}`). Opening a pull request is the session's.
Piling is never shipped: a pile is still a guess.

This repo is public, and so is anything committed in the box. Sift a note about a private project before you
commit: it goes on its pile, and once you've checked the pile the next run files it straight into that
project's own repo.

Her requests, compiled, are in [`docs/requests.md`](../docs/requests.md). The tests:
`python3 -m unittest litterbox/test_sort.py`.
