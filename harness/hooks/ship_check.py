#!/usr/bin/env python3
"""Stop hook for the semi-automatic shipping rule.

When a turn ends on a feature branch with work that isn't pushed, hold the stop once and ask Claude to
ship it (commit, push, and open a PR when the work is a complete unit) or to say why not. Silent on the
default branch, outside git, without a remote, and on the second stop (stop_hook_active).

In a cloud session (CLAUDE_CODE_REMOTE) every repo checked out beside this one is checked too: the container
is the session's own, and is thrown away with anything left unpushed in it (litterbox/sort.py writes there).
"""
import json
from pathlib import Path

from common import default_branch, enforced, git, hook_input, merges, repos


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
    merge = (f" {', '.join(merging)} {'merges' if len(merging) == 1 else 'merge'} its own pull requests: when the work "
             "is finished, run the code-review skill on the pull request and merge it as the merging rule says (the "
             "house rules merge it or hold it for her)." if merging else "")
    if len(merging) < len(found):
        merge += (" Anywhere else, a" if merging else " A") + " finished pull request is hers to merge: tell her it's ready."
    merge += " Never the default branch, no force-push."
    print(json.dumps({
        "decision": "block",
        "reason": f"House rule (KittyChat, semi-automatic shipping): {what}. If the change is done and "
                  "the repo's checks pass, commit it and push it now, and open a pull request if the work is a complete "
                  "unit and none is open." + merge + " If it isn't ready, say in one line why not and stop.",
    }))


if __name__ == "__main__":
    main()
