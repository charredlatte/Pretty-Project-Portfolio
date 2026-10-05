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
import threading
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
        self.assertEqual(names, {"house_rules", "report_status", "list_agents", "inbox", "pick_up", "drop_file", "comment", "comments", "manage", "quiz", "quizzes", "forget", "answer", "decide", "tokens", "set_tokens"})
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
        # a litter box note is a card in the same quest log: dealt once, answered, kept for filing, then cleared
        card = {"kind": "litterbox", "ref": "abc123def456", "title": "loose-ends.md", "note": "Rename her Mochi", "hint": "kittychat",
                "questions": [{"q": "Which project is it for?", "options": ["kittychat", "Settled: drop it"]}]}
        c = self.tool("quiz", **card)
        self.assertEqual(c, {"id": "litterbox-abc123def456"})
        at = self.tool("quizzes", kind="litterbox")["quizzes"][0]["at"]
        time.sleep(0.01)
        self.tool("quiz", **dict(card, note="dealt again"))
        self.assertEqual(self.tool("quizzes", kind="litterbox")["quizzes"][0]["at"], at)
        with self.assertRaises(Exception):
            self.tool("quiz", **dict(card, kind="decisions"))
        self.assertEqual([(q["id"], q["note"]) for q in self.tool("quizzes", kind="litterbox")["quizzes"]], [("litterbox-abc123def456", "dealt again")])
        heard = len(self.tool("comments", cat="queen")["notes"])
        self.assertEqual(self.tool("answer", quiz=c["id"], answers=["Settled: drop it"]), {"ok": True, "told": False})
        self.assertEqual(len(self.tool("comments", cat="queen")["notes"]), heard)
        self.assertEqual(self.tool("quiz", **card), {"id": c["id"], "done": True})
        with self.assertRaises(Exception):   # a card the café couldn't answer
            self.tool("quiz", **dict(card, questions=[{"q": "Which?", "free": True}]))
        waiting = self.tool("quiz", title="Still waiting", questions=[{"q": "Merge?", "options": ["Yes", "No"]}], **{"for": "codex-shop"})
        self.assertEqual(self.tool("forget", quizzes=[c["id"], waiting["id"]]), {"forgotten": 1})
        self.assertIn(waiting["id"], [q["id"] for q in self.tool("quizzes")["quizzes"]])
        self.assertEqual(self.tool("quizzes", done=True, kind="litterbox")["quizzes"], [])
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


