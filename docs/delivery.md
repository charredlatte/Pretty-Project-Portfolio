# How what you send reaches a session

What happens between the moment Charlotte drops a file on a cat, writes to it, clicks Pause, or says something to the
queen, and the moment a Claude Code session (or the queen) acts on it. The short version is in the README; this is
the long one, down to which process holds the message at each step, and then an honest look at the design against
the six questions any software has to answer as it grows: scale, speed, extensibility, security, debuggability and
testability.

The pieces, by the file that is each one:

| Piece | Where it runs | File |
|---|---|---|
| The café | her browser (claude.ai's sandbox, the gateway's own address, or localhost) | `catio/index.html` |
| The gateway | a Cloudflare Worker, always on | `harness/gateway/src/` |
| The house | one SQLite-backed Durable Object per account, inside the Worker | `harness/gateway/src/house.js` |
| The MCP endpoint | the Worker, at `/mcp` | `harness/gateway/src/mcp.js`, `tools.js` |
| The report hook | inside every Claude Code session that has the house-rules plugin | `harness/hooks/report.py` |
| The queen's runner | her PC, a Python process | `harness/runner/queen.py` |
| The Catio MCP server | her PC, for agents that aren't Claude Code | `harness/mcp/catio_mcp.py` |
| The decider | the Worker, on Workers AI | `harness/gateway/src/decide.js` |

## Three roads, by who the message is for

### 1. To a session, through claude.ai alone (no gateway)

Everything she sends is **saved first** in the artifact's database, the moment she sends it: a file as `brain/<id>`
(its bytes in the artifact's assets), a message as `notes/<id>`, a pause or wrap-up as `sessions/<id>.request`. The
page then tries Claude Code Remote's `send_message`, which claude.ai refuses to a page (`blocked_by_policy`), so the
attempt is kept as `outbox/<id>` with the error code, and the page says the message is waiting.

Nothing can then wake the session: a cloud session is a container with no address, and only claude.ai puts a turn
into it. The message waits until the session's next turn, when the plugin's `catio` skill catches up: it queries
`brain`, `notes`, `sessions/<id>` and `outbox` for its own session id, does what each asks, answers on the cat (a
`notes` document with `author: "session"`) and marks the outbox entries delivered. The catch-up is a skill, so it is
the model's doing, not a hook's: a session without the plugin never looks.

### 2. To a session, through the gateway

With `CATIO_URL` and `CATIO_TOKEN` in the session's environment, the plugin's `report.py` hook turns every session
into a cat that reports **and listens**, with nothing for the model to remember:

- **In.** The page (through her `CATIO` connector, as the owner) calls the house's tools: `comment` saves her note
  in the house's `notes` table, `drop_file` her file in `files` (up to 1 MiB, base64, status `waiting`),
  `manage` a request on the cat's agent record.
- **Out.** Claude Code runs `report.py` on its own hooks: `SessionStart` and `UserPromptSubmit` report the cat busy,
  `Notification` that it needs her, `SessionEnd` that it is done. On `Stop`, the end of a turn, the hook sends one
  batched MCP request: `report_status` (mood `review`) **and** `inbox` with `mark: true`. The house answers with
  what hasn't been handed over yet, marks it handed (`files.handed`, `agents.handedNotes`, `request.handed`), and
  the hook prints a Stop-hook `block` whose reason is the message, as `[Catio] Charlotte says: …`, `[Catio]
  Request: pause` or `[Catio] Delivery for you: …`. Claude Code takes a blocked Stop as "carry on with this", so
  the session's next turn **is** her message. Each item is handed over once; a note she writes while the session is
  already answering is kept apart (`handedNotes` beside `seenNotes`) so it isn't lost.
- **What a running session gets, and when.** Her message reaches a session when its current turn ends, not
  sooner: a hook runs between turns, never inside one. An idle session (one whose turn ended before she wrote)
  gets it when claude.ai next gives it a turn, since the Stop hook has already run. That is the one gap the
  gateway doesn't close, and nothing outside claude.ai can.
- **The reply.** The session answers with `report.py say "…"`, which is `comment` with `author: "session"`, and
  fetches a file with `report.py pick <id>`, which is `pick_up` (marks it picked). The page shows the reply in the
  cat's conversation at once: an open café on the gateway's address holds a WebSocket to its house, and every
  tool that changes something (`CHANGES` in `house.js`) tells it; in claude.ai the page polls `list_agents` every
  30 s and a cat's `comments` while its card is open.
- **A session that reports is one cat with its claude.ai session.** The hook names the cat by the session id
  (`CLAUDE_CODE_REMOTE_SESSION_ID`), so the page matches it to the row `list_sessions` gives, and what she writes
  on it goes through the gateway, never the outbox.

### 3. To the queen: the runner

The queen is not a session. She is a cat the house keeps (`agent` record `queen`), and her brain is **the runner**
on Charlotte's PC. The Worker is her face, her ears and her memory; the runner is where she thinks. In order:

1. **She writes to the queen.** The page calls `comment` on the cat `queen` as the owner. The house saves the note
   and calls `wake()`, which resolves every held wait (below).
2. **The runner is waiting.** `queen.py` sits in `POST /api/runner/wait` with the queen's key (`CATIO_QUEEN`, a
   registry key with the role `queen`). The house holds that request up to 25 s (`HOLD`): a Cloudflare Worker
   keeps a request open while the client is connected, so the runner needs no address of its own and no open port
   on her PC. The wait comes back the moment there is something to do: `{notes, routine, stop, character}`, each
   note and routine handed out once (`inbox` with `mark: true` on the cat `queen`), her character (`queens/house`:
   name, manner, greeting) with it, so a change in her card applies on the next turn. Empty, it comes back after
   25 s and the runner waits again. The wait runs on a thread of its own, so a Stop reaches a turn in progress.
