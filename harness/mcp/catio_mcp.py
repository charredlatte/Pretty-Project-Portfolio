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
import time
import urllib.request
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_tokens   # noqa: E402  (beside this file, standard library only)

HOME = Path(os.environ.get("CATIO_HOME") or Path.home() / ".catio")
DECIDE_URL = os.environ.get("CATIO_DECIDE_URL", "").rstrip("/")   # a System One server (laya-serve on this PC, or Jev); none: decide refuses
DECIDE_KEY = os.environ.get("CATIO_DECIDE_KEY", "")
DECIDE_TIMEOUT = 8
KEEP_DECISIONS = 500
RULES = Path(os.environ.get("CATIO_RULES") or Path(__file__).resolve().parent.parent / "rules.json")
MAX_FILE = 20 * 1024 * 1024
MAX_GRAPH = 64 * 1024
MOODS = ("needs", "busy", "review", "failed", "done")
MAX_NOTES = 500
KINDS = {"string": str, "boolean": bool, "integer": int, "number": (int, float), "array": list, "object": dict, "null": type(None)}


class StateLock:
    """One writer at a time to state.json, across threads and across processes (the stdio servers, --serve). The lock is
    the exclusive creation of state.lock; one a crash left behind is taken over after STALE seconds. On Windows a lock
    just let go can be "delete pending" while another process still looks at it, and creating it then is a
    PermissionError rather than FileExistsError: it is busy all the same, so it is waited for, not given up on."""
    STALE, WAIT = 10, 15   # a waiter outlasts STALE, so it always gets to take over a lock a crash left behind

    def __enter__(self):
        HOME.mkdir(parents=True, exist_ok=True)
        path, deadline = HOME / "state.lock", time.monotonic() + self.WAIT
        while True:
            try:
                os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except (FileExistsError, PermissionError):
                pass
            try:
                if time.time() - path.stat().st_mtime > self.STALE:
                    path.unlink()
            except FileNotFoundError:
                continue
            except PermissionError:
                pass   # Windows: being let go or looked at right now
            if time.monotonic() > deadline:
                raise OSError("state.json is busy: another Catio process holds it")
            time.sleep(0.01)

    def __exit__(self, *exc):
        (HOME / "state.lock").unlink(missing_ok=True)


LOCK = StateLock()


class UnknownTool(LookupError):
    pass
# The café whose look tokens and set_tokens read and write: its folder (index.html, art/skin.json). --serve DIR sets
# it; else CATIO_CAFE; else the repo's own catio/ when this runs from a clone.
CAFE = os.environ.get("CATIO_CAFE") or ""


# ---------- state ----------
def load():
    try:
        s = json.loads((HOME / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        s = {}
    for k in ("agents", "files", "notes"):
        s.setdefault(k, {} if k == "agents" else [])
    for n in s["notes"]:   # the owner's notes from before accounts were written as "charlotte"
        if n.get("author") == "charlotte":
            n["author"] = "owner"
    return s


def store(s):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = HOME / ("state.%d.tmp" % os.getpid())
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
    for wait in (0.01, 0.05, 0.1, 0.25, 0.5, 1, 0):   # Windows refuses a replace while anything has the file open
        try:
            return os.replace(tmp, HOME / "state.json")
        except PermissionError:
            if not wait:
                raise
            time.sleep(wait)


def now():
    return int(time.time() * 1000)


def new_id():
    return "%d-%s" % (now(), uuid.uuid4().hex[:6])


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name))[:120] or "file"


def typed(args, properties):
    """Refuse an argument that isn't the JSON type its schema names. A null stands for an omitted one."""
    for key, spec in properties.items():
        named, value = spec.get("type"), args.get(key)
        if named is None or value is None:
            continue
        kinds = [named] if isinstance(named, str) else named
        if not any(isinstance(value, KINDS[k]) and not (isinstance(value, bool) and k in ("integer", "number")) for k in kinds):
            raise ValueError("%s must be %s" % (key, " or ".join(kinds)))


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


def _project_slug(v):
    """The project's key, as catio/index.html's slug() makes it from a repo name: underscores survive, anything
    else becomes a dash. Identical to the gateway's, so an audit or a map written anywhere is read everywhere.
    The audit and the project map share it: that is what puts them in one filing cabinet."""
    return re.sub(r"[^a-z0-9_-]+", "-", str(v).split("/")[-1].lower()).strip("-")[:80] or "none"


def audit(args):
    """The opening audit the house rules start a session with, kept per project as the gateway keeps it."""
    need(args, "repo", "summary")
    key = _project_slug(args["repo"])
    rec = {"repo": str(args["repo"])[:200], "summary": str(args["summary"])[:4000],
           "by": str(args.get("by") or "agent")[:200], "at": now()}
    with LOCK:
        s = load()
        s.setdefault("audits", {})[key] = rec
        store(s)
    return {"ok": True, "doc": "audits/" + key}


