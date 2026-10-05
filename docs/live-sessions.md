# Live sessions and the saved copy

**Retired with the claude.ai artifact on 5 October 2026** (`docs/artifact.md`). In the café she uses, the gateway's,
the cats are the sessions that report to the gateway (`list_agents`); nothing below runs there.

How the café knows which Claude Code sessions exist, what it does when claude.ai won't let it ask, and how the
copy it falls back on is kept. Checked against `catio/index.html`, the artifact's database and her Routines on
4 October 2026.

## The live read

In claude.ai the page calls Claude Code Remote's `list_sessions` (limit 50) through its `mcp` capability, as
Charlotte, and asks again every minute (`watch()`). Each session becomes a cat: its state gives the mood, its
repository the room. claude.ai's warm-start placeholder is skipped, and sessions asleep or unreviewed for a week
nap in the attic.

Claude Code Remote is built into claude.ai. It is **not** one of the connectors in her Customize → Connectors
list, so there is no per-tool switch for `list_sessions` to set to Always allow (checked against her settings,
September 2026). Whether a page may call it is claude.ai's decision, not hers.

## When it is blocked

claude.ai answers a refused call with an error code. `problem()` turns each one into the status sign's line
under the brand:

| Code | What it means | The sign says | Anything for her to do |
|---|---|---|---|
| `approval_required` | the tool asks before every call, and a page can't answer a prompt | claude.ai doesn't let pages read sessions live yet | No |
| `blocked_by_policy` | claude.ai doesn't allow this call from a page | the same | No |
| `server_not_connected`, `server_not_found` | Claude Code Remote isn't available to her right now | try again later | No: wait, then Try again |
| `selection_required` | she has more than one Claude Code Remote | pick one | Pick one when claude.ai asks |
| `needs_reauth` | the connection lapsed | reconnect | Reconnect in claude.ai Settings → Connectors |
| `not_in_manifest`, `consent_required` | the page hasn't been given the tool | the page isn't allowed yet | Press Allow |
| `not_granted`, `capability_disabled`, `capability_removed` | this view of the page can't use the connector | open the page in claude.ai | Open it in claude.ai |
| `tool_error` | Claude Code Remote answered with an error | the error's own message | Try again |
| anything else (a dropped connection) | the refresh failed | "Couldn't refresh. These are the cats from 17:02." | Try again |

On every code in the table but the last two, the page drops its live list (`RETRACT`) and falls back on the saved
copy. On the last two it keeps the live cats it already had (the copy if it had none), and on a dropped connection says
how old they are.

With a saved copy to show, the sign shrinks to one line, `Saved copy · 17:02` (with the date when it isn't from
today), and the reason above shows on hover or keyboard focus. With no copy at all, the sign shows the reason and
the stage says "Only adopted chats are showing."

## The saved copy

`snapshot/sessions` in the artifact's database: `{at, savedBy, sessions[]}`, the 50 most recent sessions as
`list_sessions` returned them, cut down by `catio/tools/save-sessions.py` to what the page reads (title, state,
times, origin, repositories and branches, model, environment, tags, and the task and post-turn summaries). Only
Claude writes it, with `ArtifactData`, because only a Claude Code session can call `list_sessions` without a page
in the way. The page watches the document, so a new copy shows the moment it is saved.

The copy is a snapshot: a cat in it keeps the mood it had when Claude saved it, and a session started since isn't
there. `at` is what the sign shows, so the age is never hidden.

### Refreshing it

By hand, from any Claude Code session that has Claude Code Remote and `ArtifactData`:

1. Call `list_sessions` with `limit: 50` and save the result as JSON (as the tool returns it, `ccr` wrapper and
   all).
2. `python3 catio/tools/save-sessions.py <result>.json` writes `catio/data/sessions.json` (gitignored: it holds
   her session titles, never commit it).
3. `ArtifactData` `get` `snapshot/sessions` for its version, then `set` it to that file's object, pinned with
   `if_version`.

### Its Routine is paused

The Routine "Refresh the catio" did those three steps every two hours from 07:59 to 19:59
Paris time. It was switched off on 30 September 2026 at her request (its last run, that afternoon, failed), and
it is still off. The copy in the database is from **2 October 2026, 16:42 Paris time**, refreshed by hand.
So today the copy is only as fresh as the last time she asked a session to refresh it.

Turning it back on is `update_trigger` with `enabled: true`, and her call. It must keep firing into the session
it was made in: a fresh Routine session has neither `list_sessions` nor `ArtifactData` (tried September 2026).

## What keeps cats live anyway: the gateway

Sessions that report to the gateway (`harness/README.md`, "The gateway") don't need `list_sessions` at all. The
house-rules plugin's `report.py` hook tells the gateway each session's state as it changes, and the page reads the
gateway through her `CATIO` connector, which she can set to Always allow. In `allCats()`:

- a session in the saved copy that also reports takes the gateway's mood whenever that is newer (`fromGateway()`);
- a session that reports but isn't in the copy is a cat of its own (`catFromAgent()`).

So with the gateway set up (it is, since 2 October), the saved copy only matters for sessions without the hook:
ones in repositories that don't run the house rules, or containers older than the setup script that installs
them.

## Elsewhere

- **The café on the gateway's address** doesn't call `list_sessions`. The sign says "Live through your gateway",
  and its cats are the sessions that report.
- **On localhost** there is no `mcp` at all: the page reads `data/sessions.json` from beside it on every load
  ("On this computer: your N sessions as Claude saved them …"). Ask Claude for a fresh one.
