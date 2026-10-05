"""The right_sized rule, delegate first: an assignment costs what its model costs, so it names that model on the call.

Charlotte, 5 October: "Always run the delegation before assigning anything to anyone." Every assignment names its
model on the call, whatever this session runs and whether or not she has capped the repo: an Agent (or Task) spawn
its `model`, every agent() call in a Workflow script the `model` in its own options, and a new Claude Code Remote
session (create_session) its `model`. One that names none, or names something off the ladder, is refused with the
rubric for choosing. A fork is the one exception: it is the parent by design, and its model can't be chosen.

Facts only. The hook judges the model the call names, the one fact it can see, and nothing else:

- It never guesses whether a task is easy from its words. That is the decide tool's `easy` preset, the rubric of
  docs/delegation.md. (Only a refusal's wording reads the prompt, to tell a held, private or browser task to stay on
  a strong tier; it decides nothing.)
- It never works out what an unnamed spawn would resolve to. Claude Code resolves that from two environment
  variables, the agent's own file and the session's model, and every reimplementation of it here drifted into a
  bypass one way or a false refusal the other. So a helper whose file pins Haiku (the scout, the tester) names haiku
  on the call like any other.

Her cap: `tiers.ceiling` in a repo's `.claude/catio-rules.json` caps its sub agents. A spawn or an agent() call that
names a model above it is refused, and so is every sub agent while CLAUDE_CODE_SUBAGENT_MODEL_FORCE, which overrides
the call, is above it. A cap written in a shape the rule can't use is said, once, rather than going quiet (misread()).

Nothing here switches the session's own model: the tier is chosen for the work being assigned, because switching the
conversation mid-way throws its prompt cache away and costs more than the routing saves.
"""
import difflib
import os
import re
from pathlib import Path

from common import enforced, local, rules, said, say

SPAWN = ("Task", "Agent")   # the sub agent tool: Agent in this build, Task in older ones
WORKFLOW = "Workflow"       # a script of agent() calls, each its own sub agent
NEW_SESSION = re.compile(r"^mcp__claude[-_]code[-_]remote__create_session$")   # a new cat; other servers' sessions aren't cats
CALL = re.compile(r"(?<![\w$.])agent\s*(\?\.\s*)?\(")          # agent( and agent?.(
NAME = re.compile(r"(?<![\w$.])agent(?![\w$])")                # agent itself, called or handed on
NESTED = re.compile(r"(?<![\w$.])workflow\s*\(")               # a child workflow, run inline
REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")                       # after these, a / starts a regex literal
REGEX_WORDS = {"return", "typeof", "case", "in", "of", "void", "yield", "await", "else", "do", "throw", "delete", "new"}
FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"   # Claude Code's override of the model on the call, for every sub agent
KEYS = ("ceiling", "ladder")                 # the settings a repo's tiers block may hold

# Read only for a refusal's wording: a task that names one of these is told to stay on a strong tier. Nothing is
# allowed or refused because of them.
PRIVATE = re.compile(r"\b(legal|lawyer|solicitor|contract|tax|salary|invoice|bank|mortgage|health|medical|"
                     r"doctor|diagnosis|prescription)\b", re.I)
BROWSER = re.compile(r"\b(browser|playwright|chrome|chromium|puppeteer|selenium|log ?in|sign ?in|screenshot)\b", re.I)


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
    """A ladder the rule can use: a list of tiers, which it can do nothing without."""
    return isinstance(t.get("ladder"), list) and bool(t["ladder"]) \
        and all(isinstance(x, str) and x for x in t["ladder"])


