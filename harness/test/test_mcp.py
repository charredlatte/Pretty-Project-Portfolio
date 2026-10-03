"""The Catio MCP server over real stdio, and its --serve mode over real HTTP.

    python3 -m unittest discover harness/test
"""
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "mcp" / "catio_mcp.py"


class Stdio(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.p = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                  env=dict(os.environ, CATIO_HOME=self.home))
        self.n = 0

    def tearDown(self):
        self.p.stdin.close(); self.p.wait(5); self.p.stdout.close()

    def rpc(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            self.n += 1; msg["id"] = self.n
        self.p.stdin.write(json.dumps(msg) + "\n"); self.p.stdin.flush()
        return None if notify else json.loads(self.p.stdout.readline())

    def tool(self, tool, **args):
        r = self.rpc("tools/call", {"name": tool, "arguments": args})["result"]
        self.assertFalse(r.get("isError"), r)
        self.assertEqual(json.loads(r["content"][0]["text"]), r["structuredContent"])
        return r["structuredContent"]

    def test_a_whole_visit(self):
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "catio")
        self.rpc("notifications/initialized", notify=True)
        names = {t["name"] for t in self.rpc("tools/list")["result"]["tools"]}
        self.assertEqual(names, {"house_rules", "report_status", "list_agents", "inbox", "pick_up", "drop_file", "comment", "comments", "manage", "quiz", "quizzes", "answer", "decide"})
        self.assertIn("preflight", [r["id"] for r in self.tool("house_rules")["rules"]])

        # an agent joins, with a wake command that records what it was woken with
        woke = Path(self.home, "woke.txt")
        cmd = [sys.executable, "-c", "import sys; open(sys.argv[1], 'a').write(sys.argv[2] + '\\n')", str(woke), "{message}"]
        self.tool("report_status", agent="codex-shop", name="Codex", model="gpt-5", provider="openai", title="Shop theme",
                  repo="charredlatte/montfortoise-shopify", mood="busy", wake=cmd)
        agents = self.tool("list_agents")["agents"]
        self.assertEqual(agents[0]["id"], "codex-shop"); self.assertTrue(agents[0]["wakes"]); self.assertNotIn("wake", agents[0])

        # Charlotte drops a file on it: saved, waiting, and the agent is woken with the delivery
        out = self.tool("drop_file", name="brief.md", type="text/markdown", base64=base64.b64encode(b"# Brief").decode(), note="use this", **{"for": "codex-shop"})
        self.assertTrue(out["woke"])
        box = self.tool("inbox", agent="codex-shop")
        self.assertEqual([f["name"] for f in box["files"]], ["brief.md"])
        got = self.tool("pick_up", id=out["id"])
        self.assertEqual(base64.b64decode(got["base64"]), b"# Brief")
        self.assertEqual(self.tool("inbox", agent="codex-shop")["files"], [])

        # a conversation both ways, and management
        self.tool("comment", cat="codex-shop", text="How's the theme?")
        self.assertEqual(len(self.tool("inbox", agent="codex-shop")["notes"]), 1)
        self.tool("comment", cat="codex-shop", text="Nearly done", author="agent")
        self.assertEqual(self.tool("inbox", agent="codex-shop")["notes"], [])
        self.assertEqual([n["author"] for n in self.tool("comments", cat="codex-shop")["notes"]], ["owner", "agent"])
        self.tool("manage", cat="codex-shop", action="pause")
        self.assertEqual(self.tool("inbox", agent="codex-shop")["request"]["action"], "pause")

        # with mark, each thing waiting is handed over once (the gateway's session hooks rely on it)
        time.sleep(0.01)   # notes are stamped to the millisecond here
        self.tool("comment", cat="codex-shop", text="One more thing.")
        self.tool("drop_file", name="b.md", base64=base64.b64encode(b"b").decode(), **{"for": "codex-shop"})
        handed = self.tool("inbox", agent="codex-shop", mark=True)
        self.assertEqual((len(handed["files"]), [n["text"] for n in handed["notes"]], handed["request"]["action"]),
                         (1, ["One more thing."], "pause"))
        self.assertEqual(self.tool("inbox", agent="codex-shop", mark=True), {"files": [], "notes": [], "request": None})
        self.assertEqual(len(self.tool("inbox", agent="codex-shop")["files"]), 1)   # still waiting until picked up
        # what she writes while the agent is answering still gets handed in
        self.tool("comment", cat="codex-shop", text="Wait, one more.")
        time.sleep(0.01)
        self.tool("comment", cat="codex-shop", text="Pushed.", author="agent")
        self.assertEqual([n["text"] for n in self.tool("inbox", agent="codex-shop", mark=True)["notes"]], ["Wait, one more."])
        # homework: the queen sets a quiz for the cat; her answers reach it as her words, and the queen is told
        z = self.tool("quiz", title="The theme", questions=[{"q": "Ship it?", "options": ["Yes", "Not yet"]}, {"q": "A word for the cat?", "free": True}], **{"for": "codex-shop"})
        self.assertEqual([(q["title"], q["status"], q["by"]) for q in self.tool("quizzes")["quizzes"]], [("The theme", "set", "queen")])
        time.sleep(0.01)
        self.assertEqual(self.tool("answer", quiz=z["id"], answers=["Yes", "Good work"]), {"ok": True, "told": True})
        self.assertEqual(self.tool("quizzes")["quizzes"], [])
        handed = self.tool("inbox", agent="codex-shop", mark=True)["notes"]
        self.assertEqual(handed[-1]["text"], "Homework handed in: The theme\n1. Ship it? \u2192 Yes\n2. A word for the cat? \u2192 Good work")
        self.assertIn("(for codex-shop, told)", self.tool("comments", cat="queen")["notes"][-1]["text"])
        self.tool("manage", cat="codex-shop", action="rename", value="Biscotte")
        self.tool("manage", cat="codex-shop", action="archive")
        self.assertEqual(self.tool("list_agents")["agents"], [])
        self.assertEqual(self.tool("list_agents", archived=True)["agents"][0]["name"], "Biscotte")

        time.sleep(0.5)
        lines = woke.read_text().splitlines()
        self.assertTrue(any(l.startswith("[Catio] Delivery for you: brief.md") for l in lines), lines)
        self.assertIn("[Catio] Charlotte says: How's the theme?", lines)
        self.assertIn("[Catio] Request: pause", lines)

    def test_renames_the_owners_old_notes(self):
        # notes written before accounts said "charlotte": they read as the owner's, and the old name is still taken on write
        Path(self.home, "state.json").write_text(json.dumps({"agents": {}, "files": [], "notes": [
            {"id": "1", "cat": "codex-shop", "author": "charlotte", "text": "Old note.", "at": 1}]}), encoding="utf-8")
        self.assertEqual([n["author"] for n in self.tool("comments", cat="codex-shop")["notes"]], ["owner"])
        self.tool("comment", cat="codex-shop", text="Still me.", author="charlotte")
        self.assertEqual([n["author"] for n in self.tool("comments", cat="codex-shop")["notes"]], ["owner", "owner"])

    def test_decide_refuses_without_a_decider(self):
        r = self.rpc("tools/call", {"name": "decide", "arguments": {"state": "run the tests", "preset": "easy"}})["result"]
        self.assertTrue(r.get("isError")); self.assertIn("CATIO_DECIDE_URL", r["content"][0]["text"])
        r = self.rpc("tools/call", {"name": "decide", "arguments": {"state": "x", "questions": {"q": {"type": "guess"}}}})["result"]
        self.assertTrue(r.get("isError")); self.assertIn("noul, choice or score", r["content"][0]["text"])

    def test_errors_are_tool_errors(self):
        self.rpc("initialize", {})
        r = self.rpc("tools/call", {"name": "report_status", "arguments": {"agent": "x", "mood": "grumpy"}})["result"]
        self.assertTrue(r["isError"])
        r = self.rpc("tools/call", {"name": "report_status", "arguments": {"agent": "x", "wake": "rm -rf /"}})["result"]
        self.assertTrue(r["isError"])
        self.assertIn("error", self.rpc("tools/call", {"name": "nope", "arguments": {}}))
        self.assertIn("error", self.rpc("resources/list"))


