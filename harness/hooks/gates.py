#!/usr/bin/env python3
"""PreToolUse gates for the enforced house rules.

preflight       no browser (browser MCP tools, or a shell command that drives one) until the
                browser-agent-preflight skill has run in this session.
opening_audit   no edits, commits or pushes until the ponytail-audit skill has run in this session.
no_attribution  no Co-Authored-By or Claude-Session lines in a commit (or its -F file) in a public repo or a fork,
                no credit lines in what is posted to one through GitHub, and, after a post GitHub's integration
                signs (PostToolUse), the session is told to edit the footer off.
ship, merge     pushes, branch deletions and merges, in ship_gate.py.
small_writers   the plugin's scout and tester never edit; in a repo that merges its own pull requests, no sub agent
                on a model off the strong list edits a tracked file (the merging rule's promise: a strong model did
                the work).
right_sized     a sub agent spawn says which tier it needs; an errand above this repo's ceiling is refused when
                Charlotte set that ceiling herself, and only spoken about when the harness read it that way
                (right_sized.py).
"""
import json
import os
import re
import subprocess
from pathlib import Path

import right_sized
import ship_gate
from common import block, enforced, git, hook_input, merges, ran, rules

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


ATTRIBUTION = re.compile(r"Co-Authored-By:\s*Claude|Claude-Session:", re.I)
# a line that credits Claude in text posted to GitHub: a line of its own, so prose about the rule still passes
CREDIT_LINE = re.compile(r"^\s*(?:🤖\s*)?_?Generated\s+(?:with|by)\s+\[?Claude\s+Code\b.*$"
                         r"|^\s*https://claude\.ai/code/(?:session|cse)_\w+\s*$"
                         r"|^\s*(?:Co-Authored-By:\s*Claude\b|Claude-Session:).*$", re.I | re.M)
COMMIT = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
ELSEWHERE = re.compile(r"(?:\bgit\s+-C\s+|\bcd\s+)([^\s;&|]+)")
MESSAGE_FILE = re.compile(r"(?:\s-F\s*|\s--file[=\s]\s*)(['\"]?)([^\s'\";&|]+)\1")
# GitHub posts the integration signs with its own footer, which only an edit afterwards takes off
SIGNED_POSTS = {"mcp__github__create_pull_request", "mcp__github__add_issue_comment", "mcp__github__issue_write"}


def places(command, cwd):
    return [cwd] + [os.path.join(cwd, os.path.expanduser(p.strip("'\""))) for p in ELSEWHERE.findall(command)]


def listed(repo):
    return repo.lower() in {r.lower() for r in rules().get("public", [])}


def public(command, cwd):
    """Does this command commit in a repo on rules.json's "public" list: its own, or one it cds or -Cs into?"""
    for place in places(command, cwd):
        out = subprocess.run(["git", "-C", place, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
        m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", out)
        if m and listed(m.group(1)):
            return True
    return False


def message(command, cwd):
    """The commit's message as far as the command shows it: the command itself, and any file -F or --file names."""
    found = [command]
    for _, path in MESSAGE_FILE.findall(command):
        for place in places(command, cwd) if path != "-" else []:
            try:
                found.append(Path(place, os.path.expanduser(path)).read_text(encoding="utf-8", errors="replace"))
                break
            except OSError:
                continue
    return "\n".join(found)


def github_public(args):
    return listed(f"{args.get('owner', '')}/{args.get('repo', '')}")


def after(tool, args, cwd):
    """PostToolUse: in a public repo, a post the integration has signed gets its footer taken off at once."""
    if tool in SIGNED_POSTS and enforced("no_attribution", cwd) and github_public(args) \
            and (tool != "mcp__github__issue_write" or args.get("method") == "create"):
        block("House rule (KittyChat): this repo is public, and GitHub's Claude integration adds its own \"Generated by "
              "Claude Code\" footer to what it posts. Take it off now: update_pull_request (or issue_write with method "
              "update, or update_issue_comment) with the same text and no footer, then read it back. If the footer "
              "comes back, tell Charlotte.")


READ_ONLY = {"scout", "tester"}


def agent_models(data):
    """The models a sub agent has answered with, from its own transcript; empty when it can't be read."""
    found = set()
    try:
        with open(os.path.expanduser(data.get("agent_transcript_path") or ""), encoding="utf-8") as f:
            for line in f:
                if '"model"' in line:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    if e.get("type") == "assistant":
                        found.add((e.get("message") or {}).get("model"))
    except OSError:
        pass
    return found - {None, "<synthetic>"}


def small_writer(data, path, cwd):
    """Why this sub agent may not edit this file, or None."""
    name = str(data.get("agent_type") or "").split(":")[-1]
    if not name:
        return None
    if name in READ_ONLY:
        return f"the {name} only reads, runs and reports. Hand its findings back and make the change in the session."
    used = agent_models(data)
    strong = rules()["merging"]["strong"]
    if not used or any(s in m for m in used for s in strong) or not merges(cwd):
        return None
    full = os.path.join(cwd, os.path.expanduser(path))
    if git("ls-files", "--error-unmatch", full, cwd=os.path.dirname(full) or cwd) is None:
        return None   # not tracked: scratch is free
    return (f"a sub agent on {', '.join(sorted(used))} may not edit a tracked file in a repo that merges its own pull "
            "requests: the merging rule promises a strong model did the work. Make the change in the session.")


def main():
    data = hook_input()
    tool = data.get("tool_name", "")
    args = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    command = str(args.get("command", "")) if tool == "Bash" else ""
    if data.get("hook_event_name") == "PostToolUse":
        return after(tool, args, cwd)

    try:
        refusal, nudge = right_sized.check(data, tool, args, cwd)
    except SystemExit:
        raise
    except Exception:   # a tier is worth less than the gates below it: say nothing and let them run
        refusal = nudge = None
    if refusal:
        block(refusal)
    if nudge:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": nudge}}))

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

    if tool in EDIT_TOOLS:
        why = small_writer(data, str(args.get("file_path") or args.get("notebook_path") or ""), cwd)
        if why:
            block("House rule (KittyChat): " + why)

    if command and COMMIT.search(command) and ATTRIBUTION.search(message(command, cwd)) \
            and enforced("no_attribution", cwd) and public(command, cwd):
        block("House rule (KittyChat): no Claude attribution on public repos or forks, and this commit is in one. "
              "Leave out the Co-Authored-By and Claude-Session lines, then commit again.")
    if tool.startswith("mcp__github__") and enforced("no_attribution", cwd) and github_public(args) \
            and CREDIT_LINE.search("\n".join(str(args.get(k) or "") for k in ("body", "message", "commit_message"))):
        block("House rule (KittyChat): no Claude attribution on public repos or forks, and this is one. Leave out the "
              "\"Generated with Claude Code\" and session-link lines, and any Co-Authored-By or Claude-Session line, "
              "then try again.")

    try:
        ship_gate.check(data, tool, args, cwd, command)
    except SystemExit:
        raise
    except Exception as e:  # a hook that crashes lets the call through, so this one fails closed
        block(f"House rule (KittyChat): the shipping gate couldn't check this ({type(e).__name__}: {e}). "
              "Tell Charlotte, and leave the push or merge for her.")


if __name__ == "__main__":
    main()
