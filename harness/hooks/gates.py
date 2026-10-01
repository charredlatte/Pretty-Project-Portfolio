#!/usr/bin/env python3
"""PreToolUse gates for two enforced house rules.

preflight      no browser (browser MCP tools, or a shell command that drives one) until the
               browser-agent-preflight skill has run in this session.
opening_audit  no edits, commits or pushes until the ponytail-audit skill has run in this session.
"""
import os
import re
from pathlib import Path

from common import block, enforced, hook_input, ran

BROWSER_TOOL = re.compile(r"^mcp__.*(playwright|browser|chrome|puppeteer|computer)", re.I)
BROWSER_CMD = r"playwright|chromium|google-chrome|headless|puppeteer|selenium|webdriver|catio/test/run\.sh"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# shell commands that change the repo or leave the machine. Her scripts are dry runs until --write or --commit
# (litterbox/sort.py --write files notes into every repo checked out beside this one), so those flags count too.
WRITE_FLAG = r"\s--(write|commit)(?![\w-])"
WRITE_CMD = re.compile(
    r"(^|[;&|(]\s*|\s)(git\s+(commit|push|merge|rebase|reset|revert|cherry-pick|am|apply|stash)\b"
    r"|sed\s+(-[a-zA-Z]*i|--in-place)|tee\s|rm\s|mv\s|cp\s|truncate\s|patch\s)"
    r"|[^0-9&]>{1,2}\s*(?!/dev/null|&)[^\s|;&]+|" + WRITE_FLAG
)


def browser_patterns(cwd):
    extra = Path(cwd) / ".claude" / "browser-commands"
    try:
        lines = [l.strip() for l in extra.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    except OSError:
        lines = []
    return re.compile("|".join([BROWSER_CMD] + lines), re.I)


def in_repo(path, cwd):
    """Only the repo counts: scratch files elsewhere (/tmp, ~/.claude, ~/.catio) aren't changes to it."""
    if not path or path.startswith("$"):
        return not path
    p = os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))
    root = os.path.realpath(cwd)
    return p == root or p.startswith(root + os.sep)


def only_scratch(command, cwd):
    """A command whose only writes are redirects to files outside the repo."""
    if re.search(r"(^|[;&|(]\s*|\s)(git|sed|tee|rm|mv|cp|truncate|patch)\s|" + WRITE_FLAG, command):
        return False
    targets = re.findall(r">{1,2}\s*([^\s|;&]+)", command)
    return bool(targets) and not any(in_repo(t, cwd) for t in targets)


def main():
    data = hook_input()
    tool = data.get("tool_name", "")
    args = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    command = str(args.get("command", "")) if tool == "Bash" else ""

    if enforced("preflight", cwd):
        if BROWSER_TOOL.search(tool) or (command and browser_patterns(cwd).search(command)):
            if not ran(data, "browser-agent-preflight"):
                block("House rule (KittyChat): run the browser-agent-preflight skill before using a browser. "
                      "Invoke it with the Skill tool, then try again.")

    if enforced("opening_audit", cwd):
        path = str(args.get("file_path") or args.get("notebook_path") or "")
        edits = tool in EDIT_TOOLS and in_repo(path, cwd)
        writes = bool(command) and WRITE_CMD.search(command) and not only_scratch(command, cwd)
        if (edits or writes) and not ran(data, "ponytail-audit"):
            block("House rule (KittyChat): open the session with a read-only pass first. Run the ponytail-audit skill "
                  "on this repo (it changes nothing), save its summary to the Catio as audits/<repo>, then carry on.")


if __name__ == "__main__":
    main()
