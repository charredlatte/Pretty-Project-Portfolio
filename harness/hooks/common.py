"""Shared bits for the KittyChat house-rule hooks: the rules, the hook input, git, and the transcript."""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rules():
    return json.loads((ROOT / "rules.json").read_text(encoding="utf-8"))


def local(cwd=None):
    """The repo's own switches, .claude/catio-rules.json, or {}."""
    try:
        return json.loads((Path(cwd or os.getcwd()) / ".claude" / "catio-rules.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def enforced(rule_id, cwd=None):
    """Is this enforced rule on, here? rules.json says so, unless the repo's .claude/catio-rules.json switches it off."""
    rule = next((r for r in rules()["rules"] if r["id"] == rule_id), None)
    if not rule or not rule.get("on", True):
        return False
    return local(cwd).get(rule_id, True) is not False


def merges(cwd=None):
    """Does this repo merge its own pull requests? Only when the merging rule is on and the repo's
    .claude/catio-rules.json says {"merge": true}."""
    rule = next((r for r in rules()["rules"] if r["id"] == "merge"), {})
    return rule.get("on", False) is not False and local(cwd).get("merge") is True


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def default_branch(cwd):
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=cwd)
    if head:
        return head.split("/", 1)[-1]
    for name in ("main", "master"):
        if git("rev-parse", "--verify", "--quiet", "refs/remotes/origin/" + name, cwd=cwd) is not None:
            return name
    return "main"


def checkouts(cwd):
    """The repo cwd is in, then every repo beside it (or under cwd, when cwd isn't one)."""
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    here = Path(top).parent if top else Path(cwd or ".")
    try:
        beside = sorted(str(d) for d in here.iterdir() if (d / ".git").exists() and str(d) != top)
    except OSError:
        beside = []
    return ([top] if top else []) + beside


def repos(cwd):
    """The repos a session works in: this one and, in a cloud session, every repo beside it, since the container
    is the session's own."""
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        return checkouts(cwd)
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    return [top] if top else []


def hook_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def entries(data, needle):
    """The entries of this session's transcript(s) whose line holds `needle` (a cheap filter before parsing)."""
    for key in ("transcript_path", "agent_transcript_path"):
        path = data.get(key)
        if not path:
            continue
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as f:
                for line in f:
                    if needle in line:
                        try:
                            yield json.loads(line)
                        except ValueError:
                            continue
        except OSError:
            continue


def skill_calls(data):
    """(name, when) for every skill this session has invoked; when is seconds since the epoch, or 0."""
    for entry in entries(data, '"Skill"'):
        content = (entry.get("message") or {}).get("content")
        for part in content if isinstance(content, list) else []:
            if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Skill":
                try:
                    when = datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp()
                except ValueError:
                    when = 0
                yield str((part.get("input") or {}).get("skill", "")), when


def skills_used(data):
    """Names of every skill this session has invoked, read from its transcript(s)."""
    return {name for name, _ in skill_calls(data)}


def models(data):
    """Every model that has answered in this session, read from its transcript(s)."""
    return {(e.get("message") or {}).get("model") for e in entries(data, '"model"')
            if e.get("type") == "assistant"} - {None, "<synthetic>"}


def ran(data, skill):
    return any(skill in n for n in skills_used(data))


def block(message):
    """Refuse the tool call; Claude sees the message."""
    print(message, file=sys.stderr)
    sys.exit(2)
