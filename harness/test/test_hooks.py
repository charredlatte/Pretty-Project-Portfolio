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


def run(script, data, cwd=None, cloud=False):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
    if cloud:
        env["CLAUDE_CODE_REMOTE"] = "true"
    return subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(data), capture_output=True, text=True,
                          cwd=cwd, env=env)


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

    def test_scripts_that_write_wait_for_the_audit(self):
        for command in ("python3 litterbox/sort.py --write", "npm run vendors:apply -- --commit",
                        "python3 litterbox/sort.py --write > " + self.tmp + "/log.txt"):
            self.assertEqual(self.gate("Bash", {"command": command}).returncode, 2, command)
        for command in ("python3 litterbox/sort.py", "curl -s --write-out %{http_code} https://example.com"):
            self.assertEqual(self.gate("Bash", {"command": command}).returncode, 0, command)

    def test_no_claude_attribution_in_commits_on_public_repos(self):
        audited = ["anthropic-skills:ponytail-audit"]
        repos = {}
        for name, url in (("cafe", "https://github.com/charredlatte/Pretty-Project-Portfolio.git"),
                          ("shop", "https://github.com/charredlatte/montfortoise-shopify")):
            repos[name] = Path(self.tmp, name)
            subprocess.run(["git", "init", "-q", str(repos[name])], check=True)
            subprocess.run(["git", "-C", str(repos[name]), "remote", "add", "origin", url], check=True)
        signed = "git commit -q -F - <<'EOF'\nFix it\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF"
        session = 'git commit -m "Fix it" -m "Claude-Session: https://claude.ai/code/session_1"'
        r = self.gate("Bash", {"command": signed}, audited, cwd=str(repos["cafe"]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no Claude attribution", r.stderr)
        self.assertEqual(self.gate("Bash", {"command": session}, audited, cwd=str(repos["cafe"])).returncode, 2)
        # from outside the repo, the way a cloud session commits
        self.assertEqual(self.gate("Bash", {"command": "cd cafe && " + signed}, audited).returncode, 2)
        self.assertEqual(self.gate("Bash", {"command": "git -C cafe " + signed[4:]}, audited).returncode, 2)
        # a private repo may keep the lines, and a public one may commit without them
        self.assertEqual(self.gate("Bash", {"command": signed}, audited, cwd=str(repos["shop"])).returncode, 0)
        self.assertEqual(self.gate("Bash", {"command": 'git commit -m "Fix it"'}, audited, cwd=str(repos["cafe"])).returncode, 0)
        # the message in a file, which the command doesn't show
        Path(self.tmp, "msg.txt").write_text("Fix it\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
        for flags in ("-F ../msg.txt", "--file=../msg.txt", "--amend -F ../msg.txt"):
            self.assertEqual(self.gate("Bash", {"command": "git commit " + flags}, audited, cwd=str(repos["cafe"])).returncode, 2, flags)
            self.assertEqual(self.gate("Bash", {"command": "git commit " + flags}, audited, cwd=str(repos["shop"])).returncode, 0, flags)
        self.assertEqual(self.gate("Bash", {"command": "cd cafe && git commit -F ../msg.txt"}, audited).returncode, 2)

    def test_no_claude_attribution_in_github_posts_on_public_repos(self):
        cafe = {"owner": "charredlatte", "repo": "Pretty-Project-Portfolio"}
        shop = {"owner": "charredlatte", "repo": "montfortoise-shopify"}
        footer = "Fix it\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        for tool, args in (("mcp__github__create_pull_request", {"body": footer}),
                           ("mcp__github__add_issue_comment", {"body": "Done.\n\n---\n_Generated by [Claude Code](https://claude.ai/code/session_1)_"}),
                           ("mcp__github__update_pull_request", {"body": "Fix it\n\nhttps://claude.ai/code/session_01Abc"}),
                           ("mcp__github__merge_pull_request", {"commit_message": "Merge\n\nCo-Authored-By: Claude <noreply@anthropic.com>"}),
                           ("mcp__github__push_files", {"message": "Fix\n\nClaude-Session: https://claude.ai/code/session_1"})):
            r = self.gate(tool, dict(cafe, **args))
            self.assertEqual(r.returncode, 2, tool)
            self.assertIn("no Claude attribution", r.stderr)
            # a private repo may keep them (a merge there may still be held, by the merging rule)
            self.assertNotIn("no Claude attribution", self.gate(tool, dict(shop, **args)).stderr, tool)
        # prose about the rule isn't a credit line
        about = "The gate refuses `Co-Authored-By: Claude` lines, and links like https://claude.ai/code/session_1 in a sentence."
        self.assertEqual(self.gate("mcp__github__create_pull_request", dict(cafe, body=about)).returncode, 0)

    def test_after_a_signed_post_on_a_public_repo_the_footer_comes_off(self):
        def after(tool, args):
            return run("gates.py", {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": args,
                                    "tool_response": {}, "cwd": self.tmp})
        cafe = {"owner": "charredlatte", "repo": "Pretty-Project-Portfolio", "body": "Fix it"}
        r = after("mcp__github__create_pull_request", cafe)
        self.assertEqual(r.returncode, 2)
        self.assertIn("update_pull_request", r.stderr)
        self.assertEqual(after("mcp__github__add_issue_comment", cafe).returncode, 2)
        self.assertEqual(after("mcp__github__issue_write", dict(cafe, method="create")).returncode, 2)
        self.assertEqual(after("mcp__github__issue_write", dict(cafe, method="update")).returncode, 0)
        self.assertEqual(after("mcp__github__update_pull_request", cafe).returncode, 0)
        self.assertEqual(after("mcp__github__create_pull_request", dict(cafe, repo="montfortoise-shopify")).returncode, 0)

    def sub_agent_edit(self, agent, model, path, merges=True):
        if merges:
            Path(self.tmp, ".claude").mkdir(exist_ok=True)
            Path(self.tmp, ".claude", "catio-rules.json").write_text(json.dumps({"merge": True}))
        side = Path(self.tmp) / "agent.jsonl"
        side.write_text(json.dumps({"type": "assistant", "isSidechain": True, "message": {"model": model, "content": []}}) + "\n")
        return run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": path},
                                "transcript_path": transcript(self.tmp, ["anthropic-skills:ponytail-audit"]), "cwd": self.tmp,
                                "agent_type": agent, "agent_transcript_path": str(side)})

    def test_scout_and_tester_never_edit(self):
        for agent in ("scout", "kittychat-house-rules:tester"):
            r = self.sub_agent_edit(agent, "claude-haiku-4-5-20251001", self.tmp + "/scratch.md", merges=False)
            self.assertEqual(r.returncode, 2, agent)
            self.assertIn("only reads, runs and reports", r.stderr)

    def test_a_small_sub_agent_leaves_tracked_files_alone_where_sessions_merge(self):
        subprocess.run(["git", "init", "-q", self.tmp]); Path(self.tmp, "app.py").write_text("x = 1\n")
        subprocess.run(["git", "-C", self.tmp, "add", "app.py"])
        r = self.sub_agent_edit("general-purpose", "claude-haiku-4-5-20251001", self.tmp + "/app.py")
        self.assertEqual(r.returncode, 2)
        self.assertIn("claude-haiku-4-5-20251001 may not edit a tracked file", r.stderr)
        for model, path in (("claude-opus-5-5", "/app.py"), ("claude-haiku-4-5-20251001", "/notes.txt")):
            self.assertEqual(self.sub_agent_edit("general-purpose", model, self.tmp + path).returncode, 0, (model, path))

    def test_a_small_sub_agent_may_edit_where_she_merges_by_hand(self):
        subprocess.run(["git", "init", "-q", self.tmp]); Path(self.tmp, "app.py").write_text("x = 1\n")
        subprocess.run(["git", "-C", self.tmp, "add", "app.py"])
        self.assertEqual(self.sub_agent_edit("general-purpose", "claude-sonnet-5-5", self.tmp + "/app.py", merges=False).returncode, 0)

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

    def stop(self, cwd=None, cloud=False, **kw):
        cwd = cwd or self.work
        r = run("ship_check.py", {"hook_event_name": "Stop", "cwd": str(cwd), **kw}, cwd=cwd, cloud=cloud)
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

    def test_in_the_cloud_every_repo_beside_this_one_counts(self):
        self.g("checkout", "-b", "feature"); self.g("push", "-u", "origin", "feature")
        shop = Path(self.tmp, "shop")
        subprocess.run(["git", "clone", str(Path(self.tmp, "origin.git")), str(shop)], check=True, capture_output=True)
        self.g("checkout", "-b", "notes", cwd=shop)
        Path(shop, "notes.md").write_text("filed by the sorter")
        self.assertIsNone(self.stop())                                   # on her PC: only this repo
        self.assertIn("shop's branch notes has uncommitted", self.stop(cloud=True)["reason"])
        self.assertIn("shop's branch notes", self.stop(cwd=self.tmp, cloud=True)["reason"])   # cwd holds the repos

    def test_a_repo_can_say_its_sessions_merge(self):
        self.g("checkout", "-b", "feature")
        Path(self.work, "a").write_text("2")
        self.assertIn("A finished pull request is hers to merge: tell her it's ready.", self.stop()["reason"])
        Path(self.work, ".claude").mkdir()
        Path(self.work, ".claude", "catio-rules.json").write_text('{"merge": true}')
        reason = self.stop()["reason"]
        self.assertIn("work merges its own pull requests: when the work is finished, run the code-review skill", reason)
        self.assertNotIn("hers to merge", reason)
        self.assertIn("Never the default branch, no force-push", reason)

    def test_graphify_map_is_not_work_to_ship(self):
        self.g("checkout", "-b", "feature"); self.g("push", "-u", "origin", "feature")
        Path(self.work, "graphify-out").mkdir(); Path(self.work, "graphify-out", "graph.json").write_text("{}")
        self.assertIsNone(self.stop())


