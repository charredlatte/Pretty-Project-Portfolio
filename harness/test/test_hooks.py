"""The house-rule hooks, run as Claude Code runs them: JSON on stdin, exit code and output back.

    python3 -m unittest discover harness/test
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


def run(script, data, cwd=None):
    return subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(data), capture_output=True, text=True, cwd=cwd)


def transcript(tmp, skills=()):
    p = Path(tmp) / "t.jsonl"
    with p.open("w") as f:
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
        for s in skills:
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": s}}]}}) + "\n")
    return str(p)


class Gates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def gate(self, tool, args, skills=(), cwd=None):
        return run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args,
                                "transcript_path": transcript(self.tmp, skills), "cwd": cwd or self.tmp})

    def test_browser_tool_needs_preflight(self):
        r = self.gate("mcp__playwright__browser_navigate", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("browser-agent-preflight", r.stderr)
        self.assertEqual(self.gate("mcp__playwright__browser_navigate", {}, ["anthropic-skills:browser-agent-preflight"]).returncode, 0)

    def test_browser_command_needs_preflight(self):
        self.assertEqual(self.gate("Bash", {"command": "node e2e.mjs --playwright"}, ["ponytail-audit"]).returncode, 2)
        self.assertEqual(self.gate("Bash", {"command": "sh catio/test/run.sh"}, ["ponytail-audit"]).returncode, 2)
        self.assertEqual(self.gate("Bash", {"command": "sh catio/test/run.sh"}, ["ponytail-audit", "browser-agent-preflight"]).returncode, 0)

    def test_repo_can_add_browser_commands(self):
        Path(self.tmp, ".claude").mkdir()
        Path(self.tmp, ".claude", "browser-commands").write_text("# ours\nmy-scraper\n")
        self.assertEqual(self.gate("Bash", {"command": "./my-scraper --go"}, ["ponytail-audit"]).returncode, 2)

    def test_reading_is_free(self):
        for tool, args in (("Bash", {"command": "ls -la && git status && cat README.md 2>/dev/null"}), ("Read", {"file_path": "x"}),
                           ("mcp__github__get_file_contents", {})):
            self.assertEqual(self.gate(tool, args).returncode, 0, tool)

    def test_edits_wait_for_the_audit(self):
        for tool, args in (("Edit", {"file_path": self.tmp + "/a.py"}), ("Write", {"file_path": self.tmp + "/b.md"}),
                           ("Bash", {"command": "git commit -m x"}), ("Bash", {"command": "git push -u origin b"}),
                           ("Bash", {"command": "echo hi > notes.txt"}), ("Bash", {"command": "sed -i s/a/b/ f"})):
            r = self.gate(tool, args)
            self.assertEqual(r.returncode, 2, args)
            self.assertIn("ponytail-audit", r.stderr)
            self.assertEqual(self.gate(tool, args, ["anthropic-skills:ponytail-audit"]).returncode, 0, args)

    def test_scratch_writes_are_free(self):
        repo = Path(self.tmp, "repo"); repo.mkdir()
        self.assertEqual(self.gate("Write", {"file_path": self.tmp + "/scratch/x.md"}, cwd=str(repo)).returncode, 0)
        self.assertEqual(self.gate("Bash", {"command": "python3 x.py > " + self.tmp + "/out.json"}, cwd=str(repo)).returncode, 0)
        self.assertEqual(self.gate("Bash", {"command": "python3 x.py > out.json"}, cwd=str(repo)).returncode, 2)

    def test_a_repo_can_switch_a_rule_off(self):
        Path(self.tmp, ".claude").mkdir(exist_ok=True)
        Path(self.tmp, ".claude", "catio-rules.json").write_text(json.dumps({"opening_audit": False}))
        self.assertEqual(self.gate("Edit", {"file_path": self.tmp + "/a.py"}).returncode, 0)
        self.assertEqual(self.gate("mcp__playwright__browser_click", {}).returncode, 2)


class Ship(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        origin, work = Path(self.tmp, "origin.git"), Path(self.tmp, "work")
        g = lambda *a, cwd=work: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
        subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(origin), str(work)], check=True, capture_output=True)
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        Path(work, "a").write_text("1"); g("add", "a"); g("commit", "-m", "one"); g("push", "-u", "origin", "HEAD:main")
        g("remote", "set-head", "origin", "main")
        self.work, self.g = work, g

    def stop(self, **kw):
        r = run("ship_check.py", {"hook_event_name": "Stop", "cwd": str(self.work), **kw}, cwd=self.work)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_quiet_on_the_default_branch_and_when_clean(self):
        Path(self.work, "a").write_text("2")
        self.assertIsNone(self.stop())               # on main: never nudged
        self.g("checkout", "-b", "feature"); self.g("checkout", "a")
        self.g("push", "-u", "origin", "feature")
        self.assertIsNone(self.stop())               # clean and pushed

    def test_nudges_once_for_unpushed_work(self):
        self.g("checkout", "-b", "feature")
        Path(self.work, "a").write_text("2")
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("uncommitted", out["reason"])
        self.assertIsNone(self.stop(stop_hook_active=True))
        self.g("commit", "-am", "two")
        self.assertIn("aren't pushed", self.stop()["reason"])
        self.g("push", "-u", "origin", "feature")
        self.assertIsNone(self.stop())

    def test_graphify_map_is_not_work_to_ship(self):
        self.g("checkout", "-b", "feature"); self.g("push", "-u", "origin", "feature")
        Path(self.work, "graphify-out").mkdir(); Path(self.work, "graphify-out", "graph.json").write_text("{}")
        self.assertIsNone(self.stop())


class GraphFirst(unittest.TestCase):
    def test_quiet_without_a_map_and_when_switched_off(self):
        tmp = tempfile.mkdtemp()
        r = run("graph_first.py", {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "x"}, "cwd": tmp}, cwd=tmp)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        Path(tmp, ".claude").mkdir(); Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps({"graph_first": False}))
        Path(tmp, "graphify-out").mkdir(); Path(tmp, "graphify-out", "graph.json").write_text('{"nodes": [], "links": []}')
        r = run("graph_first.py", {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}, "cwd": tmp}, cwd=tmp)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class GraphDoc(unittest.TestCase):
    def test_digests_a_graph_for_the_catio(self):
        out = Path(tempfile.mkdtemp(), "graphify-out"); out.mkdir()
        nodes = [{"id": f"n{i}", "label": f"thing{i}()", "community": i % 2, "community_name": ["Core", "Edges"][i % 2], "source_file": "a.py"} for i in range(6)]
        links = [{"source": "n0", "target": f"n{i}"} for i in range(1, 6)] + [{"source": "n1", "target": "n2"}]
        (out / "graph.json").write_text(json.dumps({"nodes": nodes, "links": links, "built_at_commit": "abc123"}))
        (out / "GRAPH_REPORT.md").write_text("## God Nodes (x)\n1. `thing0()` - 5 edges\n\n## Surprising Connections\n"
                                             "- `thing1()` --calls--> `thing2()`  [INFERRED]\n  a.py → b.py\n\n## Suggested Questions\n- **Why thing0?**\n  _because_\n")
        r = subprocess.run([sys.executable, str(HOOKS.parent / "skills" / "catio" / "graph_doc.py"), str(out), "--by", "session_1"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        key = r.stdout.splitlines()[0]
        doc = json.loads((out / "catio-graph.json").read_text())
        self.assertTrue(key.startswith("graphs/"))
        self.assertEqual((doc["nodes"], doc["edges"], doc["communities"], doc["by"]), (6, 6, 2, "session_1"))
        self.assertEqual(doc["gods"][0], {"label": "thing0()", "degree": 5, "file": "a.py"})
        self.assertEqual(doc["surprises"][0]["b"], "thing2()")
        self.assertEqual(doc["questions"], ["Why thing0?"])
        self.assertEqual(len(doc["map"]["l"]), 12)
        for n in doc["map"]["n"]:   # no arrays inside arrays, and every dot on the 300 x 160 map
            self.assertTrue(0 <= n["x"] <= 300 and 0 <= n["y"] <= 160, n)


class SessionStart(unittest.TestCase):
    def test_prints_the_rules(self):
        r = run("session_start.py", {"hook_event_name": "SessionStart", "source": "startup", "cwd": tempfile.mkdtemp()})
        self.assertEqual(r.returncode, 0)
        for words in ("KittyChat house rules", "browser-agent-preflight", "ponytail-audit", "[Catio]", "claude.ai/artifact/"):
            self.assertIn(words, r.stdout)

    def test_resume_skips_the_audit_prompt(self):
        r = run("session_start.py", {"source": "resume", "cwd": tempfile.mkdtemp()})
        self.assertNotIn("Start now with the read-only pass", r.stdout)


class Plugin(unittest.TestCase):
    def test_manifests_parse_and_point_at_real_files(self):
        root = HOOKS.parent
        json.loads((root / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((root.parent / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(market["plugins"][0]["source"], "./harness")
        hooks = json.loads((HOOKS / "hooks.json").read_text())["hooks"]
        for groups in hooks.values():
            for g in groups:
                for h in g["hooks"]:
                    script = h["command"].split("/hooks/")[1].strip('"')
                    self.assertTrue((HOOKS / script).exists(), script)
        self.assertTrue((root / "skills" / "catio" / "SKILL.md").read_text().startswith("---\nname: catio\n"))
        self.assertTrue((root / "skills" / "graphify" / "SKILL.md").read_text().startswith("---\nname: graphify\n"))
        self.assertTrue((root / "skills" / "graphify" / "LICENSE").exists())


if __name__ == "__main__":
    unittest.main()
