#!/usr/bin/env python3
"""The Catio's MCP server: how agents and models that aren't Claude Code sessions join the harness.

    python3 catio_mcp.py                      MCP over stdio (Codex, Gemini CLI, Cursor, Claude Desktop, any MCP client)
    python3 catio_mcp.py --serve DIR [--port 8791]
                                              serve the Catio's localhost folder DIR, plus the same tools as /api/*

An agent reports what it's doing (report_status) and becomes a cat. Charlotte drops files on it, writes
to it and manages it (drop_file, comment, manage); it picks those up from its inbox. An agent that
registers a wake command (for example ["codex", "exec", "resume", "{session}", "{message}"]) is woken
straight away instead: the command runs with the message, no shell involved.

Python standard library only. State lives in ~/.catio (or $CATIO_HOME): state.json and inbox/.
"""
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOME = Path(os.environ.get("CATIO_HOME") or Path.home() / ".catio")
RULES = Path(os.environ.get("CATIO_RULES") or Path(__file__).resolve().parent.parent / "rules.json")
MAX_FILE = 20 * 1024 * 1024
MOODS = ("needs", "busy", "review", "failed", "done")
LOCK = threading.Lock()


# ---------- state ----------
def load():
    try:
        s = json.loads((HOME / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        s = {}
    for k in ("agents", "files", "notes"):
        s.setdefault(k, {} if k == "agents" else [])
    return s


def store(s):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = HOME / ("state.%d.tmp" % os.getpid())
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, HOME / "state.json")


def now():
    return int(time.time() * 1000)


def new_id():
    return "%d-%s" % (now(), uuid.uuid4().hex[:6])


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name))[:120] or "file"


def need(args, *keys):
    for k in keys:
        if not str(args.get(k) or "").strip():
            raise ValueError(k + " is required")


def wake(agent, message):
    """Run the agent's wake command with the message, if it registered one. No shell: placeholders are whole args."""
    cmd = agent.get("wake")
    if not (isinstance(cmd, list) and cmd and all(isinstance(a, str) for a in cmd)):
        return False
    subs = {"{message}": message, "{session}": str(agent.get("session") or agent["id"]), "{agent}": agent["id"]}
    argv = [subs.get(a, a) for a in cmd]
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         cwd=agent.get("cwd") or None, start_new_session=True)
        return True
    except OSError:
        return False


# ---------- tools ----------
def house_rules(args):
    r = json.loads(RULES.read_text(encoding="utf-8"))
    return {"catio": r.get("catio"), "rules": [x for x in r["rules"] if x.get("on", True)]}


def report_status(args):
    need(args, "agent")
    with LOCK:
        s = load()
        a = s["agents"].setdefault(args["agent"], {"id": args["agent"], "since": now()})
        for k in ("name", "model", "provider", "title", "project", "repo", "ask", "link", "session", "cwd", "room"):
            if k in args:
                a[k] = str(args[k])[:500]
        if "mood" in args:
            if args["mood"] not in MOODS:
                raise ValueError("mood must be one of " + ", ".join(MOODS))
            a["mood"] = args["mood"]
        if "wake" in args:
            if args["wake"] is not None and not (isinstance(args["wake"], list) and all(isinstance(x, str) for x in args["wake"])):
                raise ValueError("wake must be a list of strings, e.g. [\"codex\", \"exec\", \"{message}\"]")
            a["wake"] = args["wake"]
        a["updated"] = now()
        store(s)
    return {"ok": True, "waiting": inbox({"agent": args["agent"]})}


def list_agents(args):
    s = load()
    out = []
    for a in s["agents"].values():
        if a.get("archived") and not args.get("archived"):
            continue
        waiting = sum(1 for f in s["files"] if f["for"] == a["id"] and f["status"] == "waiting")
        out.append(dict({k: v for k, v in a.items() if k != "wake"}, waiting=waiting, wakes=bool(a.get("wake"))))
    return {"agents": sorted(out, key=lambda a: -a.get("updated", 0))}


