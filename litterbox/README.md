# The litterbox

Where useful things land before they have a home: session notes, loose ends, findings, wishlists. Drop a
Markdown file in, then let the sorter empty it into the projects it is about. Nothing in here is read by the
page or the harness.

```bash
python3 litterbox/sort.py            # a dry run: what it would drop, and file where
python3 litterbox/sort.py --write    # do it
```

The sorter reads every `*.md` here except this README, a note at a time (a top-level bullet with everything
indented under it, a paragraph, or a table), and:

- **compresses:** done checklist items (`- [x]`) and settled ones go, with what is indented under them. Settled
  means struck through whole (`- ~~An old idea~~`) or a struck label with a colon (`- ~~Lanterns~~: done`). A
  correction (`- ~~Tuesday~~ Wednesday: call the printer`) is still live, so it stays;
- **dedupes:** a note that repeats another, or one already filed, goes. Case, accents, markdown and
  punctuation don't count. A repeat says nothing new: all its words appear, in order, in the other note, and
  the longer one stays. "Rename her Mochi" and "Rename her Pochi" are two notes;
- **sorts:** a note belongs to its file's `project:` (frontmatter), else to the repo its words point at
  (`BELONGS` in `catio/tools/digest.py`, or the repo's own name), else to the repo most of its file points
  at. The projects are the repos in `catio/data/rooms.json`. A guess only ever files into this repo or a
  private one (`PRIVATE` in `sort.py`): a note that points at another public repo stays here until its file
  names the project;
- **compiles:** each project's notes go into **its own repo**, in `docs/from-the-litterbox.md` (montfortoise:
  `admin/from-the-litterbox.md`; `HOME` in `sort.py`), under *Waiting on Charlotte*, *Ideas not built*,
  *Facts learned* or *Findings*. Each sits under its file's title and heading, and ends with the file it
  came from.

Filed and dropped notes leave the box, and a file left empty is deleted (git history keeps it). A note with no
project, or whose repo isn't checked out beside this one, stays here; pass `--checkout repo=path` for a repo
kept elsewhere. The sorter only writes files: it ends by naming each repo it wrote into, and those need
committing and pushing, or a cloud session loses them with its container.

This repo is public, and so is anything committed in the box. Give a note about a private project its
`project:` and sort it before you commit, and it goes straight to that project's own repo.

It drops only what is certainly done or repeated. A note that has gone stale is a judgement call, so it gets
filed, and you can delete it where it lands; the sorter never files the same note twice.

To pin a file to a project, start it with (a file saved by Notepad works too):

```
---
project: montfortoise-shopify
date: 2026-10-01
---
```

Her requests, compiled, are in [`docs/requests.md`](../docs/requests.md). The tests:
`python3 -m unittest litterbox/test_sort.py`.
