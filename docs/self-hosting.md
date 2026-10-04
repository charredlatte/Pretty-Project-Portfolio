# Running your own: what is still Charlotte's

The page and the harness were built for one café, Charlotte's, and some of her values are written into them. The
first table is what breaks a fork until it is changed; the second is where they only name her. Both come from
searching the code for her café's link, her GitHub name and her name on 4 October 2026. Run the search again before
trusting them on a later checkout:

```bash
git grep -n -i "charlotte\|charredlatte\|KHiWnmr" -- ':!docs' ':!litterbox'
```

Making these one setting, read from one place, is the step that turns "run your own" from a fork into an install.

## What breaks a fork

| Where | Value | What it does | Set it to |
|---|---|---|---|
| `catio/index.html` | `CATIO_URL` | Her café's artifact link, quoted in every file delivery so the session knows where to fetch the file | Your café's artifact link |
| `catio/index.html` | `INSTALL` | The two install lines the wizard's How it works step shows | Your fork's address in the first line |
| `catio/index.html` | `"charredlatte/" + rp` in `openNewCat()` | Turns a bare repository name in a room into one of her repositories when New cat starts a session | Your GitHub name, or write `owner/repo` in Edit rooms |
| `catio/index.html` | `GATEWAY = "CATIO"` | The connector the page asks claude.ai for | Name your gateway's connector `CATIO`, as hers is (`harness/gateway/README.md` says `Catio`) |
| `harness/rules.json` | `catio` | The café every session is told it lives in, and where the `catio` skill reads and writes | Your café's artifact link |
| `harness/rules.json` | `public` | The repositories where nothing may credit Claude | Your public repositories, or none |
| `harness/rules.json` | `merging.audits`, `merging.review` | The skills a self-merge needs to have run, `ponytail-audit` and `code-review`; the first even with the opening audit switched off | Skills you have |
| The rules' skills | `ponytail-audit`, `browser-agent-preflight` | Called by the rules, not in this repository (`code-review` comes with Claude Code) | Install them, or switch their rules off in a repository's `.claude/catio-rules.json` |
| `harness/README.md`, `.claude/settings.json` | The `kittychat` marketplace | Where the house rules are installed from | Your fork |
| The gateway | `CATIO_HANDLE` (a Worker variable) | Names the first account; `charlotte` when unset (`src/registry.js`) | Your handle |
| `catio/data/rooms.json` | Her rooms | Seeds a fresh browser's localhost café once; after that, Edit rooms | Your rooms, or `{}` to get the wizard |
| `artifacts.json` | Her published pages | Where republishing goes | Yours, once published |
| `catio-plugin/skills/catio/SKILL.md` | `git clone https://github.com/charredlatte/…` | The setup skill clones this repository, not a fork | Your fork's address |
| The publish's `capabilities` | The setup skill's set | Has no `CATIO` server, so the page can't reach a gateway | Once your gateway is set up, the whole set in `CLAUDE.md` ("The stored capabilities") |

## Where it only names her

These work in a fork, but say "Charlotte" to every session, the queen or the person reading:

- **The words before a message**, `[Catio] Charlotte says:` (and `Charlotte's note:` before a file's note): written by the page, `harness/hooks/report.py`,
  `harness/mcp/catio_mcp.py` and `harness/runner/queen.py`; read by the `catio` skill and `harness/runner/queen.md`;
  checked by the tests. Change them all together or not at all.
- **The queen's character**: `harness/runner/queen.md` points to a section `queen.py` writes, "As Charlotte set you
  up". Change the two together.
- **The rules' texts** in `harness/rules.json`, and the messages of `harness/hooks/session_start.py` ("a cat in
  Charlotte's Catio"), `gates.py` and `ship_gate.py`.
- **Descriptions and authors**: `harness/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `catio-plugin/.claude-plugin/plugin.json`, `harness/README.md`, `harness/skills/catio/SKILL.md`.
- **Before accounts**: `charlotte` in `harness/gateway/src/houses.js`, `cafe.js` and `house.js`, and in
  `catio_mcp.py`, lets grants and notes from before accounts open the first house. Harmless in a new gateway.
- **Comments and docs**: the tools' docstrings (`catio/tools/`), `harness/gateway/wrangler.jsonc` and
  `cafe/runtime.js`, `catio/art/CREDITS.md`, the `litterbox-quiz` skill, `harness/gateway/README.md`,
  `harness/runner/README.md`, `CLAUDE.md`, and the tests' examples.
