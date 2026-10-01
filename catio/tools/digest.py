#!/usr/bin/env python3
"""Compile the KittyChat Café's sessions and adopted chats into one short digest, sorted by what needs her.

    python3 catio/tools/digest.py [cats/*.json sessions/*.json]   ->  catio/data/digest.md  and  catio/data/digest.json

Reads catio/data/sessions.json (save-sessions.py's copy) and, optionally, adopted chats exported from the
artifact's `cats` collection and her moves from `sessions` (one JSON file per document, as ArtifactData saves
them); a session she moved to a room isn't flagged as misfiled. Per project it sorts every
cat into: needs you (with its ask), working, waiting for review, done, and the attic (archived, or quiet for
STALE_DAYS). It flags what to tidy: asks gone stale, empty "ready for review" sessions, untitled sessions,
reruns after a usage limit, duplicate titles, and sessions that look filed under the wrong repository.

Both outputs hold her session titles: they are gitignored. Never commit them.
"""
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
STALE_DAYS = 7
# A title that names another project's subject: (pattern, the repo it belongs to).
BELONGS = [
    (r"\b(courses?|grocer|meal|recipe|intermarch|basket|shopping list)", "Intermarche-grocery-shopping"),
    (r"\b(catio|kittychat|manor|harness|cats?\b)", "Pretty-Project-Portfolio"),
    (r"\b(shop|montfortoise|packshot|product page|business plan|about page)", "montfortoise-shopify"),
    (r"\btiktok", "tiktok-saves"),
    (r"\b(pixel art|libresprite)", "pixel-art-app"),
]
ROUTINE = re.compile(r"refresh the catio", re.I)
UNTITLED = re.compile(r"^[a-z]+-[a-z]+-[a-z]+$")   # an auto-generated name like charpc-serene-kurzweil


def day(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")) if iso else None


def repo_of(s):
    for src in (s.get("session_context") or {}).get("sources") or []:
        url = (src.get("git_repository") or {}).get("url") or ""
        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url)
        if m:
            return m.group(2).removesuffix(".git")
    return "No repository"


def from_session(s, now):
    bucket = (s.get("status_bucket") or "").lower().replace("session_status_bucket_", "")
    status = (s.get("session_status") or "").lower().replace("session_status_", "")
    pts = (s.get("external_metadata") or {}).get("post_turn_summary") or {}
    title = s.get("title") or "Untitled"
    when = day(s.get("updated_at") or s.get("created_at"))
    age = (now - when).days if when else 0
    state = {"blocked": "needs", "failed": "failed", "review_ready": "review", "working": "working"}.get(bucket, "done")
    if pts.get("status_category") == "need_input" and state == "done":
        state = "needs"
    attic = status == "archived" or (state == "done" and age > STALE_DAYS)
    return {
        "id": s["id"], "kind": "session", "title": title, "project": repo_of(s), "state": "attic" if attic else state,
        "age": age, "updated": s.get("updated_at", "")[:10], "link": "https://claude.ai/code/" + s["id"],
        "ask": pts.get("needs_action") or (pts.get("status_detail") if state in ("needs", "failed") else ""),
        "last": pts.get("recent_action") or pts.get("status_detail") or s.get("task_summary") or "",
        "empty": not pts, "routine": bool(ROUTINE.search(title)) or s.get("origin") == "scheduled_trigger",
    }


def from_chat(d, now):
    at = d.get("updatedAt") or d.get("adoptedAt") or 0
    age = int((now.timestamp() * 1000 - at) / 864e5) if at else 0
    state = {"needs": "needs", "busy": "working"}.get(d.get("mood"), "done")
    return {
        "id": d.get("id", ""), "kind": "chat", "title": d.get("title") or "A chat", "project": d.get("project") or d.get("title") or "Chats",
        "state": state, "age": age, "updated": datetime.fromtimestamp(at / 1000, timezone.utc).strftime("%Y-%m-%d") if at else "",
        "link": d.get("link", ""), "ask": d.get("note", "") if state == "needs" else "", "last": d.get("note", ""), "empty": False, "routine": False,
    }


def home_of(project, home):
    return project.lower().startswith(home.lower())


