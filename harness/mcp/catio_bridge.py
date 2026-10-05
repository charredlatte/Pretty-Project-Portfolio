#!/usr/bin/env python3
"""Stdio MCP in, the gateway's /mcp out: how a client that only starts local MCP servers (Antigravity, Cursor, Claude
Desktop) joins the Catio on the gateway, instead of keeping a private one of its own on its computer.

    CATIO_URL=https://dog-den.<name>.workers.dev CATIO_TOKEN=<an agents' key> python3 catio_bridge.py

The gateway answers a JSON-RPC message, or a batch, to each POST and keeps no session, so each line on stdin is one
POST and its reply is one line on stdout. Python standard library only.
"""
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = 60


def post(url, key, body):
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "kittychat-bridge/1"})   # Cloudflare refuses Python's own User-Agent
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def error(mid, message, code=-32603):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def relay(url, key, line):
    """The gateway's reply to one line, or None when it has none (a notification). A line the gateway can't answer
    gets a JSON-RPC error for every request in it, so the client is never left waiting."""
    try:
        msg = json.loads(line)
    except ValueError:
        return error(None, "parse error", -32700)
    batch = isinstance(msg, list)
    asked = [m["id"] for m in (msg if batch else [msg]) if isinstance(m, dict) and m.get("id") is not None]
    try:
        status, body = post(url, key, line.encode("utf-8"))
        return None if status == 202 or not body.strip() else json.loads(body)
    except urllib.error.HTTPError as e:
        why = "the gateway refused the key (401): CATIO_TOKEN isn't an agents' key it knows" if e.code == 401 else "the gateway said %d" % e.code
    except ValueError:
        why = "the gateway's answer wasn't JSON"
    except OSError as e:
        why = "the gateway didn't answer: %s" % e
    if not asked:
        return None
    replies = [error(i, why) for i in asked]
    return replies if batch else replies[0]


def main():
    url, key = os.environ.get("CATIO_URL", "").strip().rstrip("/"), os.environ.get("CATIO_TOKEN", "").strip()
    if not url or not key:
        sys.exit("Set CATIO_URL (the gateway's address) and CATIO_TOKEN (an agents' key): harness/antigravity/README.md says how.")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        reply = relay(url + "/mcp", key, line)
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
