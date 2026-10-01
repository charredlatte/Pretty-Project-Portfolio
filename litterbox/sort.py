#!/usr/bin/env python3
"""Empty the litter box: file each useful note into its own project's repo.

    python3 litterbox/sort.py                 a dry run: what would be dropped, and filed where
    python3 litterbox/sort.py --write         do it
    python3 litterbox/sort.py --checkout montfortoise-shopify=../shop --write

Every litterbox/*.md but README.md is split into notes: a top-level bullet with everything indented under it,
a paragraph, or a table. Then:

- compress: done checklist items (`- [x]`) and settled ones (struck through whole, or `- ~~label~~: why`) are
  dropped, with what is indented under them, and so are blank runs. A correction (`- ~~Tuesday~~ Wednesday`) stays;
- dedupe: a note that repeats another, or one already filed, is dropped. Case, accents, markdown and
  punctuation don't count; a note whose words all appear, in order, in another is a repeat, and the longer is kept;
- sort: a note belongs to its file's frontmatter `project:`, else to the repo its words point at (digest.py's
  BELONGS, or the repo's own name), else to the repo most of its file points at. A guess files a note only into
  this repo or a PRIVATE one: a note guessed for another public repo stays until its file names the project;
- compile: a project's notes go to its checkout, in HOME[repo] (default docs/from-the-litterbox.md), under
  Waiting on Charlotte, Ideas not built, Facts learned or Findings (from the headings they sat under), and
  inside that under their own heading.

Filed and dropped notes leave the litter box, and a file left empty is deleted (git keeps it). A note with no
project, or whose project has no checkout beside this repo (or given with --checkout), stays where it is.
The projects are the repos in catio/data/rooms.json, plus those BELONGS names. It only writes files: it ends by
naming each repo it wrote into, to commit and push. Standard library only.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

BOX = Path(__file__).resolve().parent
sys.path.insert(0, str(BOX.parent / "catio" / "tools"))
from digest import BELONGS, home_of  # noqa: E402

HOME = {"montfortoise-shopify": "admin/from-the-litterbox.md"}
# Where a guessed note may go besides this repo: private repos. Filing a note publishes it at the next push, so a
# note for any other repo (public, or not listed here) is filed only when its file's frontmatter names the project.
PRIVATE = {"montfortoise-shopify", "tiktok-saves", "pixel-art-app"}
DEFAULT_HOME = "docs/from-the-litterbox.md"
# A note's section, from the words of the deepest heading over it that has any of them.
KINDS = [
    ("Waiting on Charlotte", r"\bquestion|\bwaiting\b|\bto decide\b"),
    ("Ideas not built", r"\bidea|\bnot built\b|\bwishlist|\bmissing\b|\bto do\b|\bbuy\b"),
    ("Facts learned", r"\bfacts?\b|\blearn|\blesson"),
]
FINDINGS = "Findings"
ORDER = [k for k, _ in KINDS] + [FINDINGS]
TITLE = """# From the litter box

