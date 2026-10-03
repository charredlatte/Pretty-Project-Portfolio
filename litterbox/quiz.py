#!/usr/bin/env python3
"""The litter box quiz: the piles waiting for a check, as cards, and her answers back.

    python3 litterbox/quiz.py deal OUT_DIR [--box DIR]       one JSON file per card: the gateway's quiz arguments (the queen's quest log)
    python3 litterbox/quiz.py cards OUT_DIR [--box DIR]      one JSON file per card, for litterbox/quiz.html's database: cards/<id>
    python3 litterbox/quiz.py apply ANSWERS [--box DIR]      her answers: the gateway's quizzes result saved as a .json file,
                                                             or the directory ArtifactData saves quiz.html's answers/ into
    python3 litterbox/quiz.py stale QUIZZES [--box DIR]      the open litter box cards whose note no longer waits: to forget

A card is one note on a pile whose header is still a guess. Its id comes from the pile's name and the note's words,
so an answer finds its note again after the pile has changed. `apply` takes every answered note off its pile:
a settled one goes, and the rest go to litterbox/<date>-sorted-<project>.md under a checked `project:` header,
which the next `sort.py --write` files into that project's own repo. Unanswered notes stay on their piles.
--box points at another litter box, such as piles kept out of git because their projects are private; give sort.py the same --box.
Standard library only.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from sort import BOX, TAG, leftover, norm, projects, read_box, root_of


def waiting(box):
    """[(pile, its frontmatter, the guessed project, its notes)] for each pile still waiting for a check."""
    files = read_box(box, projects(root_of(box)))
    return [(path, front, project, notes) for path, (front, notes, _, project, guess) in files.items() if guess and notes]


def card_id(pile, note):
    return hashlib.sha1(f"{pile.name}\n{norm(note.lines)}".encode()).hexdigest()[:12]


SETTLED = "Settled: drop it"   # the quest log's way of saying a note is done with


def fresh(out):
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.json"):   # a previous deal: its cards may be filed or dropped by now
        if re.fullmatch(r"[0-9a-f]{12}", stale.stem):
            stale.unlink()


def notes_of(box):
    """(card id, card) for every note on a pile still waiting for a check, in order."""
    order = 0
    for pile, _, guess, notes in waiting(box):
        for n in notes:
            text = "\n".join(n.lines)
            tag = TAG.search(text)
            heads = [h.lstrip("#").strip() for h in n.heads]
            card = {"text": TAG.sub("", text).rstrip(), "guess": guess, "pile": pile.name, "order": order,
                    "title": heads[0] if heads else "", "section": n.kind,
                    "from": tag.group(0).strip(" *—") if tag else f"litterbox/{n.src}"}
            yield card_id(pile, n), card
            order += 1


def cards(out, box):
    fresh(out)
    n = 0
    for cid, card in notes_of(box):
        (out / f"{cid}.json").write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
        print(cid, card["pile"], "·", card["text"].splitlines()[0][:70])
        n += 1
    print(f"{n} cards in {out}")


def deal(out, box):
    """Each card as the arguments of the gateway's quiz tool: a litter box card in the queen's quest log."""
    fresh(out)
    bare = lambda r: r.rsplit("/", 1)[-1].lower()   # owner/repo and repo are one project
    repos = list({bare(r): r for r in reversed(list(projects(root_of(box))))}.values())[::-1]
    n = 0
    for cid, card in notes_of(box):
        guess = next((r for r in repos if bare(r) == bare(card["guess"])), card["guess"])
        options = [guess] + [r for r in repos if bare(r) != bare(guess)][:10] + [SETTLED]
        args = {"kind": "litterbox", "ref": cid, "title": card["title"] or card["pile"].removesuffix(".md"), "note": card["text"],
                "from": card["from"], "hint": guess, "questions": [{"q": "Which project is it for?", "options": options}]}
        (out / f"{cid}.json").write_text(json.dumps(args, ensure_ascii=False, indent=1), encoding="utf-8")
        print(cid, card["pile"], "·", card["text"].splitlines()[0][:70])
        n += 1
    print(f"{n} cards in {out}: deal each with the gateway's quiz tool")


def saved_quizzes(path):
    """The cards in a saved result of the gateway's quizzes tool: {quizzes: [...]}, or the list itself."""
    got = json.loads(path.read_text(encoding="utf-8"))
    cards = got.get("quizzes") if isinstance(got, dict) else got
    if not isinstance(cards, list) or not all(isinstance(z, dict) for z in cards):
        sys.exit(f"{path}: not a quizzes result (save what the quizzes tool returns: {{\"quizzes\": [...]}})")
    return cards


