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

- **compresses:** done checklist items (`- [x]`) and struck-through items (`- ~~…`) go, with what is indented
  under them;
- **dedupes:** a note that repeats another, or one already filed, goes. Case, accents, markdown and
  punctuation don't count, and 90% alike is a repeat. Of two repeats, the longer one stays;
- **sorts:** a note belongs to its file's `project:` (frontmatter), else to the repo its words point at
  (`BELONGS` in `catio/tools/digest.py`, or the repo's own name), else to the repo most of its file points
  at. The projects are the repos in `catio/data/rooms.json`;
- **compiles:** each project's notes go into **its own repo**, in `docs/from-the-litterbox.md` (montfortoise:
  `admin/from-the-litterbox.md`; `HOME` in `sort.py`), under *Waiting on Charlotte*, *Ideas not built*,
  *Facts learned* or *Findings*. Each sits under its file's title and heading, and ends with the file it
  came from.

Filed and dropped notes leave the box, and a file left empty is deleted (git history keeps it). A note with no
project, or whose repo isn't checked out beside this one, stays here; pass `--checkout repo=path` for a repo
kept elsewhere. Committing and pushing each repo is up to the session or to you: the sorter only writes files.

It drops only what is certainly done or repeated. A note that has gone stale is a judgement call, so it gets
filed, and you can delete it where it lands; the sorter never files the same note twice.

To pin a file to a project, start it with:

```
---
project: montfortoise-shopify
date: 2026-10-01
---
```

Her requests, compiled, are in [`docs/requests.md`](../docs/requests.md). The tests:
`python3 -m unittest litterbox/test_sort.py`.
