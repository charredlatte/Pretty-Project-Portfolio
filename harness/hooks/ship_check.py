#!/usr/bin/env python3
"""Stop hook for the semi-automatic shipping rule.

When a turn ends on a feature branch with work that isn't pushed, hold the stop once and ask Claude to
ship it (commit, push, and open a PR when the work is a complete unit) or to say why not. Silent on the
default branch, outside git, without a remote, and on the second stop (stop_hook_active).
"""
import json
import subprocess

from common import enforced, hook_input


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def default_branch(cwd):
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=cwd)
    if head:
        return head.split("/", 1)[-1]
    for name in ("main", "master"):
        if git("rev-parse", "--verify", "--quiet", "refs/remotes/origin/" + name, cwd=cwd) is not None:
            return name
    return "main"


def main():
    data = hook_input()
    cwd = data.get("cwd")
    if data.get("stop_hook_active") or not enforced("ship", cwd):
        return
    if git("rev-parse", "--git-dir", cwd=cwd) is None or not git("remote", cwd=cwd):
        return
    branch = git("branch", "--show-current", cwd=cwd)
    if not branch or branch == default_branch(cwd):
        return
    dirty = bool(git("status", "--porcelain", "--untracked-files=normal", cwd=cwd))
    upstream = git("rev-parse", "--abbrev-ref", "@{u}", cwd=cwd)
    ahead = git("rev-list", "--count", (upstream or "origin/" + default_branch(cwd)) + "..HEAD", cwd=cwd)
    unpushed = bool(ahead and ahead != "0")
    if not (dirty or unpushed):
        return
    what = "uncommitted changes" if dirty else "commits that aren't pushed"
    print(json.dumps({
        "decision": "block",
        "reason": f"House rule (KittyChat, semi-automatic shipping): branch {branch} has {what}. If the change is done and "
                  "the repo's checks pass, commit it and push it now, and open a pull request if the work is a complete "
                  "unit and none is open. Never the default branch, no force-push, no merge. If it isn't ready, say in one "
                  "line why not and stop.",
    }))


if __name__ == "__main__":
    main()
