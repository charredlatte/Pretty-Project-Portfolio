# The litterbox

Where useful things land before they have a home: session notes, loose ends, findings, wishlists. Drop a
Markdown file in, then let the sorter empty it into the projects it is about. Nothing in here is read by the
page or the harness.

```bash
python3 litterbox/sort.py            # a dry run: what it would drop, and file where
python3 litterbox/sort.py --write    # do it, then commit and push what it filed
```

The sorter reads every `*.md` here except this README, a note at a time (a top-level bullet with everything
indented under it, a paragraph, or a table), and:

- **compresses:** done checklist items (`- [x]`) and settled ones go, with what is indented under them. Settled
  means struck through whole (`- ~~An old idea~~`) or a struck label with a colon (`- ~~Lanterns~~: done`). A
  correction (`- ~~Tuesday~~ Wednesday: call the printer`) is still live, so it stays;
- **dedupes:** a note that repeats another, or one already filed, goes. Case, accents, markdown and
  punctuation don't count. A repeat says nothing new: all its words appear, in order, in the other note, and
  the longer one stays. "Rename her Mochi" and "Rename her Pochi" are two notes;
- **sorts:** a note belongs to its file's `project:` (frontmatter). A file without one isn't filed: the sorter
  gives it the `project:` its notes point at, marked as a guess, and files it on the next run. The guess is
  the repo a note's words point at (`BELONGS` in `catio/tools/digest.py`, or the repo's own name), else the
  repo most of its file points at. A file whose notes point at different projects is split, a file for each,
  the biggest keeping the name. The projects are the repos in `catio/data/rooms.json`;
- **compiles:** each project's notes go into **its own repo**, in `docs/from-the-litterbox.md` (montfortoise:
  `admin/from-the-litterbox.md`; `HOME` in `sort.py`), under *Waiting on Charlotte*, *Ideas not built*,
  *Facts learned* or *Findings*. Each sits under its file's title and heading, and ends with the file it
  came from.

Filed and dropped notes leave the box, and a file left empty is deleted (git history keeps it). A note with no
project, or whose repo isn't checked out beside this one, stays here; pass `--checkout repo=path` for a repo
kept elsewhere.

**It ships what it files**, as the house rule for semi-automatic shipping says (`harness/rules.json`): in each
repo it wrote into, it commits the files it wrote, and only those, and pushes them to the branch that repo is
on. Never the default branch (there it only writes, and says so), never a force-push, and not where a repo
switches the rule off (`.claude/catio-rules.json`, `{"ship": false}`). Opening a pull request is the session's.
A header it has just guessed is never shipped: check it, then the next run files the notes and ships those.

This repo is public, and so is anything committed in the box. Run the sorter on a note about a private project
before you commit: the first run gives it its `project:`, the second files it straight into that project's
own repo.

It drops only what is certainly done or repeated. A note that has gone stale is a judgement call, so it gets
filed, and you can delete it where it lands; the sorter never files the same note twice.

To give a file its project yourself, start it with (a file saved by Notepad works too):

```
---
project: montfortoise-shopify
date: 2026-10-01
---
```

Her requests, compiled, are in [`docs/requests.md`](../docs/requests.md). The tests:
`python3 -m unittest litterbox/test_sort.py`.
