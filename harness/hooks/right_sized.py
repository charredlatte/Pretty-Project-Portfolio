"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

The hook deals in facts only. It works out the tier a spawn would really run on, the way Claude Code resolves
one - CLAUDE_CODE_SUBAGENT_MODEL_FORCE, then the model the call names, then the one its agent file pins, then
CLAUDE_CODE_SUBAGENT_MODEL, then the model the session is on - and does two things with it:

- **Her cap refuses.** Where Charlotte has capped a repo's sub agents (`tiers.ceiling` in its
  `.claude/catio-rules.json`), a spawn above that cap is refused, whether or not the call names a model. Two
  facts compared, so leaving `model` off the call cannot slip past it.
- **A costly inheritance speaks.** A spawn that names no tier anywhere runs on whatever the session is on, which
  is how an errand ends up costing Opus. That earns one line a session, and never a block.

Whether a *task* is easy enough for a small model is not decided here. Reading a prompt's words is a guess, and
the house already has something better: the `decide` tool's `easy` preset, the six-question rubric of
docs/delegation.md, answered by a decision model in milliseconds. The queen asks it; a hook on the tool-call
path stays offline and deals only in what it can check.

Nothing here switches the session's own model: the tier is chosen for the work being spawned, because switching
the conversation mid-way throws its prompt cache away and costs more than the routing saves.
"""
import os
import re
from pathlib import Path

from common import ROOT, answered, enforced, local, once, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
FRONT_MODEL = re.compile(r"^model:[ \t]*([^\s#]+)[ \t]*(?:#.*)?$", re.M)


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if str(t).lower() in m), None)


def tiers(cwd):
    """The ladder and the ceiling here: the house's, with the repo's own word laid over it."""
    out = dict(rules().get("tiers") or {})
    mine = local(cwd).get("tiers")
    if isinstance(mine, dict):
        out.update({k: v for k, v in mine.items() if k in ("ceiling", "ladder", "costly")})
    return out


def misread(cwd, t):
    """Why her settings can't be acted on, or None. A rule that can't read what she wrote says so rather than
    going quiet, and that includes the shapes a hand-written file comes in: the wrong type, a typo, a key
    outside the block it belongs in."""
    raw = local(cwd)
    mine = raw.get("tiers")
    if mine is not None and not isinstance(mine, dict):
        return "its tiers is not an object"
    if isinstance(mine, dict):
        odd = [k for k in mine if k not in ("ceiling", "ladder", "costly")]
        if odd:
            return "its tiers has no %s setting" % ", ".join(sorted(odd))
    if "ceiling" in raw and "ceiling" not in (mine or {}):
        return "its ceiling sits outside the tiers block"
    return unusable(t)


def unusable(t):
    """Why this tiers block can't be acted on, or None."""
    if not isinstance(t.get("ladder"), list) or not all(isinstance(x, str) and x for x in t["ladder"]):
        return "its ladder is not a list of tiers"
    if not isinstance(t.get("costly", []), list) or not all(isinstance(x, str) for x in t.get("costly", [])):
        return "its costly is not a list of tiers"
    ceiling = t.get("ceiling")
    if ceiling is None:
        return None
    if not isinstance(ceiling, str) or not ceiling.strip():
        return "its ceiling is not the name of a tier"
    if not tier_of(ceiling, t["ladder"]):
        return "its ceiling %r is not one of %s" % (ceiling, ", ".join(t["ladder"]))
    return None


def on_now(data, ladder):
    """The tier whatever is spawning is on now: the last model that answered, not the dearest it ever used,
    because a session switched down with /model hands its sub agents the model it is on. Inside a sub agent only
    its own transcript counts, since that is the model its own spawns would inherit."""
    inside = bool(data.get("agent_type"))
    found = answered(data, ("agent_transcript_path",) if inside else ("transcript_path",), sidechain=inside)
    rungs = [t for t in (tier_of(m, ladder) for m in found) if t]
    return rungs[-1] if rungs else None