def graph(args):
    """The project map graphify built, kept per project beside the audit, as the gateway keeps it."""
    need(args, "repo", "doc")
    if not isinstance(args["doc"], dict):
        raise ValueError("doc is the object graph_doc.py prints after the document id, or the catio-graph.json it saves")
    body = json.dumps(args["doc"], ensure_ascii=False)
    if len(body) > MAX_GRAPH:
        raise ValueError(f"that map is {round(len(body) / 1024)} KB, over the {MAX_GRAPH // 1024} KB a map may be")
    key = _project_slug(args["repo"])
    rec = dict(json.loads(body), repo=str(args["repo"])[:200], by=str(args.get("by") or "agent")[:200], at=now())
    with LOCK:
        s = load()
        s.setdefault("graphs", {})[key] = rec
        store(s)
    return {"ok": True, "doc": "graphs/" + key}


def report_status(args):
    need(args, "agent")
    with LOCK:
        s = load()
        a = s["agents"].setdefault(args["agent"], {"id": args["agent"], "since": now()})
        for k in ("name", "model", "provider", "title", "project", "repo", "branch", "ask", "link", "session", "via", "cwd", "room"):
            if args.get(k) is not None:
                a[k] = str(args[k])[:500]
        if args.get("mood") is not None:
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
        said = [n for n in s["notes"] if n["cat"] == a["id"] and n["author"] in ("session", "agent")]   # what it last said, for the queen
        out.append(dict({k: v for k, v in a.items() if k != "wake"}, waiting=waiting, wakes=bool(a.get("wake")),
                        **({"said": {"text": said[-1]["text"], "at": said[-1]["at"]}} if said else {})))
    return {"agents": sorted(out, key=lambda a: -a.get("updated", 0))}


def inbox(args):
    """With mark, only what hasn't been handed over yet, and now it has (as the gateway's session hooks use it).
    Handing over keeps its own place (handedNotes), apart from what an answer counts as read (seenNotes)."""
    need(args, "agent")
    with LOCK:
        s = load()
        a = s["agents"].get(args["agent"])
        mark = args.get("mark") is True and a is not None
        files = [f for f in s["files"] if f["for"] == args["agent"] and f["status"] == "waiting" and not (mark and f.get("handed"))]
        a_ = a or {}
        since = a_.get("handedNotes", a_.get("seenNotes", 0)) if mark else a_.get("seenNotes", 0)
        authors = ("owner",) if args["agent"] == "queen" else ("owner", "queen")   # a cat hears the owner and her assistant
        notes = [n for n in s["notes"] if n["cat"] == args["agent"] and n["author"] in authors and n["at"] > since]
        request = (a or {}).get("request")
        if mark:
            if request and request.get("handed"):
                request = None
            for f in files:
                f["handed"] = now()
            if notes:
                a["handedNotes"] = notes[-1]["at"]
                a["seenNotes"] = max(a.get("seenNotes", 0), a["handedNotes"])
            if request:
                a["request"] = dict(request, handed=now())
            if files or notes or request:
                store(s)
    return {"files": [{k: f[k] for k in ("id", "name", "type", "size", "note", "at")} for f in files], "notes": notes, "request": request}


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
    author = args.get("author") or "owner"
    if author == "charlotte":   # the owner's name on the wire before accounts: still taken, stored as owner
        author = "owner"
    if author not in ("owner", "agent", "session", "queen"):
        raise ValueError("author is owner, agent, session or queen")
    note = {"id": new_id(), "cat": args["cat"], "text": str(args["text"])[:4000], "author": author, "at": now()}
    with LOCK:
        s = load()
        s["notes"].append(note)
        a = s["agents"].get(args["cat"])
        if a and author not in ("owner", "queen"):
            a["seenNotes"] = note["at"]
        store(s)
    woke = author in ("owner", "queen") and bool(a) and wake(a, "[Catio] %s: %s" % ("Charlotte says" if author == "owner" else "The queen says", note["text"]))
    return {"id": note["id"], "woke": woke}


def comments(args):
    need(args, "cat")
    limit = min(max(args.get("limit") or 50, 1), MAX_NOTES)
    return {"notes": [n for n in load()["notes"] if n["cat"] == args["cat"]][-limit:]}


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
        comment({"cat": args["cat"], "text": value, "author": "owner"})
        woke = bool(a.get("wake"))
    return {"ok": True, "woke": woke}


QUIZ_MAX = 5
QUIZ_KINDS = ("unblock", "litterbox", "decision")   # unblocking a cat, sorting a litter box note, a decision waiting on her


def _quiz_of(args):
    need(args, "title")
    qs = args.get("questions")
    if not isinstance(qs, list) or not qs or len(qs) > QUIZ_MAX:
        raise ValueError("questions is a list of 1 to 5 {q, options, free}")
    out = []
    for x in qs:
        q = x if isinstance(x, dict) else {"q": x}
        text = str(q.get("q") or q.get("question") or "").strip()[:300]
        if not text:
            raise ValueError("every question needs its q")
        options = [str(o).strip()[:300] for o in (q.get("options") if isinstance(q.get("options"), list) else [])]
        options = [o for o in options if o][:12]
        out.append({"q": text, "options": options, "free": q.get("free") is True or not options})
    return str(args["title"]).strip()[:120], out