class Serve(unittest.TestCase):
    def test_serves_the_folder_and_the_api(self):
        home, folder = tempfile.mkdtemp(), tempfile.mkdtemp()
        Path(folder, "index.html").write_text("<p>catio</p>")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
        p = subprocess.Popen([sys.executable, str(SERVER), "--serve", folder, "--port", str(port)], stdout=subprocess.PIPE,
                             env=dict(os.environ, CATIO_HOME=home))
        try:
            p.stdout.readline()
            base = "http://127.0.0.1:%d" % port
            self.assertEqual(urllib.request.urlopen(base + "/index.html").read(), b"<p>catio</p>")
            post = lambda path, body, **h: urllib.request.urlopen(urllib.request.Request(
                base + path, json.dumps(body).encode(), {"Content-Type": "application/json", **h}))
            post("/api/report_status", {"agent": "gem", "provider": "google", "mood": "needs", "ask": "Which colour?"})
            agents = json.loads(post("/api/list_agents", {}).read())["agents"]
            self.assertEqual((agents[0]["id"], agents[0]["mood"]), ("gem", "needs"))
            # another site can't talk to a cat: not cross-origin, not by GET (an <img> sends no Origin), not by
            # DNS rebinding (its own name for 127.0.0.1, so Origin and Host agree)
            for path, body, h in (("/api/comment", {"cat": "gem", "text": "hi"}, {"Origin": "http://evil.example"}),
                                  ("/api/comment", {"cat": "gem", "text": "hi"},
                                   {"Origin": "http://evil.example:%d" % port, "Host": "evil.example:%d" % port})):
                with self.assertRaises(urllib.error.HTTPError) as e:
                    post(path, body, **h)
                self.assertEqual(e.exception.code, 403)
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(base + "/api/comment?cat=gem&text=hi")
            self.assertEqual(e.exception.code, 404)
            self.assertEqual(json.loads(post("/api/comments", {"cat": "gem"}).read())["notes"], [])
        finally:
            p.terminate(); p.wait(5); p.stdout.close()


