"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

Two halves, which is what makes the rule semi-automatic:

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

from common import ROOT, enforced, local, models, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones

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
    house.update({k: v for k, v in (local(cwd).get("tiers") or {}).items() if k in ("errand", "ladder", "costly")})
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


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this spawn with, and what to say about it. Either may be None."""
    if tool not in SPAWN or not enforced("right_sized", cwd):
        return None, None
    t = tiers(cwd)
    ladder = list(t.get("ladder") or [])
    ceiling = tier_of(t.get("errand"), ladder)
    if not ladder or not ceiling:
        return None, None
    prompt = " ".join(str(args.get(k) or "") for k in ("prompt", "description"))
    if never_down(prompt, cwd):
        return None, None

    named = args.get("model")
    spawn = tier_of(named, ladder) or tier_of(pinned(args.get("subagent_type"), cwd), ladder)
    if spawn is None:   # nothing names a tier: it will inherit the session's model
        session = next((x for x in (tier_of(m, ladder) for m in models(data)) if x), None)
        if session and session in (t.get("costly") or []) and once(data.get("session_id"), "unnamed"):
            return None, ("House rule (KittyChat), spend what the task is worth: this spawn names no model, so it "
                          "inherits this session's %s and runs its own requests there. Name the tier it needs on the "
                          "call: %s, cheapest first. The scout and the tester are Haiku already."
                          % (session, ", ".join(ladder)))
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