def quiz(args):
    """Homework the queen (or Charlotte) sets for Charlotte, a card in her quest log (as the gateway's quiz)."""
    title, questions = _quiz_of(args)
    if args.get("kind") and args["kind"] not in QUIZ_KINDS:
        raise ValueError("kind is unblock, litterbox or decision")
    kind = args.get("kind") or "unblock"
    if kind != "unblock" and (len(questions) != 1 or len(questions[0]["options"]) < 2):
        raise ValueError("a %s card is one question with 2 to 12 options" % kind)
    clip = lambda k, n: str(args.get(k) or "")[:n]
    ref = re.sub(r"[^A-Za-z0-9_-]", "", clip("ref", 80))
    rec = {"id": kind + "-" + ref if ref else new_id(), "for": clip("for", 200), "kind": kind, "title": title, "questions": questions,
           "note": clip("note", 4000), "from": clip("from", 200), "hint": clip("hint", 300),
           "by": "owner" if args.get("by") in ("owner", "charlotte") else "queen", "at": now(), "status": "set"}
    with LOCK:
        s = load()
        qs = s.setdefault("quizzes", [])
        old = next((q for q in qs if q["id"] == rec["id"]), None)
        if old and old.get("status") == "done":   # dealt again after she answered: her answer stands
            return {"id": rec["id"], "done": True}
        if old:   # dealt again while open: it keeps its place in the deck
            rec["at"] = old.get("at", rec["at"])
            qs[qs.index(old)] = rec
        else:
            qs.append(rec)
        store(s)
    return {"id": rec["id"]}


def quizzes(args):
    return {"quizzes": [q for q in load().get("quizzes", []) if (args.get("done") is True or q.get("status") != "done")
                        and (not args.get("kind") or q.get("kind", "unblock") == args["kind"])]}


def forget(args):
    """The cards already filed, cleared by id."""
    ids = {str(i) for i in args.get("quizzes") or []}
    with LOCK:
        s = load()
        before = len(s.get("quizzes", []))
        s["quizzes"] = [q for q in s.get("quizzes", []) if q["id"] not in ids
                        or (q.get("kind", "unblock") == "unblock" and q.get("status") != "done")]   # a cat still waits on it
        store(s)
    return {"forgotten": before - len(s["quizzes"])}


def answer(args):
    """Charlotte hands homework in: her answers go to the cat, as her words, and to the queen."""
    need(args, "quiz")
    given = args.get("answers")
    with LOCK:
        s = load()
        q = next((q for q in s.get("quizzes", []) if q["id"] == args["quiz"]), None)
        if not q:
            raise ValueError("no such quiz")
        if q.get("status") == "done":
            raise ValueError("that homework is handed in already")
        given = [str(a if a is not None else "").strip()[:1000] for a in given] if isinstance(given, list) else []
        if len(given) != len(q["questions"]) or any(not a for a in given):
            raise ValueError("answers is one answer per question, in order")
        q.update(status="done", answers=given, answeredAt=now())
        store(s)
        if q.get("kind", "unblock") != "unblock":   # a card is kept for filing, not told
            return {"ok": True, "told": False}
        told = bool(q["for"]) and q["for"] in s["agents"]
    text = "Homework handed in: " + q["title"] + "\n" + "\n".join("%d. %s \u2192 %s" % (i + 1, x["q"], given[i]) for i, x in enumerate(q["questions"]))
    if told:
        comment({"cat": q["for"], "text": text, "author": "owner"})
    comment({"cat": "queen", "text": text + (("\n(for %s, %s)" % (q["for"], "told" if told else "not a cat here")) if q["for"] else ""), "author": "owner"})
    return {"ok": True, "told": told}

# ---------- decisions: the one-bit questions, answered by whatever model is there (same as the gateway's src/decide.js) ----------
# Two shapes, and decide() uses whichever the answerer speaks: a model that takes {state, questions} itself
# (POST /v1/systemone: laya-serve, Jev) or any other model, prompted for the same answers and read back out of its
# reply (POST /v1/chat/completions: Ollama, llama.cpp, a hosted API). src/decide.js carries the contract in full.
TYPES = ("noul", "choice", "score")
SYSTEM_ONE = re.compile(r"^(?:@cf/cloudflare/clef|typesafe/jev)")   # the ids known to take questions themselves
PRESETS = {
    "easy": {   # the rubric of docs/delegation.md as six yes/no questions about a task's text
        "spelled_out": {"type": "noul", "instructions": "Does the task name exactly what to produce or change (a file, a test, an output), with no design judgement left open?"},
        "checkable": {"type": "noul", "instructions": "Would a test, a build or a diff show whether the task is done?"},
        "small": {"type": "noul", "instructions": "Is the task confined to one file, or read-only across several?"},
        "held_path": {"type": "noul", "instructions": "Does the task touch harness/, .claude/, .github/ (the workflows), the house rules, merging, pushing, or a default branch?"},
        "private": {"type": "noul", "instructions": "Does the task involve legal, money, health or other private personal matters?"},
        "browser": {"type": "noul", "instructions": "Does the task need a web browser, a login, or a key?"},
    },
}


# What a caller is likely to have called the question's text instead. The field is `instructions` and only that, and a
# question carrying anything else is refused rather than guessed at; these are only so the refusal can name the
# mistake. Same list as the gateway's src/decide.js.
NEARLY = ("instruction", "question", "prompt", "ask", "description", "text", "q")
UNSAID = 0.55   # an answer a model stated with no confidence of its own: under every floor the café uses (0.6)


