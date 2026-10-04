# Running your own: what is still Charlotte's

The page and the harness were built for one café, Charlotte's, and a few of her values are written into them. A
fork has to change each one below before its café works as its own. Found by searching the code for her café's
link, her GitHub name and her name, 4 October 2026; search again (`git grep -n -i "charlotte\|charredlatte\|KHiWnmr"`)
before trusting this list on a later checkout.

Making these one setting, read from one place, is the step that turns "run your own" from a fork into an install.

## The page, `catio/index.html`

| Value | What it does | Set it to |
|---|---|---|
| `CATIO_URL` | Her café's artifact link, quoted in every file delivery so the session knows where to fetch the file | Your café's artifact link |
| `INSTALL` | The two install lines the wizard's How it works step shows | Your fork's address in the first line |
| `"charredlatte/" + rp` in `openNewCat()` | Turns a bare repository name in a room into one of her repositories when New cat starts a session | Your GitHub name, or write `owner/repo` in Edit rooms |
| `GATEWAY = "CATIO"` | The connector the page asks claude.ai for | Name your gateway's connector `CATIO`, as hers is (the gateway's README says `Catio`) |
| `[Catio] Charlotte says:`, `Charlotte's note:` | The words a session reads before a message or a file's note | Harmless; to change them, change `harness/hooks/report.py`'s `SAYS` and the `catio` skill with them |

## The harness, `harness/`

| Value | What it does | Set it to |
|---|---|---|
| `rules.json`: `catio` | The café every session is told it lives in, and where the `catio` skill reads and writes | Your café's artifact link |
| `rules.json`: `public` | The repositories where nothing may credit Claude | Your public repositories, or none |
| `rules.json`: `merging.audits`, `merging.review` | The skills a self-merge needs to have run: `ponytail-audit` and `code-review`. The first is needed even with the opening audit switched off | Skills you have |
| `rules.json`: the rules' texts | Name Charlotte as the one sessions answer to | Your name, or "the owner" |
| `hooks/session_start.py` | Tells every session it is "a cat in Charlotte's Catio" | Your café |
| `hooks/ship_gate.py` | Says a repo's branches are Charlotte's to delete | Your name |
| `skills/catio/SKILL.md`, `runner/queen.md` | Written to and about Charlotte: her messages, her queen | Yours |
| `.claude-plugin/plugin.json` | "Charlotte's KittyChat harness" | Yours |
| The skills the rules call | `ponytail-audit` and `browser-agent-preflight` are not in this repository (`code-review` comes with Claude Code) | Install them, or switch their rules off in a repository's `.claude/catio-rules.json` |

## The gateway, `harness/gateway/`

| Value | What it does | Set it to |
|---|---|---|
| `CATIO_HANDLE` (a Worker variable) | Names the first account; `charlotte` when unset (`src/registry.js`) | Your handle |
| `charlotte` in `src/houses.js`, `src/cafe.js`, `src/house.js` | Lets grants and notes from before accounts open the first house | Nothing: harmless in a new gateway |

## Everything else

| File | What it holds | Set it to |
|---|---|---|
| `.claude/settings.json` | The `kittychat` marketplace, from her repository, for sessions in this one | Your fork |
| `catio-plugin/.claude-plugin/plugin.json` | `author` and `repository` | Yours |
| `catio/data/rooms.json` | Her rooms. A fresh browser's localhost café is seeded from it once; after that, Edit rooms | Your rooms, or `{}` to get the wizard |
| `artifacts.json` | Her published pages | Yours, once published |
