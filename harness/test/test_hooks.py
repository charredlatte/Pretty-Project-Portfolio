"""The house-rule hooks, run as Claude Code runs them: JSON on stdin, exit code and output back.

    python3 -m unittest discover harness/test
"""
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"

# Every "hold" a hand-written catio-rules.json has come in that the harness cannot match against git's own
# paths. Each must hold the pull request AND keep the session brief from claiming a hold the gate won't keep,
# so the gate's check and the brief's check read the same list: adding a shape here covers both.
# A bare null, a padded entry and a "/"- or "./"-prefixed one each merged a harness/ change before 20 Oct.
ODD_HOLDS = ("harness/", 5, {"harness/": True}, None, ["harness/", None], ["harness/*"],
             [""], ["   "], ["/harness"], ["./harness"], ["../harness"], ["a{b,c}"], ["/"], ["harness\\x"],
             ["."], [".."], ["harness/."], ["a/./b"], ["~/harness"], ["$HOME/harness"])
# And these she wrote properly, however she spaced them: each must reach the gate and hold.
GOOD_HOLDS = (["harness/"], ["  harness/  "], ["harness"], ["docs/", "harness/"])
BASH = shutil.which("bash") or "bash"   # hook commands run in bash (Git Bash on Windows)


# what the hooks read from the environment, cleared for every run and set only where it is the subject
ENV_KEYS = ("CLAUDE_CODE_REMOTE", "XDG_CACHE_HOME", "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
            "CATIO_URL", "CATIO_TOKEN")   # a developer's own café must not leak into a run


# a cache of its own, so a marker left by a real session on this machine can't decide a test
CACHE = tempfile.mkdtemp()


def run(script, data, cwd=None, cloud=False, env=None):
    env = dict({k: v for k, v in os.environ.items() if k not in ENV_KEYS}, XDG_CACHE_HOME=CACHE, **(env or {}))
    if cloud:
        env["CLAUDE_CODE_REMOTE"] = "true"
    return subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(data), capture_output=True, text=True,
                          cwd=cwd, env=env)