def _shape(args):
    qs = PRESETS.get(args.get("preset")) if args.get("preset") else args.get("questions")
    if args.get("preset") and not qs:
        raise ValueError("preset is one of " + ", ".join(PRESETS))
    if not isinstance(qs, dict) or not qs or len(qs) > 64:
        raise ValueError("questions is an object of 1 to 64 named typed questions")
    out = {}
    for name, q in qs.items():
        if not isinstance(q, dict) or q.get("type") not in TYPES:
            raise ValueError("%s: type is noul, choice or score" % name)
        clean = {"type": q["type"]}
        # Every question needs its words: Clef refuses one without them by calling the whole body malformed, and
        # never says which question was short. Name it here, as src/decide.js does, and name the key it was written
        # under when that is what went wrong.
        if q.get("instructions") is None or not str(q["instructions"]).strip():
            near = next((k for k in NEARLY if q.get(k) is not None and str(q[k]).strip()), None)
            raise ValueError("%s: instructions is the question in words%s" % (name, ', not "%s"' % near if near else ""))
        clean["instructions"] = str(q["instructions"])[:1000]
        c = q.get("criteria")
        if q["type"] == "choice":
            if not isinstance(c, dict) or not 2 <= len(c) <= 64:
                raise ValueError("%s: a choice needs criteria, 2 to 64 named options" % name)
            clean["criteria"] = {str(k)[:100]: str(v)[:500] for k, v in c.items()}
        elif q["type"] == "score":
            if not isinstance(c, list) or not 2 <= len(c) <= 64:
                raise ValueError("%s: a score needs criteria, an ordered list of 2 or more levels" % name)
            clean["criteria"] = [str(v)[:500] for v in c]
        elif isinstance(c, dict):
            clean["criteria"] = {"true": str(c.get("true", "yes"))[:500], "false": str(c.get("false", "no"))[:500]}
        out[name] = clean
    state = args.get("state")
    if state is None or not isinstance(state, (str, dict, list)):
        raise ValueError("state is the text or JSON the questions are about")
    text = state if isinstance(state, str) else json.dumps(state)
    if not text.strip():
        raise ValueError("state is empty")
    if len(text) > 60000:
        raise ValueError("state is over 60000 characters")
    return {"state": state, "questions": out}


def _verdict(a):
    if not isinstance(a, dict):
        return None
    if a.get("type") == "choice" or "choice" in a:
        return a.get("choice")
    if a.get("type") == "noul" or isinstance(a.get("noul"), (int, float)):
        return "yes" if (a.get("noul") or 0) >= 0.5 else "no"
    if isinstance(a.get("score"), (int, float)):
        return str(round(a["score"]))
    return None


def _confidence(a):
    if not isinstance(a, dict):
        return 0
    if isinstance(a.get("confidence"), (int, float)):
        return a["confidence"]
    if isinstance(a.get("noul"), (int, float)):
        return max(a["noul"], 1 - a["noul"])
    return 0


def _ask(body):
    """The same questions as one prompt, for a model that doesn't take them itself (the gateway's ask())."""
    asked, wanted = [], []
    for name, q in body["questions"].items():
        if q["type"] == "noul":
            asked.append("- %s: %s Answer yes or no." % (name, q["instructions"]))
            wanted.append('%s: {"answer": "yes" or "no", "confidence": 0 to 1}' % json.dumps(name))
        elif q["type"] == "choice":
            asked.append("- %s: %s Answer with one of %s." % (name, q["instructions"],
                         ", ".join("%s (%s)" % (k, v) for k, v in q["criteria"].items())))
            wanted.append('%s: {"answer": one of %s, "confidence": 0 to 1}'
                          % (json.dumps(name), " | ".join(json.dumps(k) for k in q["criteria"])))
        else:
            top = len(q["criteria"]) - 1
            asked.append("- %s: %s Answer with a whole number from 0 to %d, where %s."
                         % (name, q["instructions"], top, ", ".join("%d is %s" % (i, v) for i, v in enumerate(q["criteria"]))))
            wanted.append('%s: {"answer": 0 to %d, "confidence": 0 to 1}' % (json.dumps(name), top))
    state = body["state"]
    return "\n".join([
        "Answer every question about the state below. Reply with one JSON object and nothing else: no prose, no",
        "explanation, no code fence.",
        "Give each answer a confidence, from 0 (a coin toss) to 1 (certain): how sure you are of that answer. An",
        "answer with no confidence is read as barely better than a coin toss, so say one.",
        "",
        "STATE:",
        state if isinstance(state, str) else json.dumps(state),
        "",
        "QUESTIONS:",
        *asked,
        "",
        "Reply with exactly:",
        "{" + ", ".join(wanted) + "}",
    ])


def _first_json(text):
    """The first balanced JSON object in a reply, whatever prose or code fence surrounds it."""
    i = text.find("{")
    while i >= 0:
        depth, in_str, esc = 0, False, False
        for j in range(i, len(text)):
            ch = text[j]
            if esc:
                esc = False
                continue
            if in_str:
                if ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        v = json.loads(text[i:j + 1])
                        if isinstance(v, dict):
                            return v
                    except ValueError:
                        pass            # prose that merely looks like an object: try the next {
                    break
        i = text.find("{", i + 1)
    return None


def _num(v):
    if isinstance(v, bool):             # a boolean is a yes or no, never a probability
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:           # a blank string is no number: float("") raises, but "" must not read as a confident no
        return None
    pct = s.endswith("%")
    try:
        n = float(s[:-1] if pct else s)
    except ValueError:
        return None
    return n / 100 if pct else n


