"""The app's network code against a stand-in gateway on the loopback: never hers, and no real secret anywhere.

    python3 catio-app/test/test_net.py <build dir>          (ctest runs it as catio_net)

The stand-in answers as harness/gateway/src/cafe.js does -- /login's form, 303 and the __Host-catio cookie;
/api/db; the tools; writes refused without X-Catio: 1 or with another site's Origin; /art behind the cookie;
{code, error} on every failure -- and records what it was sent, so each test checks both sides: what the app
sent, and what it made of the answer. Then the app itself signs in, reads the house, fetches the art its cache
lacks, and opens a closed room, drawn into a PNG with no window.
"""
import json
import os
import re
import secrets
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

HERE = Path(__file__).resolve().parent
APP = HERE.parent
BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else APP / "build"
CHECK = BUILD / "catio_net_check"
CAFE = BUILD / "catio_app"

USER = "owner"
# harness/gateway/src/registry.js's words, as signin.js's esc() writes them: every & < > " ' as &#NN;
WRONG = ("That handle and password aren't right. The first account's handle is CATIO_HANDLE as it was when the "
         "gateway first ran (charlotte if it wasn't set), and its password is CATIO_PASSWORD.")


def esc(text):
    return "".join(f"&#{ord(c)};" if c in "&<>\"'" else c for c in text)
PASSWORD = "an invented password, with spaces & signs=+"   # a test's, nobody's
# cafe.js's DOC_PATH: what a document's path may be, segments of these characters only, none of them empty
DOC_PATH = re.compile(r"^[A-Za-z0-9_.~:@+-]{1,200}(/[A-Za-z0-9_.~:@+-]{1,200}){1,7}$")
GUEST, GUEST_PASSWORD = "guest", "another invented password"  # a second account on the same stand-in