class Merging(unittest.TestCase):
    """Semi-automatic merging: merged when nothing is a guess, held for her in the litter box when something is."""
    CARD = "Checks: unit tests pass\nGuesses: none"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = self.checkout("cafe", {"merge": True, "hold": ["harness/"]})
        box = Path(self.tmp, "box")
        subprocess.run(["git", "init", "-q", str(box)], check=True)
        Path(box, "litterbox").mkdir(); Path(box, "litterbox", "sort.py").write_text("")
        self.box = box / "litterbox"

    def checkout(self, name, rules=None):
        """A repo on a feature branch one commit ahead of origin/main, its origin on GitHub (never fetched)."""
        repo = Path(self.tmp, name)
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", f"https://github.com/charredlatte/{name}.git")
        Path(repo, "a").write_text("1")
        if rules is not None:
            Path(repo, ".claude").mkdir(); Path(repo, ".claude", "catio-rules.json").write_text(json.dumps(rules))
        g("add", "-A"); g("commit", "-qm", "one"); g("update-ref", "refs/remotes/origin/main", "HEAD")
        g("checkout", "-qb", "feature")
        Path(repo, "a").write_text("2"); g("commit", "-qam", "two")
        self.g = g
        return repo

    def head(self, repo=None):
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo or self.repo, capture_output=True, text=True).stdout.strip()

    def transcript(self, model="claude-opus-5-5", skills=("ponytail-audit", "code-review"), when="2999-01-01T00:00:00Z"):
        p = Path(self.tmp, "t.jsonl")
        with p.open("w") as f:
            for s in skills:
                f.write(json.dumps({"type": "assistant", "timestamp": when, "message": {"role": "assistant", "model": model,
                        "content": [{"type": "tool_use", "id": "t", "name": "Skill", "input": {"skill": "anthropic-skills:" + s}}]}}) + "\n")
        return str(p)

    def gate(self, tool, args, cwd=None, **kw):
        return run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args,
                                "transcript_path": self.transcript(**kw), "cwd": str(cwd or self.tmp)})

    def merge(self, message=CARD, head=None, repo="cafe", merge_method=None, **kw):
        args = {"owner": "charredlatte", "repo": repo, "pullNumber": 7, "commit_message": message,
                "expectedHeadSha": self.head() if head is None else head, "merge_method": merge_method}
        return self.gate("mcp__github__merge_pull_request", args, **kw)

    def note(self):
        p = self.box / "held-cafe-7.md"
        return p.read_text() if p.exists() else None

    def test_merges_when_a_strong_model_reviewed_it_and_nothing_is_a_guess(self):
        r = self.merge()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.note())
        self.assertEqual(self.merge(model="claude-fable-5-1").returncode, 0)

    def test_a_repo_that_doesnt_merge_leaves_it_to_her(self):
        self.checkout("shop")
        r = self.gate("mcp__github__merge_pull_request", {"owner": "charredlatte", "repo": "shop", "pullNumber": 3,
                                                           "commit_message": self.CARD, "expectedHeadSha": "x"})
        self.assertEqual(r.returncode, 2)
        self.assertIn('tell her in one line: "PR #3 is ready for you to merge."', r.stderr)
        r = self.gate("mcp__github__merge_pull_request", {"owner": "charredlatte", "repo": "elsewhere", "pullNumber": 3})
        self.assertIn("there's no checkout of charredlatte/elsewhere here", r.stderr)

    def test_guesswork_is_held_for_her_in_the_litter_box(self):
        r = self.merge("Checks: unit tests pass\nGuesses: that the Drive API rounds prices.")
        self.assertEqual(r.returncode, 2)
        self.assertIn("held PR #7 for Charlotte: guesses: that the Drive API rounds prices", r.stderr)
        self.assertIn('"PR #7 is waiting for your review: guesses: that the Drive API rounds prices."', r.stderr)
        note = self.note()
        self.assertTrue(note.startswith("---\nproject: cafe\ndate: "), note)
        self.assertIn("## Waiting on Charlotte\n\n- [ ] [charredlatte/cafe#7](https://github.com/charredlatte/cafe/pull/7)", note)
        self.assertNotIn("rounds prices..", note)

    def test_a_model_off_the_strong_list_is_held(self):
        r = self.merge(model="claude-sonnet-5-5")
        self.assertEqual(r.returncode, 2)
        self.assertIn("claude-sonnet-5-5 worked on it, and only opus or fable may merge", self.note())

    def test_held_paths_wait_for_her(self):
        Path(self.repo, "harness").mkdir(); Path(self.repo, "harness", "rules.json").write_text("{}")
        self.g("add", "-A"); self.g("commit", "-qm", "rules")
        self.assertIn("it changes harness, which always waits for her", self.merge().stderr)
        Path(self.repo, ".claude", "settings.json").write_text("{}")
        self.g("add", "-A"); self.g("commit", "-qm", "settings")
        self.assertIn("it changes .claude, harness", self.merge().stderr)

    def test_what_the_session_can_fix_is_sent_back_not_held(self):
        cases = (
            (dict(skills=("ponytail-audit",)), "run the code-review skill on PR #7"),
            (dict(when="2000-01-01T00:00:00Z"), "(it hasn't run since the last commit)"),
            (dict(skills=("code-review",)), "run the ponytail-audit skill"),
            (dict(head=""), "pass expectedHeadSha: " + self.head()),
            (dict(head="abc"), "expectedHeadSha is abc, but this checkout is at"),
            (dict(message="Merge it"), 'end the merge\'s commit message with "Checks: <what ran and passed>"'),
        )
        for kw, words in cases:
            r = self.merge(**kw)
            self.assertEqual(r.returncode, 2, kw)
            self.assertIn("not ready to merge PR #7 yet: ", r.stderr)
            self.assertIn(words, r.stderr, kw)
        Path(self.repo, "a").write_text("3")
        self.assertIn("commit or drop the uncommitted changes", self.merge().stderr)
        self.assertIsNone(self.note())

    def test_moving_a_file_out_of_a_held_path_is_still_held(self):
        Path(self.repo, "harness").mkdir(); Path(self.repo, "harness", "gate.py").write_text("x = 1\n" * 20)
        self.g("add", "-A"); self.g("commit", "-qm", "gate"); self.g("update-ref", "refs/remotes/origin/main", "HEAD")
        self.g("mv", "harness/gate.py", "gate.py"); self.g("commit", "-qm", "move it out")
        self.assertIn("it changes harness", self.merge().stderr)

    def test_the_guesses_are_their_own_paragraph(self):
        for card in ("Checks: tests pass\nGuesses: none\n\nCo-Authored-By: someone <a@b>",
                     "Guesses: none.\nChecks: tests pass"):
            self.assertEqual(self.merge(card).returncode, 0, card)
        r = self.merge("Checks: tests pass\nGuesses:\n- that prices round\n- that UTC is fine\n\nSigned-off-by: x")
        self.assertIn("guesses: - that prices round - that UTC is fine. A note", r.stderr)

    def test_only_a_plain_merge_and_a_typed_review_counts(self):
        self.assertIn('merge with merge_method "merge", not squash', self.merge(merge_method="squash").stderr)
        p = Path(self.tmp, "typed.jsonl")
        p.write_text("\n".join(json.dumps(e) for e in (
            {"type": "user", "timestamp": "2999-01-01T00:00:00Z", "message": {"role": "user", "content":
             "<command-message>code-review</command-message>\n<command-name>/code-review</command-name>"}},
            {"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [
             {"type": "tool_use", "id": "t", "name": "Skill", "input": {"skill": "ponytail-audit"}}]}},
            {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "model": "claude-haiku-4-5", "content": []}},
        )) + "\n")
        args = {"owner": "charredlatte", "repo": "cafe", "pullNumber": 7, "commit_message": self.CARD, "expectedHeadSha": self.head()}
        r = run("gates.py", {"tool_name": "mcp__github__merge_pull_request", "tool_input": args, "transcript_path": str(p), "cwd": self.tmp})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_any_github_servers_merge_is_checked(self):
        r = self.gate("mcp__plugin_github_github__merge_pull_request", {"owner": "charredlatte", "repo": "cafe", "pullNumber": 7})
        self.assertIn("not ready to merge PR #7", r.stderr)

    def test_auto_merge_and_gh(self):
        r = self.gate("mcp__github__enable_pr_auto_merge", {"owner": "charredlatte", "repo": "cafe", "pullNumber": 7})
        self.assertIn("auto-merge can't be pinned", r.stderr)
        body = f"gh pr merge 7 --merge --match-head-commit {self.head()} --body '{self.CARD}'"
        self.assertEqual(self.gate("Bash", {"command": body}, cwd=self.repo).returncode, 0)
        self.assertEqual(self.gate("Bash", {"command": "cd cafe && " + body}).returncode, 0)
        self.assertIn("auto-merge", self.gate("Bash", {"command": body + " --auto"}, cwd=self.repo).stderr)
        self.assertIn("not squash", self.gate("Bash", {"command": body + " --squash"}, cwd=self.repo).stderr)
        self.assertIn("not ready to merge PR #7", self.gate("Bash", {"command": "gh pr merge 7"}, cwd=self.repo).stderr)
        self.assertIn("name the pull request's number", self.gate("Bash", {"command": "gh pr merge feature"}, cwd=self.repo).stderr)