def without_comments(text):
    """JSONC with its comments blanked, skipping string literals: a // carrying a quote, or a /* */ block, is
    legal in wrangler.jsonc, and a regex that mangled one made the sweep call a file wrangler accepts broken."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':                                     # a string: copy it whole, escapes included
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1]); i = j + 1
        elif text[i:i + 2] == "//":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text[i:i + 2] == "/*":
            j = text.find("*/", i + 2)
            out.append(" ")                              # keep the tokens either side apart
            i = n if j < 0 else j + 2
        else:
            out.append(c); i += 1
    return "".join(out)


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

    def test_a_catio_rules_file_that_is_not_an_object_never_stops_a_gate(self):
        """Every gate asks .claude/catio-rules.json for a key. One holding a list or a number would take down
        whichever asked first, and a hook that crashes exits 1, which Claude Code reads as a warning."""
        for written in ("[]", '"merge"', "5", "null", "true", "{ not json"):
            tmp = tempfile.mkdtemp()
            Path(tmp, ".claude").mkdir()
            Path(tmp, ".claude", "catio-rules.json").write_text(written)
            r = self.gate("Write", {"file_path": str(Path(tmp, "a.py"))}, cwd=tmp)
            self.assertEqual(r.returncode, 2, (written, r.stdout, r.stderr))
            self.assertIn("ponytail-audit", r.stderr, written)

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

    def repo_at(self, name, url, public=None):
        """A checkout with a GitHub origin, and its own .claude/catio-rules.json when it has an opinion."""
        at = Path(self.tmp, name)
        subprocess.run(["git", "init", "-q", str(at)], check=True)
        subprocess.run(["git", "-C", str(at), "remote", "add", "origin", url], check=True)
        if public is not None:
            (at / ".claude").mkdir(exist_ok=True)
            (at / ".claude" / "catio-rules.json").write_text(json.dumps({"public": public}))
        return at

    def test_no_claude_attribution_in_commits_on_public_repos(self):
        audited = ["anthropic-skills:ponytail-audit"]
        # a private repo is the one case that may keep the lines, and it is the repo itself that says so
        repos = {"cafe": self.repo_at("cafe", "https://github.com/charredlatte/Pretty-Project-Portfolio.git"),
                 "priv": self.repo_at("private-notes", "https://github.com/charredlatte/private-notes", public=False)}
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
        self.assertEqual(self.gate("Bash", {"command": signed}, audited, cwd=str(repos["priv"])).returncode, 0)
        self.assertEqual(self.gate("Bash", {"command": 'git commit -m "Fix it"'}, audited, cwd=str(repos["cafe"])).returncode, 0)
        # the message in a file, which the command doesn't show
        Path(self.tmp, "msg.txt").write_text("Fix it\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
        for flags in ("-F ../msg.txt", "--file=../msg.txt", "--amend -F ../msg.txt"):
            self.assertEqual(self.gate("Bash", {"command": "git commit " + flags}, audited, cwd=str(repos["cafe"])).returncode, 2, flags)
            self.assertEqual(self.gate("Bash", {"command": "git commit " + flags}, audited, cwd=str(repos["priv"])).returncode, 0, flags)
        self.assertEqual(self.gate("Bash", {"command": "cd cafe && git commit -F ../msg.txt"}, audited).returncode, 2)
        # a fork, or any repo nobody has configured, counts as public without being named on a list anywhere
        fork = self.repo_at("fork", "https://github.com/someone-else/Pretty-Project-Portfolio")
        self.assertEqual(self.gate("Bash", {"command": signed}, audited, cwd=str(fork)).returncode, 2)

    def test_no_claude_attribution_in_github_posts_on_public_repos(self):
        cafe = {"owner": "charredlatte", "repo": "Pretty-Project-Portfolio"}
        priv = {"owner": "charredlatte", "repo": "private-notes"}
        at = self.repo_at("private-notes", "https://github.com/charredlatte/private-notes", public=False)
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
            self.assertNotIn("no Claude attribution", self.gate(tool, dict(priv, **args), cwd=str(at)).stderr, tool)
        # prose about the rule isn't a credit line
        about = "The gate refuses `Co-Authored-By: Claude` lines, and links like https://claude.ai/code/session_1 in a sentence."
        self.assertEqual(self.gate("mcp__github__create_pull_request", dict(cafe, body=about)).returncode, 0)

    def test_after_a_signed_post_on_a_public_repo_the_footer_comes_off(self):
        def after(tool, args, cwd=None):
            return run("gates.py", {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": args,
                                    "tool_response": {}, "cwd": cwd or self.tmp})
        cafe = {"owner": "charredlatte", "repo": "Pretty-Project-Portfolio", "body": "Fix it"}
        r = after("mcp__github__create_pull_request", cafe)
        self.assertEqual(r.returncode, 2)
        self.assertIn("update_pull_request", r.stderr)
        self.assertEqual(after("mcp__github__add_issue_comment", cafe).returncode, 2)
        self.assertEqual(after("mcp__github__issue_write", dict(cafe, method="create")).returncode, 2)
        self.assertEqual(after("mcp__github__issue_write", dict(cafe, method="update")).returncode, 0)
        self.assertEqual(after("mcp__github__update_pull_request", cafe).returncode, 0)
        at = self.repo_at("private-notes", "https://github.com/charredlatte/private-notes", public=False)
        self.assertEqual(after("mcp__github__create_pull_request", dict(cafe, repo="private-notes"), cwd=str(at)).returncode, 0)

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

    def note(self, repo="cafe"):
        p = self.box / f"held-{repo}-7.md"
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

    def test_a_hold_she_wrote_in_a_shape_it_cannot_read_holds_the_pull_request(self):
        """The hold list is the merging rule's sharpest promise - a change under harness/ always waits for her -
        so a shape it cannot read must hold the pull request and say so, never be dropped. Dropping it is how a
        change under harness/ merges itself: before this, "hold": "harness/" was concatenated to a list and
        raised, which at least refused; reading only the strings out of it released the pull request instead.
        A glob counts as unreadable too, because nothing here expands one, so it would protect nothing."""
        for i, hold in enumerate(ODD_HOLDS):
            name = "odd%d" % i
            repo = self.checkout(name, {"merge": True, "hold": hold})
            r = self.merge(repo=name, head=self.head(repo))
            self.assertEqual(r.returncode, 2, (hold, r.stderr))
            self.assertIn("hold list in its .claude/catio-rules.json is in a shape I can't read", r.stderr, hold)
            self.assertIn("shape I can't read", self.note(name) or "", hold)

    def test_a_broken_hold_in_the_house_rules_names_the_house_rules_not_her_repo(self):
        """Both lists can be unreadable, and the note has to send her to the file that is actually wrong."""
        plugin = Path(tempfile.mkdtemp())
        shutil.copytree(HOOKS, plugin / "hooks")
        rules = json.loads((HOOKS.parent / "rules.json").read_text(encoding="utf-8"))
        rules["merging"]["hold"] = "/.claude"                       # hers is fine; the house's is not
        (plugin / "rules.json").write_text(json.dumps(rules))
        repo = self.checkout("housebad", {"merge": True, "hold": ["docs/"]})
        args = {"owner": "charredlatte", "repo": "housebad", "pullNumber": 7, "commit_message": self.CARD,
                "expectedHeadSha": self.head(repo), "merge_method": None}
        r = subprocess.run([sys.executable, str(plugin / "hooks" / "gates.py")],
                           input=json.dumps({"hook_event_name": "PreToolUse", "cwd": str(self.tmp),
                                             "tool_name": "mcp__github__merge_pull_request", "tool_input": args,
                                             "transcript_path": self.transcript()}),
                           capture_output=True, text=True, cwd=self.tmp,
                           env=dict({k: v for k, v in os.environ.items() if k not in ENV_KEYS}, XDG_CACHE_HOME=CACHE))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("the house rules' own merging.hold", r.stderr)
        self.assertNotIn("its .claude/catio-rules.json", r.stderr)   # hers is readable: don't send her there

    def test_a_hold_she_wrote_properly_reaches_the_gate_however_she_spaced_it(self):
        """[" harness/ "] merged a harness/ change before 20 Oct. holds() trims it, so it must now hold -
        and the gate, not only the brief, is where that matters."""
        for i, hold in enumerate(GOOD_HOLDS):
            name = "good%d" % i
            repo = self.checkout(name, {"merge": True, "hold": [h.replace("harness", "a") for h in hold]})
            r = self.merge(repo=name, head=self.head(repo))   # "a" is what the feature commit changes
            self.assertEqual(r.returncode, 2, (hold, r.stderr))
            self.assertIn("which always waits for her", r.stderr, hold)
            self.assertNotIn("shape I can't read", r.stderr, hold)

    def test_a_held_path_with_an_accent_in_it_still_holds(self):
        """git C-quotes a non-ASCII path in --name-only ("catio/art/caf\\303\\251/x.png"), so a hold she spelt
        properly never matched it and the change merged unheld. The names are read with -z and quotepath off."""
        name = "accent"
        repo = Path(self.tmp, name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", f"https://github.com/charredlatte/{name}.git")
        Path(repo, ".claude").mkdir(); Path(repo, ".claude", "catio-rules.json").write_text(
            json.dumps({"merge": True, "hold": ["caf\u00e9/"]}))
        Path(repo, "a").write_text("1")
        g("add", "-A"); g("commit", "-qm", "one"); g("update-ref", "refs/remotes/origin/main", "HEAD")
        g("checkout", "-qb", "feature")
        Path(repo, "caf\u00e9").mkdir(); Path(repo, "caf\u00e9", "x.png").write_text("2")
        g("add", "-A"); g("commit", "-qm", "two")
        # Prove git sees the path before asking the gate about it, so a failure here says which half broke:
        # this one is git or the filesystem (encoding, normalisation), the one below is the gate's comparison.
        listed = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only", "-z",
                                 "refs/remotes/origin/main", "HEAD"], cwd=repo, capture_output=True,
                                encoding="utf-8", errors="surrogateescape").stdout
        self.assertIn("caf\u00e9", listed, "git did not report the accented path as written: %r" % listed)
        r = self.merge(repo=name, head=self.head(repo))
        self.assertEqual(r.returncode, 2, "the gate did not hold it; git reported %r" % listed)
        self.assertIn("which always waits for her", r.stderr)

    def test_a_hold_she_wrote_properly_still_holds_and_still_lets_the_rest_through(self):
        held = self.checkout("held", {"merge": True, "hold": ["a"]})   # "a" is what the feature commit changes
        r = self.merge(repo="held", head=self.head(held))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("it changes a, which always waits for her", r.stderr)
        for name, hold in (("free", ["docs/"]), ("none", [])):         # not touched, and nothing held at all
            repo = self.checkout(name, {"merge": True, "hold": hold})
            r = self.merge(repo=name, head=self.head(repo))
            self.assertEqual(r.returncode, 0, (hold, r.stderr))
            self.assertIsNone(self.note(name), hold)
        # A dot-folder holds like any other: a workflow change in this repo's own shape waits for her
        wf = self.checkout("wf", {"merge": True, "hold": ["harness/", ".github/"]})
        Path(wf, ".github", "workflows").mkdir(parents=True); Path(wf, ".github", "workflows", "x.yml").write_text("on: push")
        subprocess.run(["git", "add", "-A"], cwd=wf, check=True); subprocess.run(["git", "commit", "-qm", "workflow"], cwd=wf, check=True)
        r = self.merge(repo="wf", head=self.head(wf))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("it changes .github, which always waits for her", r.stderr)
        self.assertIsNotNone(self.note("wf"))   # held for her, with its note, not sent back to fix
        # and in every repo that merges its own, whether or not its own list names .github/: the house holds it
        bare = self.checkout("bare", {"merge": True})
        Path(bare, ".github", "workflows").mkdir(parents=True); Path(bare, ".github", "workflows", "x.yml").write_text("on: push")
        subprocess.run(["git", "add", "-A"], cwd=bare, check=True); subprocess.run(["git", "commit", "-qm", "workflow"], cwd=bare, check=True)
        r = self.merge(repo="bare", head=self.head(bare))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("it changes .github, which always waits for her", r.stderr)
        # And saying nothing is not saying it wrong: with no "hold" key at all the gate must not accuse her of
        # a list she never wrote. Reading it without the UNSET sentinel holds every merge in such a repo.
        quiet = self.checkout("quiet", {"merge": True})
        r = self.merge(repo="quiet", head=self.head(quiet))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("shape I can't read", r.stderr)
        self.assertIsNone(self.note("quiet"))

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

    def test_a_merge_through_gh_api_is_checked_like_any_other(self):
        """`gh api -X PUT repos/o/r/pulls/7/merge` merged with no check at all before 22 October."""
        api = lambda cmd, cwd=None: self.gate("Bash", {"command": cmd}, cwd=cwd or self.repo)
        sha, card = self.head(), shlex.quote("commit_message=" + self.CARD)
        ok = f"gh api -X PUT repos/charredlatte/cafe/pulls/7/merge -f sha={sha} -f {card}"
        r = api(ok)
        self.assertEqual(r.returncode, 0, r.stderr)
        for same in (f"gh api --method=PUT /repos/{{owner}}/{{repo}}/pulls/7/merge -F sha={sha} -f {card}",
                     f"cd cafe && gh api -XPUT https://api.github.com/repos/:owner/:repo/pulls/7/merge -fsha={sha} -f {card}"):
            r = api(same, cwd=self.tmp if same.startswith("cd") else None)
            self.assertEqual(r.returncode, 0, (same, r.stderr))
        Path(self.repo, "msg").write_text(self.CARD)
        self.assertEqual(api(f"gh api -X PUT repos/charredlatte/cafe/pulls/7/merge -f sha={sha} -F commit_message=@msg").returncode, 0)
        Path(self.repo, "body.json").write_text(json.dumps({"sha": sha, "commit_message": self.CARD}))
        self.assertEqual(api("gh api -X PUT repos/charredlatte/cafe/pulls/7/merge --input body.json").returncode, 0)
        # what the session can fix is sent back, guesswork held, as with merge_pull_request
        self.assertIn("not ready to merge PR #7", api("gh api -X PUT repos/charredlatte/cafe/pulls/7/merge").stderr)
        self.assertIn("pass expectedHeadSha", api(f"gh api -X PUT repos/charredlatte/cafe/pulls/7/merge -f {card}").stderr)
        self.assertIn("not squash", api(ok + " -f merge_method=squash").stderr)
        self.assertIn("not ready to merge PR #7", api("echo hi; gh api -X PUT repos/charredlatte/cafe/pulls/7/merge").stderr)
        self.assertIn("not ready to merge PR #7", api("gh api -f merge_method=merge repos/charredlatte/cafe/pulls/7/merge").stderr)
        Path(self.repo, "harness").mkdir(); Path(self.repo, "harness", "x").write_text("1")
        self.g("add", "-A"); self.g("commit", "-qm", "rules")
        r = api(f"gh api -X PUT repos/charredlatte/cafe/pulls/7/merge -f sha={self.head()} -f {card}")
        self.assertIn("it changes harness, which always waits for her", r.stderr)
        self.assertIsNotNone(self.note())
        # a repo that doesn't merge its own: hers, however it is asked for
        self.checkout("hers")
        self.assertIn("doesn't merge its own pull requests", api("gh api -X PUT repos/charredlatte/hers/pulls/7/merge").stderr)
        # what can't be checked is refused
        self.assertIn("name the pull request's number", api("gh api -X PUT repos/charredlatte/cafe/pulls/$PR/merge").stderr)
        self.assertIn("can't read this merge's fields", api("gh api -X PUT repos/charredlatte/cafe/pulls/7/merge --input -").stderr)
        self.assertIn("can't read this merge's fields", api("gh api -X PUT repos/charredlatte/cafe/pulls/7/merge -F commit_message=@gone").stderr)
        self.assertIn("with no pull request", api("gh api repos/charredlatte/cafe/merges -f base=main -f head=feature").stderr)
        for gql in ("gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"PR_x\"}) { clientMutationId } }'",
                    "gh api graphql -f query='mutation { enablePullRequestAutoMerge(input: {pullRequestId: \"PR_x\"}) { clientMutationId } }'"):
            self.assertIn("GraphQL merge", api(gql).stderr, gql)
        Path(self.repo, "q.graphql").write_text("mutation { mergeBranch(input: {repositoryId: \"R\", base: \"main\", head: \"x\"}) { clientMutationId } }")
        self.assertIn("GraphQL merge", api("gh api graphql -F query=@q.graphql").stderr)
        # reading goes through: asking whether it merged, and every other call
        for fine in ("gh api repos/charredlatte/cafe/pulls/7/merge", "gh api -X GET repos/charredlatte/cafe/pulls/7/merge",
                     "gh api graphql -f query='{ viewer { login } }'", "gh api -X POST repos/charredlatte/cafe/issues/7/comments -f body=merge"):
            r = api(fine)
            self.assertEqual(r.returncode, 0, (fine, r.stderr))

    def test_a_merge_through_curl_is_checked_like_any_other(self):
        """curl to GitHub's API merged with no check at all, after gh api was gated on 22 October."""
        api = lambda cmd: self.gate("Bash", {"command": cmd}, cwd=self.repo)
        url = "https://api.github.com/repos/charredlatte/cafe/pulls/7/merge"
        auth = '-H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json"'
        body = lambda **f: shlex.quote(json.dumps(f))
        ok = body(sha=self.head(), commit_message=self.CARD)
        for same in (f"curl -sS -X PUT {auth} {url} -d {ok}", f"curl -sSXPUT {url} --data-raw {ok}",
                     f"curl --request=PUT --url {url} --json {ok}", f"cd cafe && curl -X PUT '{url}?x=1' -d {ok}"):
            r = self.gate("Bash", {"command": same}, cwd=self.tmp if same.startswith("cd") else self.repo)
            self.assertEqual(r.returncode, 0, (same, r.stderr))
        Path(self.repo, "body.json").write_text(json.dumps({"sha": self.head(), "commit_message": self.CARD}))
        self.assertEqual(api(f"curl -X PUT {url} -d @body.json").returncode, 0)
        self.assertEqual(api(f"curl -T body.json {url}").returncode, 0)        # -T is a PUT of the file
        # what the session can fix is sent back, guesswork held, as with merge_pull_request
        self.assertIn("not ready to merge PR #7", api(f"curl -X PUT {url}").stderr)
        self.assertIn("pass expectedHeadSha", api(f"curl -X PUT {url} -d {body(commit_message=self.CARD)}").stderr)
        self.assertIn("not squash", api(f"curl -X PUT {url} -d {body(sha=self.head(), commit_message=self.CARD, merge_method='squash')}").stderr)
        self.assertIn("not ready to merge PR #7", api(f"curl {url} -d {body(merge_method='merge')}").stderr)   # data: a POST
        Path(self.repo, "harness").mkdir(); Path(self.repo, "harness", "x").write_text("1")
        self.g("add", "-A"); self.g("commit", "-qm", "rules")
        r = api(f"curl -X PUT {url} -d {body(sha=self.head(), commit_message=self.CARD)}")
        self.assertIn("it changes harness, which always waits for her", r.stderr)
        self.assertIsNotNone(self.note())
        # a repo that doesn't merge its own: hers, however it is asked for
        self.checkout("hers")
        self.assertIn("doesn't merge its own pull requests", api(f"curl -X PUT {url.replace('cafe', 'hers')}").stderr)
        # what can't be checked is refused
        self.assertIn("name the pull request's number", api(f"curl -X PUT {url.replace('/7/', '/$PR/')}").stderr)
        for unread in (f"curl -X PUT {url} -d @-", f"curl -X PUT {url} -d @gone.json", f"curl -X PUT {url} -d sha=abc",
                       f"curl -X PUT {url} -d {ok} -d {ok}"):
            self.assertIn("can't read this merge's fields", api(unread).stderr, unread)
        self.assertIn("with no pull request",
                      api(f"curl -X POST https://api.github.com/repos/charredlatte/cafe/merges -d {body(base='main', head='feature')}").stderr)
        q = body(query='mutation { mergePullRequest(input: {pullRequestId: "PR_x"}) { clientMutationId } }')
        self.assertIn("GraphQL merge", api(f"curl -X POST https://api.github.com/graphql {auth} -d {q}").stderr)
        Path(self.repo, "q.json").write_text(json.dumps({"query": "mutation { enablePullRequestAutoMerge(input: {pullRequestId: \"PR_x\"}) { clientMutationId } }"}))
        self.assertIn("GraphQL merge", api("curl https://api.github.com/graphql -d @q.json").stderr)
        # reading goes through: asking whether it merged, and every other call
        for fine in (f"curl -sS {auth} {url}", f"curl -I {url}", f"curl -G {url} -d per_page=1",
                     f"curl -X POST https://api.github.com/graphql -d {body(query='{ viewer { login } }')}",
                     f"curl -X POST https://api.github.com/repos/charredlatte/cafe/issues/7/comments -d {body(body='merge')}",
                     "curl -fsSL https://example.com/install.sh -o install.sh"):
            r = api(fine)
            self.assertEqual(r.returncode, 0, (fine, r.stderr))


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

    def asks(self, command):
        r = self.push(command)
        self.assertEqual(r.returncode, 0, command)
        return json.loads(r.stdout)["hookSpecificOutput"]

    def test_a_stale_tracking_ref_never_passes_as_merged(self):
        # a clone that fetches only main: a bare `fetch origin done` would leave origin/done where it was
        self.g("checkout", "-qb", "done"); self.g("push", "-q", "origin", "done")
        self.g("config", "remote.origin.fetch", "+refs/heads/main:refs/remotes/origin/main")
        self.g("commit", "-q", "--allow-empty", "-m", "more"); self.g("push", "-q", "origin", "done:refs/heads/done")
        self.g("update-ref", "refs/remotes/origin/done", "main")  # the stale copy, merged
        self.assertIn("done isn't merged into main", self.push("git push origin --delete done").stderr)

    def test_only_a_merged_branch_is_deleted_and_only_with_her_ok_where_she_merges(self):
        self.g("checkout", "-qb", "done"); self.g("push", "-q", "origin", "done")
        self.g("push", "-q", "origin", "done:also")
        self.g("checkout", "-qb", "open"); Path(self.work, "b").write_text("x"); self.g("add", "b"); self.g("commit", "-qm", "b")
        self.g("push", "-q", "origin", "open")
        out = self.asks("git push origin --delete done also")
        self.assertEqual(out["permissionDecision"], "ask")
        held = f"({self.work.name}, every commit on it already in main)"
        self.assertIn(f"delete done on origin {held}; also on origin {held}?", out["permissionDecisionReason"])
        self.assertIn("only with her OK", out["permissionDecisionReason"])
        self.assertEqual(self.asks("git push origin :done")["permissionDecision"], "ask")
        self.assertEqual(self.asks("git push origin --delete done\t\n")["permissionDecision"], "ask")
        # a carriage return keeps nothing out of sight: main\r is still main
        self.assertIn("never push to the default branch", self.push("git push origin main\r\n").stderr)
        self.assertIn(f"delete done on origin {held}?", self.asks("git push origin -d done done")["permissionDecisionReason"])
        # her OK is never asked for what the gate refuses, in the same push or another one in the command
        self.assertIn("open isn't merged into main, so it stays", self.push("git push origin --delete done open").stderr)
        self.assertEqual(self.push("git push origin --delete done; git push origin main").returncode, 2)
        self.assertEqual(self.push("git push origin --delete done && git push --force origin open").returncode, 2)
        # and her OK covers the whole command, so nothing the gate doesn't read may come with it
        for command in ("git push origin --delete done && gh api -X DELETE repos/o/r/git/refs/heads/open",
                        "git push origin --delete done | tail -1", "git push origin --delete done & rm x",
                        "git push origin --delete done; git push origin open", "git push origin --delete done > out",
                        "git push origin --delete done 2>&1", "git -c core.hooksPath=/tmp/x push origin --delete done",
                        "git push --receive-pack=/tmp/x origin --delete done", "git push origin --delete done\nrm x",
                        "git push origin --delete done # tidy\nrm x", "cd - && git push origin --delete done",
                        "git push origin open :done", 'cd a""b && git push origin --delete done',
                        "git -C a\\b push origin --delete done",
                        # a comment ends at the newline even after a backslash, and an escaped backslash joins nothing
                        "git push origin --delete done # tidy \\\nrm -rf x", "git push origin --delete a\\\\\nreboot",
                        "git push origin --delete done \\\r\nreboot", f"cd {self.work.as_posix()} && git push origin -d done",
                        f"git -C {self.work.as_posix()} push origin --delete done"):
            r = self.push(command)
            self.assertEqual(r.returncode, 2, command)
            self.assertIn("a branch deletion goes on its own", r.stderr)
        self.assertEqual(self.push("git push origin --delete done $(rm -rf x)").returncode, 2)
        # a # starts a comment only at the start of a word, as in the shell: inside one it hides nothing
        for command in ("git push origin --delete done#x", "git push origin HEAD:tmp#z :open",
                        'git push origin --delete "#x"', "git push origin --delete \\#x"):
            self.assertIn("a branch deletion goes on its own", self.push(command).stderr, command)
        self.assertIn("never push to the default branch", self.push("git push origin HEAD:tmp#z main").stderr)
        # a backslash-newline joins the lines, and git reads heads/main as main
        for command in ("git push origin \\\n  :main", "git push origin HEAD:heads/main"):
            self.assertIn("never push to the default branch", self.push(command).stderr, command)
        self.assertIn("no force-push", self.push("git push origin \\\n  --force open").stderr)
        # and a continuation before push still makes it a push
        self.assertIn("never push to the default branch", self.push("git \\\npush origin :main").stderr)
        # bash doesn't continue a comment or an escaped backslash, so the next line is still a command of its own
        for command in ("# push it \\\ngit push origin main", "git push origin open\\\\\ngit push origin main"):
            self.assertIn("never push to the default branch", self.push(command).stderr, command)
        self.assertIn("auto-merge", self.push("# merge when green \\\ngh pr merge 12 --auto").stderr)
        # an escaped space or ; starts no word, and bash keeps a carriage return in its word: no comment after either
        for command in ("git push -o a\\ #z origin :main", "git push --receive-pack=a\\;#z origin :main",
                        "git push --receive-pack=a\r#z origin :main"):
            self.assertIn("never push to the default branch", self.push(command).stderr, command)
        self.assertIn("exactly `git push origin --delete", self.push("git push upstream --delete done").stderr)
        self.g("remote", "set-url", "--push", "origin", str(self.work))
        self.assertIn("goes to origin", self.push("git push origin --delete done").stderr)
        self.g("config", "--unset", "remote.origin.pushurl")
        # every push URL counts, not just the first: git deletes on each
        self.g("remote", "set-url", "--add", "--push", "origin", str(self.work))
        self.g("remote", "set-url", "--add", "--push", "origin", str(self.work))
        self.assertIn("goes to origin", self.push("git push origin --delete done").stderr)
        self.g("config", "--unset-all", "remote.origin.pushurl")
        self.assertIn("name the branch to delete", self.push("git push origin --delete HEAD").stderr)
        self.assertIn("name the branch to delete", self.push("git push origin :HEAD").stderr)
        self.assertIn("nothing after the colon", self.push("git push origin :").stderr)
        # an ordinary push keeps its comment: the shell never sees "main" there
        self.assertEqual(self.push("git push origin open  # then merge to main").returncode, 0)
        # a branch that is gone already fails the one fetch, and the refusal names them all, not just the first
        self.assertIn("couldn't fetch done, gone", self.push("git push origin --delete done gone").stderr)
        Path(self.work, ".claude").mkdir(); Path(self.work, ".claude", "catio-rules.json").write_text('{"merge": true}')
        self.assertEqual(self.push("git push origin --delete done").stdout, "")
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
    """Delegate first (Charlotte, 5 October: "Make sure this never happens again. Always run the delegation before
    assigning anything to anyone", after a workflow's agents had all inherited the session's Opus): every assignment
    names its model on the call, and where she has capped a repo, at or below her cap. Facts only: the model the call
    names, never a guess from the prompt or from an agent's file."""

    def repo(self, **catio):
        """A fresh repo folder, with her .claude/catio-rules.json when she has said anything about it."""
        tmp = tempfile.mkdtemp()
        if catio:
            Path(tmp, ".claude").mkdir()
            Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps(catio))
        return tmp

    def spawn(self, tmp, args, model="claude-opus-5-5", tool="Agent", env=None, agent=None, sid=None):
        """An assignment, as Claude Code asks the gate about it: (exit code, stderr, the line it says)."""
        t = Path(tmp, "t.jsonl")
        t.write_text("".join(json.dumps({"type": "assistant", "message": {"model": m, "content": []}}) + "\n"
                             for m in ([model] if isinstance(model, str) else model)))
        data = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args, "cwd": tmp,
                "session_id": sid or ("s-" + Path(tmp).name), "transcript_path": str(t)}
        if agent:
            data["agent_type"] = agent
        r = run("gates.py", data, cwd=tmp, env=env)
        said = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout.strip() else ""
        return r.returncode, r.stderr, said

    BANANAS = "add bananas to my shopping list"
    NEW_SESSION = "mcp__claude-code-remote__create_session"

    # Nothing is assigned without its model named on the call, whatever the session runs and whatever her cap.
    def test_a_spawn_that_names_no_tier_is_refused_until_it_is_delegated(self):
        code, err, _ = self.spawn(self.repo(), {"prompt": "find every caller of route()", "subagent_type": "general-purpose"})
        self.assertEqual(code, 2)
        self.assertIn("delegate first", err)
        self.assertIn("names no model", err)
        self.assertIn("haiku", err)
        self.assertEqual(self.spawn(self.repo(), {"prompt": "find every caller of route()", "subagent_type": "general-purpose",
                                                  "model": "haiku"})[0], 0)

    def test_with_no_cap_an_unnamed_spawn_is_refused_every_time_not_told_once(self):
        """Her later word wins over the line said once: with no cap, an unnamed spawn is refused, every time."""
        tmp = self.repo()
        for _ in range(2):
            code, err, said = self.spawn(tmp, {"prompt": "find every caller of route()"})
            self.assertEqual((code, said), (2, ""))
            self.assertIn("names no model", err)
        self.assertEqual(self.spawn(self.repo(), {"prompt": "x", "model": "opus"}), (0, "", ""))   # it named one

    def test_a_small_session_delegates_too_and_a_repo_can_switch_it_off(self):
        # "Always": a Haiku session's unnamed spawn would inherit Haiku, whatever the work needs
        self.assertEqual(self.spawn(self.repo(), {"prompt": "find route()"}, model="claude-haiku-4-5")[0], 2)
        self.assertEqual(self.spawn(self.repo(), {"prompt": "find route()"},
                                    model=["claude-opus-5", "claude-haiku-4-5"])[0], 2)   # switched down: still named
        off = self.repo(right_sized=False, tiers={"ceiling": "haiku"})
        self.assertEqual(self.spawn(off, {"prompt": self.BANANAS, "model": "opus"})[0], 0)
        self.assertEqual(self.spawn(off, {"prompt": self.BANANAS})[0], 0)

    def test_the_tool_is_gated_under_either_name_and_a_repo_can_switch_it_off(self):
        tmp = self.repo(tiers={"ceiling": "haiku"})
        for tool in ("Agent", "Task"):
            self.assertEqual(self.spawn(tmp, {"prompt": self.BANANAS, "model": "opus"}, tool=tool)[0], 2, tool)
            self.assertEqual(self.spawn(self.repo(), {"prompt": self.BANANAS}, tool=tool)[0], 2, tool)
            self.assertEqual(self.spawn(self.repo(), {"prompt": self.BANANAS, "model": "opus"}, tool=tool)[0], 0, tool)
        off = self.repo(right_sized=False, tiers={"ceiling": "haiku"})
        self.assertEqual(self.spawn(off, {"prompt": self.BANANAS, "model": "opus"})[0], 0)

    def test_a_workflow_names_a_model_on_every_agent_call(self):
        unnamed = "const a = await agent(`walk ${x}`, { label: 'w', phase: 'Walk' })\nlog('agent() is fine in a string')\n" \
                  "const b = await agent('check', { model: 'sonnet' })\n// agent(in a comment)\nawait agent('z')\n"
        code, err, _ = self.spawn(self.repo(), {"script": unnamed}, tool="Workflow")
        self.assertEqual(code, 2)
        self.assertIn("lines 1, 5", err)
        named = "await agent(`walk ${x}`, { model: 'sonnet', label: 'w' })\nawait agent('z', { model })\n"
        self.assertEqual(self.spawn(self.repo(), {"script": named}, tool="Workflow")[0], 0)
        # a script on disk is read too
        tmp = self.repo()
        Path(tmp, "wf.js").write_text(unnamed)
        self.assertEqual(self.spawn(tmp, {"scriptPath": "wf.js"}, tool="Workflow")[0], 2)

    def test_a_new_session_names_its_model(self):
        code, err, _ = self.spawn(self.repo(), {"prompt": "tidy the README"}, tool=self.NEW_SESSION)
        self.assertEqual(code, 2)
        self.assertIn("this new session names no model", err)
        self.assertEqual(self.spawn(self.repo(), {"prompt": "tidy the README", "model": "claude-sonnet-5-5"},
                                    tool=self.NEW_SESSION)[0], 0)

    def test_a_new_session_off_the_ladder_is_told_so(self):
        code, err, _ = self.spawn(self.repo(), {"prompt": "x", "model": "default"}, tool=self.NEW_SESSION)
        self.assertEqual(code, 2)
        self.assertIn("isn't one of the tiers here", err)

    def test_a_workflow_call_off_the_ladder_is_told_so_not_that_it_names_none(self):
        code, err, _ = self.spawn(self.repo(), {"script": "await agent('x', {model: 'gpt-4'})"}, tool="Workflow")
        self.assertEqual(code, 2)
        self.assertIn("line 1 names gpt-4, which isn't one of the tiers here", err)
        self.assertNotIn("names no model", err)
        code, err, _ = self.spawn(self.repo(), {"script": "await agent('x', {model: 'gpt-4'})\nawait agent('y')"},
                                  tool="Workflow")
        self.assertIn("line 2 names no model", err)

    def test_only_claude_code_remote_s_new_session_is_a_new_cat(self):
        for tool in ("mcp__tmux__create_session", "mcp__jupyter__create_session"):
            self.assertEqual(self.spawn(self.repo(), {"session_name": "build"}, tool=tool)[0], 0, tool)

    def test_a_fork_is_the_parent_and_needs_no_tier(self):
        self.assertEqual(self.spawn(self.repo(), {"prompt": "carry on with the plan", "subagent_type": "fork"})[0], 0)
        self.assertEqual(self.spawn(self.repo(tiers={"ceiling": "haiku"}),
                                    {"prompt": "carry on with the plan", "subagent_type": "fork"})[0], 0)

    def test_held_work_that_names_no_tier_is_told_to_stay_strong(self):
        tmp = self.repo(hold=["harness/"])
        code, err, _ = self.spawn(tmp, {"prompt": "add a line to harness/rules.json"})
        self.assertEqual(code, 2)
        self.assertIn("stays on a strong tier", err)

    def test_held_private_or_browser_work_is_told_to_stay_strong_and_never_pushed_down(self):
        """The prompt's words only shape the refusal's advice: they never refuse or allow anything themselves."""
        tmp = self.repo(hold=["harness/"])
        for prompt in ("add a line to harness/rules.json", "add the solicitor's letter to the legal folder",
                       "check the shopping list in the browser"):
            code, err, _ = self.spawn(tmp, {"prompt": prompt})
            self.assertEqual(code, 2, prompt)
            self.assertIn("stays on a strong tier", err, prompt)
            self.assertEqual(self.spawn(tmp, {"prompt": prompt, "model": "opus"}), (0, "", ""), prompt)

    def test_an_agent_pinned_to_a_tier_names_it_on_the_call_too(self):
        """The rule reads no agent files: the scout and the tester are Haiku in theirs, and still say so on the call."""
        for agent in ("scout", "tester", "kittychat-house-rules:scout"):
            self.assertEqual(self.spawn(self.repo(), {"prompt": "find every caller of route()", "subagent_type": agent})[0],
                             2, agent)
            self.assertEqual(self.spawn(self.repo(), {"prompt": "find every caller of route()", "subagent_type": agent,
                                                      "model": "haiku"}), (0, "", ""), agent)

    def test_an_agent_file_of_the_repo_s_own_is_not_read_either(self):
        tmp = self.repo()
        Path(tmp, ".claude", "agents").mkdir(parents=True)
        Path(tmp, ".claude", "agents", "my-reviewer.md").write_text("---\nname: reviewer\nmodel: sonnet\n---\nReview.\n")
        self.assertEqual(self.spawn(tmp, {"prompt": "review", "subagent_type": "reviewer"})[0], 2)
        self.assertEqual(self.spawn(tmp, {"prompt": "review", "subagent_type": "reviewer", "model": "sonnet"})[0], 0)

    def test_a_repo_ladder_is_read_whatever_its_case_and_a_missing_tier_says_so(self):
        tmp = self.repo(tiers={"ladder": ["Haiku", "Sonnet"]})
        self.assertEqual(self.spawn(tmp, {"prompt": "list docs", "model": "haiku"})[0], 0)
        code, err, _ = self.spawn(tmp, {"prompt": "design the plan", "model": "opus"})
        self.assertEqual(code, 2)
        self.assertIn("isn't one of the tiers here", err)

    # Her cap (tiers.ceiling in the repo's .claude/catio-rules.json): a model named above it is refused.
    def test_under_her_cap_a_spawn_names_its_model(self):
        """The one fact the hook can see is the model on the call, so that is what her cap is kept on."""
        tmp = self.repo(tiers={"ceiling": "sonnet"})
        code, err, _ = self.spawn(tmp, {"prompt": self.BANANAS})
        self.assertEqual(code, 2)
        self.assertIn("names no model", err)
        self.assertIn("sonnet", err)
        for model in ("sonnet", "haiku", "claude-haiku-4-5-20251001"):
            self.assertEqual(self.spawn(tmp, {"prompt": self.BANANAS, "model": model})[0], 0, model)
        for model in ("opus", "fable", "claude-opus-5-5"):
            self.assertEqual(self.spawn(tmp, {"prompt": self.BANANAS, "model": model})[0], 2, model)

    def test_a_model_her_ladder_does_not_know_is_refused_with_the_list(self):
        tmp = self.repo(tiers={"ceiling": "sonnet"})
        for model in ("inherit", "default", "gpt-4"):
            code, err, _ = self.spawn(tmp, {"prompt": "x", "model": model})
            self.assertEqual(code, 2, model)
            self.assertIn("haiku, sonnet", err)

    def test_her_cap_is_about_cost_so_no_word_in_the_prompt_escapes_it(self):
        """Her cap compares two facts. A prompt that happens to say login, bank or harness is still a spawn."""
        tmp = self.repo(tiers={"ceiling": "haiku"}, hold=["harness/"])
        for prompt in ("rewrite the whole login flow", "reconcile the bank export", "tidy harness",
                       "take a screenshot of the page", "add the solicitor's letter"):
            self.assertEqual(self.spawn(tmp, {"prompt": prompt, "model": "opus"})[0], 2, prompt)

    def test_her_cap_holds_one_level_down_too(self):
        """A sub agent's own spawn is a sub agent in this repo, and it names its model like any other."""
        tmp = self.repo(tiers={"ceiling": "haiku"})
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "opus"}, agent="scout")[0], 2)
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "haiku"}, agent="scout")[0], 0)
        self.assertEqual(self.spawn(tmp, {"prompt": "x"}, agent="scout")[0], 2)

    def test_an_agent_pinned_cheap_is_named_cheap_on_the_call(self):
        """The rule does not parse agent files: naming the tier is what it asks for, and it always works."""
        tmp = self.repo(tiers={"ceiling": "haiku"})
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "subagent_type": "scout"})[0], 2)
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "subagent_type": "scout", "model": "haiku"})[0], 0)

    def test_the_environment_s_defaults_do_not_name_a_model_on_the_call(self):
        tmp = self.repo(tiers={"ceiling": "haiku"})
        for env in ({"CLAUDE_CODE_SUBAGENT_MODEL": "haiku"}, {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "haiku"}):
            self.assertEqual(self.spawn(tmp, {"prompt": "x"}, env=env)[0], 2, env)   # still unnamed on the call
            self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "haiku"}, env=env)[0], 0, env)

    def test_a_forced_default_above_her_cap_says_what_would_actually_help(self):
        tmp = self.repo(tiers={"ceiling": "haiku"})
        for force in ("opus", "something-else"):
            code, err, _ = self.spawn(tmp, {"prompt": "x", "model": "haiku"},
                                      env={"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": force})
            self.assertEqual(code, 2, force)
            self.assertIn("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", err)   # naming a model on the call cannot help here
        code, err, _ = self.spawn(tmp, {"script": "await agent('x', {model: 'haiku'})"}, tool="Workflow",
                                  env={"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "opus"})
        self.assertEqual(code, 2)
        self.assertIn("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", err)
        # with no cap of hers, the forced default is not the rule's business
        self.assertEqual(self.spawn(self.repo(), {"prompt": "x", "model": "haiku"},
                                    env={"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "opus"})[0], 0)

    def test_under_her_cap_a_workflow_spells_out_each_tier(self):
        tmp = self.repo(tiers={"ceiling": "sonnet"})
        ok = "await agent('a', {model: 'haiku'})\nawait agent('b', {model: 'claude-sonnet-5-5'})\n"
        self.assertEqual(self.spawn(tmp, {"script": ok}, tool="Workflow")[0], 0)
        for src, line in (("await agent('a', {model: 'haiku'})\nawait agent('b', {model: 'opus'})\n", "line 2"),
                          ("await agent('a', {model: w.model})\n", "line 1")):   # an expression's cost can't be read
            code, err, _ = self.spawn(tmp, {"script": src}, tool="Workflow")
            self.assertEqual(code, 2, src)
            self.assertIn(line, err, src)
            self.assertIn("sonnet or below", err, src)
        self.assertEqual(self.spawn(self.repo(), {"script": "await agent('a', {model: w.model})"}, tool="Workflow")[0], 0)

    def test_her_cap_is_on_this_repo_s_sub_agents_not_a_new_session(self):
        """A new cat may be for another repo; it names its model, and her cap here is not its own."""
        tmp = self.repo(tiers={"ceiling": "haiku"})
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "opus"}, tool=self.NEW_SESSION)[0], 0)
        self.assertEqual(self.spawn(tmp, {"prompt": "x"}, tool=self.NEW_SESSION)[0], 2)

    def test_a_cap_it_cannot_act_on_says_so_instead_of_going_quiet(self):
        """The shapes a hand-written file comes in: the wrong type, a typo, the key outside the block."""
        for catio in ({"tiers": {"ceiling": "gpt-4"}}, {"tiers": {"ceiling": False}},
                      {"tiers": "sonnet"}, {"ceiling": "haiku"}):
            tmp = self.repo(**catio)
            code, _, said = self.spawn(tmp, {"prompt": self.BANANAS, "model": "opus"})
            self.assertEqual(code, 0, catio)
            self.assertIn("doing nothing", said, catio)

    def test_a_typo_in_her_key_is_said_rather_than_silently_dropped(self):
        for catio in ({"tiers": {"celing": "haiku"}}, {"tiers": {"ceiling_": "haiku"}},
                      {"tiers": {"note": "small cats"}}, {"tier": {"ceiling": "haiku"}}):
            tmp = self.repo(**catio)
            code, _, said = self.spawn(tmp, {"prompt": "x", "model": "opus"})
            self.assertEqual(code, 0, catio)
            self.assertIn("doing nothing", said, catio)

    def test_the_errand_ceiling_of_before_is_said_to_be_gone(self):
        tmp = self.repo(tiers={"errand": "haiku"})
        code, _, said = self.spawn(tmp, {"prompt": self.BANANAS, "model": "opus"})
        self.assertEqual(code, 0)
        self.assertIn("tiers.ceiling", said)

    def test_a_cap_she_misspelt_still_leaves_the_model_to_be_named(self):
        """Her typo turns the cap off, never delegate first; and the line is said once the call can go through."""
        tmp = self.repo(tiers={"celing": "haiku"})
        code, err, said = self.spawn(tmp, {"prompt": "x"})
        self.assertEqual((code, said), (2, ""))
        self.assertIn("names no model", err)
        self.assertIn("doing nothing", self.spawn(tmp, {"prompt": "x", "model": "opus"})[2])
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "opus"}), (0, "", ""))   # said once

    def test_a_key_the_rule_does_not_know_is_not_an_error(self):
        """Her own documented block carries a _comment, so an unknown key must not switch the cap off."""
        tmp = self.repo(tiers={"_comment": "small cats only", "ceiling": "haiku"})
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "opus"})[0], 2)
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "haiku"})[0], 0)

    def test_a_ladder_written_with_capitals_still_matches(self):
        tmp = self.repo(tiers={"ceiling": "Haiku", "ladder": ["Haiku", "Sonnet", "Opus"]})
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "opus"})[0], 2)
        self.assertEqual(self.spawn(tmp, {"prompt": "x", "model": "haiku"})[0], 0)

    def test_a_ladder_the_rule_cannot_use_is_a_setting_not_a_crash(self):
        tmp = self.repo(tiers={"ceiling": "haiku", "ladder": 5})
        code, _, said = self.spawn(tmp, {"prompt": self.BANANAS, "model": "opus"})
        self.assertEqual(code, 0)
        self.assertIn("doing nothing", said)
        self.assertEqual(self.spawn(tmp, {"prompt": self.BANANAS})[0], 2)   # the house's ladder still names a tier
        r = run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                             "tool_input": {"file_path": str(Path(tmp, "a.py"))},
                             "transcript_path": transcript(tmp), "cwd": tmp}, cwd=tmp)
        self.assertEqual(r.returncode, 2)                          # the opening audit still speaks
        self.assertIn("ponytail-audit", r.stderr)

    def test_a_gate_that_cannot_run_refuses_rather_than_waving_the_call_through(self):
        """The gates are the safety net. One that cannot read the house rules must not open all of them."""
        plugin = Path(tempfile.mkdtemp())
        shutil.copytree(HOOKS, plugin / "hooks")
        (plugin / "rules.json").write_text("{ this is not json")
        tmp = self.repo()
        r = subprocess.run([sys.executable, str(plugin / "hooks" / "gates.py")],
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                             "tool_input": {"file_path": str(Path(tmp, "a.py"))}, "cwd": tmp}),
                           capture_output=True, text=True, cwd=tmp)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("couldn't be read", r.stderr)

    def test_a_hook_module_that_cannot_import_refuses_rather_than_exiting_one(self):
        """What actually took main down on 5 October: right_sized.py lost an import. gates.py imported it at
        module level, so it died before the guard above could run, and Claude Code reads a non-2 exit as a
        warning - so every rule was off and nothing said so. The wording matters as much as the exit code: a
        healthy tree also exits 2 here, through the opening-audit gate, so asserting only "exit 2, House rule"
        would stay green if a later change swallowed the error and waved the call on to the other gates."""
        for break_it in (lambda s: s.replace("import re\n", "", 1),             # a lost import, as it happened
                         lambda s: s + "\nraise RuntimeError('at import')\n",   # anything else at module level
                         lambda s: "import nonexistent_module_xyz\n" + s):
            plugin = Path(tempfile.mkdtemp())
            shutil.copytree(HOOKS, plugin / "hooks")
            shutil.copy(HOOKS.parent / "rules.json", plugin / "rules.json")
            hook = plugin / "hooks" / "right_sized.py"
            hook.write_text(break_it(hook.read_text(encoding="utf-8")), encoding="utf-8")
            tmp = self.repo()
            r = subprocess.run([sys.executable, str(plugin / "hooks" / "gates.py")],
                               input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                                 "tool_input": {"file_path": str(Path(tmp, "a.py"))}, "cwd": tmp}),
                               capture_output=True, text=True, cwd=tmp,
                               env=dict({k: v for k, v in os.environ.items() if k not in ENV_KEYS},
                                        XDG_CACHE_HOME=CACHE))
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("the gate right_sized.py couldn't be loaded", r.stderr)   # names the hook, not rules.json
            self.assertIn("not her rules file", r.stderr)
            self.assertNotIn("ponytail-audit", r.stderr)      # it never reached the gates below

    def test_gates_imports_nothing_at_module_level_that_could_exit_one(self):
        """The fix for the above is two imports moved into main(). A third hook module imported at the top of
        gates.py later would reopen the same outage, and the test above (which breaks right_sized.py) would
        stay green. So pin the shape: gates.py's own module level imports the standard library and common,
        and nothing else - every sibling hook is imported inside the guard."""
        tree = ast.parse((HOOKS / "gates.py").read_text(encoding="utf-8"))
        imported = set()
        for node in tree.body:                      # the module's own top level, wherever in the file it sits
            for inner in ast.walk(node) if isinstance(node, (ast.Try, ast.If)) else [node]:
                if isinstance(inner, ast.Import):
                    imported |= {a.name for a in inner.names}
                elif isinstance(inner, ast.ImportFrom) and inner.module:
                    imported.add(inner.module)
        siblings = {f.stem for f in HOOKS.glob("*.py")} - {"gates"}
        self.assertEqual(imported & siblings, {"common"}, imported & siblings)
        for name in sorted(imported - siblings):
            self.assertIn(name.split(".")[0], sys.stdlib_module_names, name)

    def test_one_repos_message_does_not_silence_another(self):
        """A cloud session works in several repos at once, so the marker is per repo, not per session."""
        a, b = self.repo(tiers={"celing": "haiku"}), self.repo(tiers={"celing": "haiku"})
        self.assertIn("doing nothing", self.spawn(a, {"prompt": "x", "model": "haiku"}, sid="one")[2])
        self.assertIn("doing nothing", self.spawn(b, {"prompt": "x", "model": "haiku"}, sid="one")[2])


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

    def test_an_agent_type_names_no_tier_its_model_does(self):
        """The rule reads no agent files, so a helper pinned in its own file names its model on the call too."""
        for kind in ("scout", "kittychat-house-rules:tester", "general-purpose"):
            self.assertEqual(self.lines("await agent('find callers', {agentType: '%s'})" % kind), [1], kind)
            self.assertEqual(self.lines("await agent('find callers', {agentType: '%s', model: 'haiku'})" % kind), [], kind)

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
                    "await agent('x', {'agentType': 'scout', 'model': 'haiku'})"):
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
        self.assertEqual(self.r.script_of({"scriptPath": "wf.js"}, tmp), "")
        for tool, args in (("Workflow", {"scriptPath": "wf.js"}), ("Agent", {"prompt": "x", "subagent_type": "old",
                                                                               "model": "haiku"})):
            r = run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": args, "cwd": tmp,
                                 "transcript_path": transcript(tmp)}, cwd=tmp)
            self.assertEqual((r.returncode, r.stderr), (0, ""), tool)

    def test_a_child_workflow_is_read_too(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude", "workflows").mkdir(parents=True)
        Path(tmp, ".claude", "workflows", "sweep.js").write_text("await agent('a')\n")
        Path(tmp, "named.js").write_text("await agent('a', { model: 'haiku' })\n")
        self.assertEqual(self.lines("log('x')\nawait workflow('sweep')", tmp), [2])
        self.assertEqual(self.lines("await workflow({scriptPath: 'named.js'})", tmp), [])
        self.assertEqual(self.lines("await workflow('a-built-in')", tmp), [])   # can't be read: nothing to check


class Common(unittest.TestCase):
    """The shared readers the hooks lean on: one transcript reader, and a remembered "said" with no side effect."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HOOKS))
        import common
        cls.c = common

    def test_the_hook_answers_once_with_its_nudge_and_its_ask(self):
        # two JSON answers on stdout are read as neither, which would void her prompt
        import contextlib, io
        out = io.StringIO()
        self.c.CONTEXT[:] = ["a nudge"]
        try:
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as done:
                self.c.ask("delete done?")
        finally:
            self.c.CONTEXT.clear()
        self.assertEqual(done.exception.code, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        said = json.loads(lines[0])["hookSpecificOutput"]
        self.assertEqual((said["permissionDecision"], said["permissionDecisionReason"], said["additionalContext"]),
                         ("ask", "delete done?", "a nudge"))

    def test_this_repos_own_hold_list_keeps_the_rules_and_the_workflows_for_her(self):
        rules = json.loads((HOOKS.parent.parent / ".claude" / "catio-rules.json").read_text(encoding="utf-8"))
        paths, unreadable = self.c.holds(rules)
        self.assertFalse(unreadable)
        self.assertEqual({"harness", ".github"} - {p.rstrip("/") for p in paths}, set())

    def test_one_transcript_reader_and_who_counts(self):
        tmp = Path(tempfile.mkdtemp())
        rows = [{"type": "assistant", "message": {"model": "claude-opus-5-5"}},
                {"type": "assistant", "isSidechain": True, "message": {"model": "claude-haiku-4-5"}},
                {"type": "assistant", "message": {"model": "<synthetic>"}},
                {"type": "user", "message": {"model": "not-an-answer"}},
                {"type": "assistant", "message": {"model": "claude-sonnet-5-5"}}]
        (tmp / "t.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json, \"model\"\n")
        data = {"transcript_path": str(tmp / "t.jsonl"), "agent_transcript_path": str(tmp / "t.jsonl")}
        # a session's own: in the order they answered, its sub agents' side left out
        self.assertEqual(self.c.answered(data, ("transcript_path",)), ["claude-opus-5-5", "claude-sonnet-5-5"])
        # a sub agent's own transcript: its side is the whole file
        self.assertEqual(self.c.answered(data, ("agent_transcript_path",), sidechain=True),
                         ["claude-opus-5-5", "claude-haiku-4-5", "claude-sonnet-5-5"])
        self.assertEqual(self.c.models({"transcript_path": str(tmp / "t.jsonl")}), {"claude-opus-5-5", "claude-sonnet-5-5"})
        self.assertEqual(self.c.answered({"transcript_path": str(tmp / "missing.jsonl")}), [])

    def test_said_asks_and_say_remembers_per_session_and_repo(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": tempfile.mkdtemp()}):
            self.assertFalse(self.c.said("s1", "k", "test", "/repo/a"))
            self.assertFalse(self.c.said("s1", "k", "test", "/repo/a"))   # asking twice tells nothing
            self.c.say("s1", "k", "test", "/repo/a")
            self.assertTrue(self.c.said("s1", "k", "test", "/repo/a"))
            for other in (("s2", "k", "test", "/repo/a"), ("s1", "k", "test", "/repo/b"), ("s1", "j", "test", "/repo/a")):
                self.assertFalse(self.c.said(*other), other)
            folder = Path(os.environ["XDG_CACHE_HOME"], "catio")
            self.assertTrue(any(folder.iterdir()))                         # a folder of this user's own, not /tmp
            if os.name != "nt":
                self.assertEqual(folder.stat().st_mode & 0o777, 0o700)

    def test_the_rules_hand_out_their_own_copy(self):
        tmp = tempfile.mkdtemp()
        Path(tmp, ".claude").mkdir()
        Path(tmp, ".claude", "catio-rules.json").write_text('{"hold": ["a/"]}')
        self.c.rules()["tiers"]["ladder"].append("gpt")
        self.c.local(tmp)["hold"].append("b/")
        self.assertNotIn("gpt", self.c.rules()["tiers"]["ladder"])
        self.assertEqual(self.c.local(tmp)["hold"], ["a/"])


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
        for words in ("KittyChat house rules", "browser-agent-preflight", "ponytail-audit", "[Catio]"):
            self.assertIn(words, r.stdout)
        # it names no café of its own: the address is CATIO_URL's or nothing. A host written into the hook or the
        # rules file outlived the move off the artifact (how the old link survived her asking twice), and reached
        # every fork, whose sessions read "Charlotte's Catio" as their own (her ask, 25 October).
        self.assertIn("isn't connected to a KittyChat Café", r.stdout)
        for host in ("workers.dev", "claude.ai/artifact", "Charlotte's Catio"):
            self.assertNotIn(host, r.stdout)

    def test_says_when_a_repo_merges(self):
        tmp = Path(tempfile.mkdtemp(), "cafe")
        subprocess.run(["git", "init", "-q", str(tmp)], check=True)
        self.assertIn("  cafe's pull requests are hers to merge.", run("session_start.py", {"cwd": str(tmp)}).stdout)
        Path(tmp, ".claude").mkdir()
        Path(tmp, ".claude", "catio-rules.json").write_text('{"merge": true, "hold": ["harness/"]}')
        out = run("session_start.py", {"cwd": str(tmp)}).stdout
        self.assertIn("  cafe merges its own pull requests; changes to harness/ always wait for her.", out)
        self.assertIn("**Semi-automatic merging** (enforced)", out)

    def test_the_brief_never_claims_a_hold_the_merge_gate_will_not_keep(self):
        """It read her hold list straight into a join, so it announced "changes to harness/* always wait for
        her" for a glob the gate never expands, and exited 1 on a shape that would not join at all - losing
        the whole briefing, the opening-audit instruction included, with only a traceback to show."""
        for hold in ODD_HOLDS:
            tmp = Path(tempfile.mkdtemp(), "cafe")
            subprocess.run(["git", "init", "-q", str(tmp)], check=True)
            Path(tmp, ".claude").mkdir(parents=True)
            Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps({"merge": True, "hold": hold}))
            r = run("session_start.py", {"cwd": str(tmp)})
            self.assertEqual(r.returncode, 0, (hold, r.stderr))
            self.assertIn("**Semi-automatic merging** (enforced)", r.stdout, hold)
            # the gate holds every merge there, so the brief must not say it merges its own
            self.assertIn("hold list is in a shape the harness can't read", r.stdout, hold)
            self.assertNotIn("cafe merges its own pull requests", r.stdout, hold)
            self.assertNotIn("always wait for her.", r.stdout, hold)
        padded = Path(tempfile.mkdtemp(), "cafe")   # trimmed, and quoted as she spelt it
        subprocess.run(["git", "init", "-q", str(padded)], check=True)
        Path(padded, ".claude").mkdir(parents=True)
        Path(padded, ".claude", "catio-rules.json").write_text('{"merge": true, "hold": ["  harness/  "]}')
        self.assertIn("  cafe merges its own pull requests; changes to harness/ always wait for her.",
                      run("session_start.py", {"cwd": str(padded)}).stdout)

    def test_the_brief_reads_the_house_hold_list_too_not_only_the_repos(self):
        """The merge gate holds on either list, so a brief that reads only the repo's claims merge rights the
        gate is refusing - and never mentions the house's own .claude/, which waits for her in every repo."""
        def brief(house_hold, mine, plugin_dir=None):
            plugin = Path(tempfile.mkdtemp())
            shutil.copytree(HOOKS, plugin / "hooks")
            r = json.loads((HOOKS.parent / "rules.json").read_text(encoding="utf-8"))
            r["merging"]["hold"] = house_hold
            (plugin / "rules.json").write_text(json.dumps(r))
            tmp = Path(tempfile.mkdtemp(), "cafe")
            subprocess.run(["git", "init", "-q", str(tmp)], check=True)
            Path(tmp, ".claude").mkdir(parents=True)
            Path(tmp, ".claude", "catio-rules.json").write_text(json.dumps({"merge": True, "hold": mine}))
            return subprocess.run([sys.executable, str(plugin / "hooks" / "session_start.py")],
                                  input=json.dumps({"cwd": str(tmp), "source": "startup"}),
                                  capture_output=True, text=True,
                                  env=dict({k: v for k, v in os.environ.items() if k not in ENV_KEYS},
                                           XDG_CACHE_HOME=CACHE))
        out = brief([".claude/"], ["docs/"]).stdout        # a readable house list: the brief is as before
        self.assertIn("  cafe merges its own pull requests; changes to docs/ always wait for her.", out)
        broken = brief("harness/", ["docs/"])               # the house's is unreadable: the gate holds all
        self.assertEqual(broken.returncode, 0, broken.stderr)
        self.assertIn("the house rules' hold list is in a shape the harness can't read", broken.stdout)
        self.assertNotIn("cafe merges its own pull requests;", broken.stdout)
        both = brief("harness/", "docs/").stdout            # both broken: name both, or she fixes one
        self.assertIn("the house rules' and cafe's hold list is in a shape", both)

    def test_a_merging_block_a_merge_fused_is_unreadable_not_silent(self):
        """holds() is handed the block, not the value, so a "merging" that a fused manifest left as a list
        must read as unreadable. Read as silence it says nothing and the brief claims merge rights."""
        for fused in ([{"hold": [".claude/"]}], "hold", 5):
            plugin = Path(tempfile.mkdtemp())
            shutil.copytree(HOOKS, plugin / "hooks")
            r = json.loads((HOOKS.parent / "rules.json").read_text(encoding="utf-8"))
            r["merging"] = fused
            (plugin / "rules.json").write_text(json.dumps(r))
            tmp = Path(tempfile.mkdtemp(), "cafe")
            subprocess.run(["git", "init", "-q", str(tmp)], check=True)
            Path(tmp, ".claude").mkdir(parents=True)
            Path(tmp, ".claude", "catio-rules.json").write_text('{"merge": true, "hold": ["docs/"]}')
            out = subprocess.run([sys.executable, str(plugin / "hooks" / "session_start.py")],
                                 input=json.dumps({"cwd": str(tmp), "source": "startup"}),
                                 capture_output=True, text=True,
                                 env=dict({k: v for k, v in os.environ.items() if k not in ENV_KEYS},
                                          XDG_CACHE_HOME=CACHE)).stdout
            self.assertIn("hold list is in a shape the harness can't read", out, fused)
            self.assertNotIn("cafe merges its own pull requests;", out, fused)

    def test_the_brief_says_so_rather_than_printing_nothing_when_it_cannot_be_built(self):
        """session_start had no guard at all: any exception exited 1, SessionStart reads that as a warning,
        and the session began with no rules, no hold list and no "run ponytail-audit first" - just a
        traceback. That is the class gates.py was hardened against in this same branch."""
        for break_it in (lambda r: r.pop("rules"), lambda r: r.update(rules={"not": "a list"})):
            plugin = Path(tempfile.mkdtemp())
            shutil.copytree(HOOKS, plugin / "hooks")
            r = json.loads((HOOKS.parent / "rules.json").read_text(encoding="utf-8"))
            break_it(r)
            (plugin / "rules.json").write_text(json.dumps(r))
            out = subprocess.run([sys.executable, str(plugin / "hooks" / "session_start.py")],
                                 input=json.dumps({"cwd": tempfile.mkdtemp(), "source": "startup"}),
                                 capture_output=True, text=True)
            self.assertIn("couldn't be read", out.stdout)
            self.assertIn("ponytail-audit", out.stdout)     # the one instruction it must not lose

    def test_reminds_a_fable_session_of_opus(self):
        nudge = "suggest /model opus"
        self.assertIn(nudge, run("session_start.py", {"model": "claude-fable-5-1", "cwd": tempfile.mkdtemp()}).stdout)
        self.assertNotIn(nudge, run("session_start.py", {"model": "claude-opus-5-5", "cwd": tempfile.mkdtemp()}).stdout)
        self.assertNotIn(nudge, run("session_start.py", {"cwd": tempfile.mkdtemp()}).stdout)

    def test_resume_skips_the_audit_prompt(self):
        r = run("session_start.py", {"source": "resume", "cwd": tempfile.mkdtemp()})
        self.assertNotIn("Start now with the read-only pass", r.stdout)

    def test_a_guest_session_is_told_its_own_cafe(self):
        def start(url):
            env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_REMOTE", "CATIO_URL")}
            if url:
                env["CATIO_URL"] = url
            return subprocess.run([sys.executable, str(HOOKS / "session_start.py")], capture_output=True, text=True,
                                  input=json.dumps({"source": "startup", "model": "claude-fable-5-1",
                                                    "cwd": tempfile.mkdtemp()}), env=env).stdout
        guest = start("https://catio-gateway.someone.workers.dev")
        self.assertIn("KittyChat Café of the person you are working for, at https://catio-gateway.someone.workers.dev", guest)
        # nobody else's café is named, so there is nothing to disclaim: the rules file carries no address
        for words in ("Charlotte's Catio", "Charlotte's allowance", "her own is at", "charlotte-badot"):
            self.assertNotIn(words, guest)
        # and with no CATIO_URL there is no café at all; the brief says so instead of handing over hers
        alone = start(None)
        self.assertIn("isn't connected to a KittyChat Café", alone)
        self.assertNotIn("workers.dev", alone)
        self.assertIn('{"opening_audit": false} in .claude/catio-rules.json', guest)


class Plugin(unittest.TestCase):
    def test_no_tracked_file_names_the_owner_s_own_cafe(self):
        """This repository is public, and the gateway's host carries the owner's own name, so writing her
        address down here publishes it. #157 took it out of rules.json, session_start.py and the page, and the
        brief was the copy left behind; without a check the next session writes it back, because a worked
        example is the easiest thing to reach for. The address lives in CATIO_URL, in the environment, and a
        session with none is told it isn't connected. The needle is built from parts so this file doesn't
        contain the thing it forbids, and the scan is over tracked files only: a developer's own checkout may
        hold her address in catio/data or catio/dist, which are gitignored and never leave their machine."""
        host = "catio-" + "gateway." + "charlotte" + "-badot"
        # A published page's own address, id and all. The bare path is left alone on purpose: the docs and the
        # litter box discuss "claude.ai/artifact/" as a thing, and only a real link gives a real page away.
        page = re.compile(r"claude\.ai/" + "artifact" + r"/[A-Za-z0-9_-]{10,}")
        root = HOOKS.parent.parent
        found = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True)
        self.assertEqual(found.returncode, 0, found.stderr)
        named = []
        for name in [n for n in found.stdout.split("\0") if n]:
            f = root / name
            try:
                body = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue   # binary, or gone in a half-finished checkout: neither can carry an address
            for i, line in enumerate(body.splitlines(), 1):
                if host in line or page.search(line):
                    named.append("%s:%d" % (name, i))
        self.assertEqual(named, [], "a private address of hers is in these tracked files; the gateway's belongs "
                         "in CATIO_URL and the artifact's in CATIO_ARTIFACT: " + ", ".join(named))

    def test_no_tracked_manifest_has_a_duplicate_key(self):
        """A merge that fuses two versions of a manifest leaves both keys, and json.loads takes the last and
        says nothing - which is how a broken rules.json, plugin.json and hooks.json all reached main on
        5 October, each found by hand after the damage. The check below parses them the silent way, so this
        one parses every tracked manifest the strict way, .jsonc included: wrangler.jsonc is the one Workers
        Builds deploys on every merge to main, where a fused "vars" or "ai" block is worse than a fused
        rules.json. "Parses at all" and "has no repeated key" are reported apart, so a future manifest that
        simply isn't strict JSON names itself instead of looking like a duplicate key."""
        def once(pairs):
            seen = set()
            for k, _ in pairs:
                if k in seen:
                    raise ValueError("duplicate key %r" % k)
                seen.add(k)
            return dict(pairs)
        root = HOOKS.parent.parent
        found = subprocess.run(["git", "ls-files", "-z", "*.json", "*.jsonc"], cwd=root,
                               capture_output=True, text=True)
        self.assertEqual(found.returncode, 0, found.stderr)
        checked, unparsed = set(), []
        for name in [n for n in found.stdout.split("\0") if n]:
            if "node_modules" in name or name.endswith("package-lock.json"):
                continue
            try:
                text = (root / name).read_text(encoding="utf-8")
            except OSError:
                continue
            if name.endswith(".jsonc"):
                text = without_comments(text)   # // and /* */ are part of the format, inside strings they aren't
            try:
                parsed = json.loads(text)
            except ValueError as e:
                unparsed.append("%s: %s" % (name, e))
                continue
            del parsed
            try:
                json.loads(text, object_pairs_hook=once)
            except ValueError as e:
                self.fail("%s has a repeated key, which a merge of two versions leaves: %s" % (name, e))
            checked.add(name)
        # A fixture is allowed to be malformed on purpose - that is what some of them are for. Anything else
        # tracked that isn't valid JSON is worth failing on, and says so in its own words rather than looking
        # like a repeated key.
        self.assertEqual([u for u in unparsed if "fixtures/" not in u and "/test/" not in u], [],
                         "these are tracked but are not valid JSON at all")
        for must in ("harness/rules.json", "harness/.claude-plugin/plugin.json", "harness/hooks/hooks.json",
                     "harness/gateway/wrangler.jsonc"):
            self.assertIn(must, checked, "the sweep missed %s" % must)

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

    def test_every_hook_uses_one_launcher_that_finds_python_on_windows(self):
        hooks = json.loads((HOOKS / "hooks.json").read_text())["hooks"]
        launchers = {h["command"].split(' "${CLAUDE_PLUGIN_ROOT}/hooks/')[0]
                     for groups in hooks.values() for g in groups for h in g["hooks"]}
        self.assertEqual(len(launchers), 1, launchers)
        launcher = launchers.pop()
        empty = tempfile.mkdtemp()   # a PATH with no py on it
        for os_name, path, want in (("", os.environ["PATH"], "python3"), ("Windows_NT", empty, "python")):
            env = dict(os.environ, OS=os_name, PATH=path)
            r = subprocess.run([BASH, "-c", "echo " + launcher], capture_output=True, text=True, env=env)
            self.assertEqual(r.stdout.strip(), want, os_name)
        if os.name == "nt":   # a stand-in py needs a POSIX file mode
            return
        Path(empty, "py").write_text("#!/bin/sh\n")
        Path(empty, "py").chmod(0o755)
        r = subprocess.run([BASH, "-c", "echo " + launcher], capture_output=True, text=True,
                           env=dict(os.environ, OS="Windows_NT", PATH=empty + os.pathsep + os.environ["PATH"]))
        self.assertEqual(r.stdout.strip(), "py")

    def test_the_gates_say_what_to_do_without_the_skills(self):
        tmp = tempfile.mkdtemp()
        r = run("gates.py", {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input":
                             {"file_path": str(Path(tmp, "x.txt"))}, "transcript_path": transcript(tmp), "cwd": tmp})
        self.assertEqual(r.returncode, 2)
        self.assertIn('{"opening_audit": false} in .claude/catio-rules.json', r.stderr)


if __name__ == "__main__":
    unittest.main()
