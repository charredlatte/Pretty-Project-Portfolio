"""PreToolUse gate for the shipping and merging house rules (gates.py calls it).

ship    no push to the default branch, no force-push, and no deleting a branch that isn't merged yet. A merged
        branch goes freely in a repo that merges its own pull requests; anywhere else, only with her OK (a
        permission prompt).
merge   semi-automatic merging. A pull request merges only in a repo that opts in ({"merge": true} in its
        .claude/catio-rules.json), and only when every model that worked in the session is on rules.json's strong
        list, the audits ran and the review ran after the last commit, the merge is pinned to the commit that was
        reviewed (expectedHeadSha = HEAD, nothing uncommitted), nothing on the hold list changed, and the commit
        message ends with "Checks: <what passed>" and "Guesses: none". What the session can fix, it is told to fix.
        Guesswork (a guess it names, a model not on the list, a held path) is held for Charlotte: the pull request
        stays open, and a note for her review goes in the litter box.
"""
import os
import re
import shlex
from datetime import date
from pathlib import Path

from common import ask, block, checkouts, default_branch, enforced, git, git_ok, holds, local, merges, models, \
    rules, skill_calls

REMOTE = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
# Where a command starts (after ; & | ( { ! or a quote, or a word like if, then, env, timeout 30), with any VAR=x
# before it. The ordinary ways of running git; a hook is a guard rail, not a sandbox.
START = (r"(?:^|[;&|({!\"'`]|\b(?:if|then|else|do|while|until|env|exec|command|time|nohup|sudo|timeout\s+\S+)\s)"
         r"\s*(?:\w+=\S*\s+)*")
PUSH = re.compile(START + r"git\s+(?:(?:-C\s+(\S+)|-c\s+\S+|--[\w-]+(?:=\S+)?)\s+)*push\b", re.M)
PLAIN = re.compile(r"[\w./~@:-]+")  # a path, remote or branch with nothing the shell would run or expand
GH_MERGE = re.compile(START + r"gh\s+pr\s+merge\b", re.M)
MERGE = re.compile(r"__merge_pull_request$")
API_WRITES = re.compile(r"__(push_files|create_or_update_file|delete_file)$")
SAY = "House rule (KittyChat): "


def tokens(text, punct):
    """The words the shell would see in `text`, with the characters in `punct` as tokens of their own. No comments:
    shlex's own commenter cut `done#x` to `done` and ran the next line into this one, so a # stays in its word,
    which fails closed (a branch named "#" isn't merged). An unclosed quote raises ValueError."""
    lex = shlex.shlex(text, posix=True, punctuation_chars=punct)
    lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
    return lex


def words(text):
    """The arguments the shell would give the command that starts at `text`, up to the next ; & | ( ) or line end."""
    out = []
    try:
        for w in tokens(text, ";&|()\n"):
            if w and set(w) <= set(";&|()\n") or re.search(r"[<>]", w):  # the next command, or a redirect
                break
            out.append(w)
    except ValueError:  # an unclosed quote further on: keep what came before it
        pass
    return out


def lone_deletion(command):
    """Is the command nothing but cds and one plain `git [-C dir] push <remote> --delete <branches>` (or
    `push <remote> :<branch>...`)? Her OK on the prompt approves the whole command, so that is all it may hold: no
    other command or push, pipe, redirect, comment, git -c or push option, and no `cd -`, each of which can run,
    push or overwrite something the prompt doesn't name, or leave the gate checking a different repo."""
    if "#" in command:
        return False
    parts = [[]]
    try:
        for w in tokens(command, ";&|()<>\n"):
            if w in ("&&", ";", "\n"):
                parts.append([])
            elif set(w) & set(";&|()<>\n"):
                return False
            else:
                parts[-1].append(w)
    except ValueError:  # an unclosed quote
        return False
    parts = [p for p in parts if p]
    if sum(p[0] == "git" for p in parts) != 1:
        return False
    plain = lambda a: PLAIN.fullmatch(a) and not a.startswith("-")
    for p in parts:
        if p[0] == "cd":
            ok = len(p) == 2 and plain(p[1])
        else:
            rest = p[3:] if p[1:2] == ["-C"] and len(p) > 2 and plain(p[2]) else p[1:]
            flags = [a for a in rest[1:] if a in ("-d", "--delete")]
            refs = [a for a in rest[1:] if a not in flags]
            ok = p[0] == "git" and rest[:1] == ["push"] and len(refs) > 1 and all(plain(a) for a in refs) \
                and (flags or all(a.startswith(":") for a in refs[1:]))
        if not ok:
            return False
    return True


