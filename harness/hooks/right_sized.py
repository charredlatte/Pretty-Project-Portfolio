"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

Two halves, which is what makes the rule semi-automatic, and only one of them ever blocks:

- **The owner deems.** When Charlotte has capped a repo's sub agents (`tiers.ceiling` in its
  `.claude/catio-rules.json`), that is a decision she made in an earlier session, kept where the repo's other
  decisions live. The hook works out the tier a spawn will really run on - the model it names, else the one its
  agent file pins, else CLAUDE_CODE_SUBAGENT_MODEL, else the session's own - and refuses anything above her cap.
  Facts only: nothing here reads the prompt.
- **The harness deems.** With no cap from her, the hook may still *read* a task as an errand and say so, once.
  A reading never blocks, because a guess from a prompt's words is not firm enough to refuse on; what she does
  after the line is the decision worth keeping, and the rule asks for it to be written into that same file.

Either way the tier is chosen for the work being spawned, never for the conversation: switching the session's
own model mid-way throws its prompt cache away and costs more than the routing saves (docs/delegation.md).

Nothing under a held path, nothing private and nothing needing a browser is sent down a tier at all.
"""
import os
import re
from pathlib import Path

from common import ROOT, enforced, local, models, once, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones

# A task worth a strong model says so in its own words: it asks for judgement, or reaches across a repo.
# Only the advisory half reads these, so a miss costs a line, never a refusal.
WORK = re.compile(r"\b(design|architect|refactor|rewrite|migrat|review|audit|investigat|debug|diagnos|"
                  r"decide|trade-?off|root cause|why does|across the (repo|codebase)|every file|"
                  r"bug|fix|test|error|fail)", re.I)
CHORE = re.compile(r"\b(add|append|rename|list|count|fetch|copy|tidy|sort|summar(y|ise|ize)|"
                   r"look up|note|remind|shopping|groceries|errand)\b", re.I)
PRIVATE = re.compile(r"\b(legal|lawyer|solicitor|tax|salary|invoice|bank|mortgage|health|medical|"
                     r"doctor|diagnosis|prescription)\b", re.I)
BROWSER = re.compile(r"\b(browser|playwright|chrome|chromium|puppeteer|selenium|log ?in|sign ?in|screenshot)\b", re.I)
FRONT_MODEL = re.compile(r"^model:\s*([^\s#]+)\s*$", re.M)


def tiers(cwd):
    """The ladder and the ceilings here: the house's, with the repo's own word laid over it."""
    house = dict(rules().get("tiers") or {})
    mine = local(cwd).get("tiers")
    if isinstance(mine, dict):
        house.update({k: v for k, v in mine.items() if k in ("ceiling", "errand", "ladder", "costly")})
    return house


def capped(cwd):
    """The tier Charlotte capped this repo's sub agents at, or None. Her decision, and the only thing that refuses."""
    mine = local(cwd).get("tiers")
    return (mine or {}).get("ceiling") if isinstance(mine, dict) else None


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if t in m), None)


def highest(found, ladder):
    """The dearest rung among these models: a session that fell back is still a session that can spend."""
    rungs = [t for t in (tier_of(m, ladder) for m in found) if t]
    return max(rungs, key=ladder.index) if rungs else None


def pinned(agent_type, cwd):
    """The model an agent definition pins, from the repo's, the user's or the plugin's agents, or None."""
    name = str(agent_type or "").split(":")[-1].strip()
    if not name or not re.fullmatch(r"[\w.-]+", name):
        return None
    for folder in (Path(cwd or ".") / ".claude" / "agents", Path.home() / ".claude" / "agents", ROOT / "agents"):
        try:
            head = (folder / (name + ".md")).read_text(encoding="utf-8")[:2000]
        except OSError:
            continue
        found = FRONT_MODEL.search(head.split("---")[1] if head.startswith("---") and "---" in head[3:] else head)
        if found:
            return found.group(1)
    return None


