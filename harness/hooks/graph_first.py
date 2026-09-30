#!/usr/bin/env python3
"""PreToolUse on searches and reads: when the repo has a graphify map, point Claude at it before raw files.

graphify's own `hook-guard` does the work (silent when there is no fresh graph). Quiet when graphify isn't
installed or the repo switches the rule off.
"""
import json
import shutil
import subprocess
import sys

from common import enforced, hook_input


def main():
    data = hook_input()
    exe = shutil.which("graphify")
    if not exe or not enforced("graph_first", data.get("cwd")):
        return
    mode = "read" if data.get("tool_name") in ("Read", "Glob") else "search"
    try:
        r = subprocess.run([exe, "hook-guard", mode], input=json.dumps(data), capture_output=True, text=True,
                           cwd=data.get("cwd") or None, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return
    sys.stdout.write(r.stdout)


if __name__ == "__main__":
    main()
