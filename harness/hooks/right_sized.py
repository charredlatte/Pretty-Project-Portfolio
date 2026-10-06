"""The right_sized rule: a sub agent costs what its model costs, so a spawn says which tier it needs.

Delegate first (Charlotte, 5 October: "Always run the delegation before assigning anything to anyone"). Nothing is
assigned without its tier chosen for the work: an Agent spawn, every agent() call in a Workflow script, and a new
session (create_session) each name a model, or the harness refuses them and says how to choose. A fork is the one
exception: it is the parent by design, and its model can't be chosen.

Then two halves, which is what makes the ceiling semi-automatic:

- **The owner deems.** When Charlotte has set a ceiling for this repo (`tiers` in its
  `.claude/catio-rules.json`), that is her decision, made in an earlier session and kept where the repo's
  other decisions live. A spawn above it, for a task that reads as an errand, is refused.
- **The harness deems.** With no word from her, the same reading only earns a line: the tier it would have
  picked and why. A guess never blocks; it suggests, and what she does next is the decision to keep.

Either way the tier is chosen for the work being spawned, never for the conversation: switching the session's
own model mid-way throws its prompt cache away and costs more than the routing saves (docs/delegation.md).

Nothing under a held path, nothing private and nothing needing a browser is ever sent down a tier.
"""
import os
import re
from pathlib import Path

from common import ROOT, enforced, local, rules, said, say

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
WORKFLOW = "Workflow"       # a script of agent() calls, each its own sub agent
NEW_SESSION = re.compile(r"^mcp__claude[-_]code[-_]remote__create_session$")   # a new cat; other servers' sessions aren't cats
CALL = re.compile(r"(?<![\w$.])agent\s*(\?\.\s*)?\(")          # agent( and agent?.(
NAME = re.compile(r"(?<![\w$.])agent(?![\w$])")                # agent itself, called or handed on
NESTED = re.compile(r"(?<![\w$.])workflow\s*\(")               # a child workflow, run inline
REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")                       # after these, a / starts a regex literal
REGEX_WORDS = {"return", "typeof", "case", "in", "of", "void", "yield", "await", "else", "do", "throw", "delete", "new"}

# A task worth a strong model says so in its own words: it asks for judgement, or reaches across a repo.
WORK = re.compile(r"\b(design|architect|refactor|rewrite|migrat|review|audit|investigat|debug|diagnos|"
                  r"plan\b|decide|choose between|trade-?off|across the (repo|codebase)|every file|"
                  r"root cause|why does|security|performance)", re.I)
# Everyday errands: her own example is "add bananas to my shopping list".
CHORE = re.compile(r"\b(add|append|rename|list|count|fetch|copy|tidy|sort|format|summar(y|ise|ize)|"
                   r"look up|find|check|run|note|remind|shopping|groceries|errand)\b", re.I)
PRIVATE = re.compile(r"\b(legal|lawyer|solicitor|contract|tax|salary|invoice|bank|mortgage|health|medical|"
                     r"doctor|diagnosis|prescription)\b", re.I)
BROWSER = re.compile(r"\b(browser|playwright|chrome|chromium|puppeteer|selenium|log ?in|sign ?in|screenshot)\b", re.I)
FRONT_MODEL = re.compile(r"^model:\s*([^\s#]+)\s*$", re.M)


def tiers(cwd):
    """The ladder and the errand ceiling here: the house's, with the repo's own word laid over it."""
    house = dict(rules().get("tiers") or {})
    mine = local(cwd).get("tiers")   # hers, whatever shape she wrote it in: a bad one must not stop the gate
    if isinstance(mine, dict):
        ok = {k: v for k, v in mine.items() if k in ("errand", "ladder")}
        if "errand" in ok and not (isinstance(ok["errand"], str) and ok["errand"].strip()):
            ok.pop("errand")         # an errand of hers the rule can't read leaves the house's standing
        rungs = ok.get("ladder")
        if not (isinstance(rungs, list) and any(isinstance(t, str) and t.strip() for t in rungs)):
            ok.pop("ladder", None)   # a ladder of hers with no rung the rule can read leaves the house's standing
        house.update(ok)
    ladder = house.get("ladder")
    house["ladder"] = [str(t).lower() for t in ladder if isinstance(t, str) and t.strip()] \
        if isinstance(ladder, list) else []
    return house