def _truth(v):
    """yes or no as a model writes it; a number is left to be read as a probability instead."""
    if isinstance(v, bool):
        return v
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    return True if s in ("y", "yes", "true", "t") else False if s in ("n", "no", "false", "f") else None


def _clamp(n):
    return min(1.0, max(0.0, n))


def _r4(n):
    """To four decimals, as a System One model's own probabilities come back. Everything here is 0 or more. A whole
    number comes back as one, so a score reads 2 in the JSON rather than 2.0, as the gateway's own answer does."""
    r = int(n * 1e4 + 0.5) / 1e4
    return int(r) if r == int(r) else r


def _prob(yes, c):
    # A confidence below a coin toss would flip the answer it was given for, so it is held at the toss: the answer
    # the model stated survives and _confidence reads about 0.5, under every floor the café uses.
    return _r4(max(0.5, _clamp(c)) if yes else min(0.49, 1 - _clamp(c)))


def _answer(v, q):
    """One answer, from whatever the model put under the question's name."""
    if v is None:
        return None
    said = v if isinstance(v, dict) else {"answer": v}
    got = next((said[k] for k in ("answer", "value", "choice", "score", "noul", "level") if said.get(k) is not None), None)
    if got is None:
        return None
    c = _num(said.get("confidence"))
    sure = UNSAID if c is None else _clamp(c)
    if q["type"] == "noul":
        yes = _truth(got)
        if yes is not None:
            return {"type": "noul", "noul": _prob(yes, sure)}
        n = _num(got)                   # a bare probability in place of a yes or no
        return None if n is None or n < 0 or n > 1 else {"type": "noul", "noul": _r4(n)}
    if q["type"] == "choice":
        keys = list(q["criteria"])
        pick = next((k for k in keys if k.lower() == str(got).strip().lower()), None)
        if pick is None:
            return None                 # not one of the options: unanswered, not guessed
        each = (1 - sure) / max(1, len(keys) - 1)
        return {"type": "choice", "choice": pick, "confidence": _r4(sure),
                "probabilities": {k: _r4(sure if k == pick else each) for k in keys}}
    top = len(q["criteria"]) - 1
    n = _num(got)
    if n is None:                       # a level by name rather than by number
        i = next((i for i, lv in enumerate(q["criteria"]) if lv.lower() == str(got).strip().lower()), None)
        if i is None:
            return None
        n = i
    return {"type": "score", "score": _r4(min(top, max(0, n))), "confidence": _r4(sure)}


def _read(text, questions):
    """The answers read back out of a model's reply, in the same shape a System One model returns."""
    said = _first_json("" if text is None else str(text))
    out = {}
    if not said:
        return out
    for name, q in questions.items():
        a = _answer(said.get(name), q)
        if a:
            out[name] = a
    return out


def _post(path, body, timeout):
    req = urllib.request.Request(DECIDE_URL + path, data=json.dumps(body).encode(), method="POST",
                                 headers=dict({"Content-Type": "application/json"}, **({"Authorization": "Bearer " + DECIDE_KEY} if DECIDE_KEY else {})))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError("the decider failed: %s" % e)


def _system_one(body, model, timeout):
    """A model that takes the questions itself and answers them."""
    reply = _post("/v1/systemone", dict(body, model=model) if model else body, timeout)
    if not isinstance(reply, dict) or not isinstance(reply.get("answers"), dict):
        raise ValueError("the decider answered without answers")
    return {"model": str(reply.get("model") or model or "system-one"), "answers": reply["answers"], "usage": reply.get("usage")}


def _chat(body, model, timeout):
    """Any other model: the questions as one prompt, the answers read back out of its reply."""
    sent = {"messages": [{"role": "user", "content": _ask(body)}], "temperature": 0}
    reply = _post("/v1/chat/completions", dict(sent, model=model) if model else sent, timeout)
    if not isinstance(reply, dict):
        raise ValueError("the decider answered no text")
    text = reply.get("response")        # Workers AI says response, an OpenAI-compatible API choices
    if text is None:
        ch = reply.get("choices")
        if isinstance(ch, list) and ch and isinstance(ch[0], dict) and isinstance(ch[0].get("message"), dict):
            text = ch[0]["message"].get("content")
    if text is None:
        raise ValueError("the decider answered no text")
    return {"model": str(model or reply.get("model") or "chat"), "answers": _read(text, body["questions"]), "usage": reply.get("usage")}