def png(r, g, b):
    """A 1x1 PNG of one colour: the stand-in's art, so no pack art is needed or served."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"\x00" + bytes([r, g, b, 255])
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.token = None
        self.account = True   # False: the gateway's secrets made no account yet, and it shows its warning lights
        self.homework = True  # False: an older gateway, with no quizzes tool
        self.redirect = False # True: something in front of the gateway sends /api/db elsewhere
        self.outage = False   # True: Cloudflare's own 503 page in front of /api/db
        self.proxy = False    # True: something in front of the gateway answers /api/db with its own HTML 401
        self.seen = []        # (method, path, headers, body)
        self.docs = json.loads((APP / "test" / "fixtures" / "db.json").read_text())["docs"]
        self.agents = json.loads((APP / "test" / "fixtures" / "agents.json").read_text())
        self.files = {}
        self.art = {}         # path -> bytes; anything else under /art/ is 404, as for a guest's café


class Standin(BaseHTTPRequestHandler):
    state: State = None

    def log_message(self, *a):
        pass

    def answer(self, status, body=b"", kind="application/json", headers=()):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def refuse(self, status, code, error):
        self.answer(status, {"code": code, "error": error})

    def signed_in(self):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "__Host-catio" and v and v == self.state.token:
                return True
        return False

    def handle_any(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        path = self.path
        s = self.state
        with s.lock:
            s.seen.append((method, path, dict(self.headers), body))
        if path == "/login" and method == "POST" and not s.account:
            # cafe.js's signInPage(NOT_YET, 503, noAccount(env, request)): a cross for the secret to fix, the rest fine
            lights = [("bad", "CATIO_PASSWORD is under 16 characters: set a longer one."),
                      ("ok", "CATIO_HANDLE is set: your handle will be owner."),
                      ("off", "CATIO_TOKEN isn't set, which is fine: it is the key your cats check in with, and you can make keys in the caf\u00e9 later.")]
            page = ('<h1>The KittyChat Caf\u00e9</h1><p class="bad" role="alert">The gateway has no account yet. Its warning lights:</p>'
                    '<ul class="lights">' + "".join(f'<li class="{k}">{esc(t)}</li>' for k, t in lights) + "</ul>\n\n"
                    '<p class="soft">This is what the Worker at 127.0.0.1 sees. Save and deploy each change.</p>')
            return self.answer(503, page.encode(), "text/html; charset=utf-8")
        if path == "/logout" and method == "POST":
            if self.signed_in():
                s.token = None   # this cookie stops working now, not in a month
            return self.answer(303, b"", "text/plain", [("Location", "/"), ("Set-Cookie", "__Host-catio=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0")])
        if path == "/login" and method == "POST":
            form = parse_qs(body.decode(), keep_blank_values=True)
            user = (form.get("user") or [""])[0].strip().lower()   # registry.js's checkPassword: trimmed, lower case
            if (user, form.get("password")) in ((USER, [PASSWORD]), (GUEST, [GUEST_PASSWORD])):
                s.token = secrets.token_hex(32)
                return self.answer(303, b"", "text/plain", [("Location", "/"), ("Set-Cookie",
                    f"__Host-catio={s.token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=2592000")])
            page = f'<h1>The KittyChat Caf\u00e9</h1><p class="bad" role="alert">{esc(WRONG)}</p>'
            return self.answer(401, page.encode(), "text/html; charset=utf-8")
        if not self.signed_in():
            return self.refuse(401, "signed_out", "Sign in to the café first.")
        if path.startswith("/art/") and method == "GET":
            data = s.art.get(path[1:])
            return self.answer(200, data, "image/png") if data is not None else self.answer(404, b"Not found\n", "text/plain")
        if path == "/api/db" and method == "GET" and s.proxy:
            return self.answer(401, b"<html><h1>Access denied</h1></html>", "text/html")
        if path == "/api/db" and method == "GET" and s.outage:
            return self.answer(503, b"<html><title>503 Service Unavailable</title><h1>Error 503</h1></html>", "text/html")
        if path == "/api/db" and method == "GET" and s.redirect:
            return self.answer(302, b"", "text/plain", [("Location", "https://sign-in.example/")])
        if path == "/api/db" and method == "GET":
            return self.answer(200, {"docs": s.docs})
        # fromCafe(): only the café's own page writes
        origin = self.headers.get("Origin")
        if self.headers.get("X-Catio") != "1" or (origin and origin != f"http://{self.headers.get('Host')}"):
            return self.refuse(403, "forbidden", "Only the café's own page writes here.")
        if path.startswith("/api/db/"):
            doc = unquote(path[len("/api/db/"):])
            if not DOC_PATH.match(doc) or len(doc.split("/")) % 2:   # as cafe.js refuses it
                return self.refuse(400, "bad_request", "That isn't a document's path.")
            if method == "DELETE":
                s.docs.pop(doc, None)
                return self.answer(200, {"ok": True})
            data = json.loads(body or b"{}").get("data")
            if not isinstance(data, dict):
                return self.refuse(400, "bad_request", "The body is {data: {...}}.")
            if method == "PUT":
                s.docs[doc] = data
                return self.answer(200, {"ok": True})
            if method == "PATCH":
                if doc not in s.docs:
                    return self.refuse(404, "not_found", "No such document.")
                s.docs[doc].update(data)
                return self.answer(200, {"ok": True})
        if path == "/api/files" and method == "POST":
            fid = "f" + secrets.token_hex(4)
            s.files[fid] = (unquote(self.headers.get("X-Name", "file")), self.headers.get("Content-Type"), body)
            return self.answer(200, {"id": fid, "url": "/files/" + fid, "sizeBytes": len(body), "contentType": self.headers.get("Content-Type")})
        if path.startswith("/api/files/") and method == "DELETE":
            s.files.pop(unquote(path[len("/api/files/"):]), None)
            return self.answer(200, {"deleted": True})
        if path.startswith("/api/tools/") and method == "POST":
            name = unquote(path[len("/api/tools/"):])
            if name == "list_agents":
                return self.answer(200, s.agents)
            if name == "quizzes" and s.homework:
                return self.answer(200, {"quizzes": []})
            if name == "manage":
                return self.refuse(400, "tool_error", "No cat called nobody.")
            return self.refuse(404, "not_found", "No such tool.")
        return self.refuse(404, "not_found", "Not here.")

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")

    def do_PUT(self):
        self.handle_any("PUT")

    def do_PATCH(self):
        self.handle_any("PATCH")

    def do_DELETE(self):
        self.handle_any("DELETE")


class NetTest(unittest.TestCase):
    def setUp(self):
        if not CHECK.exists():
            self.skipTest(f"{CHECK} is not built")
        self.state = State()
        handler = type("H", (Standin,), {"state": self.state})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.dir = tempfile.TemporaryDirectory()
        self.jar = Path(self.dir.name) / "cookie"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.dir.cleanup()

    def run_check(self, *steps, origin=None):
        out = subprocess.run([str(CHECK), origin or self.origin, str(self.jar), *steps], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return [json.loads(line) for line in out.stdout.splitlines()]

    def last(self, method, path):
        hits = [x for x in self.state.seen if x[0] == method and x[1] == path]
        self.assertTrue(hits, f"nothing was sent to {method} {path}")
        return hits[-1]

    def test_a_wrong_password_is_refused_in_the_gateways_own_words(self):
        (r,) = self.run_check(f"login:{USER}:not it")
        self.assertFalse(r["ok"])
        self.assertEqual((r["status"], r["code"]), (401, "wrong"))
        self.assertEqual(r["message"], WRONG, "every entity decoded, the apostrophes included")
        self.assertFalse(self.jar.exists(), "no cookie kept for a refusal")

    def test_signing_in_keeps_the_cookie_for_its_owner_alone(self):
        r, inside = self.run_check(f"login:{USER}:{PASSWORD}", "signed_in")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["status"], 303)
        self.assertTrue(inside["value"])
        method, path, headers, body = self.last("POST", "/login")
        self.assertEqual(headers.get("Content-Type"), "application/x-www-form-urlencoded")
        self.assertEqual(parse_qs(body.decode()), {"user": [USER], "password": [PASSWORD]}, "the form survives spaces, & and =")
        self.assertEqual(self.jar.read_text().split(), [self.origin, self.state.token], "the gateway it is for, then its cookie")
        self.assertEqual(stat.S_IMODE(os.stat(self.jar).st_mode), 0o600, "the cookie file is readable by its owner alone")
        # a later start finds it there: no sign-in screen
        (again,) = self.run_check("signed_in")
        self.assertTrue(again["value"])

    def test_reads_carry_the_cookie(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        docs, agents = self.run_check("docs", "tool:list_agents:{}")
        self.assertTrue(docs["ok"])
        self.assertEqual(json.loads(docs["body"])["docs"]["rooms/kitchen"]["name"], "Kitchen")
        self.assertEqual(len(json.loads(agents["body"])["agents"]), 8)
        _, _, headers, _ = self.last("GET", "/api/db")
        self.assertEqual(headers.get("Cookie"), f"__Host-catio={self.state.token}")
        self.assertIsNone(headers.get("Origin"))

    def test_writes_say_they_come_from_the_cafe_and_from_no_other_site(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        put, patch, erase, odd = self.run_check('put:cats/au-lait:{"title": "A chat"}', 'patch:rooms/bath:{"closed": false}', "erase:cats/au-lait",
                                                'put:cats/café au lait:{"title": "A chat"}')
        self.assertTrue(put["ok"] and patch["ok"] and erase["ok"], (put, patch, erase))
        self.assertEqual((odd["status"], odd["code"]), (400, "bad_request"), "the gateway takes only its own characters in a path")
        method, path, headers, body = self.last("PATCH", "/api/db/rooms/bath")
        self.assertEqual(headers.get("X-Catio"), "1")
        self.assertIsNone(headers.get("Origin"), "a native client sends no Origin, which fromCafe() lets through")
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(json.loads(body), {"data": {"closed": False}}, "the data, wrapped as the gateway wants it")
        self.assertFalse(self.state.docs["rooms/bath"]["closed"])
        self.assertIn(("PUT", "/api/db/cats/caf%C3%A9%20au%20lait"), [(m, p) for m, p, *_ in self.state.seen], "each segment encoded")
        self.assertNotIn("cats/au-lait", self.state.docs)

    def test_a_document_that_isnt_there_and_a_tool_that_refuses(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        missing, refused, unknown = self.run_check('patch:rooms/attic:{"closed": false}', 'tool:manage:{"cat": "nobody"}', "tool:nope:{}")
        self.assertEqual((missing["status"], missing["code"], missing["message"]), (404, "not_found", "No such document."))
        self.assertEqual((refused["status"], refused["code"], refused["message"]), (400, "tool_error", "No cat called nobody."))
        self.assertEqual(unknown["code"], "not_found")

    def test_a_file_goes_up_whole_and_comes_down(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        (up,) = self.run_check("file:la carte été.txt:text/plain:Bonjour, les chats")
        self.assertTrue(up["ok"], up)
        fid = json.loads(up["body"])["id"]
        self.assertEqual(self.state.files[fid], ("la carte été.txt", "text/plain", "Bonjour, les chats".encode()))
        _, _, headers, _ = self.last("POST", "/api/files")
        self.assertEqual(headers.get("X-Catio"), "1")
        (down,) = self.run_check(f"unfile:{fid}")
        self.assertTrue(down["ok"])
        self.assertNotIn(fid, self.state.files)

    def test_the_art_comes_byte_for_byte_and_a_missing_piece_says_so(self):
        self.state.art["art/licensed/ui/panel.png"] = png(220, 185, 138)
        self.run_check(f"login:{USER}:{PASSWORD}")
        got, gone = self.run_check("art:art/licensed/ui/panel.png", "art:art/licensed/house.png")
        self.assertTrue(got["ok"])
        self.assertEqual(got["size"], len(self.state.art["art/licensed/ui/panel.png"]))
        self.assertEqual((gone["status"], gone["code"]), (404, "not_found"))

    def test_a_handle_is_read_as_the_gateway_reads_it(self):
        (r,) = self.run_check(f"login: {USER.upper()} :{PASSWORD}")
        self.assertTrue(r["ok"], "trimmed and lower case, as registry.js's checkPassword")

    def test_a_wrong_password_keeps_the_cookie_already_kept(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        (r,) = self.run_check(f"login:{USER}:not it")
        self.assertEqual(r["code"], "wrong")
        self.assertTrue(self.jar.exists(), "a wrong password says nothing of the cookie kept, perhaps another gateway's")

    def test_a_cookie_run_out_signs_out_and_forgets_it(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        self.state.token = None   # revoked, or thirty days on
        r, inside = self.run_check("docs", "signed_in")
        self.assertEqual((r["status"], r["code"]), (401, "signed_out"))
        self.assertFalse(inside["value"])
        self.assertFalse(self.jar.exists(), "the cookie file is deleted, not kept to be refused again")

    def test_signing_out_ends_the_cookie_at_the_gateway_too(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        token = self.state.token
        self.run_check("sign_out")
        self.assertFalse(self.jar.exists())
        _, _, headers, _ = self.last("POST", "/logout")
        self.assertEqual(headers.get("Cookie"), f"__Host-catio={token}", "the gateway is told which cookie to end")
        self.assertIsNone(self.state.token, "so it stops working now, not in a month")

    def test_a_gateway_with_no_account_says_which_secret_to_fix(self):
        self.state.account = False
        (r,) = self.run_check(f"login:{USER}:{PASSWORD}")
        self.assertEqual((r["status"], r["code"]), (503, "no_account"))
        self.assertEqual(r["message"], "The gateway has no account yet. Its warning lights: CATIO_PASSWORD is under 16 characters: set a longer one.",
                         "the alert and the one cross; the lights that are fine ask nothing of her")
        self.assertFalse(self.jar.exists())

    def test_a_gateway_that_isnt_there(self):
        (r,) = self.run_check("docs", origin="http://127.0.0.1:9")
        self.assertEqual((r["status"], r["code"]), (0, "unreachable"))
        self.assertTrue(r["message"])

    def test_the_worker_thread_hands_back_what_was_asked(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        (r,) = self.run_check("net:docs")
        self.assertEqual(r["step"], "net:docs", "the reply came back with its own ticket")
        self.assertTrue(r["ok"])

    def serve_art(self):
        """Every file the app asks for, as one plain colour: no pack art in a test, ever."""
        if not CAFE.exists():
            self.skipTest(f"{CAFE} is not built")
        from_list = [line.split('"')[1] for line in (APP / "src" / "art.cpp").read_text().splitlines() if line.strip().startswith("{Id::")]
        for path in from_list:
            self.state.art[path] = (APP / "assets" / "Nunito-Bold.ttf").read_bytes() if path.endswith(".ttf") else png(143, 191, 79)
        return from_list

    def app(self, steps, name="shot.png"):
        return subprocess.run([str(CAFE), "--gateway", self.origin, "--home", str(Path(self.dir.name) / "home"), "--shot",
                               str(Path(self.dir.name) / name), "--size", "1280x800", "--do", steps], capture_output=True, text=True, timeout=120)

    def test_an_older_gateway_without_homework_still_lets_her_in(self):
        from_list = self.serve_art()
        self.state.homework = False
        r = self.app(f"type {USER}; key tab; type {PASSWORD}; key enter")
        self.assertEqual(r.returncode, 0, r.stderr)
        art = [p for m, p, *_ in self.state.seen if p.startswith("/art/")]
        self.assertEqual(len(art), len(from_list), "past waking the cats: the house is hers and its art fetched")
        self.assertIn("sign: \n", r.stdout, "and nothing on the sign: no homework tool is nothing wrong")

    def test_a_cookie_is_only_ever_sent_to_the_gateway_that_gave_it(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        other = self.origin.replace("127.0.0.1", "localhost")   # the same machine, another address
        inside, docs = self.run_check("signed_in", "docs", origin=other)
        self.assertFalse(inside["value"])
        self.assertEqual(docs["code"], "signed_out")
        _, _, headers, _ = self.last("GET", "/api/db")
        self.assertIsNone(headers.get("Cookie"), "the first gateway's cookie never went to the second")
        self.assertEqual(self.jar.read_text().split(), [self.origin, self.state.token], "and the second's refusal didn't delete it")

    def test_a_redirect_is_not_the_cafes_answer(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        self.state.redirect = True
        (r,) = self.run_check("docs")
        self.assertFalse(r["ok"])
        self.assertEqual((r["status"], r["code"]), (302, "redirected"))

    def test_plain_http_only_on_this_machine(self):
        (r,) = self.run_check(f"login:{USER}:{PASSWORD}", origin="http://catio-gateway.example.workers.dev")
        self.assertEqual(r["code"], "insecure", "her password never crosses the network in the clear")
        # the loopback's name before an @ is a user name, and the host is after it
        port = self.server.server_address[1]
        (r,) = self.run_check(f"login:{USER}:{PASSWORD}", origin=f"http://127.0.0.1:{port}@localhost:{port}")
        self.assertEqual(r["code"], "insecure", "an address that only starts like this machine's is not this machine")
        self.assertFalse(self.state.seen)

    def test_a_saved_cookie_is_found_whatever_the_address_ends_with(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        (r,) = self.run_check("has_cookie", origin=self.origin + "/")
        self.assertTrue(r["value"], "the next start opens on the house, not the sign-in")

    def test_an_outage_is_not_a_missing_account(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        self.state.outage = True
        (r,) = self.run_check("docs")
        self.assertEqual((r["status"], r["code"]), (503, "unavailable"), "no_account is the sign-in's answer alone")
        self.assertEqual(r["message"], "The gateway answered 503.")

    def test_an_empty_segment_stays_empty(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        (r,) = self.run_check("erase:cats//kitchen")
        self.assertIn(("DELETE", "/api/db/cats//kitchen"), [(m, p) for m, p, *_ in self.state.seen], "sent as it is, not tidied into another path")
        self.assertEqual(r["code"], "bad_request", "which the gateway refuses")

    def test_signing_out_from_the_house_menu(self):
        self.serve_art()
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        token = self.state.token
        r = self.app("click 100 40; choose Sign out")
        self.assertEqual(r.returncode, 0, r.stderr)
        _, _, headers, _ = self.last("POST", "/logout")
        self.assertEqual(headers.get("Cookie"), f"__Host-catio={token}")
        self.assertIsNone(self.state.token, "the gateway ended it")
        self.assertFalse((Path(self.dir.name) / "home" / "cookie").exists(), "and the app forgot it")
        cache = Path(self.dir.name) / "home" / "cache"
        self.assertFalse([f for f in cache.rglob("*") if f.is_file()] if cache.exists() else [],
                         "and the art it fetched: the packs' licences are personal, the next person here gets their own")

    def test_a_cookie_run_out_keeps_the_art_and_another_account_does_not(self):
        from_list = self.serve_art()
        cache = Path(self.dir.name) / "home" / "cache"
        fetched = lambda: len([p for m, p, *_ in self.state.seen if p.startswith("/art/")])
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        self.assertEqual(fetched(), len(from_list))
        self.state.token = None   # thirty days on
        self.assertEqual(self.app("").returncode, 0)
        self.assertEqual(len([f for f in cache.rglob("*") if f.is_file()]), len(from_list), "her cookie running out keeps her art")
        self.state.seen.clear()
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        self.assertEqual(fetched(), 0, "and signing in again as her fetches none of it again")
        self.state.token = None
        self.assertEqual(self.app("").returncode, 0)
        self.state.seen.clear()
        r = self.app(f"type {GUEST}; key tab; type {GUEST_PASSWORD}; key enter")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(fetched(), len(from_list), "another account's sign-in starts from no art: each piece is asked for, as served to it")

    def test_one_missing_piece_of_art_does_not_keep_the_rest_away(self):
        from_list = self.serve_art()
        del self.state.art["art/licensed/house.png"]                         # never uploaded
        self.state.art["art/licensed/ui/sprout.ttf"] = b"<html>a portal's page</html>"   # a 200 that isn't a font
        r = self.app(f"type {USER}; key tab; type {PASSWORD}; key enter")
        self.assertEqual(r.returncode, 0, r.stderr)
        asked = [p[1:] for m, p, *_ in self.state.seen if p.startswith("/art/")]
        self.assertEqual(sorted(asked), sorted(from_list), "every piece asked for once, the ones after the missing one included")
        cache = Path(self.dir.name) / "home" / "cache"
        kept = sorted(str(f.relative_to(cache)) for f in cache.rglob("*") if f.is_file())
        self.assertEqual(kept, sorted(p for p in from_list if p not in ("art/licensed/house.png", "art/licensed/ui/sprout.ttf")),
                         "the missing one isn't there, and a page that isn't a font isn't kept as one")
        self.assertIn("sign:", r.stdout)
        sign = r.stdout.split("sign: ", 1)[1].split("\n", 1)[0]
        self.assertTrue("house.png" in sign or "sprout.ttf" in sign, sign)

    def test_a_proxys_refusal_is_not_her_signing_out(self):
        self.run_check(f"login:{USER}:{PASSWORD}")
        self.state.proxy = True
        (r,) = self.run_check("docs")
        self.assertEqual((r["status"], r["code"]), (401, "unauthorized"), "signed_out is the gateway's own word, in its own JSON")
        self.assertTrue(self.jar.exists(), "and her cookie is kept")

    def test_a_folder_of_documents_never_draws_a_sign_ins_art(self):
        from_list = self.serve_art()
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        home = Path(self.dir.name) / "home"
        r = subprocess.run([str(CAFE), "--home", str(home), "--shot", str(Path(self.dir.name) / "folder.png"), "--size", "1280x800"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"isn't all here (0 of {len(from_list)})", r.stdout, "the cache is the gateway's, and only for her signed in")

    def test_a_gateway_given_as_nothing_is_asked_for(self):
        r = subprocess.run([str(CAFE), "--gateway", "/", "--home", str(Path(self.dir.name) / "home"), "--shot", str(Path(self.dir.name) / "blank.png"),
                            "--size", "390x844", "--do", "type owner; key tab; type x; key enter"], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("form: Fill in", r.stdout, "the sign-in asks for what is missing rather than falling over")
        self.assertFalse(self.state.seen)

    def test_an_empty_field_says_so(self):
        self.serve_art()
        r = self.app(f"type {USER}; key enter")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("form: Fill in your password.", r.stdout)
        self.assertNotIn(("POST", "/login"), [(m, p) for m, p, *_ in self.state.seen])

    def test_a_press_slid_onto_another_item_is_no_press(self):
        self.serve_art()
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        r = self.app("click 100 40; slide Check now > Sign out")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(("POST", "/logout"), [(m, p) for m, p, *_ in self.state.seen], "let go on Sign out, but pressed on Check now")
        self.assertIsNotNone(self.state.token)

    def test_a_menu_taller_than_a_landscape_phone_scrolls(self):
        self.serve_art()
        self.assertEqual(self.app(f"type {USER}; key tab; type {PASSWORD}; key enter").returncode, 0)
        home = Path(self.dir.name) / "home"
        token = self.state.token
        # 844 x 390 with touch: the House menu's items are 44 px each, and Sign out is the last but two
        r = subprocess.run([str(CAFE), "--gateway", self.origin, "--home", str(home), "--shot", str(Path(self.dir.name) / "phone.png"),
                            "--size", "844x390", "--touch", "--do", "click 60 30; drag 150 300 150 60; choose Sign out"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.state.token, "the item below the screen's foot was reached and pressed")

    def test_the_app_signs_in_reads_fetches_the_art_and_opens_a_room(self):
        from_list = self.serve_art()
        home = Path(self.dir.name) / "home"
        shot = Path(self.dir.name) / "signed-in.png"
        run = lambda steps, out: subprocess.run([str(CAFE), "--gateway", self.origin, "--home", str(home), "--shot", str(out),
                                                 "--size", "1280x800", "--do", steps], capture_output=True, text=True, timeout=120)
        # the sign-in screen: her handle, Tab, the password, Enter
        r = run(f"type {USER}; key tab; type {PASSWORD}; key enter", shot)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(stat.S_IMODE(os.stat(home / "cookie").st_mode), 0o600)
        sent = [(m, p) for m, p, *_ in self.state.seen]
        for want in [("POST", "/login"), ("GET", "/api/db"), ("POST", "/api/tools/list_agents"), ("POST", "/api/tools/quizzes")]:
            self.assertIn(want, sent)
        self.assertEqual(len([p for m, p in sent if p.startswith("/art/")]), len(from_list), "every missing file fetched, once")
        for path in from_list:
            self.assertEqual((home / "cache" / path).read_bytes(), self.state.art[path], path)
        # signed in already: straight to the house, the closed ensuite upstairs, its menu, Open this room
        self.state.seen.clear()
        manor = json.loads((APP / "generated" / "manor.json").read_text())
        x, y, w, h = manor["rooms"]["bath"]
        tx, ty = (1280 - 960) // 2, (800 - 576) // 2      # the whole grounds at one pixel an art pixel
        cx, cy = tx + x + w // 2, ty + y + h // 2
        r = run(f"key pageup; click {cx} {cy}; choose Open this room", Path(self.dir.name) / "opened.png")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(("POST", "/login"), [(m, p) for m, p, *_ in self.state.seen], "the cookie kept her signed in")
        self.assertFalse([p for m, p, *_ in self.state.seen if p.startswith("/art/")], "the cache is not asked for again")
        method, path, headers, body = self.last("PATCH", "/api/db/rooms/bath")
        self.assertEqual((headers.get("X-Catio"), json.loads(body)), ("1", {"data": {"closed": False}}))
        self.assertFalse(self.state.docs["rooms/bath"]["closed"])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + [a for a in sys.argv[2:] if a.startswith("-")])