def pinned(agent_type, cwd):
    """The model this agent's definition pins, or None. The first file that exists wins,
    shadowing the ones below it, whether or not it names a model - which is how Claude Code resolves it. Only a
    real frontmatter block is read: a `model:` line in the prose below it is not a pin."""
    raw = str(agent_type or "").strip()
    name = raw.split(":")[-1].strip()
    if not name or not re.fullmatch(r"[\w.-]+", name):
        return None
    # a namespaced name (plugin:agent) is that plugin's agent, so a project file of the same name is not it
    folders = [ROOT / "agents"] if ":" in raw else \
        [Path(cwd or ".") / ".claude" / "agents", Path.home() / ".claude" / "agents", ROOT / "agents"]
    for folder in folders:
        try:
            text = (folder / (name + ".md")).read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---") or "\n---" not in text[3:]:
            return None                  # a file with no readable header pins nothing; its prose is not a pin
        found = FRONT_MODEL.search(text[3:text.index("\n---", 3)])
        return found.group(1) if found else None
    return None


def will_run_on(data, args, cwd, ladder):
    """(tier, where it came from): the tier this spawn really runs on, in Claude Code's own resolution order.
    A name the ladder doesn't know - "inherit", the value that means the conversation's own model - is not an
    answer, so the walk carries on rather than giving up and letting the spawn through."""
    forced = tier_of(os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE"), ladder)
    if forced:
        return forced, "the forced environment default"
    named = tier_of(args.get("model"), ladder)
    if named:
        return named, "the call"
    rung = tier_of(pinned(args.get("subagent_type"), cwd), ladder)
    if rung:
        return rung, "its agent file"
    env = tier_of(os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL"), ladder)
    if env:
        return env, "the environment default"
    return on_now(data, ladder), "the session"


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this spawn with, and what to say about it. Either may be None."""
    if tool not in SPAWN or not enforced("right_sized", cwd):
        return None, None
    sid = data.get("session_id")
    t = tiers(cwd)
    wrong = misread(cwd, t)
    if wrong:
        if not {"tiers", "ceiling"} & set(local(cwd)) and t.get("ceiling") is None:
            return None, None   # she has said nothing here, so there is nothing of hers to lose
        if once(sid, "badcap", "tier", cwd):
            return None, ("House rule (KittyChat), spend what the task is worth: this repo's settings cap its sub "
                          "agents, but %s, so the cap is doing nothing. Tell Charlotte, and spawn at the tier the "
                          "work needs meanwhile." % wrong)
        return None, None

    ladder = t["ladder"]
    cap = tier_of(t.get("ceiling"), ladder)
    if not cap and not once(sid, "inherit", "tier", cwd, peek=True):
        return None, None   # nothing to enforce and the one line already said: don't read the transcript again
    spawn, source = will_run_on(data, args, cwd, ladder)

    if cap:
        if not spawn:
            # her cap is a promise, so an unreadable tier is refused rather than waved through: naming one works
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and the tier this one would run on can't be read from here. Name it on the call, with "
                    "model %s or below." % (cap, cap)), None
        if ladder.index(spawn) > ladder.index(cap):
            how = ("Unset CLAUDE_CODE_SUBAGENT_MODEL_FORCE, which overrides the call, or ask her to raise the cap"
                   if source == "the forced environment default" else
                   "Spawn it with model %s or below. If this really needs more, say so to her and she will raise "
                   "the cap in .claude/catio-rules.json" % cap)
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and this one would run on %s (from %s). %s." % (cap, spawn, source, how)), None

    if source == "the session" and spawn and spawn in (t.get("costly") or []) \
            and once(sid, "inherit", "tier", cwd):
        return None, ("House rule (KittyChat), spend what the task is worth: this spawn names no tier anywhere, so it "
                      "runs on %s, the model this session is on, and makes its own requests there. Name the tier it "
                      "needs on the call: %s, cheapest first. The scout and the tester are Haiku already. When she "
                      "says what this repo's sub agents should cost, write it into .claude/catio-rules.json as "
                      "{\"tiers\": {\"ceiling\": \"<tier>\"}} so the next session starts from her decision."
                      % (spawn, ", ".join(ladder)))
    return None, None
