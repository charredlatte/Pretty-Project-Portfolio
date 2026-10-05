#!/usr/bin/env python3
"""SessionStart: tell the session it lives in Charlotte's KittyChat harness, and what the house rules are."""
import os
from pathlib import Path

from common import enforced, hook_input, local, merges, repos, rules


def main():
    data = hook_input()
    cwd = data.get("cwd")
    r = rules()
    lines = [
        "# KittyChat house rules",
        "",
        "This session is a cat in Charlotte's Catio, her harness: " + r["catio"] + "." + ("" if os.environ.get("CATIO_URL") and os.environ.get("CATIO_TOKEN")
            else " This environment isn't connected to it (no CATIO_URL and CATIO_TOKEN), so nothing you report reaches her café."),
        "She can drop files on your cat, write to you and manage you from there. Those messages arrive as turns",
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
            for repo in repos(cwd):
                name, held = Path(repo).name, ", ".join(local(repo).get("hold", []))
                if not merges(repo):
                    lines.append(f"  {name}'s pull requests are hers to merge.")
                else:
                    lines.append(f"  {name} merges its own pull requests" +
                                 (f"; changes to {held} always wait for her." if held else "."))
    if data.get("source", "startup") == "startup" and enforced("opening_audit", cwd):
        lines += ["", "Start now with the read-only pass: run the ponytail-audit skill on this repo before anything else,",
                  "then run the `catio` skill's catch-up (files, notes and requests waiting for you)."]
    model = data.get("model") or ""
    costly = next((x.get("costly", []) for x in r["rules"] if x["id"] == "opus_default"), [])
    if enforced("opus_default", cwd) and any(c in model.lower() for c in costly):
        lines += ["", f"This session is on {model}, which uses Charlotte's allowance several times faster than Opus. Unless she",
                  "asked for it by name, say so in one line in your first reply and suggest /model opus."]
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
    main()