def decide(args):
    """A typed decision about a state, from whatever model at CATIO_DECIDE_URL answers: one that takes the questions
    itself (/v1/systemone) or any other, prompted for the same answers (/v1/chat/completions). With kind, logged beside
    old (what the old path chose); under floor it is the decider not deciding (sure False, agree None); ref names what
    was decided about."""
    body = _shape(args)
    if not DECIDE_URL:
        raise ValueError("no decider: set CATIO_DECIDE_URL to a model's server, either speaking the System One API "
                         "(laya-serve on this computer, or Jev) or with an OpenAI-compatible /v1/chat/completions")
    model = str(args["model"]) if args.get("model") else ""
    # the shape this model is known to speak first, then the other, so a model nobody listed here still answers
    ways = ["chat", "systemone"] if model and not SYSTEM_ONE.match(model) else ["systemone", "chat"]
    until = time.monotonic() + DECIDE_TIMEOUT
    out, last = None, None
    for way in ways:
        left = until - time.monotonic()
        if left < 0.5:                  # not enough of the budget left to be worth a round trip
            break
        try:
            got = _system_one(body, model, left) if way == "systemone" else _chat(body, model, left)
        except ValueError as e:
            last = e
            continue
        if got["answers"]:
            got["via"] = way
            out = got
            break
        last = ValueError("the decider answered nothing readable")
    if out is None:
        raise last if last else ValueError("the decider didn't answer")
    if args.get("kind"):
        first = next(iter(out["answers"]), None)
        old = None if args.get("old") is None else str(args["old"])[:200]
        got = _verdict(out["answers"].get(first))
        floor = args["floor"] if isinstance(args.get("floor"), (int, float)) else None
        sure = floor is None or _confidence(out["answers"].get(first)) >= floor
        with LOCK:
            s = load()
            log = s.setdefault("decisions", [])
            entry = {"id": new_id(), "at": now(), "kind": str(args["kind"])[:40], "model": out["model"], "via": out.get("via"),
                     "questions": list(out["answers"]), "answers": out["answers"], "verdict": got, "sure": sure, "old": old,
                     "agree": None if old is None or not sure else got == old}
            if floor is not None:
                entry["floor"] = floor
            if args.get("ref") is not None:
                entry["ref"] = str(args["ref"])[:200]
            log.append(entry)
            del log[:-KEEP_DECISIONS]
            store(s)
    return out


S = {"type": "string"}
KIND = {"type": "string", "enum": list(QUIZ_KINDS)}
# One question for the decide tool. It is spelled out because a caller that guesses the key (question, prompt, ask)
# used to reach the model with no text at all, which the model then refused for a reason naming nothing the caller
# did wrong. decide() accepts those spellings too, but the schema is what stops the guess.
QUESTION = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": list(TYPES), "description": "noul is yes/no, choice is one of named options, score is a level on a scale"},
        "instructions": dict(S, description="The question to ask about the state"),
        "criteria": {"description": "A choice: {option: what it means}, 2 to 64 of them. A score: an ordered list of 2 or more levels, lowest first. A noul: nothing, or {true: what yes means, false: what no means}"},
    },
    "required": ["type", "instructions"],
}
# ---------- the café's look as a design tokens file (design_tokens.py; the gateway's src/tokens.js) ----------
def _cafe():
    folder = Path(CAFE) if CAFE else Path(__file__).resolve().parent.parent.parent / "catio"
    if not (folder / "index.html").is_file():
        raise ValueError("no café folder here: serve one (--serve DIR) or set CATIO_CAFE to it")
    return folder, design_tokens.Page((folder / "index.html").read_text(encoding="utf-8"))


