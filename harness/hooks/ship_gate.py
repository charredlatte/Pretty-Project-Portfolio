"""PreToolUse gate for the shipping and merging house rules (gates.py calls it).

ship    no push to the default branch, no force-push, and no deleting a branch that isn't merged yet (and only in
        a repo that merges its own pull requests).
merge   semi-automatic merging. A pull request merges only in a repo that opts in ({"merge": true} in its
        .claude/catio-rules.json), and only when every model that worked in the session is on rules.json's strong
        list, the audits ran and the review ran after the last commit, the merge is pinned to the commit that was
        reviewed (expectedHeadSha = HEAD, nothing uncommitted), nothing on the hold list changed, and the commit
        message ends with "Checks: <what passed>" and "Guesses: none". What the session can fix, it is told to fix.
        Guesswork (a guess it names, a model not on the list, a held path) is held for Charlotte: the pull request
        stays open, and a note for her review goes in the litter box.
"""
import re
import shlex
import subprocess
from datetime import date
from pathlib import Path

from common import block, checkouts, default_branch, enforced, git, local, merges, models, ran, rules, skill_calls

REMOTE = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
START = r"(?:^|[;&|(])\s*(?:\w+=\S*\s+)*"  # where a command starts: not inside another one's arguments
PUSH = re.compile(START + r"git\s+(?:-C\s+(\S+)\s+)?push\b", re.M)
GH_MERGE = re.compile(START + r"gh\s+pr\s+merge\b", re.M)
API_WRITES = re.compile(r"^mcp__github__(push_files|create_or_update_file|delete_file)$")
SAY = "House rule (KittyChat): "


def words(text):
    """The arguments the shell would give the command that starts at `text`, up to the next ; & | ( ) or line end."""
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()\n")
    lex.whitespace, lex.whitespace_split, out = " \t\r", True, []
    try:
        for w in lex:
            if w and set(w) <= set(";&|()\n") or re.search(r"[<>]", w):  # the next command, or a redirect
                break
            out.append(w)
    except ValueError:  # an unclosed quote further on: keep what came before it
        pass
    return out


def where(command, at, cwd, given=None):
    """The folder a command at position `at` runs in: its -C, else the last cd before it, else cwd."""
    cds = re.findall(r"\bcd\s+([^\s;&|)]+)", command[:at])
    place = given or (cds[-1] if cds else "")
    return str(Path(cwd, Path(place.strip("'\"")).expanduser())) if place else cwd


def slug(repo):
    m = REMOTE.search(git("remote", "get-url", "origin", cwd=repo) or "")
    return m.group(1) if m else ""


def checkout_of(name, cwd):
    """The checkout of owner/repo `name` here: cwd's repo, one beside it, or one under cwd."""
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", name or ""):
        return None
    return next((r for r in checkouts(cwd) if slug(r).lower() == name.lower()), None)


# --- pushes ---------------------------------------------------------------------------------------------------