class Pushing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        origin, work = Path(self.tmp, "origin.git"), Path(self.tmp, "work")
        self.g = lambda *a: subprocess.run(["git", *a], cwd=work, check=True, capture_output=True)
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
        self.g("config", "user.email", "t@t"); self.g("config", "user.name", "t")
        Path(work, "a").write_text("1"); self.g("add", "a"); self.g("commit", "-qm", "one")
        self.g("push", "-q", "-u", "origin", "HEAD:main"); self.g("remote", "set-head", "origin", "main")
        self.work = work

    def push(self, command, tool="Bash"):
        args = {"command": command} if tool == "Bash" else command
        return run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args,
                                "transcript_path": transcript(self.tmp, ["ponytail-audit"]), "cwd": str(self.work)})

    def test_never_the_default_branch(self):
        for command in ("git push origin main", "git push", "git push -u origin HEAD:main", "git push origin feature:refs/heads/main",
                        "git -c push.default=current push origin main", "if git push origin main; then echo ok; fi",
                        "{ git push origin main; }", 'bash -c "git push origin main"', "env GIT_TRACE=1 git push origin main"):
            r = self.push(command)
            self.assertEqual(r.returncode, 2, command)
            self.assertIn("never push to the default branch (main)", r.stderr)
        self.g("checkout", "-qb", "feature")
        for command in ("git push -u origin feature", "git push", "git push origin HEAD 2>&1 | tail -1", "git push --tags",
                        'cd "$NOWHERE" && git push origin feature', 'git commit -m "then git push" --dry-run'):
            self.assertEqual(self.push(command).returncode, 0, command)
        self.assertEqual(self.push({"owner": "o", "repo": "r", "branch": "main"}, "mcp__github__push_files").returncode, 2)
        self.assertEqual(self.push({"owner": "o", "repo": "r", "branch": "feature"}, "mcp__github__push_files").returncode, 0)

    def test_no_force_push(self):
        self.g("checkout", "-qb", "feature")
        for command in ("git push -f origin feature", "git push --force-with-lease", "git push origin +feature",
                        "git push -uf origin feature", "git push --all origin", "git push origin 'refs/heads/*:refs/heads/*'"):
            self.assertEqual(self.push(command).returncode, 2, command)

    def test_only_a_merged_branch_is_deleted_and_only_where_sessions_merge(self):
        self.g("checkout", "-qb", "done"); self.g("push", "-q", "origin", "done")
        self.g("checkout", "-qb", "open"); Path(self.work, "b").write_text("x"); self.g("add", "b"); self.g("commit", "-qm", "b")
        self.g("push", "-q", "origin", "open")
        self.assertIn("Charlotte's to delete", self.push("git push origin --delete done").stderr)
        Path(self.work, ".claude").mkdir(); Path(self.work, ".claude", "catio-rules.json").write_text('{"merge": true}')
        self.assertEqual(self.push("git push origin --delete done").returncode, 0)
        self.assertEqual(self.push("git push origin :done").returncode, 0)
        self.assertIn("open isn't merged into main, so it stays", self.push("git push origin -d open").stderr)
        self.assertIn("never push to the default branch", self.push("git push origin --delete main").stderr)


