"""python3 -m unittest litterbox/test_sort.py"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sort  # noqa: E402

ROOMS = {"garden": {"repos": ["Pretty-Project-Portfolio"]}, "study": {"repos": ["montfortoise-shopify"]},
         "kitchen": {"repos": ["Intermarche-grocery-shopping-app"]}}
CAFE = "Pretty-Project-Portfolio"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


class Box(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.cafe, self.shop = top / CAFE, top / "montfortoise-shopify"
        self.food = top / "Intermarche-grocery-shopping-app"
        for repo in (self.cafe, self.shop, self.food):
            (repo / ".git").mkdir(parents=True)   # a checkout to the sorter; real() makes one a git repo
        (self.cafe / "catio" / "data").mkdir(parents=True)
        (self.cafe / "catio" / "data" / "rooms.json").write_text(json.dumps(ROOMS))
        self.box = self.cafe / "litterbox"
        self.box.mkdir()
        self.said = []

    def tearDown(self):
        self.tmp.cleanup()

    def drop(self, name, text, project=None):
        front = f"---\nproject: {project}\n---\n" if project else ""
        (self.box / name).write_text(front + text, encoding="utf-8")

    def run_sort(self, write=True, given=None):
        sort.run(self.box, write=write, given=given, say=self.said.append)

    def snapshot(self):
        return {p: p.read_text() for p in Path(self.tmp.name).rglob("*.md") if ".git" not in p.parts}

    def check(self, name):
        """What she does to a pile: reads its project:, and deletes the "# a guess" comment."""
        pile = self.box / name
        pile.write_text(re.sub(r"  # a guess[^\n]*", "", pile.read_text()))

    def notes(self, repo):
        return (repo / sort.HOME.get(repo.name, sort.DEFAULT_HOME)).read_text()

    def real(self, repo, branch="feature"):
        """Make a checkout a git repo on `branch`, everything in it committed, with an origin to push to."""
        (repo / ".git").rmdir()
        origin = repo.parent / "origins" / repo.name
        git("init", "-q", "--bare", "-b", "main", str(origin), cwd=repo)
        git("init", "-q", "-b", "main", cwd=repo)
        git("config", "user.email", "t@t", cwd=repo)
        git("config", "user.name", "t", cwd=repo)
        git("remote", "add", "origin", str(origin), cwd=repo)
        git("add", "-A", cwd=repo)
        git("commit", "-q", "--allow-empty", "-m", "start", cwd=repo)
        git("push", "-q", "-u", "origin", "main", cwd=repo)
        git("remote", "set-head", "origin", "main", cwd=repo)
        if branch != "main":
            git("checkout", "-q", "-b", branch, cwd=repo)
        return origin

    def test_compress_drops_done_and_struck_items_with_what_is_under_them(self):
        lines = ["- Licences:", "  - ~~settled~~: and why", "    more on it", "  - who made plants.zip?"]
        self.assertEqual(sort.compress(lines), ["- Licences:", "  - who made plants.zip?"])
        self.assertEqual(sort.compress(["- [x] 1. Merged.", "  with notes"]), [])

    def test_compress_keeps_a_correction(self):
        lines = ["- ~~Tuesday~~ Wednesday: call the printer.", "- ~~Lanterns~~: done.", "- ~~An old idea~~"]
        self.assertEqual(sort.compress(lines), lines[:1])

    def test_notes_without_a_project_wait_in_a_pile_until_it_is_checked(self):
        self.drop("a.md", "# A\n\n- The catio is not this.\n", project="montfortoise-shopify")
        self.drop("b.md", "---\ndate: 2026-10-01\n---\n# B\n\n- The manor's stair moved.\n\n- Plain note with no pointer.\n")
        self.drop("c.md", "# C\n\n- Nothing points anywhere.\n")
        self.run_sort()
        self.assertIn("The catio is not this.", self.notes(self.shop))   # it had its project: filed
        self.assertFalse((self.box / "b.md").exists())
        pile = (self.box / f"{CAFE}.md").read_text()
        self.assertTrue(pile.startswith(f"---\nproject: {CAFE}  # a guess"), pile)
        self.assertIn("# B\n\n- The manor's stair moved. *— litterbox/b.md, 2026-10-01*", pile)
        self.assertEqual((self.box / "c.md").read_text(), "# C\n\n- Nothing points anywhere.\n")
        self.assertIn(f"waiting for a check: {CAFE}.md", self.said[-1])
        self.run_sort()
        self.assertFalse((self.cafe / "docs").exists())                  # a guess is never filed
        self.check(f"{CAFE}.md")
        self.run_sort()
        self.assertIn("### B\n\n- The manor's stair moved. *— litterbox/b.md, 2026-10-01*", self.notes(self.cafe))
        self.assertIn("Plain note with no pointer.", self.notes(self.cafe))
        self.assertEqual(sorted(p.name for p in self.box.glob("*.md")), ["c.md"])

    def test_piles_gather_a_project_s_notes_from_every_file(self):
        self.drop("a.md", "# Leftovers\n\n- Plan the meals for the week.\n\n- The catio stair needs a rail.\n\n"
                          "- The manor's attic needs a lamp.\n")
        self.drop("b.md", "- The manor's lift is slow.\n")
        self.run_sort()
        self.assertEqual(sorted(p.name for p in self.box.glob("*.md")),
                         ["Intermarche-grocery-shopping-app.md", f"{CAFE}.md"])
        cafe = (self.box / f"{CAFE}.md").read_text()
        self.assertIn("# Leftovers\n\n- The catio stair", cafe)
        self.assertIn("# b\n\n- The manor's lift is slow. *— litterbox/b.md*", cafe)   # no title: its file's name
        self.assertNotIn("meals", cafe)
        self.drop("d.md", "- The catio needs a gate.\n")
        self.run_sort()
        self.assertIn("The catio needs a gate.", (self.box / f"{CAFE}.md").read_text())   # joins the waiting pile
        self.check(f"{CAFE}.md")
        self.check("Intermarche-grocery-shopping-app.md")
        self.run_sort()
        self.assertIn("Plan the meals", self.notes(self.food))
        for note in ("rail", "lamp", "lift", "gate"):
            self.assertIn(note, self.notes(self.cafe))
        self.assertEqual(list(self.box.glob("*.md")), [])

    def test_repeats_are_dropped_keeping_the_longer(self):
        self.drop("a.md", "# Catio\n\n- The **stair** sits in the hall.\n\n- the stair sits in the hall now\n", CAFE)
        self.run_sort()
        cafe = self.notes(self.cafe)
        self.assertEqual(cafe.count("stair"), 1)
        self.assertIn("hall now", cafe)

    def test_notes_one_word_apart_are_not_repeats(self):
        self.drop("a.md", "# Catio\n\n- Rename the queen to Mochi.\n\n- Rename the queen to Pochi.\n\n"
                          "- The sign is right.\n\n- The sign isn't right.\n", CAFE)
        self.run_sort()
        self.drop("b.md", "# Catio\n\n- Rename the queen to Mochi, and her sister too.\n", CAFE)
        self.run_sort()
        for note in ("to Mochi.", "to Pochi.", "is right.", "isn't right.", "her sister too."):
            self.assertIn(note, self.notes(self.cafe))

    def test_frontmatter_survives_notepad(self):
        (self.box / "a.md").write_bytes("﻿---\r\nproject: montfortoise-shopify\r\n---\r\n- The catio is not this.\r\n"
                                        .encode("utf-8"))
        self.run_sort()
        self.assertIn("The catio is not this.", self.notes(self.shop))
        self.assertNotIn("project:", self.notes(self.shop))

    def test_ships_what_it_files_and_nothing_else(self):
        self.drop("a.md", "- A shop note.\n", "montfortoise-shopify")
        self.drop("b.md", "- A café note.\n", CAFE)
        self.drop("c.md", "- The catio's sign lies.\n")   # piled as a guess: not shipped
        shop, cafe = self.real(self.shop), self.real(self.cafe)
        (self.shop / "wip.txt").write_text("someone's work in progress")
        self.run_sort(write=False)
        self.assertEqual(git("rev-list", "--count", "feature", cwd=self.shop), "1\n")
        self.run_sort()
        self.assertIn("montfortoise-shopify: committed and pushed to feature", self.said)
        self.assertIn(f"{CAFE}: committed and pushed to feature", self.said)
        self.assertIn("A shop note.", git("show", "feature:admin/from-the-litterbox.md", cwd=shop))
        self.assertIn("A café note.", git("show", "feature:docs/from-the-litterbox.md", cwd=cafe))
        self.assertEqual(git("log", "-1", "--format=%s", "feature", cwd=shop),
                         "File 1 note from the KittyChat Café's litter box\n")
        self.assertEqual(git("ls-tree", "--name-only", "feature", "litterbox/", cwd=cafe), "litterbox/c.md\n")
        self.assertEqual(git("status", "--porcelain", cwd=self.shop), "?? wip.txt\n")
        self.assertEqual(git("status", "--porcelain", cwd=self.cafe), f" D litterbox/c.md\n?? litterbox/{CAFE}.md\n")

    def test_never_ships_to_the_default_branch_or_where_shipping_is_off(self):
        self.drop("a.md", "- A shop note.\n", "montfortoise-shopify")
        self.drop("b.md", "- A café note.\n", CAFE)
        self.real(self.shop, branch="main")
        self.real(self.cafe)
        (self.cafe / ".claude").mkdir()
        (self.cafe / ".claude" / "catio-rules.json").write_text('{"ship": false}')
        self.run_sort()
        self.assertIn("montfortoise-shopify: written, not committed: it is on main, and the sorter never commits to the "
                      "default branch", self.said)
        self.assertIn(f"{CAFE}: written, not committed: shipping is switched off here", self.said)
        self.assertEqual(git("rev-list", "--count", "HEAD", cwd=self.shop), "1\n")
        self.assertEqual(git("rev-list", "--count", "HEAD", cwd=self.cafe), "1\n")

    def test_sections_come_from_headings_and_keep_their_own(self):
        self.drop("a.md", "# Catio audit (today)\n\n## Questions waiting\n\n- Rename the cat?\n\n"
                          "## Critical\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", CAFE)
        self.run_sort()
        cafe = self.notes(self.cafe)
        self.assertLess(cafe.index("## Waiting on Charlotte"), cafe.index("## Findings"))
        self.assertIn("### Catio audit › Critical\n\n| a | b |", cafe)
        self.assertIn("| 1 | 2 |\n\n*— litterbox/a.md*", cafe)  # right under the table, it would be a row

    def test_a_project_with_no_checkout_stays_in_the_box(self):
        (self.shop / ".git").rmdir()
        self.drop("a.md", "- A shop note.\n", "montfortoise-shopify")
        self.run_sort()
        self.assertTrue((self.box / "a.md").exists())
        self.assertTrue(any("no checkout" in s for s in self.said))
        self.run_sort(given={"montfortoise-shopify": str(self.shop)})
        self.assertFalse((self.box / "a.md").exists())

    def test_a_dry_run_writes_nothing_and_the_box_settles(self):
        self.drop("a.md", "# Loose ends\n\n## Facts learned\n\n- The catio's sign lies.\n\n"
                          "## Merge\n\n- [x] Done.\n\n- Left: the kitchen.\n\n- Who made plants.zip?\n")
        self.drop("b.md", "# B\n\n- Nothing points anywhere.\n")
        before = self.snapshot()
        self.run_sort(write=False)
        self.assertEqual(self.snapshot(), before)
        self.run_sort()   # piled
        self.check(f"{CAFE}.md")
        self.run_sort()   # filed
        after = self.snapshot()
        self.run_sort()
        self.assertEqual(self.snapshot(), after)
        self.drop("c.md", "- the catio's sign lies\n")
        self.run_sort()
        self.check(f"{CAFE}.md")
        self.run_sort()   # already filed: dropped
        self.assertEqual(self.snapshot(), after)

    def test_a_box_kept_outside_any_checkout_uses_this_repos_rooms(self):
        box = Path(self.tmp.name) / "private"
        box.mkdir()
        (box / "a.md").write_text("# A\n\n- The catio needs a gate.\n", encoding="utf-8")
        sort.run(box, write=True, say=self.said.append)
        self.assertTrue((box / "Pretty-Project-Portfolio.md").exists(), self.said)


if __name__ == "__main__":
    unittest.main()