def hers(cwd):
    """Has Charlotte set this repo's ceiling herself? Then it is a decision, not a reading. Only a block the
    rule can read counts: a refusal in her name for a decision she never made is worse than no refusal."""
    mine = local(cwd).get("tiers")
    return isinstance(mine, dict) and isinstance(mine.get("errand"), str)


def tier_of(model, ladder):
    """The rung a model id sits on, or None: any part of the id matches, as the merging rule matches strong."""
    m = str(model or "").lower()
    return next((t for t in ladder if t in m), None)


def up(cwd, *parts):
    """<folder>/.claude/<parts> for the folder and each one above it, nearest first, then the user's own."""
    here, seen = Path(cwd or ".").resolve(), []
    for folder in [here, *here.parents]:
        seen.append(folder.joinpath(".claude", *parts))
    seen.append(Path.home().joinpath(".claude", *parts))
    return seen


def front(path):
    """An agent definition's frontmatter, as text (empty when it has none or can't be read)."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except (OSError, ValueError):   # unreadable, or not UTF-8: a crash here would let every spawn through
        return ""
    return head.split("---")[1] if head.startswith("---") and "---" in head[3:] else ""


def pinned(agent_type, cwd):
    """The model an agent definition pins, or None. Claude Code knows an agent by its frontmatter name, from the
    repo's .claude/agents (and those above it), the user's ~/.claude/agents, and every plugin's agents/."""
    name = str(agent_type or "").split(":")[-1].strip()
    if not name or not re.fullmatch(r"[\w.-]+", name):
        return None
    cache = Path.home() / ".claude" / "plugins" / "cache"   # <marketplace>/<plugin>/<version>/agents
    folders = up(cwd, "agents") + [ROOT / "agents"] + (sorted(cache.glob("*/*/*/agents")) if cache.is_dir() else [])
    for folder in folders:
        candidates = [folder / (name + ".md")]
        if folder.is_dir():
            candidates += sorted(folder.glob("*.md"))
        for path in candidates:
            head = front(path)
            if not head:
                continue   # no such file, or no frontmatter: not a definition
            named = re.search(r"^name:\s*['\"]?([\w.:-]+)", head, re.M)
            if path.stem != name and not (named and named.group(1).split(":")[-1] == name):
                continue
            found = FRONT_MODEL.search(head)   # the first definition by that name is the one Claude Code runs
            return found.group(1).strip("'\"") if found else None
    return None


def held(cwd):
    """The paths whose change always waits for her: the merging rule's, plus this repo's own. A hold written
    as a string would otherwise be read letter by letter, and every letter taken for a held path."""
    def paths(v):
        return [p for p in v if isinstance(p, str) and p.strip()] if isinstance(v, list) else []
    return paths(rules().get("merging", {}).get("hold")) + paths(local(cwd).get("hold"))


def never_down(prompt, cwd):
    """Why this work must keep whatever model it was given, or None."""
    for path in held(cwd):
        if path.strip("/") and re.search(r"(^|[\s\"'`(/])" + re.escape(path.strip("/")) + r"[/\s\"'`)]", prompt):
            return "it names %s, whose changes always wait for her" % path
    if PRIVATE.search(prompt):
        return "it reads as one of her private matters"
    if BROWSER.search(prompt):
        return "it needs a browser, which the preflight rule governs"
    return None


def errand(prompt):
    """Does this read as an errand: short, an everyday verb, and nothing asking for judgement?"""
    text = prompt.strip()
    return bool(text) and len(text) <= 240 and not WORK.search(text) and bool(CHORE.search(text))


def once(session, kind, cwd=None):
    """True the first time this session is told something of this kind, here. common.said/say keep the mark:
    in a folder of this user's own, and keyed per repo, since a cloud session works in several at once."""
    if said(session, kind, "tier", cwd):
        return False
    say(session, kind, "tier", cwd)
    return True