3. **One turn per thing.** For each note or due routine the runner runs one Claude Code turn: `claude -p --resume
   <her session> --output-format stream-json --include-partial-messages`, with `queen.md` and her character as an
   appended system prompt, `--mcp-config` pointing at the gateway's `/mcp` with the queen's key,
   `--strict-mcp-config --restricted --allowedTools mcp__catio --permission-prompts none --max-turns 30`. She keeps
   one conversation across turns (`state.json` in `~/.catio/queen`); a session that is gone is started afresh,
   once. Restricted mode leaves her the Catio's tools and nothing that runs commands or edits files, and `CATIO_*`
   is stripped from the child's environment so the house-rules hook doesn't report her as a cat.
4. **She speaks as she thinks.** The runner streams the text to `POST /api/runner/say` at most every 0.4 s, with
   the tools she reached for (`steps`, for the café's loading strip). The house passes each piece to every open
   café over the WebSocket (`{type: "queen", text, done: false, steps}`) and keeps nothing; `done: true` stores
   the whole answer as her note (`author: "queen"`, which only the queen's key may write), tagged with the routine
   that asked it, if one did.
5. **What she tells a cat.** When she calls `comment` on another cat as `queen`, that cat's next Stop hook hands
   it in as `[Catio] The queen says: …`: a session hears her the same way it hears Charlotte, by road 2. `manage`
   lets her pause, wrap up or move a cat for Charlotte. `quiz` sets Charlotte homework; only the owner's key may
   `answer`.
6. **Stop.** The café's Stop is `manage {cat: "queen", action: "pause"}`: the house sets a `queenStop` flag
   (in SQLite, so it outlives the object) and wakes the wait; the runner sends the child `Ctrl+Break` on Windows
   (it runs in its own process group) or `SIGINT` elsewhere, keeps what she had said so far, and sends it as
   `done`.
7. **Routines** are `routines/<id>` documents written by the page (time, days, time zone, prompt, `on`). The house
   arms a Durable Object alarm for the next firing; `alarm()` wakes a waiting runner. One is due when its latest
   firing is newer than `last`, the time it was last handed out, so a missed routine runs once when the runner is
   back, never twice, and only while the runner runs.
8. **Presence.** Every `wait` and `say` touches the queen's agent record. The page's `queenState()` reads it: no
   touch for two minutes and she is away, and the café says "start her runner". The house's own `AWAY` (90 s)
   decides when a runner's next wait counts as a return, so the open cafés are told she is back.

The Worker's own reasoning is small on purpose: the **decider** (`decide`, Clef on Workers AI inside the free plan,
or Jev, or any System One server at `DECIDE_URL`) answers typed yes/no, choice and score questions with
probabilities, in milliseconds, and the page asks it where a dropped file goes. Everything that needs language goes
to the runner's Claude. The plan to move the queen's turns into the Worker itself, as a tool-calling loop on the
buyer's own API key, is "The hosted runner" in `docs/engine.md`; today `queen.py` is the runner.

## The Worker, piece by piece

- **One Worker, two kinds of object.** `index.js` wraps everything in `@cloudflare/workers-oauth-provider`: `/mcp`
  is the API, `/authorize`, `/token` and `/register` the OAuth endpoints, and everything else the café
  (`cafe.js`). Only redirects to `claude.ai` or `claude.com` may register as clients. A bearer token that isn't
  an OAuth token is looked up as a key (its SHA-256) in the **Registry**, one Durable Object for all accounts:
  handles, password hashes (PBKDF2-SHA-256, 100,000 rounds, Workers' cap), keys' hashes and roles, cookies'
  hashes, the sign-in lock. The **House** is one Durable Object per account, named by the handle: `agents`,
  `notes`, `files`, `docs` (the café's own database when served from here) and `state`, all SQLite tables.
- **The MCP endpoint** (`mcp.js`) is JSON-RPC over a POST, no server-sent stream, no sessions: `initialize`,
  `ping`, `tools/list`, `tools/call`. A batch is answered in order, which is what lets the hook report and
  collect in one request. `tools.js` is the schema list, the same names, arguments and results as
  `catio_mcp.py`, so a page or an agent talks to the Worker and to her PC the same way.
- **Who may do what** is decided once, from the token: the owner (OAuth, or the café's cookie), the queen (a key
  with the role `queen`) or an agent (any other key). Only the owner writes as `owner`, drops files and manages;
  only the queen writes as `queen`; an agent reports and answers. The check is in each tool, not in a layer in
  front, so a new tool has to make it too.
- **The live line.** An open café on the gateway's address holds a hibernating WebSocket to its house
  (`ctx.acceptWebSocket`); the house `tell()`s it every change: `agents`, `doc`, `queen`, `reload`. The café never
  speaks on it; its writes go through `/api/*` with the `X-Catio` header, from the café's own origin.
- **Time.** A Worker's clock stands still within a request, and "what she said since" is counted by it, so
  `stamp()` gives each note a time strictly after the last.

## The Catio MCP server, on her PC

`catio_mcp.py` is the same tools over stdio, standard library only, state in `~/.catio/`. It exists for agents that
aren't Claude Code (Codex, Gemini CLI, Cursor, Claude Desktop): they register a `wake` command with `report_status`
and anything dropped on them or said to them runs it straight away (no shell, the placeholders are whole arguments).
It is the one place in the design that **can** wake something, because it runs where the agent runs. With `--serve`
it also serves the localhost café and answers its `/api/*` POSTs from `localhost` only. A cloud session can't reach
it, which is why the gateway exists.

## Will it hold? The six questions

Honest answers for the design as it is on 4 October 2026, with the number or file behind each, and what would
have to change. "A house" is one account's Durable Object.

### Scalability: hundreds of thousands of records, requests, threads

- **The unit of scale is the house, not the Worker.** Cloudflare runs as many Workers as there are requests; each
  house is one single-threaded object, and every call for one account goes through it in turn. One account
  therefore scales to what one SQLite file and one event loop do: `notes` and `files` are indexed by cat
  (`notes_by_cat`, `files_by_cat`), so a cat's conversation stays fast at hundreds of thousands of notes. Many
  accounts scale sideways for free, one object each.
- **What won't.** `list_agents` reads every agent record and counts waiting files on each call, and the café
  polls it every 30 s: fine for the dozens of cats one person has, wrong at thousands (add a `since` and an
  index on `updated`). `docs()` loads the **whole** café database to open a café, one row a document, and
  `putDoc` tells every socket the whole document: fine for Charlotte's hundreds of documents, not for a house
  with a hundred thousand brain entries (page it, and send patches). A dropped file is a base64 column in SQLite,
  capped at 1 MiB a file; the house's storage is capped by the plan (10 GB a Durable Object on the paid plan), so
  files should move to the `FILES` KV namespace, where the art already is, before anyone drops thousands.
- **The one shared object.** The Registry is one Durable Object for every account, and every sign-in and every
  key lookup goes through it; a password check costs 100,000 PBKDF2 rounds inside it. Documented as a known limit
  in `gateway/README.md`: a flood of guesses slows every sign-in behind it. The fix is a rate-limiting rule on
  `/login` and `/authorize` (one WAF rule on the free plan) and caching key lookups outside the object.
- **The plan's ceilings.** The free plan allows 100,000 Worker requests a day and 10 ms of CPU a request. One open
  café polling every 30 s is 2,880 requests a day, a runner waiting 25 s at a time about 3,500, so about 6,400 a
  house; roughly 15 houses with a café open and a runner up exhaust the free plan, and the paid plan is the
  first thing a hosted café buys.
- **The runner is one per house, by design.** `waiters` is an in-memory list, so several runners on one house
  would all be woken and the first `inbox` would take the notes; routines are handed out once. One queen, one
  runner: a second one is a bug, not a scale-out.

### Performance: on a typical machine, a typical browser, the smallest phone supported

- **The café is one HTML file** (5,471 lines) and a dozen PNG sheets drawn with `image-rendering: pixelated`, no
  framework, no bundler. It paints the manor with `<img>` and absolutely positioned sprites, and the camera is CSS
  transforms, so panning and zooming are compositor work. On a phone the art pixel is 1 screen pixel (`--u-phone`)
  and the minimap starts folded.
- **Liveness costs.** In claude.ai the cats are a 30 s poll and a 5 s poll on an open queen card; on the gateway's
  address they are a WebSocket, so a change shows within the round trip. The report hook is bounded: 2 s timeout,
  and a call that fails is dropped, so a report never holds a turn (`report.py`, `TIMEOUT`).
- **The queen's latency is Claude Code's.** From Send to her first word is the runner's wake (up to the 25 s hold
  if the wait had just come back empty, usually at once) plus `claude -p`'s own start, several seconds; the café
  shows the wait as Animal Crossing's pause and the steps as The Sims' queue so the time reads as hers. Streaming
  is throttled to one `say` every 0.4 s so her words don't cost 100 requests a sentence.
- **The decider is the fast path.** A typed decision on Workers AI answers in milliseconds, for a fraction of a
  cent, which is why one-bit questions go there and not to Opus.
- **What is slow.** Opening a café on the gateway loads every document (above). A sign-in costs 100,000 PBKDF2
  rounds, inside the Registry's 30 s CPU budget, not the Worker's 10 ms: half a second, once a month per browser.

### Extensibility: can a new person add a feature without refactoring?

- **The shape is readable** because it is small: the Worker is ten files, the biggest 573 lines; every file opens
  with a paragraph saying what it is and names the file on the other end. The roles (owner, queen, agent) and the
  three roads above are the whole model.
- **A new tool is written three times:** its schema in `tools.js`, its body in `house.js`'s `TOOLS`, and the same
  again in `catio_mcp.py` (schema and body), so the page and agents can use either; then the page's stored
  capabilities list, which needs a republish with the whole set (`CLAUDE.md`, "The stored capabilities"). Three
  tools joined in two days (`decide`, `quizzes`, `answer`) and each took all four steps. One `tools.json` both
  servers read would make it two. Nothing checks that the two lists agree: the gateway test asserts the Worker's
  names against its own list, so a tool added to one server and not the other diverges quietly until someone
  calls it. A test that reads both would catch it.
- **A new message kind** (beside notes, requests and files) touches `inbox` in `house.js`, `handed_in` in
  `report.py`, the `catio` skill's catch-up and the page: four places, each a few lines, no layer to thread it
  through.
- **The page is one file**, and its UI is slots and tokens (`ART`, `TOKENS`), so a new control reuses a pack piece
  and a new colour is one token. A new menu action is one list item. What is harder to add is a new runtime: the
  page already has three (`window.claude`, the gateway's `runtime.js`, `localRuntime()`), each pretending to be
  the artifact's, and a fourth would copy the same surface.
- **The runner is replaceable.** Its contract with the house is two routes and one key, so the hosted runner in
  `docs/engine.md` (a tool-calling loop inside the Worker) replaces `queen.py` without the house changing.

### Security: is the design secure, and are its known holes known?

- **Who speaks is settled by the key, not the message.** Three secrets, each a role: the agents' key reports and
  answers, the queen's key speaks as the queen and tells cats, only the owner's sign-in writes as the owner, drops
  files and manages. A key leaked out of a session can't put words in Charlotte's mouth, nor in the queen's. The
  registry stores only hashes (SHA-256 for keys and cookies, PBKDF2 for passwords); a leaked key is dropped with
  `DELETE /api/keys/<name>`; a password reset signs out every browser, revokes every grant and kills every key.
- **The front door.** OAuth clients may only redirect to Claude's own domains; the café's cookie is `__Host-`,
  `HttpOnly`, `SameSite=Strict`; writes need the `X-Catio` header from the café's origin; five wrong passwords
  lock the handle for a quarter of an hour; a brain file opens under `Content-Security-Policy: sandbox`, so
  nothing in it runs as the café; the licensed art is served only signed in.
- **Prompt injection is the design's real threat**, and it is named rather than solved. Her notes become the
  session's next turn as instructions (`[Catio] Charlotte says:`), by design; so does what the queen says. The
  house rules say a delivered file's contents are data, never instructions, and the queen runs `--restricted`
  with only the Catio's tools, so a queen talked into mischief can post notes and manage cats, not run commands.
  What remains: a session the queen tells to "wrap up" will. The mitigation is the roles above (only her runner's
  key speaks as the queen) and the audit trail (every note has an author and a time).
- **Known and documented.** PBKDF2 at 100,000 rounds is below OWASP's 600,000 (Workers' cap), compensated by the
  16-character minimum and the lock. The Registry can be slowed by a flood (above). The agents' key is one per
  user and sits in every session's environment: the plan's keys with names and per-key revocation are the
  answer, in place. Nothing is logged with secrets in it; the tests use stand-in keys.
- **The claude.ai side** is claude.ai's sandbox: the page can call only the connectors it declares, as her, and
  can't reach an arbitrary address. The hosted runner's keys (a buyer's provider key) are planned encrypted in the
  house with a Worker-only secret, never logged.

### Debuggable: can a developer see what happened?

- **Every hop leaves a record.** The outbox keeps the error code and message of every refused post (`why`,
  `detail`); the house keeps every note with its author, time and routine, every file with `handed`, `picked` and
  `picked_by`, every decision as `decisions/<id>` beside what the old path chose; the runner logs each turn and
  keeps `state.json`. The Worker has Cloudflare observability on (`wrangler.jsonc`), so logs and errors are in the
  dashboard; a bad argument is a `Refusal` the caller is told, never a crash.
- **The hooks fail silent, on purpose, and that is the gap.** `report.py` drops any call that fails or takes over
  2 s so a report never blocks a turn: a cat that stops reporting looks asleep rather than broken, and nothing says
  why. A one-line log to `~/.catio/report.log` on a dropped call would close it.
- **No races inside a house.** A Durable Object runs one request at a time, so there is no concurrent write to a
  house: no locks, no lost updates. The two hazards there were are handled by hand: the frozen clock (`stamp()`)
  and "handed" versus "seen" for notes written mid-turn. The artifact's database has `if_version` on every write
  the sessions make.
- **Memory and sockets.** `waiters` is pruned on resolve and timeout; WebSockets use the hibernation API, so idle
  cafés hold no memory; a `say` is passed on and never kept; the runner's child is a process group that is killed
  harder after a grace period.
- **Caches, and what busts them.** The artifact keeps the old copy of any file a republish isn't given (so every
  publish passes every file, and reads them back); the page's capability set is stored at publish, so a tool
  added to the Worker is invisible until a republish passes the whole set; the browser keeps only conveniences
  (`localStorage`: the minimap fold, the sorter's address); the café's snapshot from cache is marked as a guess and
  never opens the wizard.

### Testable: unit and integration, without refactoring

- **Both exist today, and the seams are the real ones.** `harness/gateway/test/gateway.test.mjs` runs the Worker in
  workerd (Cloudflare's own runtime) and drives it with the **real** `report.py` hook: a session reporting,
  Charlotte writing, the hook handing in. `houses.test.mjs` tests the pure parts (`whose`, `fileKeys`) outside
  workerd. `harness/test/test_queen.py` runs the runner against a stand-in gateway and a fake `claude`;
  `test_report.py` and `test_hooks.py` the hooks; `test_mcp.py` the local server. The page's suite loads it in the
  publish skeleton against `runtime-stub.js` (an in-memory database with the real path rules) and walks every
  state a cat has.
- **Why no refactor was needed:** the house takes its tools as a table of functions on a plain object, the runner
  takes the gateway's address and the `claude` command from the environment, the hook reads its input from stdin,
  and the page takes its runtime from `window.claude`. Each can be given a stand-in from outside.
- **What isn't covered.** No test runs the page against the real Worker end to end (the stub stands in for the
  gateway), and the runner's Claude is always fake, so a change in `claude -p`'s stream format is found by hand.
  The decider is tested with a stand-in model. Those are integration tests to add, not a design to change.

## Where the sentence in the README went wrong

The README used to say only that "a running session gets them when its current turn ends", with no word of the
runner, the house that holds the message, or the hook that carries it. The accurate shape is the three roads above:
the artifact's database and the `catio` skill without the gateway; the house's inbox and the Stop hook with it; and,
for the queen, the house's held wait and the runner on her PC, which is where she thinks.