def _skin(folder):
    try:
        j = json.loads((folder / "art" / "skin.json").read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


def tokens(args):
    """The café's colours and sizes as a design tokens file: its art/skin.json over the page's own."""
    mode = "dark" if args.get("mode") == "dark" else "light"
    folder, page = _cafe()
    return {"mode": mode, "file": design_tokens.to_dtcg(page, _skin(folder), mode)}


def set_tokens(args):
    """A design tokens file brought into the café's art/skin.json, as The look's Import tokens… does."""
    mode = args.get("mode") or "light"
    if mode not in ("light", "dark"):
        raise ValueError("mode is light or dark")
    doc = args.get("file")
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except ValueError:
            doc = None
    if not isinstance(doc, dict):
        raise ValueError("file is a design tokens file, as JSON")
    folder, page = _cafe()
    with LOCK:
        skin = _skin(folder)
        nxt, report = design_tokens.import_into(page, skin, mode, doc, args.get("replace") is True)
        if not report["tokens"] and not report["refused"]:
            raise ValueError("the file has none of the café's tokens" + (" (%d of its own)" % report["foreign"] if report["foreign"] else ""))
        for m, key in (("light", "tokens"), ("dark", "dark")):
            if nxt[m]:
                skin[key] = dict(sorted(nxt[m].items()))
            else:
                skin.pop(key, None)
        (folder / "art").mkdir(parents=True, exist_ok=True)
        tmp = folder / "art" / ("skin.%d.tmp" % os.getpid())
        tmp.write_text(json.dumps(skin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, folder / "art" / "skin.json")
    return report


TOOLS = {
    "house_rules": (house_rules, "The KittyChat house rules every agent in the Catio follows. Read them when you start.", {}, []),
    "report_status": (report_status, "Join the Catio as a cat, or update your cat: what you're working on and whether you need the owner. "
                      "Call it when you start, when you need them, and when you finish. Returns what's waiting for you.",
                      {"agent": dict(S, description="Your stable id, e.g. codex-shop"), "name": S, "model": dict(S, description="e.g. gpt-5, gemini-2.5-pro"),
                       "provider": dict(S, description="openai, google, anthropic, local..."), "title": S, "project": S, "repo": dict(S, description="owner/repo"),
                       "branch": S, "mood": {"type": "string", "enum": list(MOODS)}, "ask": dict(S, description="What you need from the owner, when mood is needs"),
                       "link": S, "session": dict(S, description="Your own session id, for the wake command"),
                       "via": dict(S, description="What you run in, e.g. claude-code"), "cwd": S,
                       "wake": {"type": ["array", "null"], "items": S, "description": "Command that wakes you with a message; placeholders {message} {session} {agent}"}},
                      ["agent"]),
    "audit": (audit, "Save a repository's opening audit, the read-only pass the house rules ask for at the start of a "
              "session. The café shows it in that project's filing cabinet, so it reaches the owner where she already "
              "looks. Writing it again replaces the one before, so a later session's audit is the one she sees.",
              {"repo": dict(S, description="owner/repo, or the repository's name"),
               "summary": dict(S, description="The top findings, one line each"),
               "by": dict(S, description="Who audited, when it is not you: your session or agent id")},
              ["repo", "summary"]),
    "graph": (graph, "Save a repository's project map: the graphify digest the house rules ask you to build before you "
              "dig. The café shows it in that project's filing cabinet -- the map and its neighbourhoods, its hubs, the "
              "surprising links, and the questions the owner can put to a cat with one click. Writing it again replaces "
              "the one before.",
              {"repo": dict(S, description="owner/repo, or the repository's name"),
               "doc": {"type": "object", "description": "The document graph_doc.py prints after the document id, or the catio-graph.json it saves beside the graph"},
               "by": dict(S, description="Who built it, when it is not you: your session or agent id")},
              ["repo", "doc"]),
    "list_agents": (list_agents, "Every agent cat in the Catio.", {"archived": {"type": "boolean"}}, []),
    "inbox": (inbox, "Files, notes from the owner, and any request (pause, resume, wrap_up) waiting for an agent. With mark, only "
              "what hasn't been handed over yet, and it counts as handed over.", {"agent": S, "mark": {"type": "boolean"}}, ["agent"]),
    "pick_up": (pick_up, "Take a file from your inbox: returns it as base64 and marks it picked up.", {"id": S, "agent": S}, ["id"]),
    "drop_file": (drop_file, "Give a file to an agent's cat (and wake it, if it can be woken).",
                  {"name": S, "type": S, "base64": S, "for": dict(S, description="The agent id"), "note": S}, ["name", "base64", "for"]),
    "comment": (comment, "Add to a cat's conversation. Agents answer the owner with author agent.",
                {"cat": S, "text": S, "author": {"type": "string", "enum": ["owner", "agent", "session", "queen"]}}, ["cat", "text"]),
    "comments": (comments, "A cat's conversation, oldest first.", {"cat": S, "limit": {"type": "integer"}}, ["cat"]),
    "manage": (manage, "Manage an agent's cat: rename, move (room key), archive, unarchive, pause, resume, wrap_up, message, done (clear a request).",
               {"cat": S, "action": {"type": "string", "enum": ["rename", "move", "archive", "unarchive", "pause", "resume", "wrap_up", "message", "done"]}, "value": S},
               ["cat", "action"]),
    "quiz": (quiz, "Set the owner homework (the queen, or the owner): a card in the queen's quest log. kind unblock (the default): a short quiz "
             "whose answers unblock a cat, one per cat, 1 to 5 questions, each with up to 12 concrete options to pick, or free for a "
             "written answer; the cat gets the answers as the owner's words, and the queen is told. kind litterbox (a sifted note: which project "
             "is it for?) or decision (one decision waiting on the owner): one question, the card's text in note, where it came from in from, "
             "the guess or recommendation in hint; the answer is only kept, for filing. With ref, the card is dealt once: dealing it "
             "again replaces it while open and leaves it alone once answered.",
             {"for": dict(S, description="The cat it unblocks (its agent id), or empty for the house"), "title": S,
              "questions": {"type": "array", "items": {"type": "object", "properties": {"q": S, "options": {"type": "array", "items": S}, "free": {"type": "boolean"}}, "required": ["q"]}},
              "kind": KIND, "note": S, "from": S, "hint": S, "ref": S},
             ["title", "questions"]),
    "quizzes": (quizzes, "The homework set for the owner: the open quizzes, oldest first (done: true lists the handed-in ones too; kind lists one kind).",
                {"done": {"type": "boolean"}, "kind": KIND}, []),
    "forget": (forget, "Clear homework from the house (the queen or the owner): the cards already filed, or litter box notes and decisions no longer waiting, by id. An open unblock quiz stays.", {"quizzes": {"type": "array", "items": S}}, ["quizzes"]),
    "decide": (decide, "A typed decision about a state: named typed questions in, one typed answer each out, no prose, in milliseconds. "
               "A noul answers yes/no as noul, the probability of yes. A choice answers with the option picked, a probability for each "
               "option, and a confidence. A score answers with score, the probability-weighted level on the criteria's own scale (0 to the "
               "last level), and a confidence: one number, not a probability per level. Every question carries instructions, the question "
               "in words, and is refused without them. Any model can answer: one speaking the System One API takes the questions "
               "themselves, any other is prompted for the same answers instead. preset easy asks the six questions of the easy-task "
               "rubric about state. With kind, the decision is logged beside old (what you would have chosen), with which model answered "
               "and how.",
               {"state": {"description": "The text or JSON the questions are about"},
                "questions": {"type": "object", "additionalProperties": QUESTION,
                              "description": "Named questions: {<name>: {type, instructions, criteria}}. instructions is the question in words, and every question needs it; criteria belongs to a choice ({option: what it means}) or a score ([ordered levels])."},
                "preset": {"type": "string", "enum": ["easy"]},
                "model": dict(S, description="Any model the server at CATIO_DECIDE_URL serves; @cf/cloudflare/clef* and typesafe/jev take the questions themselves"),
                "kind": dict(S, description="A label for the log, e.g. sort"), "old": dict(S, description="What the old path chose, for the log"),
                "floor": {"type": "number", "description": "For the log: the confidence under which you would not act on the answer (it then neither agrees nor disagrees with old). Compared against the answer's confidence, not a choice's winning probability: on a choice the two differ, and the confidence is the lower"},
                "ref": dict(S, description="For the log: what was decided about (the page's brain id), to check the decision against what happened")},
               ["state"]),
    "tokens": (tokens, "The café's colours and sizes as a design tokens file (the W3C format Figma's variables import as a mode), "
               "as The look's Export tokens writes it: mode light (the default) or dark.", {"mode": {"type": "string", "enum": ["light", "dark"]}}, []),
    "set_tokens": (set_tokens, "Bring a design tokens file into the café's look (here: the art/skin.json of the café this serves), as The "
                   "look's Import tokens… does: a token is matched by its own name in any group (the café's own group wins a name found "
                   "twice), aliases are followed, a see-through colour or a size out of range is refused, and what isn't the café's is "
                   "left out. With replace, the file is the whole of that mode instead of laid over it. Returns what it did: tokens read, "
                   "changed, foreign, refused.",
                   {"mode": {"type": "string", "enum": ["light", "dark"]}, "file": {"type": "object", "description": "The design tokens file, as JSON"},
                    "replace": {"type": "boolean"}}, ["file"]),
    "answer": (answer, "Hand homework in (the owner only): one answer per question, in order. An unblock quiz's answers reach the cat, as the owner's words, and the queen; a litterbox or decision card's are only kept, for filing.",
               {"quiz": S, "answers": {"type": "array", "items": S}}, ["quiz", "answers"]),
}


def call(name, args):
    tool = TOOLS.get(name) if isinstance(name, str) else None
    if not tool:
        raise UnknownTool(name)
    args = {} if args is None else args
    if not isinstance(args, dict):
        raise ValueError("arguments is an object")
    typed(args, tool[2])
    return tool[0](args)


# ---------- MCP over stdio ----------
def handle(msg):
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None                                   # a notification
    params = msg["params"] if isinstance(msg.get("params"), dict) else {}
    if method == "initialize":
        ver = params.get("protocolVersion") or "2025-06-18"
        result = {"protocolVersion": ver, "capabilities": {"tools": {}}, "serverInfo": {"name": "catio", "version": "0.1.0"},
                  "instructions": "The Catio is its owner's harness. Read house_rules, report_status when you start, need them, or finish, and check inbox."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                            for n, (_, d, p, r) in TOOLS.items()]}
    elif method == "tools/call":
        try:
            out = call(params.get("name"), params.get("arguments"))
            result = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}], "structuredContent": out}
        except UnknownTool:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool " + str(params.get("name"))}}
        except (ValueError, OSError) as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        except Exception as e:   # a tool's bug fails that call, never the server
            result = {"content": [{"type": "text", "text": "internal error: " + type(e).__name__}], "isError": True}
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
        except (ValueError, RecursionError):
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
        except UnknownTool:
            self.reply(404, {"error": "no such tool"})
        except (ValueError, OSError) as e:
            self.reply(400, {"error": str(e)})
        except Exception:
            self.reply(500, {"error": "internal error"})

    def do_GET(self):
        # The tools are POST only: any page she visits can make her browser GET a URL (an <img> will do)
        if urlparse(self.path).path.startswith("/api/"):
            return self.reply(404, {"error": "the tools are POST only"})
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if not u.path.startswith("/api/"):
            return self.reply(404, {"error": "not found"})
        # same-origin only: the page is served from here, so a browser tab elsewhere can't post. And only as this
        # computer's own name, or a site could point its own name at 127.0.0.1 (DNS rebinding) and be same-origin.
        host = urlparse("//" + (self.headers.get("Host") or "")).hostname
        origin = self.headers.get("Origin")
        if host not in ("localhost", "127.0.0.1") or origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.reply(403, {"error": "cross-origin"})
        length = self.headers.get("Content-Length") or "0"
        if not (length.isascii() and length.isdigit()):
            return self.reply(400, {"error": "bad length"})
        n = int(length)
        if n > MAX_FILE * 2:
            return self.reply(413, {"error": "too large"})
        try:
            args = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, RecursionError):
            return self.reply(400, {"error": "bad json"})
        self.api(u.path[5:], args)


def serve(folder, port):
    global CAFE
    CAFE = CAFE or folder   # the café it serves is the one whose look the tools change
    handler = lambda *a, **k: Handler(*a, directory=folder, **k)
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("The Catio is at http://localhost:%d  (Ctrl+C to stop)" % port, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    with LOCK:   # notes from before accounts are renamed once, here, so load() has nothing left to rename
        store(load())
    if "--serve" in sys.argv:
        i = sys.argv.index("--serve")
        folder = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") else "."
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8791
        serve(os.path.abspath(folder), port)
    else:
        stdio()