def where(command, at, cwd, given=None):
    """The folder a command at position `at` runs in: every cd before it, in turn, then its -C. cwd when that
    folder isn't there (a variable the hook can't see, say)."""
    place = Path(cwd)
    for step in re.findall(r"\bcd\s+([^\s;&|)]+)", command[:at]) + ([given] if given else []):
        place = place / Path(os.path.expandvars(step.strip("'\""))).expanduser()
    return str(place) if place.is_dir() else cwd


def slug(repo):
    m = REMOTE.search(git("remote", "get-url", "origin", cwd=repo) or "")
    return m.group(1) if m else ""


def checkout_of(name, cwd):
    """The checkout of owner/repo `name` here: cwd's repo, one beside it, or one under cwd."""
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", name or ""):
        return None
    return next((r for r in checkouts(cwd) if slug(r).lower() == name.lower()), None)


# --- pushes ---------------------------------------------------------------------------------------------------

def check_push(args, repo, alone=False):
    flags = [a for a in args if a.startswith("-")]
    pos = [a for a in args if not a.startswith("-")]
    if any(f in ("--mirror", "--all") for f in flags):
        block(SAY + "push one branch at a time, by name (no --all or --mirror).")
    if any(f.startswith("--force") or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", f) for f in flags) \
            or any(p.startswith("+") for p in pos[1:]):
        block(SAY + "no force-push. Merge the default branch into this one instead, and push that.")
    remote, specs = (pos[0] if pos else "origin"), pos[1:]
    if any("*" in s for s in specs):
        block(SAY + "push one branch at a time, by name (no patterns).")
    deleting = "--delete" in flags or any(re.fullmatch(r"-[a-zA-Z]*d[a-zA-Z]*", f) for f in flags)
    branch = git("branch", "--show-current", cwd=repo) or ""
    if not specs and not deleting and "--tags" not in flags:
        specs = [branch]
    default = default_branch(repo)
    gone = []
    for spec in specs:
        src, _, dst = spec.lstrip(":").partition(":")
        name = re.sub(r"^refs/heads/", "", dst or (branch if src == "HEAD" else src))
        if name == default:
            block(SAY + f"never push to the default branch ({default}). Push this work to the session's branch "
                  "and open a pull request; merging is the merging rule's.")
        if (deleting or spec.startswith(":")) and name not in gone:
            gone.append(name)
    if not gone:
        return []
    ask_her = not merges(repo)
    if ask_her and not alone:  # before any fetch: the refusal costs nothing, and the fetches add up
        block(SAY + "her OK covers the whole command, so a branch deletion goes on its own: one plain "
              "`git push <remote> --delete <branches>` (a cd before it is fine), nothing else in the command.")
    check_delete(repo, remote, gone, default)
    return [f"{name} ({Path(repo).name})" for name in gone] if ask_her else []


def check_delete(repo, remote, names, default):
    # one fetch for them all, bounded: a hook that times out lets the call through, so a stalled fetch counts
    # as nothing merged
    if not git_ok("fetch", "-q", remote, default, *names, cwd=repo, timeout=20):
        block(SAY + f"couldn't fetch {', '.join(names)} to check against {default} (a branch may be gone already, or "
              "the fetch failed or timed out), so they stay. Only a merged branch is deleted.")
    for name in names:
        if git("merge-base", "--is-ancestor", f"refs/remotes/{remote}/{name}", f"refs/remotes/{remote}/{default}",
               cwd=repo) is None:
            block(SAY + f"{name} isn't merged into {default}, so it stays. Only a merged branch is deleted.")


# --- merges ---------------------------------------------------------------------------------------------------

def check_merge(data, cwd, name, number, message, head, method=None):
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

    calls = list(skill_calls(data))
    for skill in cfg.get("audits", []):
        if not any(skill in s for s, _ in calls):
            fix.append(f"run the {skill} skill")
    review, sha = cfg.get("review", "code-review"), git("rev-parse", "HEAD", cwd=repo)
    made = int(git("log", "-1", "--format=%ct", cwd=repo) or 0)
    if not any(review in s and when >= made for s, when in calls):
        fix.append(f"run the {review} skill on {pr} (it hasn't run since the last commit)")
    if not head:
        fix.append(f"pass expectedHeadSha: {sha}, the commit that was reviewed")
    elif head != sha:
        fix.append(f"expectedHeadSha is {head}, but this checkout is at {sha}: check out and review what's on {pr}")
    if method not in (None, "", "merge"):
        fix.append(f"merge with merge_method \"merge\", not {method}: the reviewed commit itself goes into "
                   "the default branch, and the branch can be deleted after")
    status = git("status", "--porcelain", "--untracked-files=no", cwd=repo) or ""
    if any("graphify-out/" not in l for l in status.splitlines()):
        fix.append("commit or drop the uncommitted changes")

    base = git("merge-base", f"refs/remotes/origin/{default_branch(repo)}", "HEAD", cwd=repo)
    # -z and quotepath off: git C-quotes a path with an accent in it ("catio/art/caf\303\251/x.png"), which
    # would never equal or sit under a held path she spelt properly, so the change would merge unheld
    names = git("-c", "core.quotepath=false", "diff", "--name-only", "--no-renames", "-z", base, "HEAD",
                cwd=repo) if base else None
    changed = [n for n in (names or "").split("\0") if n] if names is not None else None
    mine_cfg = local(repo)                               # read once: the message must quote what was parsed
    house, house_odd = holds(cfg)
    mine, mine_odd = holds(mine_cfg)
    held_paths = [p.rstrip("/") for p in house + mine]   # compared against git's paths, which carry no slash
    # a hold it can't read holds the pull request: dropping it is how a change under harness/ merges itself.
    # Name the file each broken list is in, and both when both are, or she edits the wrong one.
    for odd, in_file, raw in ((mine_odd, "its .claude/catio-rules.json", mine_cfg.get("hold")),
                              (house_odd, "the house rules' own merging.hold", cfg.get("hold"))):
        if odd:   # in_file, not where: where() is this module's own function, and a for-target would shadow it
            held.append("the hold list in %s is in a shape I can't read (%r), so I can't tell what it protects"
                        % (in_file, raw))
    if changed is None:
        held.append("there's no way to tell what it changes")
    else:
        touched = sorted({h for p in changed for h in held_paths if p == h or p.startswith(h + "/")})
        if touched:
            held.append(f"it changes {', '.join(touched)}, which always waits for her")

    card = message or ""
    guess = re.search(r"^Guesses:", card, re.M)
    if not (re.search(r"^Checks:\s*\S", card, re.M) and guess):
        fix.append("end the merge's commit message with \"Checks: <what ran and passed>\" and \"Guesses: none\" "
                   "(or each thing you assumed rather than checked)")
    else:
        lines = card[guess.end():].split("\n")  # its paragraph: up to a blank line, or another "Key:" line
        lines = lines[:1] + next((lines[1:i] for i in range(1, len(lines))
                                  if not lines[i].strip() or re.match(r"[A-Za-z][\w-]*:\s", lines[i])), lines[1:])
        guesses = " ".join(" ".join(lines).split())
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
        elif a in ("--squash", "-s", "--rebase", "-r"):
            out["method"] = "squash" if a in ("--squash", "-s") else "rebase"
        elif not a.startswith("-"):
            m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", a)
            out["number"], out["repo"] = (m.group(2), m.group(1)) if m else (a, out.get("repo"))
        i += 1
    return out


def check(data, tool, args, cwd, command):
    if re.search(r"enable_pr_auto_merge$", tool):
        block(SAY + "auto-merge can't be pinned to the commit that was reviewed. Merge with merge_pull_request, "
              "as the merging rule says.")
    if MERGE.search(tool):
        name = f"{args.get('owner', '')}/{args.get('repo', '')}"
        return check_merge(data, cwd, name, args.get("pullNumber"), args.get("commit_message"),
                           args.get("expectedHeadSha"), args.get("merge_method"))
    if API_WRITES.search(tool):
        repo = checkout_of(f"{args.get('owner', '')}/{args.get('repo', '')}", cwd)
        default = default_branch(repo) if repo else "main"
        if args.get("branch") in (default, "main", "master") and enforced("ship", repo or cwd):
            block(SAY + f"never write to the default branch ({args.get('branch')}). Write to the session's branch.")
        return
    hers, alone = [], lone_deletion(command)
    for m in PUSH.finditer(command):
        place = where(command, m.start(), cwd, m.group(1))
        repo = git("rev-parse", "--show-toplevel", cwd=place)
        if repo and enforced("ship", repo):
            hers += check_push(words(command[m.end():]), repo, alone)
    for m in GH_MERGE.finditer(command):
        place = where(command, m.start(), cwd)
        got = gh_merge(words(command[m.end():]))
        if got["auto"]:
            block(SAY + "auto-merge can't be pinned to the commit that was reviewed: merge without --auto.")
        if not str(got.get("number", "")).isdigit():
            block(SAY + "name the pull request's number, so the house rules can check the merge.")
        name = got.get("repo") or slug(git("rev-parse", "--show-toplevel", cwd=place) or place)
        check_merge(data, place, name, got["number"], got.get("body"), got.get("head"), got.get("method"))
    if hers:  # asked last, so her OK never carries anything the checks above would refuse
        ask(SAY + f"delete {', '.join(hers)}? Merged, but where Charlotte merges by hand a branch is deleted only "
            "with her OK.")
