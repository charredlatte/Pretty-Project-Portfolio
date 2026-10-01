#!/usr/bin/env python3
"""Stop hook for the semi-automatic shipping rule.

When a turn ends on a feature branch with work that isn't pushed, hold the stop once and ask Claude to
ship it (commit, push, and open a PR when the work is a complete unit) or to say why not. Silent on the
default branch, outside git, without a remote, and on the second stop (stop_hook_active).

In a cloud session (CLAUDE_CODE_REMOTE) every repo checked out beside this one is checked too: the container
is the session's own, and is thrown away with anything left unpushed in it (litterbox/sort.py writes there).
"""
import json
import os
import subprocess
from pathlib import Path

from common import enforced, hook_input, merges


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


def repos(cwd):
    """This repo and, in a cloud session, every repo beside it (or under cwd, when cwd isn't one)."""
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    if os.environ.get("CLAUDE_CODE_REMOTE") != "true":
        return [top] if top else []
    here = Path(top).parent if top else Path(cwd or ".")
    beside = sorted(str(d) for d in here.iterdir() if (d / ".git").exists() and str(d) != top)
    return ([top] if top else []) + beside


def unshipped(repo):
    """What a repo holds that isn't pushed, or None."""
    if not git("remote", cwd=repo):
        return None
    branch = git("branch", "--show-current", cwd=repo)
    if not branch or branch == default_branch(repo):
        return None
    # graphify's map (graphify-out/) is a local build, not work to ship
    dirty = any("graphify-out/" not in l for l in (git("status", "--porcelain", "--untracked-files=normal", cwd=repo) or "").splitlines())
    upstream = git("rev-parse", "--abbrev-ref", "@{u}", cwd=repo)
    ahead = git("rev-list", "--count", (upstream or "origin/" + default_branch(repo)) + "..HEAD", cwd=repo)
    if not (dirty or (ahead and ahead != "0")):
        return None
    return f"branch {branch} has " + ("uncommitted changes" if dirty else "commits that aren't pushed")


def main():
    data = hook_input()
    cwd = data.get("cwd")
    if data.get("stop_hook_active") or not enforced("ship", cwd):
        return
    found = [(r, w) for r, w in ((r, unshipped(r)) for r in repos(cwd)) if w]
    if not found:
        return
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    what = "; ".join(w if r == top else f"{Path(r).name}'s {w}" for r, w in found)
    merging = [Path(r).name for r, _ in found if merges(r)]
    merge = (f" {', '.join(merging)} {'merges' if len(merging) == 1 else 'merge'} its own pull requests: merge the "
             "pull request once its checks pass. Never push to the "
             "default branch, no force-push, and no merge anywhere else." if merging else
             " Never the default branch, no force-push, no merge.")
    print(json.dumps({
        "decision": "block",
        "reason": f"House rule (KittyChat, semi-automatic shipping): {what}. If the change is done and "
                  "the repo's checks pass, commit it and push it now, and open a pull request if the work is a complete "
                  "unit and none is open." + merge + " If it isn't ready, say in one line why not and stop.",
    }))


if __name__ == "__main__":
    main()
