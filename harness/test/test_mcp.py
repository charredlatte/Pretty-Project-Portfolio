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
        self.assertEqual(names, {"house_rules", "report_status", "list_agents", "inbox", "pick_up", "drop_file", "comment", "comments", "manage", "quiz", "quizzes", "answer"})
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
        self.assertEqual([n["author"] for n in self.tool("comments", cat="codex-shop")["notes"]], ["charlotte", "agent"])
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
