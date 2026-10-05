"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

Delegate first (Charlotte, 5 October: "Always run the delegation before assigning anything to anyone"). Nothing is
assigned without its tier chosen for the work: an Agent spawn, every agent() call in a Workflow script, and a new
session (create_session) each name a model, or the harness refuses them and says how to choose. A fork is the one
exception: it is the parent by design, and its model can't be chosen.

Then two halves, which is what makes the ceiling semi-automatic:

- **The owner deems.** When Charlotte has set a ceiling for this repo (`tiers` in its
  `.claude/catio-rules.json`), that is her decision, made in an earlier session and kept where the repo's
  other decisions live. A spawn above it, for a task that reads as an errand, is refused.
- **The harness deems.** With no word from her, the same reading only earns a line: the tier it would have
  picked and why. A guess never blocks; it suggests, and what she does next is the decision to keep.

Either way the tier is chosen for the work being spawned, never for the conversation: switching the session's
own model mid-way throws its prompt cache away and costs more than the routing saves (docs/delegation.md).

Nothing under a held path, nothing private and nothing needing a browser is ever sent down a tier.
"""
import os
import re
import tempfile
from pathlib import Path

from common import ROOT, enforced, local, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
WORKFLOW = "Workflow"       # a script of agent() calls, each its own sub agent
NEW_SESSION = re.compile(r"__create_session$")   # a new cat: Claude Code Remote's create_session
CALL = re.compile(r"(?<![\w$.])agent\s*\(")

# A task worth a strong model says so in its own words: it asks for judgement, or reaches across a repo.
WORK = re.compile(r"\b(design|architect|refactor|rewrite|migrat|review|audit|investigat|debug|diagnos|"
                  r"plan\b|decide|choose between|trade-?off|across the (repo|codebase)|every file|"
                  r"root cause|why does|security|performance)", re.I)
# Everyday errands: her own example is "add bananas to my shopping list".
CHORE = re.compile(r"\b(add|append|rename|list|count|fetch|copy|tidy|sort|format|summar(y|ise|ize)|"
                   r"look up|find|check|run|note|remind|shopping|groceries|errand)\b", re.I)
PRIVATE = re.compile(r"\b(legal|lawyer|solicitor|contract|tax|salary|invoice|bank|mortgage|health|medical|"
                     r"doctor|diagnosis|prescription)\b", re.I)
BROWSER = re.compile(r"\b(browser|playwright|chrome|chromium|puppeteer|selenium|log ?in|sign ?in|screenshot)\b", re.I)
FRONT_MODEL = re.compile(r"^model:\s*([^\s#]+)\s*$", re.M)


def tiers(cwd):
    """The ladder and the errand ceiling here: the house's, with the repo's own word laid over it."""
    house = dict(rules().get("tiers") or {})
    house.update({k: v for k, v in (local(cwd).get("tiers") or {}).items() if k in ("errand", "ladder")})
    return house


def hers(cwd):
    """Has Charlotte set this repo's ceiling herself? Then it is a decision, not a reading."""
    return "errand" in (local(cwd).get("tiers") or {})


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if t in m), None)


def pinned(agent_type, cwd):
    """The model an agent definition pins, from the repo's .claude/agents or the plugin's own, or None."""
    name = str(agent_type or "").split(":")[-1].strip()
    if not name or not re.fullmatch(r"[\w.-]+", name):
        return None
    for folder in (Path(cwd or ".") / ".claude" / "agents", ROOT / "agents"):
        try:
            head = (folder / (name + ".md")).read_text(encoding="utf-8")[:2000]
        except OSError:
            continue
        found = FRONT_MODEL.search(head.split("---")[1] if head.startswith("---") and "---" in head[3:] else head)
        if found:
            return found.group(1)
    return None


def held(cwd):
    """The paths whose change always waits for her: the merging rule's, plus this repo's own."""
    return list(rules().get("merging", {}).get("hold") or []) + list(local(cwd).get("hold") or [])


def never_down(prompt, cwd):
    """Why this work must keep whatever model it was given, or None."""
    for path in held(cwd):
        if path.strip("/") and re.search(r"(^|[\s\"'`(/])" + re.escape(path.strip("/")) + r"[/\s\"'`)]", prompt):
            return "it names %s, whose changes always wait for her" % path
    if PRIVATE.search(prompt):
        return "it reads as one of her private matters"
    if BROWSER.search(prompt):
        return "it needs a browser, which the preflight rule governs"
    return None


def errand(prompt):
    """Does this read as an errand: short, an everyday verb, and nothing asking for judgement?"""
    text = prompt.strip()
    return bool(text) and len(text) <= 240 and not WORK.search(text) and bool(CHORE.search(text))


def once(session, kind):
    """True the first time this session is told something of this kind."""
    mark = Path(tempfile.gettempdir()) / "catio-tier-{}-{}".format(re.sub(r"\W", "", str(session or "")), kind)
    if mark.exists():
        return False
    try:
        mark.touch()
    except OSError:
        pass
    return True