def inbox(args):
    need(args, "agent")
    s = load()
    a = s["agents"].get(args["agent"], {})
    seen = a.get("seenNotes", 0)
    return {
        "files": [{k: f[k] for k in ("id", "name", "type", "size", "note", "at")} for f in s["files"]
                  if f["for"] == args["agent"] and f["status"] == "waiting"],
        "notes": [n for n in s["notes"] if n["cat"] == args["agent"] and n["author"] == "charlotte" and n["at"] > seen],
        "request": a.get("request"),
    }


def pick_up(args):
    need(args, "id")
    with LOCK:
        s = load()
        f = next((f for f in s["files"] if f["id"] == args["id"]), None)
        if not f:
            raise ValueError("no such file")
        data = (HOME / "inbox" / f["file"]).read_bytes()
        f.update(status="picked", pickedAt=now(), pickedBy=args.get("agent") or f["for"])
        store(s)
    return {"name": f["name"], "type": f["type"], "base64": base64.b64encode(data).decode()}


def drop_file(args):
    need(args, "name", "base64", "for")
    data = base64.b64decode(args["base64"], validate=True)
    if len(data) > MAX_FILE:
        raise ValueError("files are capped at 20 MiB")
    fid = new_id()
    (HOME / "inbox").mkdir(parents=True, exist_ok=True)
    fname = fid + "-" + safe_name(args["name"])
    (HOME / "inbox" / fname).write_bytes(data)
    rec = {"id": fid, "for": args["for"], "name": str(args["name"])[:200], "type": str(args.get("type") or "application/octet-stream"),
           "size": len(data), "note": str(args.get("note") or "")[:2000], "file": fname, "at": now(), "status": "waiting"}
    with LOCK:
        s = load()
        s["files"].append(rec)
        store(s)
        agent = s["agents"].get(args["for"])
    woke = bool(agent) and wake(agent, "[Catio] Delivery for you: %s (%s, %d bytes), file id %s. %s Fetch it with the catio "
                               "server's pick_up tool." % (rec["name"], rec["type"], rec["size"], fid, ("Charlotte's note: " + rec["note"]) if rec["note"] else ""))
    return {"id": fid, "woke": woke}


def comment(args):
    need(args, "cat", "text")
    author = args.get("author") or "charlotte"
    if author not in ("charlotte", "agent", "session"):
        raise ValueError("author is charlotte, agent or session")
    note = {"id": new_id(), "cat": args["cat"], "text": str(args["text"])[:4000], "author": author, "at": now()}
    with LOCK:
        s = load()
        s["notes"].append(note)
        a = s["agents"].get(args["cat"])
        if a and author != "charlotte":
            a["seenNotes"] = note["at"]
        store(s)
    woke = author == "charlotte" and bool(a) and wake(a, "[Catio] Charlotte says: " + note["text"])
    return {"id": note["id"], "woke": woke}


def comments(args):
    need(args, "cat")
    return {"notes": [n for n in load()["notes"] if n["cat"] == args["cat"]][-int(args.get("limit") or 50):]}


def manage(args):
    need(args, "cat", "action")
    act, value = args["action"], args.get("value")
    with LOCK:
        s = load()
        a = s["agents"].get(args["cat"])
        if not a:
            raise ValueError("no such agent")
        if act == "rename":
            need(args, "value"); a["name"] = str(value)[:60]
        elif act == "move":
            need(args, "value"); a["room"] = str(value)[:40]
        elif act in ("archive", "unarchive"):
            a["archived"] = act == "archive"
        elif act in ("pause", "resume", "wrap_up"):
            a["request"] = {"action": act, "at": now()}
        elif act == "message":
            need(args, "value")
        elif act == "done":
            a.pop("request", None)
        else:
            raise ValueError("action is rename, move, archive, unarchive, pause, resume, wrap_up, message or done")
        store(s)
    woke = False
    if act in ("pause", "resume", "wrap_up"):
        woke = wake(a, "[Catio] Request: " + act)
    elif act == "message":
        comment({"cat": args["cat"], "text": value, "author": "charlotte"})
        woke = bool(a.get("wake"))
    return {"ok": True, "woke": woke}


