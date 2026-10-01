"""python3 -m unittest litterbox/test_sort.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sort  # noqa: E402

ROOMS = {"garden": {"repos": ["Pretty-Project-Portfolio"]}, "study": {"repos": ["montfortoise-shopify"]}}


class Box(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.cafe, self.shop = top / "Pretty-Project-Portfolio", top / "montfortoise-shopify"
        for repo in (self.cafe, self.shop):
            (repo / ".git").mkdir(parents=True)
        (self.cafe / "catio" / "data").mkdir(parents=True)
        (self.cafe / "catio" / "data" / "rooms.json").write_text(json.dumps(ROOMS))
        self.box = self.cafe / "litterbox"
        self.box.mkdir()
        self.said = []

    def tearDown(self):
        self.tmp.cleanup()

    def drop(self, name, text):
        (self.box / name).write_text(text, encoding="utf-8")

    def run_sort(self, write=True, given=None):
        sort.run(self.box, write=write, given=given, say=self.said.append)

    def snapshot(self):
        return {p: p.read_text() for p in Path(self.tmp.name).rglob("*.md")}

    def test_compress_drops_done_and_struck_items_with_what_is_under_them(self):
        lines = ["- Licences:", "  - ~~settled~~: and why", "    more on it", "  - who made plants.zip?"]
        self.assertEqual(sort.compress(lines), ["- Licences:", "  - who made plants.zip?"])
        self.assertEqual(sort.compress(["- [x] 1. Merged.", "  with notes"]), [])

    def test_routes_by_frontmatter_then_words_then_the_file(self):
        self.drop("a.md", "---\nproject: montfortoise-shopify\n---\n# A\n\n- The catio is not this.\n")
        self.drop("b.md", "# B\n\n- The manor's stair moved.\n\n- Plain note with no pointer.\n")
        self.drop("c.md", "# C\n\n- Nothing points anywhere.\n")
        self.run_sort()
        shop = (self.shop / "admin" / "from-the-litterbox.md").read_text()
        cafe = (self.cafe / "docs" / "from-the-litterbox.md").read_text()
        self.assertIn("The catio is not this.", shop)
        self.assertIn("The manor's stair moved.", cafe)
        self.assertIn("Plain note with no pointer.", cafe)
        self.assertFalse((self.box / "a.md").exists())
        self.assertEqual((self.box / "c.md").read_text(), "# C\n\n- Nothing points anywhere.\n")

    def test_repeats_are_dropped_keeping_the_longer(self):
        self.drop("a.md", "# Catio\n\n- The **stair** sits in the hall.\n\n- the stair sits in the hall now\n")
        self.run_sort()
        cafe = (self.cafe / "docs" / "from-the-litterbox.md").read_text()
        self.assertEqual(cafe.count("stair"), 1)
        self.assertIn("hall now", cafe)

    def test_sections_come_from_headings_and_keep_their_own(self):
        self.drop("a.md", "# Catio audit (today)\n\n## Questions waiting\n\n- Rename the cat?\n\n"
                          "## Critical\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.run_sort()
        cafe = (self.cafe / "docs" / "from-the-litterbox.md").read_text()
        self.assertLess(cafe.index("## Waiting on Charlotte"), cafe.index("## Findings"))
        self.assertIn("### Catio audit › Critical\n\n| a | b |", cafe)
        self.assertIn("| 1 | 2 |\n*— litterbox/a.md*", cafe)

    def test_a_project_with_no_checkout_stays_in_the_box(self):
        (self.shop / ".git").rmdir()
        self.drop("a.md", "---\nproject: montfortoise-shopify\n---\n- A shop note.\n")
        self.run_sort()
        self.assertTrue((self.box / "a.md").exists())
        self.assertTrue(any("no checkout" in s for s in self.said))
        self.run_sort(given={"montfortoise-shopify": str(self.shop)})
        self.assertFalse((self.box / "a.md").exists())

    def test_a_dry_run_writes_nothing_and_a_second_run_changes_nothing(self):
        self.drop("a.md", "# Loose ends\n\n## Facts learned\n\n- The catio's sign lies.\n\n"
                          "## Merge\n\n- [x] Done.\n\n- Left: the kitchen.\n\n- Who made plants.zip?\n")
        self.drop("b.md", "# B\n\n- Nothing points anywhere.\n")
        before = self.snapshot()
        self.run_sort(write=False)
        self.assertEqual(self.snapshot(), before)
        self.run_sort()
        after = self.snapshot()
        self.run_sort()
        self.assertEqual(self.snapshot(), after)
        self.drop("c.md", "- the catio's sign lies\n")
        self.run_sort()
        self.assertEqual(self.snapshot(), after)


if __name__ == "__main__":
    unittest.main()
