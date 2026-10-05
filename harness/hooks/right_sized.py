"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

The hook enforces one thing, on the one fact it can actually see: the model the call names.

- **Her cap refuses.** Where Charlotte has capped a repo's sub agents (`tiers.ceiling` in its
  `.claude/catio-rules.json`), every spawn there names its model on the call, at or below her cap. A spawn
  that names none is refused too, because an unnamed one runs on whatever the session is on - which is how an
  errand ends up costing Opus, and is the whole reason for the cap.
- **A costly inheritance speaks.** With no cap, a spawn that names no model gets one line a session saying
  which model it is about to inherit.

What the hook deliberately does not do is work out the tier an unnamed spawn would resolve to. Claude Code
resolves that from two environment variables, the agent's own file and the session's model, and guessing at
another program's internals from a hook is wrong in both directions: it waves spawns past her cap when it
guesses low and refuses cheap ones when it guesses high. Naming the model is the thing the session can always
do, and it is what every refusal here asks for.

Whether a *task* is easy enough for a small model is not decided here either. That is the `decide` tool's
`easy` preset, the six-question rubric of docs/delegation.md, answered by a decision model in milliseconds.

Nothing here switches the session's own model: the tier is chosen for the work being spawned, because
switching the conversation mid-way throws its prompt cache away and costs more than the routing saves.
"""
from common import answered, enforced, local, once, rules

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
KEYS = ("ceiling", "ladder", "costly")


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if str(t).lower() in m), None)


def tiers(cwd):
    """The ladder and the ceiling here: the house's, with the repo's own word laid over it."""
    out = dict(rules().get("tiers") or {})
    mine = local(cwd).get("tiers")
    if isinstance(mine, dict):
        out.update({k: v for k, v in mine.items() if k in KEYS})
    return out


def house_ok(t):
    """The house's own ladder, which the rule can do nothing without."""
    return isinstance(t.get("ladder"), list) and all(isinstance(x, str) and x for x in t["ladder"])


def misread(cwd, t):
    """Why what Charlotte wrote here can't be acted on, or None. A rule that can't read her settings says so
    rather than going quiet; a key it doesn't know (a comment of hers, say) is simply not one of its settings."""
    raw = local(cwd)
    mine = raw.get("tiers")
    if "tiers" in raw and not isinstance(mine, dict):
        return "its tiers is not an object"
    if not house_ok(t):
        return ("its ladder is not a list of tiers" if isinstance(mine, dict) and "ladder" in mine
                else "the house's own ladder is not a list of tiers")
    if "ceiling" in raw and "ceiling" not in (mine or {}):
        return "its ceiling sits outside the tiers block"
    if isinstance(mine, dict) and "ceiling" in mine:
        ceiling = mine["ceiling"]
        if not isinstance(ceiling, str) or not ceiling.strip():
            return "its ceiling is not the name of a tier"
        if not tier_of(ceiling, t.get("ladder") or []):
            return "its ceiling %r is not one of %s" % (ceiling, ", ".join(map(str, t.get("ladder") or [])))
    return None


def on_now(data, ladder):
    """The tier the session is on now: the last model that answered. Only the line about what an unnamed spawn
    inherits needs this, never a refusal."""
    rungs = [t for t in (tier_of(m, ladder) for m in answered(data, ("transcript_path",))) if t]
    return rungs[-1] if rungs else None


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this spawn with, and what to say about it. Either may be None."""
    if tool not in SPAWN or not enforced("right_sized", cwd):
        return None, None
    sid, t = data.get("session_id"), tiers(cwd)
    wrong = misread(cwd, t)
    if wrong:
        if not {"tiers", "ceiling"} & set(local(cwd)):
            return None, None   # she has said nothing here, so there is nothing of hers to lose
        if once(sid, "badcap", "tier", cwd):
            return None, ("House rule (KittyChat), spend what the task is worth: this repo caps its sub agents, but "
                          "%s, so the cap is doing nothing. Tell Charlotte, and spawn at the tier the work needs "
                          "meanwhile." % wrong)
        return None, None

    ladder = t["ladder"]
    cap = tier_of(t.get("ceiling"), ladder)
    named = args.get("model")

    if cap:
        at_most = "model %s or below (%s)" % (cap, ", ".join(ladder[:ladder.index(cap) + 1]))
        if not named:
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and this spawn names no model, so it would run on whatever this session is on. Name it "
                    "on the call: %s." % (cap, at_most)), None
        rung = tier_of(named, ladder)
        if not rung:
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and %r is not one of %s, so what it would cost can't be told from here. Name one: %s."
                    % (cap, str(named), ", ".join(ladder), at_most)), None
        if ladder.index(rung) > ladder.index(cap):
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents "
                    "at %s, and this one names %s. Spawn it with %s. If this really needs more, say so to her and "
                    "she will raise the cap in .claude/catio-rules.json." % (cap, rung, at_most)), None
        return None, None

    if not named and once(sid, "inherit", "tier", cwd, peek=True):
        spawn = on_now(data, ladder)
        costly = [str(c).lower() for c in (t.get("costly") or [])]
        if spawn and spawn.lower() in costly and once(sid, "inherit", "tier", cwd):
            return None, ("House rule (KittyChat), spend what the task is worth: this spawn names no model, so it "
                          "runs on %s, the model this session is on, and makes its own requests there. Name the tier "
                          "it needs on the call: %s, cheapest first. The scout and the tester are Haiku already. "
                          "When she says what this repo's sub agents should cost, write it into "
                          ".claude/catio-rules.json as {\"tiers\": {\"ceiling\": \"<tier>\"}} so the next session "
                          "starts from her decision." % (spawn, ", ".join(ladder)))
    return None, None
