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

from common import ROOT, enforced, entries, local, once, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
FRONT_MODEL = re.compile(r"^model:\s*([^\s#]+)\s*$", re.M)


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if t in m), None)


def tiers(cwd):
    """The ladder and the ceiling here: the house's, with the repo's own word laid over it."""
    out = dict(rules().get("tiers") or {})
    mine = local(cwd).get("tiers")
    if isinstance(mine, dict):
        out.update({k: v for k, v in mine.items() if k in ("ceiling", "ladder", "costly")})
    return out


def unusable(t):
    """Why this tiers block can't be acted on, or None. A rule that can't read its settings says so."""
    if not isinstance(t.get("ladder"), list) or not all(isinstance(x, str) and x for x in t["ladder"]):
        return "its ladder is not a list of tiers"
    ceiling = t.get("ceiling")
    if ceiling is None:
        return None
    if not isinstance(ceiling, str) or not ceiling.strip():
        return "its ceiling is not the name of a tier"
    if not tier_of(ceiling, t["ladder"]):
        return "its ceiling %r is not one of %s" % (ceiling, ", ".join(t["ladder"]))
    return None


def on_now(data, ladder):
    """The tier the session is on now: the last model that answered, not the dearest it ever used, because a
    session switched down with /model hands its sub agents the model it is on."""
    last = None
    for e in entries(data, '"model"'):
        if e.get("type") == "assistant" and not e.get("isSidechain"):
            rung = tier_of((e.get("message") or {}).get("model"), ladder)
            if rung:
                last = rung
    return last


def pinned(agent_type, cwd):
    """(the model this agent's definition pins, was there a definition at all). The first file that exists wins,
    shadowing the ones below it, whether or not it names a model - which is how Claude Code resolves it."""
    name = str(agent_type or "").split(":")[-1].strip()
    if not name or not re.fullmatch(r"[\w.-]+", name):
        return None, False
    for folder in (Path(cwd or ".") / ".claude" / "agents", Path.home() / ".claude" / "agents", ROOT / "agents"):
        try:
            head = (folder / (name + ".md")).read_text(encoding="utf-8")[:2000]
        except OSError:
            continue
        found = FRONT_MODEL.search(head.split("---")[1] if head.startswith("---") and "---" in head[3:] else head)
        return (found.group(1) if found else None), True
    return None, False


def will_run_on(data, args, cwd, ladder):
    """(tier, where it came from): the tier this spawn really runs on, in Claude Code's own resolution order."""
    forced = tier_of(os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE"), ladder)
    if forced:
        return forced, "the forced environment default"
    if args.get("model"):
        return tier_of(args["model"], ladder), "the call"
    model, has_file = pinned(args.get("subagent_type"), cwd)
    if has_file and model:
        return tier_of(model, ladder), "its agent file"
    if not has_file:
        env = tier_of(os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL"), ladder)
        if env:
            return env, "the environment default"
    return on_now(data, ladder), "the session"


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this spawn with, and what to say about it. Either may be None."""
    if tool not in SPAWN or data.get("agent_type") or not enforced("right_sized", cwd):
        return None, None   # a sub agent's own spawn reads its parent's transcript, so leave it be
    t = tiers(cwd)
    wrong = unusable(t)
    if wrong:
        if t.get("ceiling") is None:
            return None, None   # no cap to lose, so nothing is at stake
        if once(data.get("session_id"), "badcap", "tier"):
            return None, ("House rule (KittyChat), spend what the task is worth: this repo caps its sub agents, but "
                          "%s, so the cap is doing nothing. Tell Charlotte, and spawn at the tier the work needs "
                          "meanwhile." % wrong)
        return None, None

    ladder = t["ladder"]
    cap = tier_of(t.get("ceiling"), ladder)
    spawn, source = will_run_on(data, args, cwd, ladder)

    if cap:
        if not spawn:
            if once(data.get("session_id"), "unknown", "tier"):
                return None, ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub "
                              "agents at %s, and the tier this spawn would run on can't be read from here. Name it on "
                              "the call, at %s or below." % (cap, cap))
            return None, None
        if ladder.index(spawn) > ladder.index(cap):
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and this one would run on %s (from %s). Spawn it with model %s or below. If this really "
                    "needs more, say so to her and she will raise the cap in .claude/catio-rules.json."
                    % (cap, spawn, source, cap)), None
        return None, None

    if source == "the session" and spawn and spawn in (t.get("costly") or []) \
            and once(data.get("session_id"), "inherit", "tier"):
        return None, ("House rule (KittyChat), spend what the task is worth: this spawn names no tier anywhere, so it "
                      "runs on %s, the model this session is on, and makes its own requests there. Name the tier it "
                      "needs on the call: %s, cheapest first. The scout and the tester are Haiku already. When she "
                      "says what this repo's sub agents should cost, write it into .claude/catio-rules.json as "
                      "{\"tiers\": {\"ceiling\": \"<tier>\"}} so the next session starts from her decision."
                      % (spawn, ", ".join(ladder)))
    return None, None
