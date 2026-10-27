"""The queen's runner (harness/runner/queen.py) against a stand-in gateway and a fake claude on the PATH: it relays a
turn as it streams, keeps her session, runs a routine, strips CATIO_* from the turn, and a Stop ends a turn in
progress (SIGINT here; Ctrl+Break on Windows can't be sent from this test). And against a stand-in OpenAI-compatible
model (CATIO_MODEL_URL) with no claude anywhere: a turn streamed, a tool called through the gateway's /mcp, her
conversation kept in messages.json, a Stop mid-stream, and a model that refuses or isn't there.

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
MODEL_KEY = "sk-model-key"
TOOLS = [{"name": "list_agents", "description": "Every cat.", "inputSchema": {"type": "object", "properties": {"archived": {"type": "boolean"}}}},
         {"name": "comments", "description": "A cat's conversation.", "inputSchema": {"type": "object", "properties": {"cat": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["cat"]}}]
ANSWER = ["Good ", "morrow, ", "my ", "lady. ", "Two ", "cats ", "need ", "thee."]
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
            s.waits.append(body)
            if s.refuse:   # a status to answer with before it answers properly
                self.send_response(s.refuse.pop(0)); self.end_headers(); return
            if s.garble:   # a reply that is cut off (it promises more than it sends) or isn't an object
                data, promised = s.garble.pop(0)
                self.send_response(200); self.send_header("Content-Length", str(promised)); self.end_headers()
                self.wfile.write(data); self.wfile.flush(); return
            try:
                out = dict(EMPTY, **s.jobs.get(timeout=0.3))
            except queue.Empty:
                out = dict(EMPTY)
            out["character"] = s.character
            out["homework"] = dict(s.homework)
        elif self.path == "/api/runner/say":
            s.says.append(body); out = {"ok": True, "id": None}
        elif self.path == "/mcp":   # the Catio's tools, as the queen's model is handed them
            method, params, rid = body.get("method"), body.get("params") or {}, body.get("id")
            if method == "tools/list":
                out = {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
            elif method == "tools/call":
                s.calls.append(params)
                got = {"notes": [{"author": "owner", "text": "Praline, are you there?"}]}
                out = {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(got)}], "structuredContent": got}}
            else:
                out = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found: %s" % method}}
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


class Model(BaseHTTPRequestHandler):
    """An OpenAI-compatible server, as the runner's ModelDriver sees it: POST /v1/chat/completions, streamed as
    server-sent events, scripted by the last thing Charlotte said. "look in" asks for a tool first (the call's
    arguments arrive in fragments, as OpenAI sends them), "slowly" goes on and on (for a Stop), anything else
    is her answer, word by word. Every request is recorded."""
    def log_message(self, *a):
        pass

    def chunk(self, delta, finish=None):
        c = {"id": "chatcmpl-1", "object": "chat.completion.chunk", "model": "fake", "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        self.wfile.write(("data: " + json.dumps(c) + "\n\n").encode()); self.wfile.flush()

    def do_POST(self):
        s = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        s.asks.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if self.path != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return
        if self.headers.get("Authorization") != "Bearer " + MODEL_KEY:
            self.send_response(401); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"error": {"message": "Incorrect API key provided"}}'); return
        msgs = body.get("messages") or []
        asked = next((m.get("content") or "" for m in reversed(msgs) if m.get("role") == "user"), "").lower()
        answered_tool = any(m.get("role") == "tool" for m in msgs)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            self.chunk({"role": "assistant", "content": ""})
            if "look in" in asked and not answered_tool:   # she reaches for a tool before she answers
                self.chunk({"tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": "comments", "arguments": ""}}]})
                self.chunk({"tool_calls": [{"index": 0, "function": {"arguments": '{"cat": "cse'}}]})
                self.chunk({"tool_calls": [{"index": 0, "function": {"arguments": '_1", "limit": 5}'}}]})
                self.chunk({}, "tool_calls")
            else:
                slow = "slowly" in asked
                for w in ANSWER[:4] + (["(and on) "] * 40 if slow else ANSWER[4:]):
                    self.chunk({"content": w})
                    time.sleep(0.25 if slow else 0.01)
                self.chunk({}, "stop")
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):   # the runner closed it: a Stop
            s.cut.append(True)


class Queen(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.srv.jobs, self.srv.says, self.srv.waits, self.srv.refuse, self.srv.garble, self.srv.calls = queue.Queue(), [], [], [], [], []
        self.model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
        self.model.asks, self.model.cut = [], []
        threading.Thread(target=self.model.serve_forever, daemon=True).start()
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
        self.model.shutdown()
        self.model.server_close()

    def start(self, model=False, **more):
        """With model, the runner thinks with the stand-in model (CATIO_MODEL_URL) and has no claude on its PATH at all."""
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CATIO_", "CLAUDE_CODE_"))}
        env.update(CATIO_URL="http://127.0.0.1:%d" % self.srv.server_address[1], CATIO_QUEEN=KEY, CATIO_QUEEN_DIR=str(self.home),
                   CATIO_TOKEN="the-agents-key-never-passed-on", FAKE_CLAUDE_LOG=str(self.log),
                   CATIO_NOTIFY=str(self.notifier), FAKE_NOTIFY_LOG=str(self.toasts),
                   PATH=str(self.tmp / "bin") + os.pathsep + env.get("PATH", ""),
                   NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
        if model:
            env.update(CATIO_MODEL_URL="http://127.0.0.1:%d/v1" % self.model.server_address[1], CATIO_MODEL_KEY=MODEL_KEY, CATIO_MODEL="llama3.1",
                       PATH=str(self.tmp / "no-bin"), CATIO_CLAUDE="no-such-claude-here")
        env.update(more)
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
        if not self.log.exists():
            return []
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

    def test_says_which_notes_she_has_been_given_on_her_next_wait(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "First.", "at": 5}, {"id": "n2", "cat": "queen", "author": "owner", "text": "Second.", "at": 9}]})
        self.start()
        self.said(2)
        end = time.time() + 10
        while time.time() < end and not any(w.get("ack") == 9 for w in self.srv.waits):
            time.sleep(0.05)
        acks = [w.get("ack") for w in self.srv.waits]
        self.assertEqual(acks[0], 0, "the first wait has been given nothing yet")
        self.assertIn(9, acks, "a later wait names the newest note she was given")
        self.assertEqual(acks, sorted(acks), "and never goes back")

    def test_a_503_is_a_blip_she_waits_out_but_a_401_is_the_end(self):
        self.srv.refuse.append(503)
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Hello?", "at": 1}]})
        self.start()
        self.said(1, timeout=25)
        self.assertIsNone(self.proc.poll(), "she is still running after a 503")
        self.assertIn("the gateway answered 503", (self.tmp / "runner.log").read_text())
        self.srv.refuse.append(401)
        self.assertEqual(self.proc.wait(30), 2, "a refused key stops her, so it is seen")

    def test_a_reply_cut_off_or_not_an_object_doesnt_leave_her_deaf(self):
        self.srv.garble += [(b'{"notes": [{"id": "n0"', 100), (b"[1]", 3)]
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Still there?", "at": 1}]})
        self.start()
        self.said(1, timeout=45)
        self.assertIsNone(self.proc.poll())
        log = (self.tmp / "runner.log").read_text()
        self.assertIn("no gateway:", log)
        self.assertIn("isn't an object", log)

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

    # ---- a model of her own: CATIO_MODEL_URL, with no claude anywhere ----

    def model_asks(self):
        return [a["body"] for a in self.model.asks if a["path"] == "/v1/chat/completions"]

    def test_a_model_relays_a_turn_as_it_streams_and_keeps_her_conversation(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Who needs me today?", "at": 1}]})
        self.start(model=True)
        says = self.said()
        self.assertEqual(says[-1]["text"], "Good morrow, my lady. Two cats need thee.")
        self.assertEqual((says[0]["text"], says[0]["done"]), ("", False), "she is up before her first word")
        partial = [s for s in says if not s["done"] and s["text"]]
        self.assertTrue(partial, "nothing streamed before the end")
        self.assertTrue("Good morrow, my lady. Two cats need thee.".startswith(partial[-1]["text"]))
        self.assertEqual(self.claude_calls(), [], "claude was never run")
        ask, = self.model_asks()
        self.assertEqual(self.model.asks[0]["auth"], "Bearer " + MODEL_KEY)
        self.assertEqual(ask["model"], "llama3.1")
        self.assertTrue(ask["stream"])
        self.assertEqual([t["function"]["name"] for t in ask["tools"]], ["list_agents", "comments"])
        self.assertEqual(ask["tools"][1]["function"]["parameters"], TOOLS[1]["inputSchema"])
        self.assertEqual(ask["messages"][0]["role"], "system")
        for words in ("queen of the house", "Thy name is Duchesse.", "Elizabethan English, warm."):
            self.assertIn(words, ask["messages"][0]["content"])
        self.assertEqual(ask["messages"][-1], {"role": "user", "content": "[Catio] Charlotte says: Who needs me today?"})
        kept = json.loads((self.home / "messages.json").read_text(encoding="utf-8"))
        self.assertEqual([m["role"] for m in kept], ["user", "assistant"])
        self.assertNotIn("system", [m["role"] for m in kept], "her character is never stored: it is rebuilt each turn")
        # the next turn carries the conversation on
        self.srv.jobs.put({"notes": [{"id": "n2", "cat": "queen", "author": "owner", "text": "And the shop?", "at": 2}]})
        self.said(2)
        second = self.model_asks()[-1]
        self.assertEqual([(m["role"], m["content"]) for m in second["messages"][1:]],
                         [("user", "[Catio] Charlotte says: Who needs me today?"), ("assistant", "Good morrow, my lady. Two cats need thee."),
                          ("user", "[Catio] Charlotte says: And the shop?")])

    def test_a_model_reaches_for_a_tool_through_the_gateway_and_the_cafe_is_told(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Look in on Praline.", "at": 1}]})
        self.start(model=True)
        says = self.said()
        self.assertEqual(says[-1]["text"], "Good morrow, my lady. Two cats need thee.")
        self.assertEqual(self.srv.calls, [{"name": "comments", "arguments": {"cat": "cse_1", "limit": 5}}], "the call reached /mcp, with the queen's key")
        tool = [s for s in says if s.get("steps")]
        self.assertTrue(tool, "no step told: %r" % says)
        self.assertEqual(tool[0]["steps"], [{"tool": "comments", "cat": "cse_1"}])
        self.assertNotIn("steps", says[-1])
        first, second = self.model_asks()
        asked = second["messages"][-2]
        self.assertEqual(asked["role"], "assistant")
        self.assertEqual(asked["tool_calls"][0]["id"], "call_1")
        self.assertEqual(json.loads(asked["tool_calls"][0]["function"]["arguments"]), {"cat": "cse_1", "limit": 5}, "the fragments were put together")
        answered = second["messages"][-1]
        self.assertEqual((answered["role"], answered["tool_call_id"]), ("tool", "call_1"))
        self.assertIn("Praline, are you there?", answered["content"])
        kept = json.loads((self.home / "messages.json").read_text(encoding="utf-8"))
        self.assertEqual([m["role"] for m in kept], ["user", "assistant", "tool", "assistant"], "the call and its answer are remembered together")

    def test_a_stop_ends_a_model_turn_and_keeps_what_she_said(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Tell me slowly.", "at": 1}]})
        self.start(model=True)
        end = time.time() + 15
        while time.time() < end and not any(s["text"].startswith("Good morrow, my lady.") for s in self.srv.says):
            time.sleep(0.05)
        self.assertTrue(self.srv.says, "nothing streamed")
        self.srv.jobs.put({"stop": True})
        says = self.said()
        self.assertTrue(says[-1]["text"].startswith("Good morrow, my lady."), says[-1]["text"])
        self.assertLess(len(says[-1]["text"]), len("Good morrow, my lady. " + "(and on) " * 40), "it stopped before the end")
        kept = json.loads((self.home / "messages.json").read_text(encoding="utf-8"))
        self.assertEqual(kept[-1]["role"], "assistant")
        self.assertTrue(kept[-1]["content"].startswith("Good morrow, my lady."), "what she had said is remembered")
        # and she goes on with the next thing
        self.srv.jobs.put({"notes": [{"id": "n2", "cat": "queen", "author": "owner", "text": "Thank you.", "at": 2}]})
        self.assertEqual(self.said(2)[-1]["text"], "Good morrow, my lady. Two cats need thee.")

    def test_a_model_that_refuses_or_isnt_there_is_said_and_she_stays_up(self):
        self.srv.jobs.put({"notes": [{"id": "n1", "cat": "queen", "author": "owner", "text": "Hello?", "at": 1}]})
        self.start(model=True, CATIO_MODEL_KEY="the-wrong-key", CATIO_MODEL="")
        says = self.said()
        self.assertTrue(says[-1]["text"].startswith("Forgive me, my lady"), says[-1]["text"])
        self.assertIn("401", says[-1]["text"])
        self.assertIn("CATIO_MODEL_KEY", says[-1]["text"])
        self.assertIsNone(self.proc.poll(), "the model is replaceable: she stays up")
        self.assertNotIn("model", self.model_asks()[0], "CATIO_MODEL unset: no model named, for a server that serves one")
        self.proc.terminate(); self.proc.wait(5); self.out.close()
        time.sleep(0.5)   # a wait of the stopped runner's may still be at the gateway: let it come back empty
        self.srv.says.clear()
        self.srv.jobs.put({"notes": [{"id": "n2", "cat": "queen", "author": "owner", "text": "Anyone?", "at": 2}]})
        self.start(model=True, CATIO_MODEL_URL="http://127.0.0.1:9/v1")
        says = self.said()
        self.assertTrue(says[-1]["text"].startswith("Forgive me, my lady"), says[-1]["text"])
        self.assertIn("no model", says[-1]["text"])
        self.assertIsNone(self.proc.poll())

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
