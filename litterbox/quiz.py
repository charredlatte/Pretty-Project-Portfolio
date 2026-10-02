#!/usr/bin/env python3
"""The litter box quiz (litterbox/quiz.html): the piles waiting for a check, as cards, and her answers back.

    python3 litterbox/quiz.py cards OUT_DIR [--box DIR]      one JSON file per card, for ArtifactData: cards/<id>
    python3 litterbox/quiz.py apply ANSWERS_DIR [--box DIR]  her answers, as ArtifactData saves answers/ (out_dir)

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
import sys
import time
from pathlib import Path

from sort import BOX, TAG, leftover, norm, projects, read_box


def waiting(box):
    """[(pile, its frontmatter, the guessed project, its notes)] for each pile still waiting for a check."""
    files = read_box(box, projects(BOX.parent))
    return [(path, front, project, notes) for path, (front, notes, _, project, guess) in files.items() if guess and notes]


def card_id(pile, note):
    return hashlib.sha1(f"{pile.name}\n{norm(note.lines)}".encode()).hexdigest()[:12]


def cards(out, box):
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.json"):   # a previous deal: its cards may be filed or dropped by now
        stale.unlink()
    order = 0
    for pile, _, guess, notes in waiting(box):
        for n in notes:
            text = "\n".join(n.lines)
            tag = TAG.search(text)
            heads = [h.lstrip("#").strip() for h in n.heads]
            card = {"text": TAG.sub("", text).rstrip(), "guess": guess, "pile": pile.name, "order": order,
                    "title": heads[0] if heads else "", "section": n.kind,
                    "from": tag.group(0).strip(" *—") if tag else f"litterbox/{n.src}"}
            cid = card_id(pile, n)
            (out / f"{cid}.json").write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
            print(cid, pile.name, "·", card["text"].splitlines()[0][:70])
            order += 1
    print(f"{order} cards in {out}")


def apply(answers_dir, box):
    answers = {}
    for path in Path(answers_dir).rglob("*.json"):
        a = json.loads(path.read_text(encoding="utf-8"))
        answers[path.stem] = a.get("data", a)
    today = time.strftime("%Y-%m-%d")
    sorted_, dropped = {}, 0
    for pile, front, _, notes in waiting(box):
        keep = []
        for n in notes:
            a = answers.get(card_id(pile, n)) or {}
            if a.get("verdict") == "file" and a.get("project"):
                sorted_.setdefault(a["project"], []).append(n)
            elif a.get("verdict") == "drop":
                dropped += 1
            else:   # unanswered, or an answer that says nothing: the note stays
                keep.append(n)
        if len(keep) == len(notes):
            continue   # untouched: leave the pile byte for byte
        text = leftover(front, keep)
        if text:
            pile.write_text(text, encoding="utf-8")
        else:
            pile.unlink()
        print(f"{pile.name}: {len(notes) - len(keep)} answered, {len(keep)} left")
    for project, notes in sorted_.items():
        dest = box / f"{today}-sorted-{project}.md"
        before = dest.read_text(encoding="utf-8") if dest.exists() else f"---\nproject: {project}\ndate: {today}\n---\n"
        dest.write_text(before.rstrip() + "\n\n" + leftover("", notes), encoding="utf-8")
        print(f"{dest.name}: {len(notes)} checked for {project}")
    print(f"dropped as settled: {dropped}. Next: python3 litterbox/sort.py --write" + (f" --box {box}" if box != BOX.resolve() else ""))


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("what", choices=["cards", "apply"])
    p.add_argument("dir", type=Path)
    p.add_argument("--box", type=Path, default=BOX)
    args = p.parse_args(argv)
    (cards if args.what == "cards" else apply)(args.dir, args.box.resolve())


if __name__ == "__main__":
    main(sys.argv[1:])