def delegate_first(what, ladder, why=None):
    """The refusal for an assignment that names no model: what it is, and how to choose."""
    keep = (" This one stays on a strong tier: %s." % why) if why else ""
    return ("House rule (KittyChat), delegate first: %s names no model, so it would run on whatever this session "
            "runs. Choose the tier for the work before assigning it (docs/delegation.md, \"cheap models for volume, "
            "premium where a mistake compounds\"): haiku to read, search, run and report; sonnet for spelled-out, "
            "checkable work in one place; opus or fable for everything else, and for anything under a held path, "
            "private, or needing a browser.%s Not sure? Ask the decider (decide, preset easy). Then name it on the "
            "call: %s." % (what, keep, ", ".join(ladder)))


def off_ladder(what, model, ladder):
    """The refusal for an assignment that names a model this repo's ladder doesn't have."""
    return ("House rule (KittyChat), delegate first: %s names %s, which isn't one of the tiers here (%s). Name one of "
            "them." % (what, model, ", ".join(ladder)))


def mask(src):
    """The script with what isn't code blanked (newlines kept): string and regex literals, comments, and a template
    literal's text, though not the code in its ${...}. Only code is read for agent() calls and their options."""
    out, n = list(src), len(src)

    def blank(i, j):
        for k in range(i, min(j, n)):
            if out[k] != "\n":
                out[k] = " "

    def starts_regex(i):
        k = i - 1
        while k >= 0 and out[k] in " \t\r\n":
            k -= 1
        if k > 0 and out[k] in "+-" and out[k - 1] == out[k]:
            return False   # after a postfix ++ or --, a / divides
        if k < 0 or out[k] in REGEX_AFTER:
            return True
        word = re.search(r"[\w$]+$", "".join(out[max(0, k - 12):k + 1]))
        if not word or word.group(0) not in REGEX_WORDS:
            return False
        start = k + 1 - len(word.group(0))
        return not (start > 0 and out[start - 1] == ".")   # obj.in / 2 divides; return /x/ is a regex

    def regex_end(i):
        j, cls = i + 1, False
        while j < n and src[j] != "\n":
            if src[j] == "\\":
                j += 2
                continue
            if cls:
                cls = src[j] != "]"
            elif src[j] == "[":
                cls = True
            elif src[j] == "/":
                return j
            j += 1
        return j

    def code(i, in_braces):
        depth = 0
        while i < n:
            c = src[i]
            if c in "\"'":
                j = i + 1
                while j < n and src[j] not in (c, "\n"):
                    j += 2 if src[j] == "\\" else 1
                blank(i + 1, j)
                i = j + 1
            elif c == "`":
                i = template(i + 1) + 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                i = j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank(i, j)
                i = j
            elif c == "/" and starts_regex(i):
                j = regex_end(i)
                blank(i + 1, j)
                i = j + 1
            else:
                if in_braces and c == "{":
                    depth += 1
                elif in_braces and c == "}":
                    if not depth:
                        return i
                    depth -= 1
                i += 1
        return n

    def template(i):
        start = i
        while i < n:
            if src[i] == "\\":
                i += 2
            elif src[i] == "`":
                blank(start, i)
                return i
            elif src.startswith("${", i):
                blank(start, i)
                i = code(i + 2, True) + 1
                start = i
            else:
                i += 1
        blank(start, n)
        return n

    code(0, False)
    return "".join(out)


def close(code, i):
    """The index of the ) matching the ( at i in masked code (or the end)."""
    depth = 0
    for j in range(i, len(code)):
        depth += {"(": 1, ")": -1}.get(code[j], 0)
        if not depth:
            return j
    return len(code)