class Hostile(unittest.TestCase):
    """Whatever a client sends, one call fails and the server carries on."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.env = dict(os.environ, CATIO_HOME=self.home)

    def run_server(self, *messages):
        lines = [m if isinstance(m, str) else json.dumps(m) for m in messages]
        done = subprocess.run([sys.executable, str(SERVER)], input="\n".join(lines) + "\n", capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return [json.loads(line) for line in done.stdout.splitlines()]

    @staticmethod
    def call(name, arguments, id=1):
        return {"jsonrpc": "2.0", "id": id, "method": "tools/call", "params": {"name": name, "arguments": arguments}}

    def test_survives_what_isnt_json_rpc(self):
        ping = {"jsonrpc": "2.0", "id": 99, "method": "ping"}
        for bad in ("null", "[]", '"x"', "12", "[" * 100000, '{"id": 1, "method": ["a"]}', '{"id": 1, "method": "tools/call", "params": "x"}',
                    '{"id": 1, "method": "tools/call", "params": {"name": ["a"]}}'):
            replies = self.run_server(bad, ping)
            self.assertEqual(replies[-1]["id"], 99, bad[:40])

    def test_arguments_of_the_wrong_type_are_refused_by_name(self):
        for name, arguments, why in (("comment", "x", "arguments is an object"), ("comment", [1], "arguments is an object"),
                                     ("report_status", {"agent": ["x"]}, "agent must be string"), ("inbox", {"agent": {"a": 1}}, "agent must be string"),
                                     ("comments", {"cat": "x", "limit": [1]}, "limit must be integer"), ("comments", {"cat": "x", "limit": True}, "limit must be integer"),
                                     ("forget", {"quizzes": 5}, "quizzes must be array"), ("manage", {"cat": ["x"], "action": "done"}, "cat must be string")):
            reply, probe = self.run_server(self.call(name, arguments), {"jsonrpc": "2.0", "id": 2, "method": "ping"})
            self.assertTrue(reply["result"]["isError"], (name, arguments))
            self.assertEqual(reply["result"]["content"][0]["text"], why)
            self.assertEqual(probe["id"], 2)

    def test_a_null_is_an_omitted_argument(self):
        reply, = self.run_server(self.call("report_status", {"agent": "a", "branch": None, "mood": None}))
        self.assertTrue(reply["result"]["structuredContent"]["ok"])
        agent = json.loads(Path(self.home, "state.json").read_text())["agents"]["a"]
        self.assertNotIn("branch", agent)
        self.assertNotIn("mood", agent)

    def test_a_conversation_is_read_a_page_at_a_time(self):
        notes = [self.call("comment", {"cat": "c", "text": str(i), "author": "agent"}, i) for i in range(1, 8)]
        replies = self.run_server(*notes, self.call("comments", {"cat": "c", "limit": 3}, 90), self.call("comments", {"cat": "c", "limit": -4}, 91),
                                  self.call("comments", {"cat": "c", "limit": 10 ** 9}, 92))
        texts = {r["id"]: [n["text"] for n in r["result"]["structuredContent"]["notes"]] for r in replies if r["id"] >= 90}
        self.assertEqual(texts[90], ["5", "6", "7"])
        self.assertEqual(texts[91], ["7"], "a limit under one is one")
        self.assertEqual(len(texts[92]), 7)

    def test_two_servers_at_once_lose_nothing(self):
        def visit(tag):
            self.run_server(*[self.call("report_status", {"agent": "%s-%d" % (tag, i), "mood": "busy"}, i + 1) for i in range(30)])
        threads = [threading.Thread(target=visit, args=(tag,)) for tag in "abcd"]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(json.loads(Path(self.home, "state.json").read_text())["agents"]), 120)

    def test_windows_busy_lock_and_state_are_waited_for_not_lost(self):
        # Windows says PermissionError, not FileExistsError, when the lock just let go is still "delete pending", and
        # refuses os.replace while anything has state.json open: either lost one agent in four servers' 120 (CI, 5 Oct).
        sys.path.insert(0, str(SERVER.parent))
        import catio_mcp
        from unittest import mock
        real_open, real_replace = os.open, os.replace
        busy = {"open": 2, "replace": 2}

        def flaky_open(path, *a, **k):
            if str(path).endswith("state.lock") and busy["open"]:
                busy["open"] -= 1
                raise PermissionError(13, "delete pending")
            return real_open(path, *a, **k)

        def flaky_replace(src, dst):
            if busy["replace"]:
                busy["replace"] -= 1
                raise PermissionError(13, "in use")
            return real_replace(src, dst)

        with mock.patch.object(catio_mcp, "HOME", Path(self.home)), mock.patch.object(catio_mcp.os, "open", flaky_open), \
                mock.patch.object(catio_mcp.os, "replace", flaky_replace):
            with catio_mcp.LOCK:
                catio_mcp.store({"agents": {"a": {"id": "a"}}, "files": [], "notes": []})
        self.assertEqual(busy, {"open": 0, "replace": 0})
        self.assertIn("a", json.loads(Path(self.home, "state.json").read_text())["agents"])
        self.assertFalse(Path(self.home, "state.lock").exists(), "the lock is let go")

    def test_a_lock_left_by_a_crash_is_taken_over(self):
        lock = Path(self.home, "state.lock")
        lock.touch()
        old = time.time() - 60
        os.utime(lock, (old, old))
        reply, = self.run_server(self.call("report_status", {"agent": "a"}))
        self.assertTrue(reply["result"]["structuredContent"]["ok"])
        self.assertFalse(lock.exists(), "the lock is let go")


class Bundle(unittest.TestCase):
    def test_the_server_starts_from_the_localhost_bundle(self):
        # The first user test (5 October): bundle.py shipped catio_mcp.py without design_tokens.py, which it imports,
        # so the documented command died on its first line.
        repo = SERVER.parent.parent.parent
        done = subprocess.run([sys.executable, str(repo / "catio" / "tools" / "bundle.py")], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        server = repo / "catio" / "dist" / "catio-local" / "harness" / "mcp" / "catio_mcp.py"
        ping = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
        run = subprocess.run([sys.executable, str(server)], input=ping, capture_output=True, text=True, timeout=30,
                             env=dict(os.environ, CATIO_HOME=tempfile.mkdtemp()))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout.splitlines()[0])["id"], 1, run.stdout)


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
            # a body that isn't an object, a length that isn't a number, a tool that doesn't exist: refused, and it still answers
            for path, body, code in (("/api/comment", ["x"], 400), ("/api/report_status", {"agent": ["x"]}, 400), ("/api/nothing", {}, 404)):
                with self.assertRaises(urllib.error.HTTPError) as e:
                    post(path, body)
                self.assertEqual(e.exception.code, code, path)
            with socket.create_connection(("127.0.0.1", port)) as raw:
                raw.sendall(b"POST /api/list_agents HTTP/1.1\r\nHost: localhost\r\nContent-Length: -5\r\n\r\n")
                self.assertIn(b" 400 ", raw.recv(1024).split(b"\r\n")[0])
            self.assertEqual(json.loads(post("/api/comments", {"cat": "gem"}).read())["notes"], [])
        finally:
            p.terminate(); p.wait(5); p.stdout.close()


class Tokens(unittest.TestCase):
    """tokens and set_tokens on the café a server serves: what The look's Export and Import tokens do, written to its
    art/skin.json, and the shared Figma file read as the page, skin.py and the gateway read it."""
    REPO = Path(__file__).resolve().parent.parent.parent
    FIX = Path(__file__).resolve().parent / "fixtures"

    def cafe(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "index.html").write_text((self.REPO / "catio" / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
        (folder / "art").mkdir()
        (folder / "art" / "skin.json").write_text(json.dumps({"panel": "art/skin/panel.png"}))
        return folder

    def stdio(self, folder):
        return subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                env=dict(os.environ, CATIO_HOME=tempfile.mkdtemp(), CATIO_CAFE=str(folder)))

    def call(self, p, tool, **args):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}) + "\n")
        p.stdin.flush()
        r = json.loads(p.stdout.readline())["result"]
        return {"refused": r["content"][0]["text"]} if r.get("isError") else r["structuredContent"]

    def test_brings_a_figma_file_in_and_gives_the_look_back(self):
        folder = self.cafe()
        p = self.stdio(folder)
        try:
            figma = json.loads((self.FIX / "tokens-figma.json").read_text())
            want = json.loads((self.FIX / "tokens-figma.expected.json").read_text())
            r = self.call(p, "set_tokens", file=figma)
            self.assertEqual((r["mode"], r["tokens"], r["foreign"], r["refused"]), ("light", len(want["found"]), want["foreign"], want["refused"]))
            skin = json.loads((folder / "art" / "skin.json").read_text())
            self.assertEqual(skin["tokens"], want["found"])
            self.assertEqual(skin["panel"], "art/skin/panel.png")   # her pieces stay
            out = self.call(p, "tokens")["file"]
            self.assertEqual(out["colours"]["ink"]["$value"]["hex"], "#1d3557")
            self.assertEqual(out["type"]["px-size"]["$value"], {"value": 20, "unit": "px"})
            # dark says only what differs: the same as light isn't kept
            self.assertEqual(self.call(p, "set_tokens", mode="dark", file={"colours": {"ink": {"$value": "#eeeeee"}, "grass": {"$value": "#5A8F29"}}})["changed"], 1)
            self.assertEqual(json.loads((folder / "art" / "skin.json").read_text())["dark"], {"--ink": "#eeeeee"})
            self.assertEqual(self.call(p, "tokens", mode="dark")["file"]["colours"]["grass"]["$value"]["hex"], "#5a8f29")
            self.assertRegex(self.call(p, "set_tokens", file={"brand": {"red": {"$value": "#ff0000"}}})["refused"], r"none of the café's tokens \(1 of its own\)")
            self.assertRegex(self.call(p, "set_tokens", mode="dusk", file=figma)["refused"], "mode is light or dark")
        finally:
            p.stdin.close(); p.wait(5); p.stdout.close()

    def test_says_when_it_has_no_cafe(self):
        p = self.stdio(tempfile.mkdtemp())
        try:
            self.assertRegex(self.call(p, "tokens")["refused"], "no café folder here")
        finally:
            p.stdin.close(); p.wait(5); p.stdout.close()

    def test_serves_its_own_cafe(self):
        folder = self.cafe()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k != "CATIO_CAFE"}
        p = subprocess.Popen([sys.executable, str(SERVER), "--serve", str(folder), "--port", str(port)], stdout=subprocess.PIPE,
                             env=dict(env, CATIO_HOME=tempfile.mkdtemp()))
        try:
            p.stdout.readline()
            req = urllib.request.Request("http://127.0.0.1:%d/api/set_tokens" % port,
                                         json.dumps({"file": {"colours": {"ink": {"$value": "#1D3557"}}}}).encode(), {"Content-Type": "application/json"})
            self.assertEqual(json.loads(urllib.request.urlopen(req).read())["changed"], 1)
            self.assertEqual(json.loads((folder / "art" / "skin.json").read_text())["tokens"], {"--ink": "#1D3557"})
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
        # under the caller's floor the decider hasn't decided: it neither agrees nor disagrees, and ref names the file
        self.tool("decide", state={"file": "notes.md"}, kind="sort", old="shop", floor=0.9, ref="b-1",
                  questions={"cat": {"type": "choice", "criteria": {"shop": "the shop", "catio": "the café"}}})
        last = json.loads(Path(self.home, "state.json").read_text())["decisions"][-1]
        self.assertEqual((last["verdict"], last["sure"], last["agree"], last["ref"]), ("shop", False, None, "b-1"))