Notes filed here from the KittyChat Café's litter box by `litterbox/sort.py`. Each ends with the file it came
from. Edit them freely: the sorter only adds, and never files a note that is already here."""

HEADING = re.compile(r"(#{1,6})\s")
BULLET = re.compile(r"([-*+]|\d+[.)])\s")
RULE = re.compile(r"(-{3,}|\*{3,}|_{3,})$")
DONE = re.compile(r"\s*([-*+]|\d+[.)])\s+(\[[xX]\]|~~[^~]+~~(:|\W*$))")
FRONT = re.compile(r"---\n(.*?)\n---\n", re.S)
TAG = re.compile(r"\s*\*— litterbox/[^*]+\*\s*$")


@dataclass
class Note:
    heads: tuple
    lines: list
    src: str = ""
    date: str = ""
    project: str = ""
    pinned: bool = False

    @property
    def kind(self):
        for h in reversed(self.heads):
            for name, words in KINDS:
                if re.search(words, h, re.I):
                    return name
        return FINDINGS

    @property
    def topic(self):
        """The heading it goes under in its section: its file's title (up to any bracket), and the deepest
        heading under that which isn't just the section's name."""
        heads = [h.lstrip("#").strip() for h in self.heads]
        title = heads.pop(0).split(" (")[0] if self.heads and self.heads[0].startswith("# ") else ""
        inner = next((h for h in reversed(heads) if h.lower() != self.kind.lower()), "")
        return " › ".join(filter(None, [title, inner]))

    def tagged(self):
        dated = self.date and self.date not in self.src
        tag = f"*— litterbox/{self.src}{', ' + self.date if dated else ''}*"
        last = self.lines[-1]
        if last.startswith("|"):  # a line right under a table would be one more row of it
            return "\n".join(self.lines + ["", tag])
        if last.lstrip().startswith("```"):
            return "\n".join(self.lines + [tag])
        return "\n".join(self.lines[:-1] + [f"{last} {tag}"])


def split(body):
    """The notes of a markdown body, each with the heading lines over it."""
    heads, out, cur, kind, fence, gap = [], [], None, "", False, False

    def flush():
        nonlocal cur, gap
        if cur:
            out.append(Note(tuple(heads), cur))
        cur, gap = None, False

    for line in body.splitlines():
        line = line.rstrip()
        if fence:
            cur.append(line)
            fence = not line.lstrip().startswith("```")
            continue
        if not line:
            gap = cur is not None
            continue
        indent = len(line) - len(line.lstrip())
        if RULE.match(line):
            flush()
        elif HEADING.match(line):
            flush()
            level = len(line) - len(line.lstrip("#"))
            heads = [h for h in heads if len(h) - len(h.lstrip("#")) < level] + [line]
        elif line.lstrip().startswith("```"):
            if cur is None or kind == "table":
                flush()
                cur, kind = [], "para"
            cur += [""] * gap + [line]
            fence, gap = True, False
        elif BULLET.match(line):
            flush()
            cur, kind = [line], "bullet"
        elif cur is not None and kind == "bullet" and (indent or not (gap or line.startswith("|"))):
            cur += [""] * gap + [line]
            gap = False
        elif line.startswith("|"):
            if not (cur is not None and kind == "table" and not gap):
                flush()
                cur, kind = [], "table"
            cur.append(line)
        elif cur is not None and kind == "para" and not gap:
            cur.append(line)
        else:
            flush()
            cur, kind = [line], "para"
    flush()
    return out


def compress(lines):
    """The note without its done or struck-through items (and what is indented under them), or []."""
    kept, skip = [], None
    for line in lines:
        indent = len(line) - len(line.lstrip())
        if skip is not None and (not line or indent > skip):
            continue
        skip = None
        if DONE.match(line):
            skip = indent
            continue
        if line or (kept and kept[-1]):
            kept.append(line)
    while kept and not kept[-1]:
        kept.pop()
    return kept


def norm(lines):
    text = TAG.sub("", "\n".join(lines))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^\w\s]|_", " ", text).split())


def within(a, b):
    """Does note a say nothing that b doesn't: all its words, in order, inside b's? (Mochi is not Pochi.)"""
    return a == b or bool(a) and f" {a} " in f" {b} "


def projects(root):
    rooms = json.loads((root / "catio" / "data" / "rooms.json").read_text(encoding="utf-8"))
    repos = [r for room in rooms.values() for r in room.get("repos", [])]
    repos += [home for _, home in BELONGS if not any(home_of(r, home) for r in repos)]
    pats = {r: [re.escape(r).replace(r"\-", r"[-\s]")] for r in dict.fromkeys(repos)}
    for pat, home in BELONGS:
        pats[next(r for r in pats if home_of(r, home))].append(pat)
    return pats


def point(text, pats):
    """The one repo the text names most, or "" on a tie or none."""
    top = Counter({r: sum(len(re.findall(p, text, re.I)) for p in ps) for r, ps in pats.items()}).most_common(2)
    if top and top[0][1] and (len(top) == 1 or top[0][1] > top[1][1]):
        return top[0][0]
    return ""


def checkout(repo, root, given):
    if repo in given:
        return Path(given[repo]).expanduser().resolve()
    for d in root.parent.iterdir():
        if d.name.lower() == repo.lower() and (d / ".git").exists():
            return d
    return None


def read_box(box, pats):
    """{file: (frontmatter, notes)}, each note compressed, dated and pointed at a project. Also the drops."""
    files, dropped = {}, 0
    for path in sorted(box.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8-sig")  # -sig: Notepad starts a file with a BOM
        m = FRONT.match(text)
        meta = dict((k.strip(), v.split("#")[0].strip()) for k, _, v in
                    (line.partition(":") for line in m.group(1).splitlines()) if v) if m else {}
        date = meta.get("date") or (re.match(r"\d{4}-\d{2}-\d{2}", path.name) or [""])[0]
        notes = []
        for n in split(text[m.end():] if m else text):
            n.lines = compress(n.lines)
            if not n.lines:
                dropped += 1
                continue
            n.src, n.date = path.name, date
            n.pinned = bool(meta.get("project"))
            n.project = meta.get("project") or point("\n".join(n.heads + tuple(n.lines)), pats)
            notes.append(n)
        most = Counter(n.project for n in notes if n.project).most_common(1)
        for n in notes:
            n.project = n.project or (most[0][0] if most else "")
        files[path] = (m.group(0) if m else "", notes, dropped)
        dropped = 0
    return files


def sections(text):
    """A destination file as its head and {section: {heading in it: body}}."""
    head, out, kind, sub = [], {}, None, ""
    for line in text.splitlines():
        if line.startswith("## "):
            kind, sub = line[3:].strip(), ""
            out.setdefault(kind, {}).setdefault(sub, [])
        elif kind is None:
            head.append(line)
        elif line.startswith("### "):
            sub = line[4:].strip()
            out[kind].setdefault(sub, [])
        else:
            out[kind][sub].append(line)
    return "\n".join(head).strip(), {k: {s: "\n".join(b).strip() for s, b in subs.items()} for k, subs in out.items()}


def compose(head, secs):
    parts = [head]
    for kind in [k for k in ORDER if k in secs] + [k for k in secs if k not in ORDER]:
        subs = {s: b for s, b in secs[kind].items() if b}
        if subs:
            parts.append(f"## {kind}")
            parts += [x for s, b in subs.items() for x in ([f"### {s}"] if s else []) + [b]]
    return "\n\n".join(parts) + "\n"


def file_into(dest, notes):
    """The notes not already in dest (keeping the longer of two repeats), and dest's new text."""
    text = dest.read_text(encoding="utf-8-sig") if dest.exists() else ""
    have = [norm(n.lines) for n in split(text)]
    new = []
    for n in notes:
        key = norm(n.lines)
        if any(within(key, h) for h in have):
            continue
        twin = next((i for i, (k, _) in enumerate(new) if within(key, k) or within(k, key)), None)
        if twin is None:
            new.append((key, n))
        elif len(key) > len(new[twin][0]):
            new[twin] = (key, n)
    head, secs = sections(text)
    for _, n in new:
        subs = secs.setdefault(n.kind, {})
        subs[n.topic] = "\n\n".join(filter(None, [subs.get(n.topic, ""), n.tagged()]))
    return [n for _, n in new], compose(head or TITLE, secs)