def flags(cats):
    seen = defaultdict(list)
    sessions = {c["link"]: c for c in cats if c["kind"] == "session"}
    for c in cats:
        seen[re.sub(r"\W+", " ", c["title"].lower()).strip()].append(c)
        f = []
        if c["state"] in ("needs", "review") and c["age"] > STALE_DAYS:
            f.append(f"stale: asked {c['age']} days ago, close or archive?")
        if c["state"] == "review" and c["empty"]:
            f.append("nothing to review: no summary, likely archive")
        if c["kind"] == "session" and UNTITLED.match(c["title"]):
            f.append("untitled")
        if c["state"] == "failed" and re.search(r"limit|API Error", c["ask"]):
            f.append("stopped by a limit or an API error: rerun if still wanted")
        for pat, home in BELONGS:
            if re.search(pat, c["title"], re.I):
                if c["kind"] == "session" and not c.get("moved") and c["project"] != "No repository" and not any(home_of(c["project"], h) and re.search(p, c["title"], re.I) for p, h in BELONGS):
                    f.append("filed under " + c["project"] + ", looks like " + home)
                break
        twin = c["kind"] == "chat" and sessions.get(c["link"])
        if twin:
            f.append("adopted, but its link is the session " + repr(twin["title"]) + ", already a cat: let one go")
        c["flags"] = f
    for group in seen.values():
        if len(group) > 1:
            for c in group:
                c["flags"].append(f"duplicate title ({len(group)} sessions)")


ORDER = ["needs", "failed", "review", "working", "done", "attic"]
HEAD = {"needs": "Needs you", "failed": "Failed", "review": "To review", "working": "Working", "done": "Done", "attic": "Attic"}


def markdown(cats, at):
    live = [c for c in cats if not c["routine"]]
    by = defaultdict(list)
    for c in live:
        by[c["project"]].append(c)
    count = lambda xs, s: sum(1 for c in xs if c["state"] == s)
    out = [f"# KittyChat Café digest", "", f"{len(live)} cats ({sum(c['kind'] == 'chat' for c in live)} adopted chats), from the copy saved {at}. "
           + ", ".join(f"{count(live, s)} {HEAD[s].lower()}" for s in ORDER if count(live, s)) + ".", ""]
    urgent = sorted((c for c in live if c["state"] in ("needs", "failed") and c["age"] <= STALE_DAYS), key=lambda c: c["age"])
    if urgent:
        out += ["## Needs you now", ""] + [f"- **{c['title']}** ({c['project']}, {c['age']}d): {c['ask'] or 'see the session'} [open]({c['link']})" for c in urgent] + [""]
    tidy = [c for c in live if c["flags"]]
    if tidy:
        out += ["## To tidy", ""] + [f"- {c['title']} ({c['project']}): " + "; ".join(c["flags"]) for c in tidy] + [""]
    rank = lambda p: (-sum(c["state"] in ("needs", "failed", "review") for c in by[p]), -sum(c["state"] == "working" for c in by[p]), p)
    for p in sorted(by, key=rank):
        xs = sorted(by[p], key=lambda c: (ORDER.index(c["state"]), c["age"]))
        out += [f"## {p}", "", " · ".join(f"{count(xs, s)} {HEAD[s].lower()}" for s in ORDER if count(xs, s)), ""]
        for s in ORDER:
            row = [c for c in xs if c["state"] == s]
            if not row:
                continue
            out.append(f"**{HEAD[s]}**")
            for c in row:
                note = c["ask"] if s in ("needs", "failed") else c["last"]
                out.append(f"- {c['title']} · {c['updated']}" + (f": {note[:160]}" if note and s != "attic" else ""))
            out.append("")
    return "\n".join(out)


def main(chat_files):
    snap = json.loads((DATA / "sessions.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    cats = [from_session(s, now) for s in snap.get("sessions", [])]
    for f in chat_files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        d = d.get("data", d) if isinstance(d, dict) else d
        d.setdefault("id", Path(f).stem)
        if d["id"].startswith("session_"):   # a sessions/<id> document: her move of that cat, already sorted
            for c in cats:
                if c["id"] == d["id"] and d.get("room"):
                    c["moved"] = d["room"]
            continue
        cats.append(from_chat(d, now))
    flags(cats)
    at = datetime.fromtimestamp(snap.get("at", time.time() * 1000) / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (DATA / "digest.md").write_text(markdown(cats, at), encoding="utf-8")
    keep = [{k: c[k] for k in ("title", "kind", "project", "state", "age", "ask", "flags", "link")} for c in cats if not c["routine"]]
    (DATA / "digest.json").write_text(json.dumps({"at": snap.get("at"), "cats": keep}, ensure_ascii=False), encoding="utf-8")
    print("wrote", DATA / "digest.md", "and digest.json", f"({len(keep)} cats, {sum(bool(c['flags']) for c in keep)} to tidy)")


if __name__ == "__main__":
    main(sys.argv[1:])
