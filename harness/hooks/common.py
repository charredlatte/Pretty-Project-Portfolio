"""Shared bits for the KittyChat house-rule hooks: the rules, the hook input, git, and the transcript."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=None)
def _rules_text():
    return (ROOT / "rules.json").read_text(encoding="utf-8")


def rules():
    """The house rules. The file is read once a process; every caller gets its own copy to build on."""
    return json.loads(_rules_text())


@lru_cache(maxsize=None)
def _local_text(cwd):
    try:
        return (Path(cwd or os.getcwd()) / ".claude" / "catio-rules.json").read_text(encoding="utf-8")
    except OSError:
        return "{}"


def local(cwd=None):
    """The repo's own switches, .claude/catio-rules.json, or {}."""
    try:
        found = json.loads(_local_text(cwd))
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def _mark(session, kind, prefix, where):
    """Where the fact that something was said is remembered: a folder of this user's own, not a guessable name
    in the shared temp directory, which anything on the machine could plant or point elsewhere."""
    folder = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "catio"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        folder.chmod(0o700)
    except OSError:
        folder = Path(tempfile.gettempdir())
    tag = hashlib.sha1(("%s\0%s" % (session or "", where or "")).encode()).hexdigest()[:16]
    return folder / "said-{}-{}-{}".format(prefix, tag, kind)


def said(session, kind, prefix, where=None):
    """Has this session already been told something of this kind, here? The cheap question, no side effect."""
    return _mark(session, kind, prefix, where).exists()


def say(session, kind, prefix, where=None):
    """Remember that it has been told, so it is said once. Call it when the thing is actually being said."""
    try:
        _mark(session, kind, prefix, where).touch()
    except OSError:
        pass           # can't remember it was said; say it anyway rather than lose it


def holds(mapping, key="hold"):
    """(paths, unreadable): the hold paths in mapping[key], and whether it said something this can't read.

    It does its own lookup on purpose. The hold list is what makes a change under harness/ wait for her, so
    losing one quietly is the one failure this must not have - and the way it was lost before was a caller
    reading the setting itself: .get("hold") cannot tell an absent key from one she wrote as null, so a null
    read as silence and the pull request merged. With the lookup in here no caller can write that.

    Only the key being absent from a mapping this can read is silence. A mapping that isn't one (a merging
    block a merge fused into a list, say) is unreadable, not silent. Everything she did write that cannot be
    matched against git's own
    --name-only output comes back unreadable, for the caller to hold on rather than drop: a shape that isn't
    a list, an entry that isn't a string, a glob or brace (nothing here expands one), a backslash, an
    absolute or dot-relative path, a "." or ".." segment anywhere, and a ~ or $ the shell would have grown.
    A path is returned trimmed but otherwise as she spelt it, so the brief quotes her and the caller
    normalises where it compares.
    """
    if not isinstance(mapping, dict):
        return [], True        # a block this can't read is not her saying nothing
    if key not in mapping:
        return [], False
    value = mapping[key]
    if not isinstance(value, list):
        return [], True        # a string, a number, an object - and an explicit null
    paths = [q for q in (p.strip() for p in value if isinstance(p, str)) if q and path_like(q)]
    return paths, len(paths) != len(value)


def path_like(p):
    """Is this a repo-relative path git's own --name-only output could equal or sit under?"""
    if set("*?[]{}\\~$") & set(p) or p.startswith("/"):
        return False
    parts = p.strip("/").split("/")
    return bool(parts) and all(parts) and not ({".", ".."} & set(parts))


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
    """git's answer, or None. Decoded as UTF-8, which is what git writes: text=True would decode with the
    locale's encoding, cp1252 on Windows, and a path with an accent in it came back mangled - so it matched
    no held path she had spelt properly, and the change merged unheld on Windows alone."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           encoding="utf-8", errors="surrogateescape")
    except OSError:  # cwd isn't there
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def git_ok(*args, cwd=None, timeout):
    """Did git succeed within `timeout` seconds? Run with no pipes: on Windows a helper git starts (ssh,
    git-remote-https) holds a captured pipe open after git itself is killed, and the wait outlives the timeout."""
    try:
        return subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=timeout).returncode == 0
    except (OSError, subprocess.TimeoutExpired):  # cwd isn't there, or git took too long
        return False


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


def entries(data, *needles, keys=("transcript_path", "agent_transcript_path")):
    """The entries of these transcript(s) whose line holds one of `needles` (a cheap filter before parsing)."""
    for key in keys:
        path = data.get(key)
        if not path:
            continue
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as f:
                for line in f:
                    if any(n in line for n in needles):
                        try:
                            yield json.loads(line)
                        except ValueError:
                            continue
        except OSError:
            continue


def skill_calls(data):
    """(name, when) for every skill this session has run, by the Skill tool or typed as /name; when is seconds since
    the epoch, or 0."""
    for entry in entries(data, '"Skill"', "<command-name>"):
        try:
            when = datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            when = 0
        content = (entry.get("message") or {}).get("content")
        parts = content if isinstance(content, list) else [{"type": "text", "text": content}]
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and part.get("name") == "Skill":
                yield str((part.get("input") or {}).get("skill", "")), when
            elif entry.get("type") == "user" and part.get("type") == "text":
                for name in re.findall(r"<command-name>/?([\w:.-]+)</command-name>", str(part.get("text") or "")):
                    yield name, when


def skills_used(data):
    """Names of every skill this session has invoked, read from its transcript(s)."""
    return {name for name, _ in skill_calls(data)}


def answered(data, keys=("transcript_path", "agent_transcript_path"), sidechain=False):
    """Every model that answered, in the order it answered, from these transcripts. One reader, so the one
    question that matters - does a sub agent's own side of the conversation count - is answered in one place.
    It counts when you are reading a sub agent's own transcript, and not when you are reading a session's."""
    return [m for m in ((e.get("message") or {}).get("model") for e in entries(data, '"model"', keys=keys)
                        if e.get("type") == "assistant" and (sidechain or not e.get("isSidechain")))
            if m and m != "<synthetic>"]


def models(data):
    """Every model that has answered in this session, read from its transcript(s). A subagent's own side of the
    conversation (a sidechain) doesn't count: it searched or read for the session, it didn't do the work."""
    return set(answered(data))


def ran(data, skill):
    return any(skill in n for n in skills_used(data))


def block(message):
    """Refuse the tool call; Claude sees the message."""
    print(message, file=sys.stderr)
    sys.exit(2)


# What a gate has to say without refusing (additionalContext). The hook answers once, through answer(): two
# JSON answers on stdout are read as neither.
CONTEXT = []


def answer(**decision):
    """The hook's one JSON answer: what CONTEXT holds, plus any permission decision. Nothing when both are empty."""
    out = dict(decision, **({"additionalContext": "\n\n".join(CONTEXT)} if CONTEXT else {}))
    if out:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **out}}))


def ask(message):
    """Put the tool call to her: Claude Code shows her a permission prompt with the message."""
    answer(permissionDecision="ask", permissionDecisionReason=message)
    sys.exit(0)
