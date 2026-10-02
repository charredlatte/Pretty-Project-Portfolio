"""python3 -m unittest litterbox/test_quiz.py"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quiz  # noqa: E402
from sort import GUESSED  # noqa: E402

PILE = f"""---
project: LibreSprite  {GUESSED}
---

# 2 October 2026: a round

## Waiting on Charlotte

- **The deployment session is waiting on a choice:** the dashboard, or an API key. *— litterbox/round.md*

- **The Emscripten build stopped at a usage limit.** Rerun it if it is still wanted. *— litterbox/round.md*

- **A third note nobody has answered yet.** *— litterbox/round.md*
"""


class Quiz(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.box = Path(self.tmp.name) / "box"
        self.box.mkdir()
        (self.box / "LibreSprite.md").write_text(PILE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def cards(self):
        out = Path(self.tmp.name) / "cards"
        with contextlib.redirect_stdout(io.StringIO()):
            quiz.cards(out, self.box)
        return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("*.json"))}

    def test_a_card_per_note_on_a_pile_waiting_for_a_check(self):
        cards = self.cards()
        self.assertEqual(len(cards), 3)
        first = min(cards.values(), key=lambda c: c["order"])
        self.assertEqual(first["guess"], "LibreSprite")
        self.assertEqual(first["section"], "Waiting on Charlotte")
        self.assertEqual(first["from"], "litterbox/round.md")
        self.assertNotIn("*— litterbox", first["text"])
        self.assertEqual(sorted(cards), sorted(self.cards()), "ids are stable")

    def test_a_checked_pile_is_not_a_quiz(self):
        (self.box / "LibreSprite.md").write_text(PILE.replace(GUESSED, ""), encoding="utf-8")
        self.assertEqual(self.cards(), {})

    def test_answers_file_settle_or_leave_each_note(self):
        ids = sorted(self.cards(), key=lambda i: self.cards()[i]["order"])
        answers = Path(self.tmp.name) / "saved" / "answers"
        answers.mkdir(parents=True)
        (answers / f"{ids[0]}.json").write_text(json.dumps({"verdict": "file", "project": "LibreSprite-on-iPad"}))
        (answers / f"{ids[1]}.json").write_text(json.dumps({"verdict": "drop", "project": None}))
        with contextlib.redirect_stdout(io.StringIO()):
            quiz.apply(answers.parent, self.box)
        sorted_ = next(self.box.glob("*-sorted-LibreSprite-on-iPad.md")).read_text(encoding="utf-8")
        self.assertIn("project: LibreSprite-on-iPad\n", sorted_)
        self.assertNotIn("guess", sorted_)
        self.assertIn("The deployment session is waiting", sorted_)
        self.assertIn("*— litterbox/round.md*", sorted_)
        self.assertNotIn("Emscripten", sorted_)
        left = (self.box / "LibreSprite.md").read_text(encoding="utf-8")
        self.assertIn("A third note", left)
        self.assertNotIn("Emscripten", left)
        self.assertNotIn("deployment session", left)


if __name__ == "__main__":
    unittest.main()
