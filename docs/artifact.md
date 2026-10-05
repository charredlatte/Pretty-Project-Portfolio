# The claude.ai artifact (retired)

The café's first home was a private claude.ai artifact, `kittychat-cafe` in `artifacts.json`. On 5 October 2026 Charlotte
retired it: "I honestly don't care about the artifact. It doesn't function the way I want the gateway to work, so I
don't use it." The café she uses is the gateway's (CLAUDE.md, "Where the café lives"). The artifact's copy of the page
stopped at the 4 October version, and its database is apart from the gateway's.

Nothing here is current work. **Don't republish it, and don't offer to**, unless she asks. It is kept for one
thing the gateway can't do yet:

- **The licensed art, in a cloud session.** `art/licensed/` is gitignored, and the artifact's published files are the
  one copy a session can read back (`Artifact` read with `path: "art/licensed/<file>"`; the files are listed under
  "Republishing" below). The gateway serves the same art at `/art/*`, but only to her, signed in.

The page keeps its claude.ai paths (claude.ai's own `window.claude`, Claude Code Remote through the `mcp` capability, the
saved copy of `list_sessions`). The gateway's `cafe/runtime.js` stands in for the same `window.claude`, and the test
suite loads the page in the skeleton the Artifact tool publishes, so those paths cost little to keep and stay tested.
Taking them out is a separate decision, hers.

## What claude.ai did that the gateway café doesn't (yet)

In the gateway café the page runs with `VIA_GATEWAY` set and says plainly what it can't do there:

- **New session**: `create_session` is Claude Code Remote's, and only claude.ai can call it for her.
- **A session's title**: renaming a cat doesn't retitle its session.
- **Posting into a session mid-turn**: what she writes reaches a session through the gateway's `inbox`, which its
  report hook hands in when its turn ends, not straight away as `send_message` did.
- **Every session, reporting or not**: the gateway knows only the sessions that report to it (the house rules'
  `report.py`); claude.ai's `list_sessions` listed them all.
- **The sorter**: claude.ai's `sample` capability guessed where a dropped file goes; on the gateway the decider does
  (`decide`).

## Republishing (only if she asks)

The page is **one** private artifact. Its URL is the `kittychat-cafe` entry in `artifacts.json`. Always republish to that
URL (`Artifact` publish with `url`, after reading it back), never a new one: the database with
her rooms, renames and adopted chats belongs to that artifact.

Publish `catio/index.html` with:

- `files`: every file the page references: `art/furniture.png`, `art/licensed/*.png` (`house.png`,
  `house-upper.png`, `decor.png`, `furniture.png`, `meadow.png`, `mochi-idle.png`, `mochi-box.png`,
  `pochi.png`) and the interface
  in `art/licensed/ui/` (`panel`, `button`, `button-hover`, `button-down`, `button-green`,
  `button-pink`, `field`, `arrow`, `frame`, `divider`, `bubble`, `corners`,
  `toggle`, `status`, `faces`, `crown`, `stars`, `cursor`, `cursor-point`, `pointer`, `logo`, `pastel` `.png`,
  and `sprout.ttf`), and the map panel in `art/licensed/pastel/` (`panel`, `panel-dark`, `frame`, `button`,
  `button-hover`, `button-down`, `icons` `.png`); and, once she has pieces of her own in `art/skin/`,
  `art/skin.json` and each file it lists (below, "Plug-and-play design");
- `capabilities`: omit it on a republish to keep what's stored. Pass it, as the whole set in "The stored capabilities"
  below, to add a tool on purpose or when that section says a tool joined since the last publish (the first republish
  after PR #31 must, to add `list_repos`: until it has, the wizard's GitHub step says the page isn't allowed to ask).

`catio/data/` is not published: it is for the localhost copy.

After publishing, read back every art file you changed (`Artifact` read with `path`) and look at it: a
republish keeps the old copy of any file it wasn't given. Then check the real database with `ArtifactData`:
list `rooms`, and create, update and delete one probe document in `cats` the way the page does.

### The stored capabilities

The stored capabilities (the full set, to pass whole if a tool is ever added):
`{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions","list_repos","send_message","delete_trigger","create_session","set_session_title","archive_session","unarchive_session","interrupt_session"] }, { server: "CATIO", tools: ["list_agents","comment","comments","drop_file","manage","decide","quizzes","answer"] }] }, db: {}, assets: {}, sample: {}, downloads: true }`

`downloads` joined it on 4 October (The look's Export tokens): until a republish passes the whole set, Export falls
back to the browser's own download, which claude.ai's frame may not allow.

`decide` joined the set on 3 October (the decider, below): the first republish after it must pass the whole set, or in claude.ai the
page cannot ask the decider and the brain simply keeps sorting the old way. `quizzes` and `answer` joined it the same evening (her
quest log): until a republish passes the whole set, the claude.ai café shows no homework; the café on the gateway's address does.

`host:catio` (the same five tools) can only be declared from the Claude desktop app, so it isn't in the stored
set. `delete_trigger` stays only to clean up the Routines older versions bound. Posting into a session through a bound Routine doesn't reach the session
(it starts a new one): see `docs/audit-2026-10-01.md` and phase 0 of `docs/plan.md` before touching
`postToSession()`. What's next, renovation mode included, is `docs/plan.md`.

## Live sessions in claude.ai

The page calls `list_sessions` (limit 50) through the `mcp` capability as the viewer. Its write
tools are the harness's, above, and only ever run on her click or drop. Don't add `mine: true`: a page has no calling session, and that flag can
error without one. Every connector error code has its own message in `problem()`.

claude.ai can refuse the page's read (`approval_required`: the tool asks before every call,
which a page can't do; `blocked_by_policy`). Claude Code Remote is a built-in connector: it is
**not** in her Customize → Connectors list, so there is no `list_sessions` switch for her to set
(checked against her settings, September 2026). Don't send her looking for one. The page shows
`snapshot/sessions`. To refresh it, call `list_sessions` (limit 50) from a session, save the
result, run
`python3 catio/tools/save-sessions.py <result>.json`, and write `catio/data/sessions.json`'s
object to `snapshot/sessions` with `ArtifactData` (`set`, pinned with `if_version`). The script
keeps only what the page reads, and accepts the result as the tool returns it
(wrapped in `ccr`).

`python3 catio/tools/digest.py [cats/*.json sessions/*.json]` compiles that copy, adopted chats exported from `cats` and her moves from `sessions`,
into `catio/data/digest.md` and `digest.json`: per project, what needs her, what to review, and what to tidy
(stale asks, empty reviews, untitled sessions, reruns, duplicates, misfiled repos). Both are gitignored: never
commit them.

A Routine, "Refresh the catio", did this every two hours from 07:59 to 19:59 Paris time until she paused it
on 30 September 2026; it is still off, so the copy is refreshed by hand when she asks. Turning it back on is her
call. It fires into the Claude Code session it was created from, not a fresh one: a fresh routine session has
neither `list_sessions` nor `ArtifactData`, so it can't refresh anything (tried September 2026). What each
refusal means and the whole fallback: `docs/live-sessions.md`.
