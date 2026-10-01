#!/usr/bin/env python3
"""Turn a Claude Code Remote `list_sessions` result into the page's saved copy of the sessions.

    python3 catio/tools/save-sessions.py list_sessions.json   ->  catio/data/sessions.json

Keeps only what the page reads: title, state, times, origin, repos and branches, the model (a cat's
breed), the environment (for New cat), the tags (the warm-start placeholder is skipped), and the task
summary and post-turn summary that become a cat's speech bubble. The same object is what goes into
the artifact's `snapshot/sessions` document. The output is gitignored: never commit it.
"""
import json
import sys
import time
from pathlib import Path

KEEP = ("id", "title", "status_bucket", "session_status", "updated_at", "created_at", "origin", "task_summary",
        "tags", "environment_id", "configured_model")
OUT = Path(__file__).resolve().parent.parent / "data" / "sessions.json"


def main(src):
    raw = json.loads(Path(src).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "ccr" in raw:
        raw = raw["ccr"]
    rows = raw.get("data", raw) if isinstance(raw, dict) else raw
    sessions = []
    for s in rows:
        ctx = s.get("session_context") or {}
        keep = {k: s[k] for k in KEEP if k in s}
        keep["session_context"] = {k: ctx[k] for k in ("sources", "outcomes", "model") if k in ctx}
        meta = {k: v for k, v in (s.get("external_metadata") or {}).items() if k in ("task_summary", "post_turn_summary") and v}
        if meta:
            keep["external_metadata"] = meta
        sessions.append(keep)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"at": int(time.time() * 1000), "savedBy": "Claude", "sessions": sessions}), encoding="utf-8")
    print("wrote", OUT, f"({len(sessions)} sessions)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
