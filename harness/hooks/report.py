#!/usr/bin/env python3
"""Report this session to the Catio's gateway, so its cat is live without anyone asking claude.ai.

Hooks (hooks.json): SessionStart and UserPromptSubmit say the session is busy, Notification that it needs Charlotte,
Stop that its turn is done, SessionEnd that it's finished. At Stop it also hands in what she sent from the Catio
(her notes, a pause or wrap-up, files), each once, as the reason to carry on.

It needs CATIO_URL (the gateway, e.g. https://catio-gateway.<name>.workers.dev) and CATIO_TOKEN (its key) in the
environment; without them it does nothing. A call that fails or takes over two seconds is dropped, so a report never
holds up a turn.

As a command, for the catio skill:
    report.py say "text"        answer Charlotte on this session's cat
    report.py pick <file id>    save a file she dropped on the cat, and print where it went
    report.py audit "summary"   file the opening audit in this repository's filing cabinet
    report.py map [file]        file the project map graph_doc.py wrote (default graphify-out/catio-graph.json)
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from common import hook_input

TIMEOUT = 2
HERE = Path(__file__).resolve()
NEEDS = ("permission_prompt", "idle_prompt", "elicitation_dialog", "agent_needs_input")


def gateway():
    url, token = os.environ.get("CATIO_URL", "").strip().rstrip("/"), os.environ.get("CATIO_TOKEN", "").strip()
    if not (url and token):
        return None
    return (url if url.endswith("/mcp") else url + "/mcp"), token


def call(*calls, timeout=TIMEOUT):
    """Call the gateway's tools, in order, in one request: each one's result, or None if it failed."""
    g = gateway()
    if not g:
        return [None] * len(calls)
    body = [{"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}
            for i, (name, args) in enumerate(calls)]
    # Cloudflare refuses Python's own User-Agent on workers.dev (error 1010), so the hook names itself
    req = urllib.request.Request(g[0], data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": "Bearer " + g[1],
        "User-Agent": "kittychat-report/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            replies = json.load(r)
    except Exception:
        return [None] * len(calls)
    results = {}
    for reply in replies if isinstance(replies, list) else [replies]:
        result = reply.get("result") if isinstance(reply, dict) else None
        if isinstance(result, dict) and not result.get("isError"):
            results[reply.get("id")] = result.get("structuredContent")
    return [results.get(i) for i in range(len(calls))]


def me(data=None):
    """This session's cat id, and its link: the claude.ai session id when there is one, so the page can match the
    cat to the session it lists."""
    sid = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID") or os.environ.get("CLAUDE_CODE_BRIDGE_SESSION_ID")
    if sid:
        return sid, "https://claude.ai/code/" + sid
    local = (data or {}).get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID")
    return ("cli-" + local if local else None), None


def git(*args, cwd=None):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def facts(data):
    """What the cat shows: who it is, where it works, and what Claude Code says about it."""
    cwd = data.get("cwd") or os.getcwd()
    agent, link = me(data)
    f = {"agent": agent, "via": "claude-code", "provider": "anthropic"}
    if link:
        f.update(link=link, session=agent)
    m = re.search(r"[/:]([^/:]+)/([^/]+?)(?:\.git)?/?$", git("remote", "get-url", "origin", cwd=cwd))
    if m:
        f.update(repo=m.group(1) + "/" + m.group(2), project=m.group(2))
    branch = git("branch", "--show-current", cwd=cwd)
    if branch:
        f["branch"] = branch
    for key, field in (("session_title", "title"), ("model", "model")):
        if data.get(key):
            f[field] = str(data[key])
    return f


SAYS = {"owner": "Charlotte says", "queen": "The queen says"}   # the owner, and the queen of the house, her assistant (harness/runner)


def handed_in(box):
    """What she sent, as the turn the session carries on with. Empty when nothing is waiting."""
    lines = ["[Catio] " + SAYS.get(n.get("author"), "Charlotte says") + ": " + n["text"] for n in (box or {}).get("notes") or []]
    request = (box or {}).get("request")
    if request and request.get("action"):
        lines.append("[Catio] Request: " + request["action"])
    for f in (box or {}).get("files") or []:
        note = f" Her note: {f['note']}" if f.get("note") else ""
        lines.append(f"[Catio] Delivery for you: {f['name']} ({f['type']}, {f['size']} bytes).{note} "
                     f"Fetch it with: python3 \"{HERE}\" pick {f['id']}")
    if not lines:
        return ""
    lines.append(f"(From the Catio's gateway. Handle it with the catio skill, and answer her on your cat: "
                 f"python3 \"{HERE}\" say \"<your answer>\")")
    return "\n\n".join(lines)


def main():
    data = hook_input()
    event = data.get("hook_event_name")
    if not gateway():
        return
    f = facts(data)
    if not f["agent"]:
        return
    if event in ("SessionStart", "UserPromptSubmit"):
        call(("report_status", dict(f, mood="busy", ask="")))
    elif event == "Notification":
        kind = data.get("notification_type")
        if kind is None or kind in NEEDS:
            call(("report_status", dict(f, mood="needs", ask=str(data.get("message") or "Waiting for you.")[:300])))
    elif event == "SessionEnd":
        call(("report_status", dict(f, mood="done", ask="")))
    elif event == "Stop":
        done = ("report_status", dict(f, mood="review", ask=""))
        if data.get("stop_hook_active"):          # already carrying on from a held stop: just say where it is
            call(done)
            return
        _, box = call(done, ("inbox", {"agent": f["agent"], "mark": True}))
        reason = handed_in(box)
        if reason:
            call(("report_status", dict(f, mood="busy")))
            print(json.dumps({"decision": "block", "reason": reason}))


def command(argv):
    if not gateway():
        sys.exit("CATIO_URL and CATIO_TOKEN aren't set: this session isn't connected to the Catio's gateway.")
    agent, _ = me()
    if not agent:
        sys.exit("There's no session id in the environment.")
    if argv[0] == "say" and len(argv) > 1:
        said, = call(("comment", {"cat": agent, "text": " ".join(argv[1:]), "author": "session"}), timeout=15)
        if not said:
            sys.exit("The gateway didn't take it. Try again.")
        print("Said on your cat.")
    elif argv[0] == "pick" and len(argv) == 2:
        got, = call(("pick_up", {"id": argv[1], "agent": agent}), timeout=30)
        if not got:
            sys.exit("No such file, or the gateway didn't answer.")
        folder = Path(tempfile.gettempdir()) / "catio"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (re.sub(r"[^A-Za-z0-9._-]+", "_", Path(got["name"]).name).strip(".") or "file")
        path.write_bytes(base64.b64decode(got["base64"]))
        print(path)
    elif argv[0] in ("audit", "map") and (len(argv) > 1 or argv[0] == "map"):
        repo = facts({}).get("repo")
        if not repo:
            sys.exit("This checkout has no GitHub remote to file it under.")
        if argv[0] == "audit":
            args = {"kind": "audit", "repo": repo, "summary": " ".join(argv[1:]), "by": agent}
        else:
            src = Path(argv[1] if len(argv) > 1 else "graphify-out/catio-graph.json")
            try:
                args = {"kind": "map", "repo": repo, "map": json.loads(src.read_text(encoding="utf-8")), "by": agent}
            except (OSError, ValueError):
                sys.exit(f"No project map at {src}: run graph_doc.py first.")
        saved, = call(("save_report", args), timeout=30)
        if not saved:
            sys.exit("The gateway didn't take it (too long, or not reachable). Try again.")
        print("Filed as " + saved["id"] + ".")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command(sys.argv[1:])
    else:
        try:
            main()
        except Exception:   # a report is never worth breaking a turn
            pass
