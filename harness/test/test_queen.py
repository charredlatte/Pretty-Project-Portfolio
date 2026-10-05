"""The queen's runner (harness/runner/queen.py) against a stand-in gateway and a fake claude on the PATH: it relays a
turn as it streams, keeps her session, runs a routine, strips CATIO_* from the turn, and a Stop ends a turn in
progress (SIGINT here; Ctrl+Break on Windows can't be sent from this test).

    python3 -m unittest discover -s harness/test
"""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "runner" / "queen.py"
KEY = "queen-key-0123456789abcdef"
EMPTY = {"notes": [], "routine": None, "stop": False}

# claude, as the runner sees it: prints stream-json, records what it was given, and stops on SIGINT
FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, signal, sys, time
log = open(os.environ["FAKE_CLAUDE_LOG"], "a")
note = lambda o: (log.write(json.dumps(o) + "\n"), log.flush())
out = lambda o: print(json.dumps(o), flush=True)
prompt = sys.stdin.read()
argv = sys.argv[1:]
note({"argv": argv, "stdin": prompt, "env": {k: v for k, v in os.environ.items() if k.startswith("CATIO_")}, "cwd": os.getcwd(),
      "prompt_file": open(argv[argv.index("--append-system-prompt-file") + 1], encoding="utf-8").read(),
      "mcp": json.load(open(argv[argv.index("--mcp-config") + 1]))})
if "--resume" in argv and argv[argv.index("--resume") + 1] == "s-gone":
    sys.stderr.write("No conversation found with session ID: s-gone\n"); sys.exit(1)
