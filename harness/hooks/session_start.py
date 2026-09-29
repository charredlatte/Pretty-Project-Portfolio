#!/usr/bin/env python3
"""SessionStart: tell the session it lives in Charlotte's KittyChat harness, and what the house rules are."""
from common import enforced, hook_input, rules


def main():
    data = hook_input()
    cwd = data.get("cwd")
    r = rules()
    lines = [
        "# KittyChat house rules",
        "",
        "This session is a cat in Charlotte's Catio, her harness: " + r["catio"],
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
    if data.get("source", "startup") == "startup" and enforced("opening_audit", cwd):
        lines += ["", "Start now with the read-only pass: run the ponytail-audit skill on this repo before anything else,",
                  "then run the `catio` skill's catch-up (files, notes and requests waiting for you)."]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