def option(code, src, key):
    """The raw value text of `key` in an options object passed straight to this call (not a nested one), or None.
    Shorthand ({ model }) gives the key itself."""
    for m in re.finditer(r"""(?<![\w$.])(['"]?)%s\1(?![\w$])""" % key, src):
        quote = m.group(1)
        if quote and not (code[m.start()] == quote and code[m.end() - 1] == quote and not code[m.start() + 1:m.end() - 1].strip()):
            continue   # a quoted key must be a whole string of its own
        if not quote and code[m.start():m.end()] != key:
            continue   # an unquoted one must be code, not text in a string or comment
        before = code[:m.start()]
        parens = before.count("(") - before.count(")") + before.count("[") - before.count("]")
        braces = before.count("{") - before.count("}")
        if parens or braces != 1 or before.rstrip()[-1:] not in ("{", ","):
            continue   # not a key of an options object given to this call itself
        rest = code[m.end():].lstrip()
        if rest[:1] in (",", "}") and not quote:
            return key
        if rest[:1] == ":":
            at = m.end() + (len(code[m.end():]) - len(rest)) + 1
            return src[at:].lstrip()
    return None


def tier_named(value, ladder):
    """Does an option's raw value name a tier? A literal (the whole value, with no ${} in it) must be on the ladder; an
    expression is the author's choice, made on the call, except the ways of saying nothing (undefined, null, void)."""
    v = (value or "").strip()
    lit = re.match(r"""(['"`])(.*?)\1""", v, re.S)
    if lit and not (lit.group(1) == "`" and "${" in lit.group(2)) and v[lit.end():].lstrip()[:1] in ("", ",", "}"):
        return bool(tier_of(lit.group(2), ladder))
    return bool(v) and not re.match(r"(undefined|null)(?![\w$])|void\b", v)


def handed_on(code, start, end):
    """Is this mention of agent (not a call) the real one handed on, rather than a name of the script's own?"""
    before, after = code[:start], code[end:]
    if re.match(r"\s*:(?!:)", after) or re.search(r"(function|const|let|var|typeof)\s+$", before):
        return False   # an object key, a declaration, or typeof
    if re.match(r"\s*\??\.(?!\s*(call|apply|bind)\b)", after):
        return False   # a property read (agent.summary): the real agent spawns nothing that way
    if re.match(r"\s*(=>|of\b|in\b)", after) or re.search(r"(const|let|var)\s*[{\[][^;=]*$", before):
        return False   # an arrow's parameter, a for-of variable, or destructuring
    if re.search(r"[(,]\s*$", before):   # in a list: a parameter if the list is a function's
        depth, j = 0, end
        while j < len(code):
            if code[j] in "([{":
                depth += 1
            elif code[j] in ")]}":
                if not depth:
                    break
                depth -= 1
            j += 1
        if code[j:j + 1] == ")" and re.match(r"\s*(=>|\{)", code[j + 1:]):
            return False
    return True


def unnamed_agents(src, cwd=None, ladder=(), depth=0):
    """The line of every agent() in a workflow script that names no tier, or is handed on uncalled."""
    code, lines = mask(src), []
    line = lambda at: src.count("\n", 0, at) + 1
    calls = set()
    for m in CALL.finditer(code):
        calls.add(m.start())
        end = close(code, m.end() - 1)
        if re.search(r"function\s*$", code[:m.start()]) or re.match(r"\s*\{", code[end + 1:]):
            continue   # its own definition: function agent(...) or a method agent() { ... }
        args_code, args_src = code[m.end():end], src[m.end():end]
        model = option(args_code, args_src, "model")
        kind = option(args_code, args_src, "agentType")
        kind = re.match(r"""(['"`])([\w.:-]+)\1""", kind or "")
        if (model and tier_named(model, ladder)) or (not model and kind and tier_of(pinned(kind.group(2), cwd), ladder)):
            continue
        lines.append(line(m.start()))
    for m in NAME.finditer(code):
        if m.start() in calls or not handed_on(code, m.start(), m.end()):
            continue
        lines.append(line(m.start()))   # handed on uncalled (items.map(agent), const run = agent): no tier to read
    if depth == 0:
        for m in NESTED.finditer(code):
            arg = src[m.end():close(code, m.end() - 1)].strip()
            first = re.match(r"""(['"`])([\w.-]+)\1\s*(,|$)""", arg)        # workflow('name', args?)
            path = re.search(r"""scriptPath\s*:\s*(['"`])(.+?)\1""", arg)   # workflow({scriptPath}, args?)
            named = re.search(r"""\bname\s*:\s*(['"`])([\w.-]+)\1""", arg)  # workflow({name}, args?)
            ref = {"name": first.group(2)} if first else {"scriptPath": path.group(2)} if path else \
                {"name": named.group(2)} if named else {}
            child = script_of(ref, cwd) if ref else ""
            if child and unnamed_agents(child, cwd, ladder, depth + 1):
                lines.append(line(m.start()))   # a child workflow with an unnamed agent() of its own
    return sorted(set(lines))