def check_push(args, repo):
    flags = [a for a in args if a.startswith("-")]
    pos = [a for a in args if not a.startswith("-")]
    if any(f in ("--mirror", "--all") for f in flags):
        block(SAY + "push one branch at a time, by name (no --all or --mirror).")
    if any(f.startswith("--force") or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", f) for f in flags) \
            or any(p.startswith("+") for p in pos[1:]):
        block(SAY + "no force-push. Merge the default branch into this one instead, and push that.")
    remote, specs = (pos[0] if pos else "origin"), pos[1:]
    deleting = "--delete" in flags or any(re.fullmatch(r"-[a-zA-Z]*d[a-zA-Z]*", f) for f in flags)
    branch = git("branch", "--show-current", cwd=repo) or ""
    if not specs and not deleting and "--tags" not in flags:
        specs = [branch]
    default = default_branch(repo)
    for spec in specs:
        gone = deleting or spec.startswith(":")
        src, _, dst = spec.lstrip(":").partition(":")
        name = re.sub(r"^refs/heads/", "", dst or (branch if src == "HEAD" else src))
        if name == default:
            block(SAY + f"never push to the default branch ({default}). Push this work to the session's branch "
                  "and open a pull request; merging is the merging rule's.")
        if gone:
            check_delete(repo, remote, name, default)


def check_delete(repo, remote, name, default):
    if not merges(repo):
        block(SAY + f"this repo's branches are Charlotte's to delete. Leave {name} for her.")
    fetched = git("fetch", "-q", remote, default, name, cwd=repo) is not None
    merged = fetched and subprocess.run(["git", "merge-base", "--is-ancestor", f"refs/remotes/{remote}/{name}",
                                         f"refs/remotes/{remote}/{default}"], cwd=repo, capture_output=True).returncode == 0
    if not merged:
        block(SAY + f"{name} isn't merged into {default}, so it stays. Only a merged branch is deleted.")


# --- merges ---------------------------------------------------------------------------------------------------

def check_merge(data, cwd, name, number, message, head):
    pr = f"PR #{number}"
    repo = checkout_of(name, cwd)
    if not repo:
        block(SAY + f"there's no checkout of {name} here to check {pr} against. Check it out beside this session "
              f"and try again, or leave it and tell her in one line: \"{pr} is ready for you to merge.\"")
    if not merges(repo):
        block(SAY + f"{name} doesn't merge its own pull requests (no \"merge\": true in its .claude/catio-rules.json). "
              f"Leave {pr} open and tell her in one line: \"{pr} is ready for you to merge.\"")
    cfg = rules().get("merging", {})
    fix, held = [], []

    used = models(data)
    weak = sorted(m for m in used if not any(s in m.lower() for s in cfg.get("strong", [])))
    if not used:
        held.append("the session's transcript doesn't say which model did the work")
    elif weak:
        held.append(f"{', '.join(weak)} worked on it, and only {' or '.join(cfg.get('strong', []))} may merge")

    for skill in cfg.get("audits", []):
        if not ran(data, skill):
            fix.append(f"run the {skill} skill")
    review, sha = cfg.get("review", "code-review"), git("rev-parse", "HEAD", cwd=repo)
    made = int(git("log", "-1", "--format=%ct", cwd=repo) or 0)
    if not any(review in s and when >= made for s, when in skill_calls(data)):
        fix.append(f"run the {review} skill on {pr} (it hasn't run since the last commit)")
    if not head:
        fix.append(f"pass expectedHeadSha: {sha}, the commit that was reviewed")
    elif head != sha:
        fix.append(f"expectedHeadSha is {head}, but this checkout is at {sha}: check out and review what's on {pr}")
    if any("graphify-out/" not in l for l in (git("status", "--porcelain", cwd=repo) or "").splitlines()):
        fix.append("commit or drop the uncommitted changes")

    base = git("merge-base", f"refs/remotes/origin/{default_branch(repo)}", "HEAD", cwd=repo)
    changed = (git("diff", "--name-only", base, "HEAD", cwd=repo) or "").splitlines() if base else None
    holds = [h.rstrip("/") for h in cfg.get("hold", []) + local(repo).get("hold", [])]
    if changed is None:
        held.append("there's no way to tell what it changes")
    else:
        touched = sorted({h for p in changed for h in holds if p == h or p.startswith(h + "/")})
        if touched:
            held.append(f"it changes {', '.join(touched)}, which always waits for her")

    card = message or ""
    guess = re.search(r"^Guesses:", card, re.M)
    if not (re.search(r"^Checks:\s*\S", card, re.M) and guess):
        fix.append("end the merge's commit message with \"Checks: <what ran and passed>\" and \"Guesses: none\" "
                   "(or each thing you assumed rather than checked)")
    else:
        guesses = " ".join(card[guess.end():].split())
        if guesses.rstrip(".").lower() != "none":
            held.append("guesses: " + guesses)

    if held:
        hold(cwd, name, number, held + fix)
    if fix:
        block(SAY + f"not ready to merge {pr} yet: " + "; ".join(fix) + ". Then merge it again.")


def hold(cwd, name, number, why):
    """Leave the pull request for Charlotte, with a note in the litter box saying why."""
    pr, reason = f"PR #{number}", "; ".join(w.rstrip(".") for w in why)
    box = next((Path(r) / "litterbox" for r in checkouts(cwd) if (Path(r) / "litterbox" / "sort.py").exists()), None)
    if box:
        repo = name.split("/")[-1]
        note = box / f"held-{repo.lower()}-{number}.md"
        note.write_text(f"""---
project: {repo}
date: {date.today().isoformat()}
---
# Held for review: {name}#{number}

## Waiting on Charlotte

- [ ] [{name}#{number}](https://github.com/{name}/pull/{number}) is held for your review before it merges: {reason}.
  Merge it on GitHub if it's right, or say what to change.
""", encoding="utf-8")
        filed = f"A note for her review is in {note}: commit and push it on this session's branch."
    else:
        filed = "No litter box is checked out here: put the same reasons in a comment on the pull request."
    block(SAY + f"semi-automatic merging held {pr} for Charlotte: {reason}. {filed} Leave {pr} open, don't merge "
          f"it, and tell her in one line: \"{pr} is waiting for your review: {reason}.\"")


def gh_merge(args):
    """The PR number, its owner/repo (when given), the merge's body and its pinned head, from `gh pr merge` args."""
    out, i = {"auto": False}, 0
    while i < len(args):
        a, key = args[i], args[i].split("=", 1)[0]
        value = a.split("=", 1)[1] if "=" in a else (args[i + 1] if i + 1 < len(args) else "")
        if key in ("-b", "--body", "--match-head-commit", "-R", "--repo"):
            out[{"-b": "body", "--body": "body", "--match-head-commit": "head", "-R": "repo", "--repo": "repo"}[key]] = value
            i += 1 if "=" in a else 2
            continue
        if a == "--auto":
            out["auto"] = True
        elif not a.startswith("-"):
            m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", a)
            out["number"], out["repo"] = (m.group(2), m.group(1)) if m else (a, out.get("repo"))
        i += 1
    return out


def check(data, tool, args, cwd, command):
    if re.search(r"enable_pr_auto_merge$", tool):
        block(SAY + "auto-merge can't be pinned to the commit that was reviewed. Merge with merge_pull_request, "
              "as the merging rule says.")
    if tool == "mcp__github__merge_pull_request":
        name = f"{args.get('owner', '')}/{args.get('repo', '')}"
        return check_merge(data, cwd, name, args.get("pullNumber"), args.get("commit_message"), args.get("expectedHeadSha"))
    if API_WRITES.search(tool):
        repo = checkout_of(f"{args.get('owner', '')}/{args.get('repo', '')}", cwd)
        default = default_branch(repo) if repo else "main"
        if args.get("branch") in (default, "main", "master") and enforced("ship", repo or cwd):
            block(SAY + f"never write to the default branch ({args.get('branch')}). Write to the session's branch.")
        return
    for m in PUSH.finditer(command):
        place = where(command, m.start(), cwd, m.group(1))
        repo = git("rev-parse", "--show-toplevel", cwd=place)
        if repo and enforced("ship", repo):
            check_push(words(command[m.end():]), repo)
    for m in GH_MERGE.finditer(command):
        place = where(command, m.start(), cwd)
        got = gh_merge(words(command[m.end():]))
        if got["auto"]:
            block(SAY + "auto-merge can't be pinned to the commit that was reviewed: merge without --auto.")
        if not str(got.get("number", "")).isdigit():
            block(SAY + "name the pull request's number, so the house rules can check the merge.")
        name = got.get("repo") or slug(git("rev-parse", "--show-toplevel", cwd=place) or place)
        check_merge(data, place, name, got["number"], got.get("body"), got.get("head"))
