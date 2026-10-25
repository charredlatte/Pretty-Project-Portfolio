#!/usr/bin/env python3
"""SessionStart: tell the session which KittyChat café it lives in, and what the house rules are."""
import os
from pathlib import Path

try:   # a brief that cannot be built must say so: exit 1 loses all of it and leaves only a traceback
    from common import enforced, holds, hook_input, local, merges, repos, rules
except Exception as _e:
    import sys
    print("# KittyChat house rules\n\nThe house rules couldn't be loaded (%s: %s), so this session has not "
          "been told them. Run the ponytail-audit skill before changing anything, and tell Charlotte."
          % (type(_e).__name__, _e))
    sys.exit(0)


def main():
    data = hook_input()
    cwd = data.get("cwd")
    r = rules()
    gateway = os.environ.get("CATIO_URL", "").strip()
    whose, they = "their", "They"
    # The café is wherever CATIO_URL points, and nowhere else. The rules file names no address of anyone's, so a
    # session without one is told it isn't connected, rather than handed somebody else's café as its own.
    if gateway:
        cafe = f"This session is a cat in the KittyChat Café of the person you are working for, at {gateway}."
    else:
        cafe = ("This session isn't connected to a KittyChat Café: CATIO_URL isn't set, so no cat checks in and nothing is "
                "handed over. The house rules below still hold; harness/gateway/README.md says how to connect one.")
    lines = [
        "# KittyChat house rules",
        "",
        cafe,
        f"{they} can drop files on your cat, write to you and manage you from there. Those messages arrive as turns",
        "that start with [Catio]; use the `catio` skill to handle them.",
        "",
    ]
    for rule in r["rules"]:
        if not rule.get("on", True):
            continue
        if rule["enforced"] and not enforced(rule["id"], cwd):
            continue
        lines.append(f"- **{rule['title']}**{' (enforced)' if rule['enforced'] else ''}: {rule['text']}")
        if rule["id"] == "merge":
            _, house_odd = holds(r.get("merging", {}))   # the same for every checkout: read it once
            for repo in repos(cwd):
                # Both lists are checked, the same two the merge gate reads, because the gate holds on
                # either: a brief that looked at only one claimed merge rights the gate was refusing. Only
                # the repo's own paths are named, as before - whether the house's .claude/ should be named
                # here too is a change to what the brief says, so it is Charlotte's to ask for.
                mine, mine_odd = holds(local(repo))
                name, held = Path(repo).name, ", ".join(mine)
                broken = [w for w, odd in (("the house rules'", house_odd), (f"{name}'s", mine_odd)) if odd]
                if not merges(repo):
                    lines.append(f"  {name}'s pull requests are hers to merge.")
                elif broken:   # the gate holds every merge there: don't say it may merge
                    lines.append(f"  {' and '.join(broken)} hold list is in a shape the harness can't read, "
                                 f"so every pull request in {name} waits for her until she fixes it.")
                else:
                    lines.append(f"  {name} merges its own pull requests" +
                                 (f"; changes to {held} always wait for her." if held else "."))
    if data.get("source", "startup") == "startup" and enforced("opening_audit", cwd):
        lines += ["", "Start now with the read-only pass: run the ponytail-audit skill on this repo before anything else,",
                  "then run the `catio` skill's catch-up (files, notes and requests waiting for you). This plugin doesn't ship",
                  "ponytail-audit: if it isn't installed, say so, and ask whether to install it or switch the rule off for this",
                  'repo with {"opening_audit": false} in .claude/catio-rules.json (not yours to decide).']
    model = data.get("model") or ""
    costly = next((x.get("costly", []) for x in r["rules"] if x["id"] == "opus_default"), [])
    if enforced("opus_default", cwd) and any(c in model.lower() for c in costly):
        lines += ["", f"This session is on {model}, which uses {whose} allowance several times faster than Opus. Unless "
                  f"{they.lower()}", "asked for it by name, say so in one line in your first reply and suggest /model opus."]
    if enforced("graph_first", cwd):
        if (Path(cwd or ".") / "graphify-out" / "graph.json").exists():
            lines += ["", "This repo has a graphify map in graphify-out/. Run `graphify update .` to bring it up to date, then ask it",
                      "(`graphify query`, `path`, `explain`) before grepping or reading files."]
        else:
            lines += ["", "This repo has no graphify map yet. Before digging in, build one with the graphify skill (`graphify update .`",
                      "maps the code with no model), keep graphify-out/ out of git (.git/info/exclude), and save it to the Catio",
                      "as the `catio` skill's Project map section says."]
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # the same class gates.py fails closed on: say it, rather than print nothing
        print("# KittyChat house rules\n\nThe house rules couldn't be read (%s: %s), so this session has not "
              "been told them. Run the ponytail-audit skill before changing anything, and tell Charlotte."
              % (type(e).__name__, e))