def will_run_on(data, args, cwd, ladder):
    """The tier this spawn will really run on, as Claude Code resolves it: the call, then the agent file, then
    CLAUDE_CODE_SUBAGENT_MODEL, then the session's own model (docs/delegation.md). None when nothing says."""
    for model in (args.get("model"), pinned(args.get("subagent_type"), cwd), os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL")):
        rung = tier_of(model, ladder)
        if rung:
            return rung, bool(args.get("model"))
    return highest(models(data), ladder), False


def held(cwd):
    """The paths whose change always waits for her: the merging rule's, plus this repo's own."""
    return list(rules().get("merging", {}).get("hold") or []) + list(local(cwd).get("hold") or [])


def never_down(prompt, cwd):
    """Why this work keeps whatever model it was given, or None. Erring towards leaving work alone is safe."""
    for path in held(cwd):
        name = path.strip("/")
        if name and re.search(r"(^|[\s\"'`(/])" + re.escape(name) + r"(?=[/\s\"'`)]|$)", prompt):
            return "it names %s, whose changes always wait for her" % path
    if PRIVATE.search(prompt):
        return "it reads as one of her private matters"
    if BROWSER.search(prompt):
        return "it needs a browser, which the preflight rule governs"
    return None


def errand(prompt):
    """Does this read as an errand: short, an everyday verb, and nothing asking for judgement? A reading only."""
    text = prompt.strip()
    return bool(text) and len(text) <= 240 and not WORK.search(text) and bool(CHORE.search(text))


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this spawn with, and what to say about it. Either may be None."""
    if tool not in SPAWN or not enforced("right_sized", cwd):
        return None, None
    t = tiers(cwd)
    ladder = list(t.get("ladder") or [])
    if not ladder:
        return None, None
    prompt = " ".join(str(args.get(k) or "") for k in ("prompt", "description"))
    if never_down(prompt, cwd):
        return None, None

    spawn, named = will_run_on(data, args, cwd, ladder)

    # Her cap: facts only, so it holds whether or not the call names a model.
    said = capped(cwd)
    cap = tier_of(said, ladder)
    if said and not cap:
        # she capped this repo at something that is not on the ladder: say so rather than go quiet
        if once(data.get("session_id"), "badcap", "tier"):
            return None, ("House rule (KittyChat), spend what the task is worth: this repo's "
                          ".claude/catio-rules.json caps its sub agents at \"%s\", which is not one of %s, so the "
                          "cap is doing nothing. Tell Charlotte, and spawn at the tier the work needs meanwhile."
                          % (said, ", ".join(ladder)))
        return None, None
    if cap and spawn and ladder.index(spawn) > ladder.index(cap):
        return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents at "
                "%s, and this one would run on %s%s. Spawn it with model %s or below. If this really needs more, "
                "say so to her and she will raise the cap in .claude/catio-rules.json."
                % (cap, spawn, "" if named else " (inherited, since the call names none)", cap)), None

    # The harness's reading: a line, never a refusal.
    ceiling = tier_of(t.get("errand"), ladder)
    if ceiling and spawn and errand(prompt) and ladder.index(spawn) > ladder.index(ceiling) \
            and once(data.get("session_id"), "errand", "tier"):
        return None, ("House rule (KittyChat), spend what the task is worth: this reads as an errand (spelled out, "
                      "checkable, small) and it would run on %s. %s or below does it. Carry on if it is more than it "
                      "looks; if she tells you what this repo's sub agents should cost, write it into "
                      ".claude/catio-rules.json as {\"tiers\": {\"ceiling\": \"<tier>\"}} so the next session starts "
                      "from her decision instead of asking again."
                      % (spawn, ceiling.capitalize()))

    if not named and spawn and spawn in (t.get("costly") or []) and once(data.get("session_id"), "unnamed", "tier"):
        return None, ("House rule (KittyChat), spend what the task is worth: this spawn names no model, so it runs on "
                      "%s and makes its own requests there. Name the tier it needs on the call: %s, cheapest first. "
                      "The scout and the tester are Haiku already."
                      % (spawn, ", ".join(ladder)))
    return None, None