def delegate_first(what, ladder, why=None):
    """The refusal for an assignment that names no model: what it is, and how to choose."""
    keep = (" This one stays on a strong tier: %s." % why) if why else ""
    return ("House rule (KittyChat), delegate first: %s names no model, so it would run on whatever this session "
            "runs. Choose the tier for the work before assigning it (docs/delegation.md, \"cheap models for volume, "
            "premium where a mistake compounds\"): haiku to read, search, run and report; sonnet for spelled-out, "
            "checkable work in one place; opus or fable for everything else, and for anything under a held path, "
            "private, or needing a browser.%s Not sure? Ask the decider (decide, preset easy). Then name it on the "
            "call: %s." % (what, keep, ", ".join(ladder)))


def mask(src):
    """The script with every string, template literal and comment blanked (newlines kept), so only code is read."""
    out, n = list(src), len(src)

    def blank(i, j):
        for k in range(i, min(j, n)):
            if out[k] != "\n":
                out[k] = " "

    def code(i, in_braces):
        depth = 0
        while i < n:
            c = src[i]
            if c in "\"'":
                j = i + 1
                while j < n and src[j] not in (c, "\n"):
                    j += 2 if src[j] == "\\" else 1
                blank(i + 1, j)
                i = j + 1
            elif c == "`":
                j = template(i + 1)
                blank(i + 1, j)
                i = j + 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank(i, j)
                i = j
            else:
                if in_braces and c == "{":
                    depth += 1
                elif in_braces and c == "}":
                    if not depth:
                        return i
                    depth -= 1
                i += 1
        return n

    def template(i):
        while i < n:
            if src[i] == "\\":
                i += 2
            elif src[i] == "`":
                return i
            elif src.startswith("${", i):
                i = code(i + 2, True) + 1
            else:
                i += 1
        return n

    code(0, False)
    return "".join(out)


def unnamed_agents(src):
    """The line of every agent() call in a workflow script whose arguments don't name a model."""
    code, lines = mask(src), []
    for m in CALL.finditer(code):
        depth, j = 0, m.end() - 1
        while j < len(code):
            depth += {"(": 1, ")": -1}.get(code[j], 0)
            if not depth:
                break
            j += 1
        if not re.search(r"\bmodel\b", code[m.end():j]):
            lines.append(src.count("\n", 0, m.start()) + 1)
    return lines


def script_of(args, cwd):
    """A Workflow call's script: inline, from its scriptPath, or a saved one in the repo's .claude/workflows."""
    if args.get("script"):
        return str(args["script"])
    paths = [args.get("scriptPath")] if args.get("scriptPath") else []
    if args.get("name") and re.fullmatch(r"[\w.-]+", str(args["name"])):
        paths.append(Path(cwd or ".") / ".claude" / "workflows" / (str(args["name"]) + ".js"))
    for path in paths:
        try:
            return Path(cwd or ".", os.path.expanduser(str(path))).read_text(encoding="utf-8")
        except OSError:
            continue
    return ""   # a built-in workflow, or one this hook can't read: nothing to check


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this assignment with, and what to say about it. Either may be None."""
    workflow, session = tool == WORKFLOW, bool(NEW_SESSION.search(tool))
    if not (tool in SPAWN or workflow or session) or not enforced("right_sized", cwd):
        return None, None
    t = tiers(cwd)
    ladder = list(t.get("ladder") or [])
    ceiling = tier_of(t.get("errand"), ladder)
    if not ladder:
        return None, None

    if workflow:
        lines = unnamed_agents(script_of(args, cwd))
        if lines:
            return delegate_first("this workflow's agent() call on line%s %s" % ("s" if len(lines) > 1 else "",
                                  ", ".join(map(str, lines))), ladder), None
        return None, None
    if session:
        if not tier_of(args.get("model"), ladder):
            return delegate_first("this new session", ladder, never_down(str(args.get("prompt") or ""), cwd)), None
        return None, None
    if str(args.get("subagent_type") or "") == "fork":
        return None, None   # a fork is the parent by design: its model can't be chosen

    prompt = " ".join(str(args.get(k) or "") for k in ("prompt", "description"))
    keep = never_down(prompt, cwd)
    spawn = tier_of(args.get("model"), ladder) or tier_of(pinned(args.get("subagent_type"), cwd), ladder)
    if spawn is None:   # nothing names a tier: it would inherit the session's model, whatever the work
        return delegate_first("this spawn", ladder, keep), None
    if keep or not ceiling:
        return None, None

    if not errand(prompt) or ladder.index(spawn) <= ladder.index(ceiling):
        return None, None
    if hers(cwd):
        return ("House rule (KittyChat), spend what the task is worth: Charlotte set this repo's ceiling for an "
                "errand at %s, and this reads as one. Spawn it on %s or below. If it is really not an errand, say "
                "so to her and she will raise the ceiling in .claude/catio-rules.json."
                % (ceiling, ceiling)), None
    if once(data.get("session_id"), "errand"):
        return None, ("House rule (KittyChat), spend what the task is worth: this reads as an errand (spelled out, "
                      "checkable, small) and it is spawned on %s. %s or below does it. Carry on if it is more than "
                      "it looks; if she tells you the ceiling for this repo, write it into .claude/catio-rules.json "
                      "as {\"tiers\": {\"errand\": \"<tier>\"}} so the next session starts from her decision."
                      % (spawn, ceiling.capitalize()))
    return None, None
