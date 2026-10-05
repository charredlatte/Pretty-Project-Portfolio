"""report.py against a stand-in gateway: what each hook reports, what Stop hands in, and that a gateway that is
missing, down or refusing never breaks a turn.

    python3 -m unittest discover harness/test
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPORT = Path(__file__).resolve().parent.parent / "hooks" / "report.py"
KEY = "test-key-0123456789abcdef"
EMPTY = {"files": [], "notes": [], "request": None}


class Gateway(BaseHTTPRequestHandler):
    """Answers MCP tool calls as the gateway does, from `box` (what's waiting), and records every call."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        s = self.server
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("User-Agent", "").startswith("Python-urllib"):   # Cloudflare's bot check: error 1010
            self.send_response(403); self.end_headers(); return
        if self.headers.get("Authorization") != "Bearer " + KEY:
            self.send_response(401); self.end_headers(); return
        s.paths.append(self.path)
        replies = []
        for msg in body if isinstance(body, list) else [body]:
            name, args = msg["params"]["name"], msg["params"]["arguments"]
            s.calls.append((name, args))
            out = {"report_status": {"ok": True, "waiting": EMPTY}, "comment": {"id": "n1", "woke": False},
                   "inbox": s.box, "pick_up": s.file, "save_report": {"id": "graphs/some-repo"}}[name]
            replies.append({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": json.dumps(out)}],
                                                                           "structuredContent": out}})
        data = json.dumps(replies if isinstance(body, list) else replies[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Report(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.srv.calls, self.srv.paths, self.srv.box, self.srv.file = [], [], EMPTY, None
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp, "repo")
        g = lambda *a: subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True)
        self.repo.mkdir()
        g("init", "-b", "main"); g("remote", "add", "origin", "http://proxy@127.0.0.1:9/git/charredlatte/Some-Repo")
        g("checkout", "-b", "claude/fix-it")

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CATIO_", "CLAUDE_CODE_"))}
        env.update(CATIO_URL=self.url, CATIO_TOKEN=KEY, CLAUDE_CODE_REMOTE_SESSION_ID="session_01Abc",
                   NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost", TMPDIR=self.tmp)
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def hook(self, event, env=None, **data):
        return subprocess.run([sys.executable, str(REPORT)], input=json.dumps({"hook_event_name": event, "cwd": str(self.repo),
                              "session_id": "cli-uuid", **data}), capture_output=True, text=True, env=env or self.env(), timeout=20)

    def test_quiet_without_the_gateway(self):
        r = self.hook("SessionStart", env=self.env(CATIO_URL=None))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(self.srv.calls, [])

    def test_session_start_says_who_and_where(self):
        r = self.hook("SessionStart", source="startup", model="claude-opus-5-5", session_title="Fix the tests")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(self.srv.paths, ["/mcp"])
        name, args = self.srv.calls[0]
        self.assertEqual(name, "report_status")
        self.assertEqual(args, {"agent": "session_01Abc", "via": "claude-code", "provider": "anthropic", "session": "session_01Abc",
                                "link": "https://claude.ai/code/session_01Abc", "repo": "charredlatte/Some-Repo", "project": "Some-Repo",
                                "branch": "claude/fix-it", "title": "Fix the tests", "model": "claude-opus-5-5", "mood": "busy", "ask": ""})

    def test_a_terminal_session_without_remote_control_has_no_link(self):
        self.hook("UserPromptSubmit", env=self.env(CLAUDE_CODE_REMOTE_SESSION_ID=None, CATIO_URL=self.url + "/mcp/"), prompt="hi")
        args = self.srv.calls[0][1]
        self.assertEqual(args["agent"], "cli-cli-uuid")
        self.assertNotIn("link", args)
        self.assertEqual(self.srv.paths, ["/mcp"])

    def test_a_question_makes_it_meow(self):
        self.hook("Notification", notification_type="permission_prompt", message="Claude needs your permission to use Bash")
        self.assertEqual(self.srv.calls[0][1]["mood"], "needs")
        self.assertEqual(self.srv.calls[0][1]["ask"], "Claude needs your permission to use Bash")
        self.hook("Notification", notification_type="auth_success", message="Signed in")
        self.assertEqual(len(self.srv.calls), 1)

    def test_stop_with_nothing_waiting_just_reports(self):
        r = self.hook("Stop", stop_hook_active=False)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual([(n, a.get("mood"), a.get("mark")) for n, a in self.srv.calls],
                         [("report_status", "review", None), ("inbox", None, True)])

    def test_stop_hands_in_what_she_sent_once(self):
        self.srv.box = {"notes": [{"id": "1", "cat": "session_01Abc", "text": "Push it, please.", "author": "owner", "at": 1}],
                        "request": {"action": "wrap_up", "at": 2},
                        "files": [{"id": "f1", "name": "brief.md", "type": "text/markdown", "size": 12, "note": "the plan", "at": 3}]}
        r = self.hook("Stop", stop_hook_active=False)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("[Catio] Charlotte says: Push it, please.", out["reason"])
        self.assertIn("[Catio] Request: wrap_up", out["reason"])
        self.assertIn("[Catio] Delivery for you: brief.md (text/markdown, 12 bytes). Her note: the plan", out["reason"])
        self.assertIn('report.py" pick f1', out["reason"])
        self.assertIn('report.py" say', out["reason"])
        self.assertEqual(self.srv.calls[-1][1]["mood"], "busy")
        # carrying on from that held stop: report, but never hold it again
        self.srv.calls.clear()
        r = self.hook("Stop", stop_hook_active=True)
        self.assertEqual(r.stdout, "")
        self.assertEqual([n for n, _ in self.srv.calls], ["report_status"])

    def test_stop_hands_in_what_the_queen_says_as_hers(self):
        self.srv.box = {"notes": [{"id": "1", "cat": "session_01Abc", "text": "Prithee, push thy work.", "author": "queen", "at": 1},
                                  {"id": "2", "cat": "session_01Abc", "text": "And then rest.", "author": "owner", "at": 2}],
                        "request": None, "files": []}
        out = json.loads(self.hook("Stop", stop_hook_active=False).stdout)
        self.assertIn("[Catio] The queen says: Prithee, push thy work.", out["reason"])
        self.assertIn("[Catio] Charlotte says: And then rest.", out["reason"])

    def test_session_end_puts_it_to_sleep(self):
        self.hook("SessionEnd", reason="prompt_input_exit")
        self.assertEqual(self.srv.calls[0][1]["mood"], "done")

    def test_a_gateway_that_is_down_or_refuses_never_holds_a_turn(self):
        for env in (self.env(CATIO_URL="http://127.0.0.1:9"), self.env(CATIO_TOKEN="wrong-key-0123456789")):
            started = time.time()
            r = self.hook("Stop", env=env, stop_hook_active=False)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
            self.assertLess(time.time() - started, 5)

    def test_say_answers_on_the_cat(self):
        r = subprocess.run([sys.executable, str(REPORT), "say", "Pushed,", "PR is up."], capture_output=True, text=True, env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.srv.calls, [("comment", {"cat": "session_01Abc", "text": "Pushed, PR is up.", "author": "session"})])

    def test_pick_saves_the_file_outside_the_repo(self):
        self.srv.file = {"name": "../../evil name.md", "type": "text/markdown", "base64": base64.b64encode(b"# hi\n").decode()}
        r = subprocess.run([sys.executable, str(REPORT), "pick", "f1"], capture_output=True, text=True, env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(r.stdout.strip())
        self.assertEqual(path, Path(self.tmp, "catio", "evil_name.md"))
        self.assertEqual(path.read_bytes(), b"# hi\n")
        self.assertEqual(self.srv.calls, [("pick_up", {"id": "f1", "agent": "session_01Abc"})])

    def test_audit_and_map_file_under_this_repository(self):
        r = subprocess.run([sys.executable, str(REPORT), "audit", "delete:", "dead code."], capture_output=True, text=True, env=self.env(), cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        Path(self.repo, "graphify-out").mkdir()
        Path(self.repo, "graphify-out", "catio-graph.json").write_text(json.dumps({"title": "Some-Repo", "hubs": []}))
        r = subprocess.run([sys.executable, str(REPORT), "map"], capture_output=True, text=True, env=self.env(), cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("graphs/some-repo", r.stdout)
        self.assertEqual(self.srv.calls, [
            ("save_report", {"kind": "audit", "repo": "charredlatte/Some-Repo", "summary": "delete: dead code.", "by": "session_01Abc"}),
            ("save_report", {"kind": "map", "repo": "charredlatte/Some-Repo", "map": {"title": "Some-Repo", "hubs": []}, "by": "session_01Abc"})])

    def test_map_says_where_it_looked(self):
        r = subprocess.run([sys.executable, str(REPORT), "map", "nowhere.json"], capture_output=True, text=True, env=self.env(), cwd=self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No project map at nowhere.json", r.stderr)
        self.assertEqual(self.srv.calls, [])

    def test_commands_say_why_without_the_gateway(self):
        r = subprocess.run([sys.executable, str(REPORT), "say", "hi"], capture_output=True, text=True, env=self.env(CATIO_TOKEN=None))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CATIO_URL and CATIO_TOKEN", r.stderr)


if __name__ == "__main__":
    unittest.main()