def misread(cwd, t):
    """Why what Charlotte wrote here can't be acted on, or None. A rule that can't read her settings says so
    rather than going quiet; a key it doesn't know (a comment of hers, say) is simply not one of its settings."""
    raw = local(cwd)
    near_block = [k for k in raw if k != "tiers" and difflib.get_close_matches(str(k), ("tiers",), 1, 0.85)]
    if near_block and "tiers" not in raw:
        return "its %s is not one of my settings (did she mean tiers?)" % ", ".join(sorted(map(str, near_block)))
    mine = raw.get("tiers")
    if "tiers" not in raw and "ceiling" not in raw:
        return None                      # she has said nothing here, so there is nothing of hers to report
    if not isinstance(mine, dict) and "tiers" in raw:
        return "its tiers is not an object"
    if not house_ok(t):
        return ("its ladder is not a list of tiers" if isinstance(mine, dict) and "ladder" in mine
                else "the house's own ladder is not a list of tiers")
    if "ceiling" in raw and "ceiling" not in (mine or {}):
        return "its ceiling sits outside the tiers block"
    if isinstance(mine, dict) and "ceiling" not in mine:
        if "errand" in mine:   # the errand ceiling of before: what she meant then is her cap now
            return "its errand is no longer one of my settings (her cap is tiers.ceiling now)"
        near = [k for k in mine if k not in KEYS and difflib.get_close_matches(str(k), KEYS, 1, 0.8)]
        if near:
            return "its %s is not one of my settings (did she mean %s?)" % (
                ", ".join(sorted(map(str, near))), difflib.get_close_matches(str(near[0]), KEYS, 1, 0.8)[0])
        if not set(mine) & set(KEYS):
            return "nothing in its tiers block is one of my settings"
    if isinstance(mine, dict) and "ceiling" in mine:
        ceiling = mine["ceiling"]
        if not isinstance(ceiling, str) or not ceiling.strip():
            return "its ceiling is not the name of a tier"
        if not tier_of(ceiling, t.get("ladder") or []):
            return "its ceiling %r is not one of %s" % (ceiling, ", ".join(map(str, t.get("ladder") or [])))
    return None


def up(cwd, *parts):
    """<folder>/.claude/<parts> for the folder and each one above it, nearest first, then the user's own."""
    here, seen = Path(cwd or ".").resolve(), []
    for folder in [here, *here.parents]:
        seen.append(folder.joinpath(".claude", *parts))
    seen.append(Path.home().joinpath(".claude", *parts))
    return seen


def held(cwd):
    """The paths whose change always waits for her: the merging rule's, plus this repo's own."""
    return list(rules().get("merging", {}).get("hold") or []) + list(local(cwd).get("hold") or [])


def never_down(prompt, cwd):
    """Why a refusal should tell this work to stay on a strong tier, or None. Wording only: nothing is decided here."""
    for path in held(cwd):
        if path.strip("/") and re.search(r"(^|[\s\"'`(/])" + re.escape(path.strip("/")) + r"[/\s\"'`)]", prompt):
            return "it names %s, whose changes always wait for her" % path
    if PRIVATE.search(prompt):
        return "it reads as one of her private matters"
    if BROWSER.search(prompt):
        return "it needs a browser, which the preflight rule governs"
    return None


def allowed(ladder, cap):
    """The tiers a call may name here: the whole ladder, or up to her cap."""
    return ladder[:ladder.index(cap) + 1] if cap else ladder


def lines_of(lines):
    return "line%s %s" % ("s" if len(lines) > 1 else "", ", ".join(map(str, lines)))


def delegate_first(what, ladder, why=None, cap=None):
    """The refusal for an assignment that names no model: what it is, and how to choose."""
    capped = (" Charlotte capped this repo's sub agents at %s." % cap) if cap else ""
    keep = ""
    if why:
        keep = (" This one needs the strongest tier her cap allows, %s: %s." % (cap, why) if cap
                else " This one stays on a strong tier: %s." % why)
    return ("House rule (KittyChat), delegate first: %s names no model, so it would run on whatever this session "
            "runs. Choose the tier for the work before assigning it (docs/delegation.md, \"cheap models for volume, "
            "premium where a mistake compounds\"): haiku to read, search, run and report; sonnet for spelled-out, "
            "checkable work in one place; opus or fable for everything else, and for anything under a held path, "
            "private, or needing a browser.%s%s Not sure? Ask the decider (decide, preset easy). Then name it on the "
            "call: %s." % (what, capped, keep, ", ".join(allowed(ladder, cap))))


def off_ladder(what, model, ladder, cap=None):
    """The refusal for an assignment that names a model this repo's ladder doesn't have."""
    capped = (" Charlotte capped this repo's sub agents at %s, so name one of %s."
              % (cap, ", ".join(allowed(ladder, cap))) if cap else "")
    return ("House rule (KittyChat), delegate first: %s names %s, which isn't one of the tiers here (%s), so what it "
            "would cost can't be told from here. Name one of them.%s" % (what, model, ", ".join(ladder), capped))