def leftover(front, notes):
    """What stays of a litter file: its frontmatter, and its notes under their headings."""
    out, shown = [front.rstrip()] if front else [], ()
    for n in notes:
        same = 0
        while same < min(len(shown), len(n.heads)) and shown[same] == n.heads[same]:
            same += 1
        out += list(n.heads[same:]) + ["\n".join(n.lines)]
        shown = n.heads
    return "\n\n".join(out) + "\n" if notes else ""


def run(box=BOX, write=False, given=None, say=print):
    root, given = box.parent, given or {}
    files = read_box(box, projects(root))
    guessable = {r.lower() for r in PRIVATE | {root.name}}
    by_repo, homes, stay = {}, {}, {}
    for path, (_, notes, _) in files.items():
        for n in notes:
            if n.project and not n.pinned and n.project.lower() not in guessable:
                stay.setdefault((n.project, ", a guess at a public repo (name it in the file's project:)"), []).append(n)
                continue
            co = checkout(n.project, root, given) if n.project else None
            if co is None:
                why = ", no checkout here (use --checkout)" if n.project else ""
                stay.setdefault((n.project or "no project", why), []).append(n)
                continue
            homes[n.project] = co / HOME.get(n.project, DEFAULT_HOME)
            by_repo.setdefault(n.project, []).append(n)

    filed, wrote = set(), []
    for repo, notes in by_repo.items():
        new, text = file_into(homes[repo], notes)
        filed.update(id(n) for n in notes)
        say(f"{repo}: {len(new)} to file in {homes[repo]}" + (f", {len(notes) - len(new)} already there or repeated"
                                                               if len(notes) > len(new) else ""))
        if write and new:
            homes[repo].parent.mkdir(parents=True, exist_ok=True)
            homes[repo].write_text(text, encoding="utf-8")
            wrote.append(repo)
    for (project, why), notes in stay.items():
        say(f"staying in the box: {len(notes)} for {project}{why}, from " + ", ".join(sorted({n.src for n in notes})))
    done = sum(d for _, _, d in files.values())
    if done:
        say(f"dropped: {done} done or struck through")

    for path, (front, notes, dropped) in files.items():
        left = [n for n in notes if id(n) not in filed]
        if len(left) == len(notes) and not dropped:
            continue
        say(f"{path.name}: " + ("emptied, deleted" if not left else f"{len(left)} notes left"))
        if write and left:
            path.write_text(leftover(front, left), encoding="utf-8")
        elif write:
            path.unlink()
        if write and root.name not in wrote:
            wrote.insert(0, root.name)
    if wrote:
        say("written, not committed: commit and push " + ", ".join(wrote) + ", or the notes are lost with the checkout")
    if not write:
        say("dry run: nothing written. Add --write to do it.")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write", action="store_true", help="file the notes and empty the box")
    ap.add_argument("--checkout", action="append", default=[], metavar="REPO=PATH",
                    help="where a project's checkout is, when it isn't beside this repo")
    a = ap.parse_args(argv)
    run(write=a.write, given=dict(c.split("=", 1) for c in a.checkout))


if __name__ == "__main__":
    main(sys.argv[1:])