S = {"type": "string"}
TOOLS = {
    "house_rules": (house_rules, "The KittyChat house rules every agent in the Catio follows. Read them when you start.", {}, []),
    "report_status": (report_status, "Join the Catio as a cat, or update your cat: what you're working on and whether you need Charlotte. "
                      "Call it when you start, when you need her, and when you finish. Returns what's waiting for you.",
                      {"agent": dict(S, description="Your stable id, e.g. codex-montfortoise"), "name": S, "model": dict(S, description="e.g. gpt-5, gemini-2.5-pro"),
                       "provider": dict(S, description="openai, google, anthropic, local..."), "title": S, "project": S, "repo": dict(S, description="owner/repo"),
                       "mood": {"type": "string", "enum": list(MOODS)}, "ask": dict(S, description="What you need from her, when mood is needs"),
                       "link": S, "session": dict(S, description="Your own session id, for the wake command"), "cwd": S,
                       "wake": {"type": ["array", "null"], "items": S, "description": "Command that wakes you with a message; placeholders {message} {session} {agent}"}},
                      ["agent"]),
    "list_agents": (list_agents, "Every agent cat in the Catio.", {"archived": {"type": "boolean"}}, []),
    "inbox": (inbox, "Files, notes from Charlotte, and any request (pause, resume, wrap_up) waiting for an agent.", {"agent": S}, ["agent"]),
    "pick_up": (pick_up, "Take a file from your inbox: returns it as base64 and marks it picked up.", {"id": S, "agent": S}, ["id"]),
    "drop_file": (drop_file, "Give a file to an agent's cat (and wake it, if it can be woken).",
                  {"name": S, "type": S, "base64": S, "for": dict(S, description="The agent id"), "note": S}, ["name", "base64", "for"]),
    "comment": (comment, "Add to a cat's conversation. Agents answer Charlotte with author agent.",
                {"cat": S, "text": S, "author": {"type": "string", "enum": ["charlotte", "agent", "session"]}}, ["cat", "text"]),
    "comments": (comments, "A cat's conversation, oldest first.", {"cat": S, "limit": {"type": "integer"}}, ["cat"]),
    "manage": (manage, "Manage an agent's cat: rename, move (room key), archive, unarchive, pause, resume, wrap_up, message, done (clear a request).",
               {"cat": S, "action": {"type": "string", "enum": ["rename", "move", "archive", "unarchive", "pause", "resume", "wrap_up", "message", "done"]}, "value": S},
               ["cat", "action"]),
}


def call(name, args):
    if name not in TOOLS:
        raise KeyError(name)
    return TOOLS[name][0](args or {})


# ---------- MCP over stdio ----------
def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None                                   # a notification
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        result = {"protocolVersion": ver, "capabilities": {"tools": {}}, "serverInfo": {"name": "catio", "version": "0.1.0"},
                  "instructions": "The Catio is Charlotte's harness. Read house_rules, report_status when you start, need her, or finish, and check inbox."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                            for n, (_, d, p, r) in TOOLS.items()]}
    elif method == "tools/call":
        p = msg.get("params") or {}
        try:
            out = call(p.get("name"), p.get("arguments"))
            result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}], "structuredContent": out}
        except KeyError:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool " + str(p.get("name"))}}
        except (ValueError, OSError) as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: " + str(method)}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle(json.loads(line))
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


# ---------- the localhost folder, with the tools as /api/* ----------
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def api(self, name, args):
        try:
            self.reply(200, call(name, args))
        except KeyError:
            self.reply(404, {"error": "no such tool"})
        except (ValueError, OSError) as e:
            self.reply(400, {"error": str(e)})

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            return self.api(u.path[5:], {k: v[0] for k, v in parse_qs(u.query).items()})
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if not u.path.startswith("/api/"):
            return self.reply(404, {"error": "not found"})
        # same-origin only: the page is served from here, so a browser tab elsewhere can't post
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.reply(403, {"error": "cross-origin"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_FILE * 2:
            return self.reply(413, {"error": "too large"})
        try:
            args = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.reply(400, {"error": "bad json"})
        self.api(u.path[5:], args)


def serve(folder, port):
    handler = lambda *a, **k: Handler(*a, directory=folder, **k)
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("The Catio is at http://localhost:%d  (Ctrl+C to stop)" % port, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if "--serve" in sys.argv:
        i = sys.argv.index("--serve")
        folder = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") else "."
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8791
        serve(os.path.abspath(folder), port)
    else:
        stdio()