def over_cap(what, rung, ladder, cap):
    """The refusal for a model named above her cap."""
    return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents at %s, and "
            "%s names %s. Name model %s or below (%s) instead. If this really needs more, say so to her and she will "
            "raise the cap in .claude/catio-rules.json." % (cap, what, rung, cap, ", ".join(allowed(ladder, cap))))


def forced(ladder, cap):
    """The refusal when CLAUDE_CODE_SUBAGENT_MODEL_FORCE, which overrides the call, is above her cap (or isn't a tier
    at all, so its cost can't be told), or None. Naming a model on the call cannot help here, so it names the
    variable."""
    model = os.environ.get(FORCE, "").strip()
    if not cap or not model:
        return None
    rung = tier_of(model, ladder)
    if rung and ladder.index(rung) <= ladder.index(cap):
        return None
    return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents at %s, and "
            "%s is set to %s, which overrides the model on the call, so every sub agent runs on it whatever the call "
            "names. Unset %s, or ask her to raise the cap in .claude/catio-rules.json."
            % (cap, FORCE, rung or ("%r, which isn't one of the tiers here" % model), FORCE))


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


def literal(value):
    """The text of an option's raw value when it is a plain string literal (the whole value, with no ${} in it), or
    None for an expression."""
    v = (value or "").strip()
    lit = re.match(r"""(['"`])(.*?)\1""", v, re.S)
    if lit and not (lit.group(1) == "`" and "${" in lit.group(2)) and v[lit.end():].lstrip()[:1] in ("", ",", "}"):
        return lit.group(2)
    return None


def tier_named(value, ladder):
    """Does an option's raw value name a tier? A literal must be on the ladder; an expression is the author's choice,
    made on the call, except the ways of saying nothing (undefined, null, void)."""
    text = literal(value)
    if text is not None:
        return bool(tier_of(text, ladder))
    v = (value or "").strip()
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


def assignments(src, cwd=None, depth=0):
    """(line, model) for every sub agent a workflow script assigns: each agent() call with the raw text of the model
    its own options name, or None when they name none; agent handed on uncalled (items.map(agent)), which names none;
    and the calls of a child workflow() it runs, at that line."""
    code, found = mask(src), []
    line = lambda at: src.count("\n", 0, at) + 1
    calls = set()
    for m in CALL.finditer(code):
        calls.add(m.start())
        end = close(code, m.end() - 1)
        if re.search(r"function\s*$", code[:m.start()]) or re.match(r"\s*\{", code[end + 1:]):
            continue   # its own definition: function agent(...) or a method agent() { ... }
        found.append((line(m.start()), option(code[m.end():end], src[m.end():end], "model")))
    for m in NAME.finditer(code):
        if m.start() in calls or not handed_on(code, m.start(), m.end()):
            continue
        found.append((line(m.start()), None))   # handed on uncalled: no model to read
    if depth == 0:
        for m in NESTED.finditer(code):
            arg = src[m.end():close(code, m.end() - 1)].strip()
            first = re.match(r"""(['"`])([\w.-]+)\1\s*(,|$)""", arg)        # workflow('name', args?)
            path = re.search(r"""scriptPath\s*:\s*(['"`])(.+?)\1""", arg)   # workflow({scriptPath}, args?)
            named = re.search(r"""\bname\s*:\s*(['"`])([\w.-]+)\1""", arg)  # workflow({name}, args?)
            ref = {"name": first.group(2)} if first else {"scriptPath": path.group(2)} if path else \
                {"name": named.group(2)} if named else {}
            child = script_of(ref, cwd) if ref else ""
            found += [(line(m.start()), model) for _, model in assignments(child, cwd, depth + 1)] if child else []
    return found


def unnamed_agents(src, cwd=None, ladder=(), depth=0):
    """The line of every agent() in a workflow script that names no tier, or is handed on uncalled."""
    return sorted({at for at, model in assignments(src, cwd, depth) if not (model and tier_named(model, ladder))})


