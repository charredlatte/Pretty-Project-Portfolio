"""Shared bits for the KittyChat house-rule hooks: the rules, the hook input, and the transcript."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rules():
    return json.loads((ROOT / "rules.json").read_text(encoding="utf-8"))


def enforced(rule_id, cwd=None):
    """Is this enforced rule on, here? rules.json says so, unless the repo's .claude/catio-rules.json switches it off."""
    rule = next((r for r in rules()["rules"] if r["id"] == rule_id), None)
    if not rule or not rule.get("on", True):
        return False
    local = Path(cwd or os.getcwd()) / ".claude" / "catio-rules.json"
    try:
        return json.loads(local.read_text(encoding="utf-8")).get(rule_id, True) is not False
    except (OSError, ValueError):
        return True


def hook_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def skills_used(data):
    """Names of every skill this session has invoked, read from its transcript(s)."""
    names = set()
    for key in ("transcript_path", "agent_transcript_path"):
        path = data.get(key)
        if not path:
            continue
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as f:
                for line in f:
                    if '"Skill"' not in line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    content = (entry.get("message") or {}).get("content")
                    for part in content if isinstance(content, list) else []:
                        if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Skill":
                            names.add(str((part.get("input") or {}).get("skill", "")))
        except OSError:
            continue
    return names


def ran(data, skill):
    return any(skill in n for n in skills_used(data))


def block(message):
    """Refuse the tool call; Claude sees the message."""
    print(message, file=sys.stderr)
    sys.exit(2)
