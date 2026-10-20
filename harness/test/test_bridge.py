"""catio_bridge.py over real stdio against a stand-in gateway: what it forwards, what it hands back, and that a gateway
that is down or refusing leaves the client an answer instead of silence.

    python3 -m unittest discover harness/test
"""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent.parent / "mcp" / "catio_bridge.py"
KEY = "test-key-0123456789abcdef"


class Gateway(BaseHTTPRequestHandler):
    """Answers /mcp as the gateway does: a reply per request, 202 for notifications, and what the key and the
    User-Agent decide. Records every POST."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        s = self.server
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        s.posts.append((self.path, dict(self.headers), raw))
        if self.headers.get("User-Agent", "").startswith("Python-urllib"):   # Cloudflare's bot check: error 1010
            return self.send_response(403) or self.end_headers()
        if self.headers.get("Authorization") != "Bearer " + KEY:
            return self.send_response(401) or self.end_headers()
        if s.mode == "down":
            return self.send_response(502) or self.end_headers()
        if s.mode == "garbage":
            return self.send(200, b"<html>not json</html>")
        body = json.loads(raw)
        replies = [{"jsonrpc": "2.0", "id": m["id"], "result": {"echo": m["method"], "café": "ünï"}} for m in (body if isinstance(body, list) else [body]) if m.get("id") is not None]
        if not replies:
            return self.send_response(202) or self.end_headers()
        self.send(200, json.dumps(replies if isinstance(body, list) else replies[0]).encode())

    def send(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Bridge(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.server.posts, self.server.mode = [], "ok"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def run_bridge(self, *lines, key=KEY, url=None):
        env = dict(os.environ, CATIO_URL=self.url if url is None else url, CATIO_TOKEN=key)
        done = subprocess.run([sys.executable, str(BRIDGE)], input="\n".join(lines) + "\n", capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
        return done, [json.loads(line) for line in done.stdout.splitlines()]

    @staticmethod
    def call(mid, method="tools/list", **extra):
        return json.dumps(dict({"jsonrpc": "2.0", "id": mid, "method": method}, **extra))

    def test_a_request_goes_out_with_the_key_and_the_reply_comes_back(self):
        done, replies = self.run_bridge(self.call(1), self.call(2, "ping"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([r["id"] for r in replies], [1, 2])
        self.assertEqual(replies[0]["result"], {"echo": "tools/list", "café": "ünï"}, "UTF-8 survives both ways")
        path, headers, _ = self.server.posts[0]
        self.assertEqual(path, "/mcp")
        self.assertEqual(headers["Authorization"], "Bearer " + KEY)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Python-urllib", headers["User-Agent"])

    def test_a_notification_gets_no_reply_and_a_batch_gets_a_batch(self):
        note = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        batch = json.dumps([{"jsonrpc": "2.0", "id": 7, "method": "a"}, {"jsonrpc": "2.0", "method": "n"}, {"jsonrpc": "2.0", "id": 8, "method": "b"}])
        done, replies = self.run_bridge(note, batch, self.call(9, "ping"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(replies), 2, "the notification was silent")
        self.assertEqual([r["id"] for r in replies[0]], [7, 8])
        self.assertEqual(replies[1]["id"], 9)

    def test_a_line_that_is_not_json_is_a_parse_error_and_the_bridge_carries_on(self):
        _, replies = self.run_bridge("{nope", "", self.call(1, "ping"))
        self.assertEqual((replies[0]["id"], replies[0]["error"]["code"]), (None, -32700))
        self.assertEqual(replies[1]["id"], 1)
        self.assertEqual(len(self.server.posts), 1, "the bad line never reached the gateway")

    def test_a_gateway_that_refuses_down_or_garbles_answers_every_request_with_an_error(self):
        _, replies = self.run_bridge(self.call(1), self.call(2, "ping"), key="wrong-key-0123456789")
        self.assertEqual([r["id"] for r in replies], [1, 2])
        self.assertIn("401", replies[0]["error"]["message"])
        self.assertIn("CATIO_TOKEN", replies[0]["error"]["message"])
        for mode, words in (("down", "502"), ("garbage", "wasn't JSON")):
            self.server.mode = mode
            batch = json.dumps([{"jsonrpc": "2.0", "id": 5, "method": "a"}, {"jsonrpc": "2.0", "method": "n"}])
            _, replies = self.run_bridge(self.call(3), batch)
            self.assertIn(words, replies[0]["error"]["message"], mode)
            self.assertEqual([r["id"] for r in replies[1]], [5], "one error for the one request in the batch")

    def test_an_address_nothing_listens_on_is_an_error_not_a_hang(self):
        _, replies = self.run_bridge(self.call(1), url="http://127.0.0.1:1")
        self.assertIn("didn't answer", replies[0]["error"]["message"])

    def test_a_failed_batch_of_notifications_stays_silent(self):
        self.server.mode = "down"
        done, replies = self.run_bridge(json.dumps([{"jsonrpc": "2.0", "method": "n"}]))
        self.assertEqual((done.returncode, replies), (0, []))

    def test_it_says_what_is_missing_when_started_without_its_settings(self):
        done = subprocess.run([sys.executable, str(BRIDGE)], input="", capture_output=True, text=True, env={k: v for k, v in os.environ.items() if not k.startswith("CATIO_")}, timeout=30)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("CATIO_URL", done.stderr)
        self.assertIn("CATIO_TOKEN", done.stderr)


if __name__ == "__main__":
    unittest.main()