if __name__ == "__main__":
    unittest.main()


class Decider(unittest.TestCase):
    """decide against a stand-in System One server (the shape laya-serve, Clef and Jev share): the request it gets,
    the answers it returns, and the log of decisions beside what the old path chose."""

    def setUp(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading
        seen = self.seen = []

        class One(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append((self.path, self.headers.get("Authorization"), body))
                answers = {}
                for name, q in body["questions"].items():
                    if q["type"] == "noul": answers[name] = {"type": "noul", "noul": 0.9 if name != "held_path" else 0.1}
                    elif q["type"] == "choice":
                        first = next(iter(q["criteria"]))
                        answers[name] = {"type": "choice", "choice": first, "confidence": 0.8, "probabilities": {k: (0.8 if k == first else 0.2 / max(1, len(q["criteria"]) - 1)) for k in q["criteria"]}}
                    else: answers[name] = {"type": "score", "score": 1.0, "confidence": 0.7, "probabilities": {"0": 0.1, "1": 0.9}}
                data = json.dumps({"model": "stand-in", "answers": answers, "usage": {"input_tokens": 42}}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        self.srv = HTTPServer(("127.0.0.1", 0), One)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.home = tempfile.mkdtemp()
        self.p = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                  env=dict(os.environ, CATIO_HOME=self.home, CATIO_DECIDE_URL="http://127.0.0.1:%d/" % self.srv.server_port, CATIO_DECIDE_KEY="k1"))
        self.n = 0

    def tearDown(self):
        self.p.stdin.close(); self.p.wait(5); self.p.stdout.close(); self.srv.shutdown()

    def tool(self, tool, **args):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": "tools/call", "params": {"name": tool, "arguments": args}}) + "\n"); self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())["result"]
        return r["content"][0]["text"] if r.get("isError") else r["structuredContent"]

    def test_asks_logs_and_compares(self):
        out = self.tool("decide", state={"file": "notes.md", "cats": ["shop", "catio"]}, kind="sort", old="catio",
                        questions={"cat": {"type": "choice", "instructions": "Which cat?", "criteria": {"shop": "the shop", "catio": "the café"}}})
        self.assertEqual(out["answers"]["cat"]["choice"], "shop"); self.assertEqual(out["model"], "stand-in")
        path, auth, body = self.seen[0]
        self.assertEqual(path, "/v1/systemone"); self.assertEqual(auth, "Bearer k1")
        self.assertEqual(body["state"], {"file": "notes.md", "cats": ["shop", "catio"]}); self.assertEqual(body["questions"]["cat"]["criteria"]["catio"], "the café")
        easy = self.tool("decide", state="Add a test for parse_time in utils.py", preset="easy")
        self.assertEqual(set(easy["answers"]), {"spelled_out", "checkable", "small", "held_path", "private", "browser"})
        self.assertEqual(self.seen[1][2]["questions"]["held_path"]["type"], "noul")
        log = json.loads(Path(self.home, "state.json").read_text())["decisions"]
        self.assertEqual(len(log), 1)   # the easy call had no kind: not logged
        self.assertEqual((log[0]["kind"], log[0]["old"], log[0]["agree"]), ("sort", "catio", False))
