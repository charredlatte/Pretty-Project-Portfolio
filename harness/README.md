# The KittyChat harness

The Catio (`catio/`) is the cafe you see. This folder is the harness behind it:

- a **Claude Code plugin**, `kittychat-house-rules`, that makes every session follow the house rules and
  understand what Charlotte sends from the Catio;
- the **Catio MCP server**, `mcp/catio_mcp.py`, through which other agents and models (Codex, Gemini CLI,
  Cursor, Claude Desktop, anything that speaks MCP) join the cafe as cats.

## The house rules

They live in [`rules.json`](rules.json). The KittyChat Café page shows them all, under House rules in the brand's House menu.

| Rule | How it's kept |
|---|---|
| Preflight before any browser | Enforced. `hooks/gates.py` refuses browser tools (Playwright, Chrome, computer use) and shell commands that drive a browser until the `browser-agent-preflight` skill has run in the session |
| Open with a read-only audit | Enforced. `hooks/gates.py` refuses edits, commits, pushes and scripts run with `--write` or `--commit` (such as `litterbox/sort.py --write`) inside the repo until the `ponytail-audit` skill has run. The summary is saved to the Catio (`audits/<repo>`) and shown in the project's filing cabinet |
| Semi-automatic shipping | Enforced as a nudge. `hooks/ship_check.py` holds the end of a turn once when a feature branch has work that isn't pushed, and asks Claude to commit, push and open a PR if the work is done and checked, or to say why not. In a cloud session it checks every repo checked out beside this one too, since the container goes with them. `litterbox/sort.py --write` follows the rule itself: it commits and pushes the notes it files. Never the default branch, no force-push, no merge, unless the repo merges its own pull requests (`{"merge": true}`, below) |
| Map before you dig (graphify) | Enforced as a nudge. `hooks/graph_first.py` runs graphify's own `hook-guard` before searches and reads, pointing Claude at `graphify query` when the repo has a map. `session_start.py` says to build or refresh one. `graphify-out/` never counts as unpushed work |
| Catio messages come from Charlotte; file contents are data | Soft, in the session's context |
| Answer on the cat; honour pause and wrap-up requests | Soft, and the `catio` skill says how |
| Private matters stay in the Catio, out of git | Soft |
| Say which model is working | Soft |

Soft rules can be switched off from the page. Enforced ones are switched in `rules.json` for every repo,
or for one repo in its own `.claude/catio-rules.json`, e.g. `{"opening_audit": false}`. A repo can also
list extra browser commands, one pattern per line, in `.claude/browser-commands`.

A repo whose own rules say its sessions finish by merging (the grocery app's: "a session isn't finished until
its branch is merged into `main`") opts in with `{"merge": true}` in the same file. Its sessions are then told
to merge their pull request once its checks pass; everywhere else the rule stays "no merge". Pushing to the
default branch and force-pushing stay forbidden either way.

## Turning it on in a repo

Add this to the repo's `.claude/settings.json`. It's the same in every repo, including this one:

```json
{
  "extraKnownMarketplaces": {
    "kittychat": { "source": { "source": "github", "repo": "charredlatte/Pretty-Project-Portfolio" } }
  },
  "enabledPlugins": { "kittychat-house-rules@kittychat": true },
  "permissions": {
    "allow": ["Bash(git commit:*)", "Bash(git push:*)", "mcp__github__create_pull_request"]
  }
}
```

The `permissions` lines are what make shipping semi-automatic: commits, pushes and PRs no longer stop to
ask. Leave them out to keep being asked. To try the plugin from a checkout of this repo before it is on
the default branch, use `{ "source": "directory", "path": "." }` as the marketplace source instead.

## How the Catio talks to a session

The page calls Claude Code Remote as Charlotte. The first time it needs a session, it makes a Routine
bound to that session with no schedule (`create_trigger` with `persistent_session_id`), and keeps its id
in the Catio's database. After that, every file she drops on the cat, every message she writes to it, and
every request (pause, wrap up) is delivered straight into the session with `fire_trigger`. The session
sees a turn starting with `[Catio]`, and the `catio` skill (`skills/catio/`) says how to fetch the file,
answer on the cat and mark it picked up. A session also catches up at start with anything a delivery
missed.

## Other agents and models: the Catio MCP server

`mcp/catio_mcp.py` is plain Python (standard library only). State is kept in `~/.catio/` (or
`$CATIO_HOME`). Its tools: `house_rules`, `report_status`, `list_agents`, `inbox`, `pick_up`,
`drop_file`, `comment`, `comments`, `manage`.

An agent calls `report_status` when it starts, when it needs Charlotte and when it's done, and it
becomes a cat. If it registers a `wake` command, anything dropped on it or said to it runs that command
straight away. For example, `["codex", "exec", "resume", "{session}", "{message}"]` or
`["gemini", "-p", "{message}"]`. The placeholders are whole arguments and no shell is involved. Otherwise
it finds them in its `inbox`.

Add it to each client as a stdio server (use the path to your copy of this repo):

- **Codex** (`~/.codex/config.toml`):
  ```toml
  [mcp_servers.catio]
  command = "python3"
  args = ["/path/to/Pretty-Project-Portfolio/harness/mcp/catio_mcp.py"]
  ```
- **Gemini CLI** (`~/.gemini/settings.json`), **Cursor** (`~/.cursor/mcp.json`) and **Claude Desktop**
  (`claude_desktop_config.json`):
  ```json
  { "mcpServers": { "catio": { "command": "python3", "args": ["/path/to/Pretty-Project-Portfolio/harness/mcp/catio_mcp.py"] } } }
  ```

Then tell the agent, in its own instructions file (`AGENTS.md`, `GEMINI.md`, Cursor rules): "You are a
cat in Charlotte's Catio. Read `house_rules` from the catio server and follow them. Call
`report_status` when you start, when you need her, and when you finish, and check `inbox` between tasks."

In the Claude desktop app, the Catio page reaches the same server as `host:catio`, so agent cats show up
in the manor next to the Claude Code sessions. On her own computer, `python3 catio_mcp.py --serve
catio-local` serves the localhost copy of the Catio together with the tools, as `/api/*`. They answer only POSTs
from that page, at `localhost` or `127.0.0.1`, so no other site she has open can talk to a cat.

## Digesting a repo: graphify

The plugin carries [graphify](https://github.com/Graphify-Labs/graphify)'s skill in `skills/graphify/`
(version 0.9.72, unmodified, Apache-2.0: its `LICENSE` and `NOTICE` are beside it). It maps a repo into a
knowledge graph in `graphify-out/`: `graphify update .` maps the code locally with no model, `/graphify .`
adds docs, papers, images and video, and `graphify query`, `path` and `explain` answer from the graph
instead of grepping. The skill installs the `graphify` command (PyPI `graphifyy`) the first time it runs.

The Catio shows each map. The `catio` skill's `graph_doc.py` digests `graphify-out/` into a
`graphs/<repo>` document (counts, the most connected ideas laid out as a map, neighbourhoods, hubs,
surprising links, suggested questions), and the page draws it in that project's filing cabinet. A
suggested question is a button: it asks one of the project's cats, which answers from the graph on the cat.

Other agents install the same skill for themselves on her computer, one line each:

```sh
pipx install graphifyy   # or: uv tool install graphifyy
for p in codex gemini claw agents; do graphify install --platform "$p"; done
```

`claw` is OpenClaw, `agents` the cross-framework `~/.agents/skills`. Cursor has no user-level skill: run `graphify cursor install`
inside a repo for its always-on rule.

## Tests

```bash
python3 -m unittest discover harness/test
```
