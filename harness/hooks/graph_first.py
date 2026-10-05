#!/usr/bin/env python3
"""PreToolUse on searches, reads and commands: point Claude at the cheaper way before it digs.

graph_first   when the repo has a graphify map, graphify's own `hook-guard` points at it before raw files (silent
              when there is no fresh graph, or graphify isn't installed).
delegate      once a session each, a strong main session that searches the whole repo, or runs the tests itself,
              is reminded that the plugin's Haiku scout or tester would do it for a fraction. A nudge, never a block.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import enforced, hook_input, models, once, rules

TESTS = re.compile(r"(\bnpm (run )?test\b|\bpytest\b|\bunittest\b|node --test|\brun\.sh\b|\bcargo test\b|\bgo test\b|\bvitest\b|\bjest\b)")
SAY = {
    "search": "House rule (KittyChat), send the small stuff to a smaller cat: a search across the whole repo is the "
              "scout's job. Agent with subagent_type scout (Haiku) finds it and answers in paths and lines, for a "
              "fraction of what this session costs. Carry on if you need the raw results yourself.",
    "test": "House rule (KittyChat), send the small stuff to a smaller cat: running the checks is the tester's job. "
            "Agent with subagent_type tester (Haiku) runs them and reports only what failed, with the failing lines. "
            "Carry on if you need the whole log yourself.",
}


def graph_first(data):
    exe = shutil.which("graphify")
    if not exe or not enforced("graph_first", data.get("cwd")):
        return ""
    mode = "read" if data.get("tool_name") in ("Read", "Glob") else "search"
    try:
        r = subprocess.run([exe, "hook-guard", mode], input=json.dumps(data), capture_output=True, text=True,
                           cwd=data.get("cwd") or None, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout


def whole_repo(path, cwd):
    if not path:
        return True
    return os.path.realpath(os.path.join(cwd or ".", path)) == os.path.realpath(cwd or ".")


def delegate(data):
    """The nudge's text, or "" when it doesn't apply: inside a sub agent, with the rule off, for anything but a
    whole-repo search or a test run, once it has been said this session, or when no strong model is working."""
    if data.get("agent_type") or not enforced("delegate", data.get("cwd")):
        return ""
    tool, args = data.get("tool_name"), data.get("tool_input") or {}
    if tool in ("Grep", "Glob") and whole_repo(args.get("path"), data.get("cwd")):
        kind = "search"
    elif tool == "Bash" and TESTS.search(str(args.get("command", ""))):
        kind = "test"
    else:
        return ""
    strong = rules()["merging"]["strong"]
    if not any(s in m for m in models(data) for s in strong):
        return ""
    return SAY[kind] if once(data.get("session_id"), kind) else ""


def main():
    data = hook_input()
    out = graph_first(data)
    if out:   # the map's pointer speaks first; the nudge waits for a later call
        sys.stdout.write(out)
        return
    say = delegate(data)
    if say:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": say}}))


if __name__ == "__main__":
    main()
