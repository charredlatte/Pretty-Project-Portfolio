---
name: litterbox-quiz
description: Check the litter box's piles one note at a time, as a quiz - a private artifact where each card asks which project a sifted note belongs to, or whether it is settled, and the answers are filed by litterbox/quiz.py and sort.py. The same page deals any deck with choices, such as the decisions waiting on Charlotte. Use when someone wants to sort or check the piles the sifter guessed, publish or republish the litter box quiz, deal its cards, says "file my litter box quiz answers", asks for a quiz of decisions, or says "file my decisions".
---

# The litter box quiz

`litterbox/sort.py` piles loose notes by project and marks each pile as a guess until someone checks it
(`litterbox/README.md`). The quiz is the checking, done like a round of flashcards: one note a card, the
project it belongs to as four choices (or every project), *Settled: drop it*, *Skip* and *Back*, and a peek
at the sifter's guess on the card's back. Every answer is saved as it is given, to the quiz's own database,
so piles of private projects never enter a public repository. Nothing is filed until the person says so.

Three parts, all in the repository:

| Part | What it is |
|---|---|
| `litterbox/quiz.html` | the page: a private artifact with the `db` capability. It reads `cards/*`, `meta/projects` and `answers/*` and writes only `answers/<card id>` |
| `litterbox/quiz.py` | `cards`: one JSON file per note on a pile still marked as a guess. `apply`: takes the answered notes off their piles |
| `litterbox/test_quiz.py` | `python3 -m unittest litterbox/test_quiz.py` |

## 1. Publish the page (once)

Publish `litterbox/quiz.html` as a **private** artifact with `capabilities: {db: {}}` and **no `files`**. Record
its URL in `artifacts.json` as `litter-box-quiz`; every later publish goes to that URL (`Artifact` publish with
`url`), so the cards and answers in its database carry over.

**The art is not shipped.** The page is drawn in the KittyChat Café's look: Cup Nooble's Sprout Lands UI pack
(panels, buttons, divider, pointer, paw cursor, the pixel font) and ToffeeCraft's cat-face logo. Both licences
forbid redistributing the files, even modified, so they are not in this repository and this skill does not pass
them. Without them the page still reads: each piece falls back to its own face colour, and the pixel font to
Fredoka. Someone who owns the packs may add them to their own copy as published files, cut by
`catio/tools/build-art.py`, at these paths:

`art/licensed/ui/panel.png`, `button.png`, `button-hover.png`, `button-down.png`, `button-green.png`,
`button-pink.png`, `divider.png`, `pointer.png`, `cursor.png`, `cursor-point.png`, `logo.png`, `sprout.ttf`.

Never commit them, and never publish them to a page anyone else can open.

## 2. Deal the cards

When piles are waiting for a check (`python3 litterbox/sort.py` lists them at the end of a dry run):

1. `python3 litterbox/quiz.py cards <dir>` writes one JSON file per note, named by the card's id. Pass
   `--box <dir>` when the piles are kept somewhere other than `litterbox/` (private projects, out of git).
2. Write each to the quiz's database with `ArtifactData`: a `batch` of `set`s to `cards/<id>`, `file_path`
   each. Delete cards that are no longer on a pile.
3. Write the projects to choose from to `meta/projects`: `{list: [{repo, label, words}]}`, where `words`
   are the words that point at that project (`BELONGS` in `catio/tools/digest.py`, or the repo's own name).
   The page scores the four choices from them and the sifter's guess.

Then tell the person the quiz is ready, with its URL. Answers save as they go; nothing else happens until
step 3.

## 3. File the answers

On "File my litter box quiz answers" (the line the page offers to copy when a round ends):

1. `ArtifactData` `list` `answers` with `out_dir`: one JSON file per answered card.
2. `python3 litterbox/quiz.py apply <out_dir>` (with the same `--box` as the cards). A settled note leaves its
   pile. A note given a project goes to `litterbox/<date>-sorted-<project>.md` under a checked `project:`
   header. Unanswered notes stay where they were.
3. `python3 litterbox/sort.py --write` files the checked notes into each project's own repository and pushes
   them, under the shipping rule.
4. Delete the filed cards and their answers from the database, so the next round starts clean.

Say what was filed where, and what is still waiting.

## A deck of decisions

The same page deals any deck whose cards carry their own choices: the decisions waiting on her (`docs/plan.md`
"Waiting on Charlotte", `docs/from-the-litterbox.md`, `docs/requests.md`), one to a card, with Claude's
recommendation on the back. It is a second private artifact, `decisions-quiz` in `artifacts.json`, published from
the same `litterbox/quiz.html` (its `<title>` swapped to "Decisions Quiz" in a copy outside the repo) with the same
twelve art files, copied server side from the litter box quiz (`files: {path: {artifact, path}}`), never from a
checkout.

1. **Its words:** `meta/deck`. Every key has the litter box's text as its default: `title`, `ask` ("WHAT DO YOU
   DECIDE?"), `peek`, `back` ("CLAUDE RECOMMENDS"), `noGuess`, `drop` ("DECIDE LATER"), `dropped` ("LATER"),
   `droppedTally`, `droppedSaid`, `same`, `differs` (`{guess}` is the recommended label), `src` (`{from}`), `tell`
   ("File my decisions."), `done`, `empty`, `footNone`, `footDrop`, `foot`.
2. **Deal the cards:** `cards/<key>` with `text` (markdown: the decision in bold, then its context), `title` (the
   area), `section` ("decision"), `from` (the doc it comes from), `order`, `options` (2 to 6 of `{key, label, why}`;
   the first four fill the grid, the rest open under "None of these"), `guess` (the recommended option's key) and
   `why` (one sentence, shown on the back). Write them by hand from the docs: no script, the decisions are prose.
   Facts only she can give (who made a file) are not decisions; leave them on the plan's list.
3. **File the answers** on "File my decisions.": `ArtifactData` `list` `answers`. Each answer is
   `{verdict: "file", project: <option key>}` or `{verdict: "drop"}` (later). Write every decided card as a line
   under a dated "Decided" heading in `docs/requests.md`, strike it from "Waiting on Charlotte" in `docs/plan.md`,
   leave the "later" ones there, then delete the filed cards and their answers from the database so the next deal
   starts clean.