sid = argv[argv.index("--resume") + 1] if "--resume" in argv else "s-" + str(int(time.time() * 1000))
out({"type": "system", "subtype": "init", "session_id": sid})
stopped = []
signal.signal(signal.SIGINT, lambda *a: stopped.append(1))
if "look in" in prompt.lower():   # she reaches for a tool before she answers
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__catio__comments", "input": {"cat": "cse_1", "limit": 5}}]}})
slow = "slowly" in prompt
words = ["Good ", "morrow, ", "my ", "lady. "] + (["(and on) "] * 40 if slow else ["Two ", "cats ", "need ", "thee."])
out({"type": "stream_event", "event": {"type": "message_start"}})
for w in words:
    if stopped:
        note({"stopped": True}); sys.exit(130)
    out({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": w}}})
    time.sleep(0.25 if slow else 0.01)
text = "".join(words)
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "subtype": "success", "result": text, "session_id": sid})
'''


class Gateway(BaseHTTPRequestHandler):
    """The runner's two routes: wait hands out what the test queued (else comes back empty), say is recorded."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        s = self.server
        if self.headers.get("User-Agent", "").startswith("Python-urllib"):   # Cloudflare's bot check: error 1010
            self.send_response(403); self.end_headers(); return
        if self.headers.get("Authorization") != "Bearer " + KEY:
            self.send_response(401); self.end_headers(); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/runner/wait":
            try:
                out = dict(EMPTY, **s.jobs.get(timeout=0.3))
            except queue.Empty:
                out = dict(EMPTY)
            out["character"] = s.character
            out["homework"] = dict(s.homework)
        elif self.path == "/api/runner/say":
            s.says.append(body); out = {"ok": True, "id": None}
        else:
            self.send_response(404); self.end_headers(); return
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:   # the runner was stopped mid-wait
            pass


class Queen(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.srv.jobs, self.srv.says = queue.Queue(), []
        self.srv.character = {"name": "Duchesse", "manner": "Elizabethan English, warm.", "greeting": "Good morrow."}
        self.srv.homework = {}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "queen"
        fake = self.tmp / "bin" / "claude"
        fake.parent.mkdir()
        fake.write_text(FAKE_CLAUDE.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1), encoding="utf-8")
        fake.chmod(0o755)
        if os.name == "nt":
            # Windows has no shebang and ignores chmod, and shutil.which only matches names in
            # PATHEXT, so the extensionless stub above is invisible to the runner: it would find a
            # real claude on the PATH instead and the test would measure that.
            (fake.parent / "claude.cmd").write_text(f'@"{sys.executable}" "{fake}" %*\n', encoding="utf-8")
        self.log = self.tmp / "claude.log"
        self.toasts = self.tmp / "toasts.log"
        tell = self.tmp / "bin" / "notify"
        tell.write_text("#!%s\nimport os, sys\n"
                        "open(os.environ['FAKE_NOTIFY_LOG'], 'a').write(sys.argv[1] + '\\n')\n" % sys.executable,
                        encoding="utf-8")
        tell.chmod(0o755)
        self.notifier = tell
        if os.name == "nt":   # as for claude above: no shebang, so the runner must be given a .cmd to run
            (tell.parent / "notify.cmd").write_text(f'@"{sys.executable}" "{tell}" %*\n', encoding="utf-8")
            self.notifier = tell.parent / "notify.cmd"
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(5)
        if self.proc:
            self.out.close()
        self.srv.shutdown()
        self.srv.server_close()

    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CATIO_", "CLAUDE_CODE_"))}
        env.update(CATIO_URL="http://127.0.0.1:%d" % self.srv.server_address[1], CATIO_QUEEN=KEY, CATIO_QUEEN_DIR=str(self.home),
                   CATIO_TOKEN="the-agents-key-never-passed-on", FAKE_CLAUDE_LOG=str(self.log),
                   CATIO_NOTIFY=str(self.notifier), FAKE_NOTIFY_LOG=str(self.toasts),
                   PATH=str(self.tmp / "bin") + os.pathsep + env.get("PATH", ""),
                   NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
        self.out = open(self.tmp / "runner.log", "w")
        self.proc = subprocess.Popen([sys.executable, str(RUNNER)], env=env, stdout=self.out, stderr=subprocess.STDOUT)

    def said(self, n=1, timeout=20):
        """Wait until the runner has said n finished turns; returns every say so far."""
        end = time.time() + timeout
        while time.time() < end:
            if sum(1 for s in self.srv.says if s.get("done")) >= n:
                return list(self.srv.says)
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        self.out.flush()
        self.fail("the runner didn't finish %d turn(s):\n%s" % (n, (self.tmp / "runner.log").read_text()))

    def claude_calls(self):
        return [json.loads(l) for l in self.log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def toasted(self, n, timeout=10):
        """Wait until n notifications have reached her desktop; returns all of them."""
        end = time.time() + timeout
        while time.time() < end:
            lines = [l for l in self.toasts.read_text(encoding="utf-8").splitlines() if l.strip()] if self.toasts.exists() else []
            if len(lines) >= n:
                return lines
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        self.fail("her desktop was told %d time(s), not %d" % (len(lines), n))

    def quiet(self, seconds=1.5):
        """Nothing reached her desktop in that time."""
        time.sleep(seconds)
        lines = [l for l in self.toasts.read_text(encoding="utf-8").splitlines() if l.strip()] if self.toasts.exists() else []
        self.assertEqual(lines, [], "her desktop was told something it shouldn't have been")

    def test_says_homework_on_her_desktop_only_when_it_grows(self):
        """Her quest log is in the café; the runner is the part of the café that is always running. What is already
        waiting when it starts is hers to find in the café: only a card that lands while it runs is worth saying."""
        self.srv.homework = {"litterbox": 1}
        self.start()
        self.quiet()                                   # the count it starts on is remembered, never announced
        self.srv.homework = {"litterbox": 2, "decision": 1}
        self.assertEqual(self.toasted(1), ["2 notes to sort, 1 decision waiting in the cafe"])
        self.srv.homework = {"litterbox": 2, "decision": 1}
        time.sleep(1.5)
        self.assertEqual(len(self.toasted(1)), 1, "the same count said twice")
        self.srv.homework = {"litterbox": 1}           # she sorted one: fewer is not news
        time.sleep(1.5)
        self.assertEqual(len(self.toasted(1)), 1, "homework going down was announced")
        self.srv.homework = {"unblock": 1, "litterbox": 1}
        self.assertEqual(self.toasted(2)[-1], "1 quiz to hand in, 1 note to sort waiting in the cafe")

    def test_a_kind_nobody_gave_words_to_is_never_said(self):
        """A quiz document's own text must not reach a notification: macOS and Windows take it inside a quoted
        string. Only the kinds with words in HOMEWORK are counted at all."""
        self.srv.homework = {}
        self.start()
        self.quiet(1.0)
        self.srv.homework = {"\"; rm -rf /": 3}
        self.quiet()

    def test_relays_a_turn_as_it_streams_and_keeps_her_session(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Who needs me today?", "at": 1}]})
        self.start()
        says = self.said()
        self.assertEqual(says[-1]["done"], True)
        self.assertEqual(says[-1]["text"], "Good morrow, my lady. Two cats need thee.")
        self.assertNotIn("routine", says[-1])
        partial = [s for s in says if not s["done"]]
        self.assertTrue(partial, "nothing streamed before the end")
        self.assertTrue(all(s["turn"] == says[-1]["turn"] for s in says))
        self.assertTrue("Good morrow, my lady. Two cats need thee.".startswith(partial[-1]["text"]))
        call, = [c for c in self.claude_calls() if "argv" in c]
        self.assertEqual(call["stdin"], "[Catio] Charlotte says: Who needs me today?")
        for flag in ("-p", "--output-format", "--include-partial-messages", "--restricted", "--strict-mcp-config", "--permission-prompts", "--max-turns"):
            self.assertIn(flag, call["argv"])
        self.assertEqual(call["argv"][call["argv"].index("--allowedTools") + 1], "mcp__catio")
        self.assertNotIn("--resume", call["argv"])
        self.assertIn("queen of the house", call["prompt_file"])
        self.assertIn("Thy name is Duchesse.", call["prompt_file"])
        self.assertIn("Elizabethan English, warm.", call["prompt_file"])
        self.assertEqual(call["mcp"]["mcpServers"]["catio"]["headers"]["Authorization"], "Bearer " + KEY)
        self.assertTrue(call["mcp"]["mcpServers"]["catio"]["url"].endswith("/mcp"))
        self.assertEqual(call["env"], {}, "CATIO_* must not reach the turn")
        self.assertEqual(Path(call["cwd"]), self.home)
        state = json.loads((self.home / "state.json").read_text())
        self.assertTrue(state["session"].startswith("s-"))
        # the next turn carries the conversation on
        self.srv.jobs.put({"notes": [{"id": "n2", "cat": "queen", "author": "owner", "text": "And the shop?", "at": 2}]})
        self.said(2)
        second = [c for c in self.claude_calls() if "argv" in c][-1]
        self.assertEqual(second["argv"][second["argv"].index("--resume") + 1], state["session"])

    def test_runs_a_routine_and_starts_afresh_when_her_session_is_gone(self):
        self.home.mkdir(parents=True)
        (self.home / "state.json").write_text(json.dumps({"session": "s-gone"}))
        self.srv.jobs.put({"routine": {"id": "round", "name": "Morning round", "prompt": "Who needs me?", "at": 1}})
        self.start()
        says = self.said()
        self.assertEqual(says[-1]["routine"], {"id": "round", "name": "Morning round"})
        self.assertEqual(says[-1]["text"], "Good morrow, my lady. Two cats need thee.")
        calls = [c for c in self.claude_calls() if "argv" in c]
        self.assertEqual(len(calls), 2, "the gone session is tried once, then a new one starts")
        self.assertEqual(calls[0]["argv"][calls[0]["argv"].index("--resume") + 1], "s-gone")
        self.assertNotIn("--resume", calls[1]["argv"])
        self.assertEqual(calls[1]["stdin"], '[Catio] Routine "Morning round": Who needs me?')
        self.assertNotEqual(json.loads((self.home / "state.json").read_text())["session"], "s-gone")

    def test_tells_the_cafe_she_is_up_and_each_tool_she_reaches_for(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Look in on Praline.", "at": 1}]})
        self.start()
        says = self.said()
        self.assertEqual((says[0]["text"], says[0]["done"], says[0]["steps"]), ("", False, []), "she said nothing was afoot before her first word")
        tool = [s for s in says if s.get("steps")]
        self.assertTrue(tool, "no step told: %r" % says)
        self.assertEqual(tool[0]["steps"], [{"tool": "comments", "cat": "cse_1"}])
        self.assertNotIn("steps", says[-1], "a finished turn has no steps to show")
        self.assertEqual(says[-1]["text"], "Good morrow, my lady. Two cats need thee.")

    @unittest.skipIf(os.name == "nt", "Ctrl+Break can't be sent from this test, as the module docstring says; "
                                      "queen.py does send it on Windows (runner/queen.py, stop)")
    def test_a_stop_ends_the_turn_in_progress_and_keeps_what_she_said(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Tell me slowly.", "at": 1}]})
        self.start()
        end = time.time() + 15
        while time.time() < end and not any(s["text"].startswith("Good morrow, my lady.") for s in self.srv.says):
            time.sleep(0.05)
        self.assertTrue(self.srv.says, "nothing streamed")
        self.srv.jobs.put({"stop": True})
        says = self.said()
        self.assertTrue(says[-1]["text"].startswith("Good morrow, my lady."), says[-1]["text"])
        self.assertLess(len(says[-1]["text"]), len("Good morrow, my lady. " + "(and on) " * 40), "it stopped before the end")
        self.assertIn({"stopped": True}, self.claude_calls())
        # and she goes on with the next thing
        self.srv.jobs.put({"notes": [{"id": "n2", "cat": "queen", "author": "owner", "text": "Thank you.", "at": 2}]})
        self.assertEqual(self.said(2)[-1]["text"], "Good morrow, my lady. Two cats need thee.")

    def test_says_why_without_the_gateway_or_claude(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("CATIO_")}
        r = subprocess.run([sys.executable, str(RUNNER)], env=env, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CATIO_URL", r.stderr)
        env.update(CATIO_URL="http://127.0.0.1:9", CATIO_QUEEN=KEY, CATIO_CLAUDE="no-such-claude-here")
        r = subprocess.run([sys.executable, str(RUNNER)], env=env, capture_output=True, text=True, timeout=20)
        self.assertIn("claude isn't on the PATH", r.stderr)


if __name__ == "__main__":
    unittest.main()