def script_of(args, cwd):
    """A Workflow call's script: inline, from its scriptPath, or a saved one in .claude/workflows (the repo's, those
    above it, or the user's own)."""
    if args.get("script"):
        return str(args["script"])
    paths = [Path(cwd or ".", os.path.expanduser(str(args["scriptPath"])))] if args.get("scriptPath") else []
    if args.get("name") and re.fullmatch(r"[\w.-]+", str(args["name"])):
        paths += [folder / (str(args["name"]) + ".js") for folder in up(cwd, "workflows")]
    for path in paths:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
    return ""   # a built-in workflow, or one this hook can't read: nothing to check


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this assignment with, and what to say about it. Either may be None."""
    workflow, session = tool == WORKFLOW, bool(NEW_SESSION.search(tool))
    if not (tool in SPAWN or workflow or session) or not enforced("right_sized", cwd):
        return None, None
    t = tiers(cwd)
    ladder = list(t.get("ladder") or [])
    ceiling = tier_of(t.get("errand"), ladder)
    if not ladder:
        return None, None

    if workflow:
        lines = unnamed_agents(script_of(args, cwd), cwd, ladder)
        if lines:
            return delegate_first("this workflow's agent() call on line%s %s" % ("s" if len(lines) > 1 else "",
                                  ", ".join(map(str, lines))), ladder), None
        return None, None
    if session:
        if args.get("model") and not tier_of(args.get("model"), ladder):
            return off_ladder("this new session", args.get("model"), ladder), None
        if not tier_of(args.get("model"), ladder):
            return delegate_first("this new session", ladder, never_down(str(args.get("prompt") or ""), cwd)), None
        return None, None
    if str(args.get("subagent_type") or "") == "fork":
        return None, None   # a fork is the parent by design: its model can't be chosen

    prompt = " ".join(str(args.get(k) or "") for k in ("prompt", "description"))
    keep = never_down(prompt, cwd)
    # Claude Code reads the call's model ahead of the agent's file, so a name it cannot place is not covered
    # by the agent's pin: it would still run on whatever that name resolves to.
    if args.get("model"):
        spawn = tier_of(args["model"], ladder)
        if spawn is None:
            return off_ladder("this spawn", args["model"], ladder), None
    else:
        spawn = tier_of(pinned(args.get("subagent_type"), cwd), ladder)
    if spawn is None:   # nothing names a tier: it would inherit the session's model, whatever the work
        return delegate_first("this spawn", ladder, keep), None
    if keep or not ceiling:
        return None, None

    if not errand(prompt) or ladder.index(spawn) <= ladder.index(ceiling):
        return None, None
    if hers(cwd):
        return ("House rule (KittyChat), spend what the task is worth: Charlotte set this repo's ceiling for an "
                "errand at %s, and this reads as one. Spawn it on %s or below. If it is really not an errand, say "
                "so to her and she will raise the ceiling in .claude/catio-rules.json."
                % (ceiling, ceiling)), None
    if once(data.get("session_id"), "errand", cwd):
        return None, ("House rule (KittyChat), spend what the task is worth: this reads as an errand (spelled out, "
                      "checkable, small) and it is spawned on %s. %s or below does it. Carry on if it is more than "
                      "it looks; if she tells you the ceiling for this repo, write it into .claude/catio-rules.json "
                      "as {\"tiers\": {\"errand\": \"<tier>\"}} so the next session starts from her decision."
                      % (spawn, ceiling.capitalize()))
    return None, None