def against_cap(src, cwd, ladder, cap):
    """The lines whose agent() her cap can't let through: a tier spelt out above it, or a model built in code, whose
    cost can't be read from here. Under her cap the call spells its tier out."""
    out = []
    for at, model in assignments(src, cwd):
        rung = tier_of(literal(model), ladder) if model else None
        if model and (not rung or ladder.index(rung) > ladder.index(cap)):
            out.append(at)
    return sorted(set(out))


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


def assessed(kind, args, cwd, ladder, cap):
    """The refusal for this assignment, or None: it names its model on the call, on the ladder, and at or below her
    cap where she has set one."""
    prompt = " ".join(str(args.get(k) or "") for k in ("prompt", "description"))
    if kind == "session":   # a new cat, maybe in another repo: it names its model, and this repo's cap is not its own
        model = args.get("model")
        if model and not tier_of(model, ladder):
            return off_ladder("this new session", model, ladder)
        return None if model else delegate_first("this new session", ladder, never_down(prompt, cwd))

    if kind == "workflow":
        src = script_of(args, cwd)
        lines = unnamed_agents(src, cwd, ladder)
        if lines:
            return delegate_first("this workflow's agent() call on %s" % lines_of(lines), ladder, cap=cap)
        if not cap or not assignments(src, cwd):
            return None
        refusal = forced(ladder, cap)
        if refusal:
            return refusal
        lines = against_cap(src, cwd, ladder, cap)
        if lines:
            return ("House rule (KittyChat), spend what the task is worth: Charlotte capped this repo's sub agents at "
                    "%s, and this workflow's agent() %s on %s %s a model above it, or %s one in code, whose cost can't "
                    "be told from here. Spell it out on each call: model %s or below (%s). If this really needs more, "
                    "say so to her and she will raise the cap in .claude/catio-rules.json."
                    % (cap, "calls" if len(lines) > 1 else "call", lines_of(lines),
                       "name" if len(lines) > 1 else "names", "build" if len(lines) > 1 else "builds",
                       cap, ", ".join(allowed(ladder, cap))))
        return None

    named = args.get("model")
    if not named:   # it would inherit the session's model, whatever the work
        return delegate_first("this spawn", ladder, never_down(prompt, cwd), cap)
    rung = tier_of(named, ladder)
    if not rung:
        return off_ladder("this spawn", named, ladder, cap)
    if not cap:
        return None
    refusal = forced(ladder, cap)
    if refusal:
        return refusal
    return over_cap("this spawn", rung, ladder, cap) if ladder.index(rung) > ladder.index(cap) else None


def check(data, tool, args, cwd):
    """(refusal, nudge): what to refuse this assignment with, and what to say about it. Either may be None."""
    kind = "spawn" if tool in SPAWN else "workflow" if tool == WORKFLOW else \
        "session" if NEW_SESSION.search(tool) else None
    if not kind or not enforced("right_sized", cwd):
        return None, None
    if kind == "spawn" and str(args.get("subagent_type") or "") == "fork":
        return None, None   # a fork is the parent by design: its model can't be chosen

    sid, t, house = data.get("session_id"), tiers(cwd), dict(rules().get("tiers") or {})
    wrong = misread(cwd, t)
    note = None
    if house_ok(t):
        ladder = t["ladder"]
    elif house_ok(house):
        ladder = house["ladder"]   # her ladder can't be used: the house's still says what a tier is
    else:
        wrong, ladder = None, None
        note = ("House rule (KittyChat), delegate first: the house's own ladder in rules.json is not a list of tiers, "
                "so this rule is doing nothing. Tell Charlotte, and name the model the work needs on the call "
                "meanwhile.")
    if wrong:
        note = ("House rule (KittyChat), spend what the task is worth: this repo caps its sub agents, but %s, so the "
                "cap is doing nothing. Tell Charlotte, and spawn at the tier the work needs meanwhile." % wrong)

    refusal = assessed(kind, args, cwd, ladder, None if wrong else tier_of(t.get("ceiling"), ladder)) \
        if ladder else None
    if refusal:
        return refusal, None
    if note and not said(sid, "badcap", "tier", cwd):
        say(sid, "badcap", "tier", cwd)
        return None, note
    return None, None