class GraphFirst(unittest.TestCase):
    def test_quiet_without_a_map_and_when_switched_off(self):
        tmp = tempfile.mkdtemp()
        r = run("graph_first.py", {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "x"}, "cwd": tmp}, cwd=tmp)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        Path(tmp, ".claude").mkdir(); Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps({"graph_first": False}))
        Path(tmp, "graphify-out").mkdir(); Path(tmp, "graphify-out", "graph.json").write_text('{"nodes": [], "links": []}')
        r = run("graph_first.py", {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}, "cwd": tmp}, cwd=tmp)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


    def nudge(self, tmp, tool, args, model="claude-opus-5-5", agent=None):
        t = Path(tmp, "t.jsonl")
        t.write_text(json.dumps({"type": "assistant", "message": {"model": model, "content": []}}) + "\n")
        data = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args, "cwd": tmp,
                "session_id": "s-" + Path(tmp).name, "transcript_path": str(t)}
        if agent:
            data["agent_type"] = agent
        r = run("graph_first.py", data, cwd=tmp)
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout.strip() else ""

    def test_a_strong_session_is_pointed_at_the_scout_and_the_tester_once(self):
        tmp = tempfile.mkdtemp()
        self.assertIn("scout", self.nudge(tmp, "Grep", {"pattern": "route"}))
        self.assertEqual(self.nudge(tmp, "Grep", {"pattern": "again"}), "")          # once a session
        self.assertIn("tester", self.nudge(tmp, "Bash", {"command": "python3 -m unittest discover -s harness/test"}))
        self.assertEqual(self.nudge(tmp, "Bash", {"command": "npm test"}), "")

    def test_no_nudge_for_narrow_reads_small_models_or_sub_agents(self):
        for tool, args, model, agent in (("Grep", {"pattern": "x", "path": "src/a.py"}, "claude-opus-5-5", None),
                                         ("Read", {"file_path": "a.py"}, "claude-opus-5-5", None),
                                         ("Bash", {"command": "git status"}, "claude-opus-5-5", None),
                                         ("Grep", {"pattern": "x"}, "claude-sonnet-5-5", None),
                                         ("Grep", {"pattern": "x"}, "claude-opus-5-5", "scout")):
            self.assertEqual(self.nudge(tempfile.mkdtemp(), tool, args, model, agent), "", (tool, args, model, agent))