def stale(where, box):
    """The open litter box cards whose note is no longer on a pile waiting for a check: forget them."""
    waiting_now = {cid for cid, _ in notes_of(box)}
    gone = [z["id"] for z in saved_quizzes(Path(where)) if z.get("kind") == "litterbox" and z.get("status") != "done"
            and z.get("id", "").removeprefix("litterbox-") not in waiting_now]
    print("stale cards: " + " ".join(gone) if gone else "no stale cards")


def answers_of(where):
    """{card id: {verdict, project}}: from the gateway's quizzes result (a file), or quiz.html's answers (a directory)."""
    if where.is_file():
        out = {}
        for z in saved_quizzes(where):
            if z.get("kind") != "litterbox" or z.get("status") != "done" or not z.get("answers"):
                continue
            a = z["answers"][0]
            out[z["id"].removeprefix("litterbox-")] = {"verdict": "drop"} if a == SETTLED else {"verdict": "file", "project": a}
        return out
    answers = {}
    for path in Path(where).rglob("*.json"):
        a = json.loads(path.read_text(encoding="utf-8"))
        answers[path.stem] = a.get("data", a)
    return answers


def apply(where, box):
    where = Path(where)
    answers = answers_of(where)
    filed = []
    today = time.strftime("%Y-%m-%d")
    sorted_, rewrite, dropped = {}, {}, 0
    for pile, front, _, notes in waiting(box):
        keep = []
        for n in notes:
            cid = card_id(pile, n)
            a = answers.get(cid) or {}
            project = (a.get("project") or "").rsplit("/", 1)[-1]   # owner/repo: the pile is named after the repo
            if a.get("verdict") == "file" and project and project not in (".", "..") and "\\" not in project:
                sorted_.setdefault(project, []).append(n)
                filed.append(cid)
            elif a.get("verdict") == "drop":
                dropped += 1
                filed.append(cid)
            else:   # unanswered, or an answer that says nothing: the note stays
                if a:
                    print(f"{pile.name}: an answer names no project, note kept: {a}")
                keep.append(n)
        if len(keep) < len(notes):   # an untouched pile is left byte for byte
            rewrite[pile] = (front, keep, len(notes))
    for project, notes in sorted_.items():   # the sorted files first: a note is never taken off its pile before it has landed
        dest = box / f"{today}-sorted-{project}.md"
        before = dest.read_text(encoding="utf-8") if dest.exists() else f"---\nproject: {project}\ndate: {today}\n---\n"
        dest.write_text(before.rstrip() + "\n\n" + leftover("", notes), encoding="utf-8")
        print(f"{dest.name}: {len(notes)} checked for {project}")
    for pile, (front, keep, had) in rewrite.items():
        text = leftover(front, keep)
        if text:
            pile.write_text(text, encoding="utf-8")
        else:
            pile.unlink()
        print(f"{pile.name}: {had - len(keep)} answered, {len(keep)} left")
    print(f"dropped as settled: {dropped}. Next: python3 litterbox/sort.py --write" + (f" --box {box}" if box != BOX.resolve() else ""))
    if filed:   # the cards to clear: forget them in the gateway, or delete them from quiz.html's database
        print("filed cards: " + " ".join(f"litterbox-{c}" if where.is_file() else c for c in filed))


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("what", choices=["deal", "cards", "apply", "stale"])
    p.add_argument("dir", type=Path)
    p.add_argument("--box", type=Path, default=BOX)
    args = p.parse_args(argv)
    {"deal": deal, "cards": cards, "apply": apply, "stale": stale}[args.what](args.dir, args.box.resolve())


if __name__ == "__main__":
    main(sys.argv[1:])