class RightSized(unittest.TestCase):
    """Spend what the task is worth: a spawn names its tier, and an errand has a ceiling."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def spawn(self, args, model="claude-opus-5-5", tmp=None, tool="Agent"):
        """A sub agent spawn, as Claude Code asks the gate about it. Returns (exit code, stderr, nudge)."""
        tmp = tmp or self.tmp
        t = Path(tmp, "t.jsonl")
        t.write_text(json.dumps({"type": "assistant", "message": {"model": model, "content": []}}) + "\n")
        r = run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args, "cwd": tmp,
                             "session_id": "s-" + Path(tmp).name,   # one session per repo folder, so "once" means once
                             "transcript_path": str(t)}, cwd=tmp)
        nudge = ""
        if r.stdout.strip():
            nudge = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        return r.returncode, r.stderr, nudge

    def word(self, tmp, tiers):
        Path(tmp, ".claude").mkdir(exist_ok=True)
        Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps(tiers))

    def test_an_errand_on_opus_is_spoken_about_once(self):
        code, _, nudge = self.spawn({"prompt": "add bananas to my shopping list", "model": "opus"})
        self.assertEqual(code, 0)                      # a reading only suggests
        self.assertIn("Sonnet", nudge)
        self.assertIn("errand", nudge)
        # and only once a session, so it never nags
        self.assertEqual(self.spawn({"prompt": "add apples to the shopping list", "model": "opus"})[2], "")

    def test_her_word_for_a_repo_refuses_it(self):
        self.word(self.tmp, {"tiers": {"errand": "haiku"}})
        code, err, _ = self.spawn({"prompt": "add bananas to my shopping list", "model": "sonnet"})
        self.assertEqual(code, 2)
        self.assertIn("haiku", err)
        self.assertEqual(self.spawn({"prompt": "add bananas to my shopping list", "model": "haiku"})[0], 0)

    def test_the_tool_is_gated_under_either_name(self):
        for tool in ("Agent", "Task"):
            self.word(self.tmp, {"tiers": {"errand": "haiku"}})
            self.assertEqual(self.spawn({"prompt": "list the files in docs", "model": "opus"}, tool=tool,
                                        tmp=tempfile.mkdtemp())[0], 0, tool)   # no word in a fresh repo: a reading
        tmp = tempfile.mkdtemp()
        self.word(tmp, {"tiers": {"errand": "haiku"}})
        for tool in ("Agent", "Task"):
            self.assertEqual(self.spawn({"prompt": "add bananas to the shopping list", "model": "opus"},
                                        tool=tool, tmp=tmp)[0], 2, tool)

    def test_real_work_is_left_alone(self):
        for prompt in ("refactor the camera so the minimap and the stage share one transform",
                       "review this diff for correctness bugs",
                       "investigate why the gateway drops reports and propose a fix"):
            self.word(self.tmp, {"tiers": {"errand": "haiku"}})
            code, _, nudge = self.spawn({"prompt": prompt, "model": "opus"}, tmp=tempfile.mkdtemp())
            self.assertEqual((code, nudge), (0, ""), prompt)

    def test_nothing_held_private_or_browser_is_sent_down(self):
        tmp = tempfile.mkdtemp()
        self.word(tmp, {"tiers": {"errand": "haiku"}, "hold": ["harness/"]})
        for prompt in ("add a line to harness/rules.json", "add the solicitor's letter to the legal folder",
                       "check the shopping list in the browser"):
            code, _, nudge = self.spawn({"prompt": prompt, "model": "opus"}, tmp=tmp)
            self.assertEqual((code, nudge), (0, ""), prompt)

    # Her word, 5 October: "Make sure this never happens again. Always run the delegation before assigning anything
    # to anyone" (a workflow's agents had all inherited the session's Opus). Nothing is assigned without a tier.
    def test_a_spawn_that_names_no_tier_is_refused_until_it_is_delegated(self):
        code, err, _ = self.spawn({"prompt": "find every caller of route()", "subagent_type": "general-purpose"})
        self.assertEqual(code, 2)
        self.assertIn("delegate first", err)
        self.assertIn("names no model", err)
        self.assertIn("haiku", err)
        self.assertEqual(self.spawn({"prompt": "find every caller of route()", "subagent_type": "general-purpose",
                                     "model": "haiku"}, tmp=tempfile.mkdtemp())[0], 0)

    def test_a_workflow_names_a_model_on_every_agent_call(self):
        unnamed = "const a = await agent(`walk ${x}`, { label: 'w', phase: 'Walk' })\nlog('agent() is fine in a string')\n" \
                  "const b = await agent('check', { model: 'sonnet' })\n// agent(in a comment)\nawait agent('z')\n"
        code, err, _ = self.spawn({"script": unnamed}, tool="Workflow")
        self.assertEqual(code, 2)
        self.assertIn("lines 1, 5", err)
        named = "await agent(`walk ${x}`, { model: 'sonnet', label: 'w' })\nawait agent('z', { model })\n"
        self.assertEqual(self.spawn({"script": named}, tool="Workflow", tmp=tempfile.mkdtemp())[0], 0)
        # a script on disk is read too
        tmp = tempfile.mkdtemp()
        Path(tmp, "wf.js").write_text(unnamed)
        self.assertEqual(self.spawn({"scriptPath": "wf.js"}, tool="Workflow", tmp=tmp)[0], 2)

    def test_a_new_session_names_its_model(self):
        tool = "mcp__claude-code-remote__create_session"
        code, err, _ = self.spawn({"prompt": "tidy the README"}, tool=tool)
        self.assertEqual(code, 2)
        self.assertIn("this new session names no model", err)
        self.assertEqual(self.spawn({"prompt": "tidy the README", "model": "claude-sonnet-5-5"}, tool=tool,
                                    tmp=tempfile.mkdtemp())[0], 0)

    def test_held_work_that_names_no_tier_is_told_to_stay_strong(self):
        tmp = tempfile.mkdtemp()
        self.word(tmp, {"hold": ["harness/"]})
        code, err, _ = self.spawn({"prompt": "add a line to harness/rules.json"}, tmp=tmp)
        self.assertEqual(code, 2)
        self.assertIn("stays on a strong tier", err)

    def test_only_claude_code_remote_s_new_session_is_a_new_cat(self):
        for tool in ("mcp__tmux__create_session", "mcp__jupyter__create_session"):
            self.assertEqual(self.spawn({"session_name": "build"}, tool=tool, tmp=tempfile.mkdtemp())[0], 0, tool)

    def test_an_agent_is_found_by_its_own_name_wherever_claude_code_keeps_it(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude", "agents").mkdir(parents=True)
        Path(tmp, ".claude", "agents", "my-reviewer.md").write_text("---\nname: reviewer\nmodel: sonnet\n---\nReview.\n")
        self.assertEqual(self.spawn({"prompt": "review", "subagent_type": "reviewer"}, tmp=tmp)[0], 0)
        home = tempfile.mkdtemp()
        Path(home, ".claude", "agents").mkdir(parents=True)
        Path(home, ".claude", "agents", "x.md").write_text("---\nname: mine\nmodel: haiku\n---\n")
        sys.path.insert(0, str(HOOKS))
        import right_sized
        from unittest import mock
        with mock.patch.object(right_sized.Path, "home", return_value=Path(home)):   # HOME on POSIX, USERPROFILE on Windows
            self.assertEqual(right_sized.pinned("mine", tempfile.mkdtemp()), "haiku")

    def test_a_repo_ladder_is_read_whatever_its_case_and_a_missing_tier_says_so(self):
        tmp = tempfile.mkdtemp()
        self.word(tmp, {"tiers": {"ladder": ["Haiku", "Sonnet"]}})
        self.assertEqual(self.spawn({"prompt": "list docs", "model": "haiku"}, tmp=tmp)[0], 0)
        code, err, _ = self.spawn({"prompt": "design the plan", "model": "opus"}, tmp=tmp)
        self.assertEqual(code, 2)
        self.assertIn("isn't one of the tiers here", err)

    def test_a_new_session_off_the_ladder_is_told_so(self):
        code, err, _ = self.spawn({"prompt": "x", "model": "default"}, tool="mcp__claude-code-remote__create_session")
        self.assertEqual(code, 2)
        self.assertIn("isn't one of the tiers here", err)

    def test_a_fork_is_the_parent_and_needs_no_tier(self):
        self.assertEqual(self.spawn({"prompt": "carry on with the plan", "subagent_type": "fork"})[0], 0)

    def test_an_agent_pinned_to_a_tier_is_already_right_sized(self):
        for agent in ("scout", "tester"):
            code, _, nudge = self.spawn({"prompt": "find every caller of route()", "subagent_type": agent},
                                        tmp=tempfile.mkdtemp())
            self.assertEqual((code, nudge), (0, ""), agent)

    def test_a_small_session_delegates_too_and_a_repo_can_switch_it_off(self):
        # "Always": a Haiku session's unnamed spawn would inherit Haiku, whatever the work needs
        self.assertEqual(self.spawn({"prompt": "find route()"}, model="claude-haiku-4-5")[0], 2)
        tmp = tempfile.mkdtemp()
        self.word(tmp, {"right_sized": False, "tiers": {"errand": "haiku"}})
        self.assertEqual(self.spawn({"prompt": "add bananas to my shopping list", "model": "opus"}, tmp=tmp)[0], 0)


class WorkflowReader(unittest.TestCase):
    """How right_sized reads a Workflow script: every agent() names a tier on the call, whatever the script's text
    looks like around it (the review of 5 October found each of these)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HOOKS))
        import right_sized
        cls.r = right_sized
        cls.ladder = ["haiku", "sonnet", "opus", "fable"]

    def lines(self, src, cwd=None):
        return self.r.unnamed_agents(src, cwd or tempfile.mkdtemp(), self.ladder)

    def test_regex_literals_are_not_strings_comments_or_templates(self):
        self.assertEqual(self.lines("await agent(text.replace(/\\)/g, ''), { model: 'haiku' })"), [])
        self.assertEqual(self.lines("const re = /`/\nconst p = `then call agent(foo) here`\n"), [])
        self.assertEqual(self.lines("const q = s.replace(/'/g, ''); await agent('a', {label:'x'})"), [1])
        self.assertEqual(self.lines("const g = /[/*]/\nawait agent('a')\nawait agent('b')\n// */"), [2, 3])
        self.assertEqual(self.lines("s.replace(/https?:\\/\\//, ''); await agent(u)"), [1])
        self.assertEqual(self.lines("const tick = /`/g\nawait agent('a')\nconst t = `b`"), [2])
        self.assertEqual(self.lines("const half = total / 2; await agent('a', { model: 'sonnet' }) / 1"), [])

    def test_an_agent_inside_a_template_is_read(self):
        self.assertEqual(self.lines("const r = `Summary: ${await agent('summarise the diff')}`"), [1])
        self.assertEqual(self.lines("const r = `S: ${await agent('x', { model: 'haiku' })}`"), [])

    def test_only_this_call_s_own_model_counts_and_it_must_be_a_tier(self):
        self.assertEqual(self.lines("await agent(await agent('x', {model: 'haiku'}), {label: 'outer'})"), [1])
        for src in ("await agent(prompt, { label: model })", "await agent(pick(model), { label: 'x' })",
                    "await agent('a', { model: undefined })", "await agent('a', { model: '' })",
                    "await agent('a', { model: 'inherit' })", "await agent('x', {label: cfg.model})"):
            self.assertEqual(self.lines(src), [1], src)
        for src in ("await agent('a', { model: w.model })", "await agent('a', { model })",
                    "await agent('a', { label: 'x', model: 'claude-sonnet-5-5' })"):
            self.assertEqual(self.lines(src), [], src)

    def test_an_agent_handed_on_uncalled_is_refused(self):
        for src in ("await Promise.all(items.map(agent))", "const run = agent\nawait run('a')"):
            self.assertTrue(self.lines(src), src)
        self.assertEqual(self.lines("await agent?.('a', {label:'x'})"), [1])
        self.assertEqual(self.lines("const o = { agent: 1 }; await agent('a', { model: 'haiku' })"), [])

    def test_a_pinned_agent_type_names_its_tier(self):
        self.assertEqual(self.lines("await agent('find callers', {agentType: 'scout'})"), [])
        self.assertEqual(self.lines("await agent('find callers', {agentType: 'kittychat-house-rules:tester'})"), [])
        self.assertEqual(self.lines("await agent('find callers', {agentType: 'general-purpose'})"), [1])

    # Round 2 of the review, 5 October
    def test_a_child_workflow_with_args_is_read(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude", "workflows").mkdir(parents=True)
        Path(tmp, ".claude", "workflows", "sweep.js").write_text("await agent('a')\n")
        for src in ("await workflow('sweep', {x: 1})", "await workflow('sweep',args)", "await workflow({name: 'sweep'}, {x: 1})"):
            self.assertEqual(self.lines(src, tmp), [1], src)

    def test_an_expression_that_builds_a_model_is_the_author_s_choice(self):
        for src in ("await agent('x', {model: `claude-${tier}`})", "await agent('x', {model: 'claude-' + tier})",
                    "await agent('x', {model: nullableTier})", "await agent('x', {model: undefinedOr(t, 'haiku')})"):
            self.assertEqual(self.lines(src), [], src)
        for src in ("await agent('x', {model: ''})", "await agent('x', {model: `inherit`})", "await agent('x', {model: null})",
                    "await agent('x', {model: void 0})"):
            self.assertEqual(self.lines(src), [1], src)

    def test_quoted_keys_are_keys(self):
        for src in ("await agent('x', {'model': 'haiku'})", 'await agent("x", {"model": "haiku"})',
                    "await agent('x', {'agentType': 'scout'})"):
            self.assertEqual(self.lines(src), [], src)
        self.assertEqual(self.lines("await agent('model', {label: 'model'})"), [1])

    def test_a_name_of_the_script_s_own_called_agent_is_not_the_real_one(self):
        named = ", {model:'haiku'})"
        for src in ("if (typeof agent !== 'function') throw 1\nawait agent('a'" + named,
                    "for (const agent of reviewers) log(agent.name)\nawait agent('a'" + named,
                    "async function run(agent) { return 1 }\nawait agent('a'" + named,
                    "const f = (agent, x) => x\nawait agent('a'" + named,
                    "const { agent } = ctx\nawait agent('a'" + named,
                    "const rs = xs.map(agent => agent.summary)\nawait agent('a'" + named,
                    "const o = { agent() { return 1 } }\nawait agent('a'" + named):
            self.assertEqual(self.lines(src), [], src)
        self.assertTrue(self.lines("await Promise.all(xs.map(agent))"))
        self.assertTrue(self.lines("const go = agent.bind(null)"))

    def test_division_after_a_postfix_or_a_property_is_division(self):
        self.assertEqual(self.lines("const h = i++ / 2; await agent('x')"), [1])
        self.assertEqual(self.lines("const r = obj.in / 2; const s = 'x'; await agent('x')"), [1])
        self.assertEqual(self.lines("const ok = /agent('x')/.test(s)"), [])

    def test_a_file_that_isn_t_utf8_never_crashes_the_gate(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude", "agents").mkdir(parents=True)
        Path(tmp, ".claude", "agents", "old.md").write_bytes(b"---\nname: caf\xe9\nmodel: haiku\n---\n")
        Path(tmp, "wf.js").write_bytes(b"await agent('\xe9')\n")
        self.assertIsNone(self.r.pinned("old", tmp))
        self.assertEqual(self.r.script_of({"scriptPath": "wf.js"}, tmp), "")

    def test_the_first_definition_by_a_name_decides(self):
        tmp, home = tempfile.mkdtemp(), tempfile.mkdtemp()
        Path(tmp, ".claude", "agents").mkdir(parents=True)
        Path(tmp, ".claude", "agents", "reviewer.md").write_text("---\nname: reviewer\n---\nReview.\n")
        Path(home, ".claude", "agents").mkdir(parents=True)
        Path(home, ".claude", "agents", "reviewer.md").write_text("---\nname: reviewer\nmodel: haiku\n---\n")
        from unittest import mock
        with mock.patch.object(self.r.Path, "home", return_value=Path(home)):
            self.assertIsNone(self.r.pinned("reviewer", tmp))   # the project's, which inherits, is the one that runs

    def test_a_child_workflow_is_read_too(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude", "workflows").mkdir(parents=True)
        Path(tmp, ".claude", "workflows", "sweep.js").write_text("await agent('a')\n")
        Path(tmp, "named.js").write_text("await agent('a', { model: 'haiku' })\n")
        self.assertEqual(self.lines("log('x')\nawait workflow('sweep')", tmp), [2])
        self.assertEqual(self.lines("await workflow({scriptPath: 'named.js'})", tmp), [])
        self.assertEqual(self.lines("await workflow('a-built-in')", tmp), [])   # can't be read: nothing to check


class GraphDoc(unittest.TestCase):
    def test_digests_a_graph_for_the_catio(self):
        out = Path(tempfile.mkdtemp(), "graphify-out"); out.mkdir()
        nodes = [{"id": f"n{i}", "label": f"thing{i}()", "community": i % 2, "community_name": ["Core", "Edges"][i % 2], "source_file": "a.py"} for i in range(6)]
        links = [{"source": "n0", "target": f"n{i}"} for i in range(1, 6)] + [{"source": "n1", "target": "n2"}]
        (out / "graph.json").write_text(json.dumps({"nodes": nodes, "links": links, "built_at_commit": "abc123"}))
        (out / "GRAPH_REPORT.md").write_text("## God Nodes (x)\n1. `thing0()` - 5 edges\n\n## Surprising Connections\n"
                                             "- `thing1()` --calls--> `thing2()`  [INFERRED]\n  a.py → b.py\n\n## Suggested Questions\n- **Why thing0?**\n  _because_\n",
                                             encoding="utf-8")
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

    def test_says_when_a_repo_merges(self):
        tmp = Path(tempfile.mkdtemp(), "cafe")
        subprocess.run(["git", "init", "-q", str(tmp)], check=True)
        self.assertIn("  cafe's pull requests are hers to merge.", run("session_start.py", {"cwd": str(tmp)}).stdout)
        Path(tmp, ".claude").mkdir()
        Path(tmp, ".claude", "catio-rules.json").write_text('{"merge": true, "hold": ["harness/"]}')
        out = run("session_start.py", {"cwd": str(tmp)}).stdout
        self.assertIn("  cafe merges its own pull requests; changes to harness/ always wait for her.", out)
        self.assertIn("**Semi-automatic merging** (enforced)", out)

    def test_reminds_a_fable_session_of_opus(self):
        nudge = "suggest /model opus"
        self.assertIn(nudge, run("session_start.py", {"model": "claude-fable-5-1", "cwd": tempfile.mkdtemp()}).stdout)
        self.assertNotIn(nudge, run("session_start.py", {"model": "claude-opus-5-5", "cwd": tempfile.mkdtemp()}).stdout)
        self.assertNotIn(nudge, run("session_start.py", {"cwd": tempfile.mkdtemp()}).stdout)

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
