# The Catio's gateway

The always-on hub every agent reports to, so the KittyChat Café knows who is working without asking claude.ai
for a list (claude.ai refuses the page's `list_sessions`, and the Routine that saved a copy stops at her weekly
limit). It is the shape OpenClaw's gateway has, built from what the Catio already had.

It is a Cloudflare Worker on the free plan, at `https://catio-gateway.<her subdomain>.workers.dev`. It needs no
server and no domain of her own. It speaks MCP at `/mcp`, with the same tools as `harness/mcp/catio_mcp.py`, and
keeps its cats, their conversations and the files waiting for them in one SQLite-backed Durable Object.

```
 Claude Code sessions ── report.py hook ──┐
 Codex, Gemini, Cursor… ── MCP + key ─────┼──►  catio-gateway (Cloudflare)  ◄── claude.ai: the "CATIO" connector,
 her PC's sessions ── report.py hook ─────┘      /mcp, /authorize, /token        which the page reads as her
```

It has accounts (`src/registry.js`): each user has a handle, a password and a house of their own, and sees only
their own cats and café. Two kinds of caller, told apart by how they sign in:

- **A user, through claude.ai.** The gateway is a custom connector, signed in once with their handle and password
  (OAuth). They read every cat in their house, write as its owner, drop files and manage cats.
- **Agents and the sessions' hooks.** They send one of the user's agents' keys as a bearer token. They report,
  read and answer, but never as the owner: only the owner writes as `owner` (`charlotte` is still taken as the
  owner's old name, and stored as `owner`),
  drops files and manages. So a key that leaks out of a session can't put words in her mouth to another one.

The first account is `charlotte`'s, made from the two secrets below the first time the gateway runs with accounts;
it is the admin, which uploads the café's art, creates the other accounts and invites people to sign up.

## Setting it up (once)

1. **Cloudflare.** Workers & Pages → Create → Import a repository → `charredlatte/Pretty-Project-Portfolio`
   (on a gateway that isn't hers, your fork of it).
   - Name it `catio-gateway`. Cloudflare fills in the repo's name, `pretty-project-portfolio`: replace it, because
     the Worker's name must match `wrangler.jsonc` or later deploys fail. A Worker made under the wrong name is
     simplest deleted (Settings → Danger zone) and imported again; delete its leftover KV namespace too.
   - Set the root directory to `harness/gateway` and the production branch to `main`. Leave the build command
     empty, and keep the deploy command as `npx wrangler deploy`.
   - Deploy. The first deploy creates the KV namespace and the Durable Object. Its address is on the Worker's page:
     `https://catio-gateway.<subdomain>.workers.dev`. If Cloudflare asks for a workers.dev subdomain, pick one.
   - From then on every merge to `main` redeploys it.
2. **Three secrets.** On the Worker, go to Settings → Variables and Secrets → Add, type *Secret*, under
   *Production*, then Deploy:
   - `CATIO_TOKEN`: the agents' key, 32 random characters or more.
   - `CATIO_PASSWORD`: a different one, the password she signs in with (16 characters or more). It goes into her
     password manager and nowhere else.
   - `CATIO_QUEEN`: the queen's runner's own key (below), 32 random characters or more; also on the PC that runs
     her.
   - `CATIO_HANDLE`, on a gateway that isn't hers: the handle you sign in with. Unset, the first account is
     `charlotte`, whatever your own name is.

   Never paste any of them into a chat. `CATIO_PASSWORD` and `CATIO_HANDLE` make the first account once, on the first
   request after the deploy: changing either afterwards changes nothing, so sign in with the ones it was made from. To
   start again with no accounts, import the repository again as a new Worker and set `name` in `wrangler.jsonc` to
   that Worker's name: Workers Builds refuses a build when the two differ.
3. **Claude's environments.** In a cloud session, open the environment menu in the session's title bar → Edit. In
   each environment her sessions use:
   - add two environment variables, `CATIO_URL` = the address above and `CATIO_TOKEN` = the agents' key;
   - under Network access, add `catio-gateway.<subdomain>.workers.dev` to the allowed domains;
   - install the house-rules plugin in its setup script (`harness/README.md`, *In cloud sessions*): the hook that
     reports is in it, and a cloud session doesn't install it by itself.

   On her PC, the same two variables go under `"env"` in `~/.claude/settings.json`, for local sessions.
4. **claude.ai.** Customize → Connectors → Add → Custom → Web. Name it `CATIO`, with the URL `<address>/mcp`: the
   name matters, because the page looks for a connector called `CATIO` exactly. A window opens on the gateway's
   sign-in page: type the handle (`CATIO_HANDLE`, or `charlotte` when it is unset) and `CATIO_PASSWORD`, and choose
   *Let it in*. Then open the connector and set its tools to **Always allow**. That setting is the one Claude Code
   Remote, being built in, doesn't have, and the reason the page's live read is refused today.
5. Tell Claude it's done. The page is then republished to read the `CATIO` connector (docs/plan.md, phase 5).

To check: the address alone asks for her handle and password (the café's sign-in), so it says the Worker is up. Until
there is an account, both sign-ins show the setup's warning lights instead of a form: each of the four secrets as this
Worker sees it (set, missing, too short, not a handle; never its value), the handle the account will have, and what to
fix. The key is right when an agent's call to `/mcp`
gets an answer instead of a 401 `invalid_token`. Once a session has started in an environment with the two
variables and the plugin, it is in `list_agents`.

## Accounts

- **Sign-up, by invite:** an admin, signed in to the café, opens `/invite` on the gateway's address and presses
  **Make an invite**. The link it shows (once: the registry keeps only its hash) goes to the person invited, who
  opens it, picks a handle and a password at `/signup`, and is signed in to a café of their own: first a page that
  shows their first agents' key once, the café's address for `CATIO_URL` and the plugin's two install lines, then
  **Open my café**. An invite works
  once and lapses after a week; **Take back unused invites** on the same page cancels the ones still out. A
  signed-up account is never an admin. A refused sign-up (a taken handle, a short password, two passwords that
  differ) doesn't spend the invite; two sign-ups with one invite at once let one in. There is no open sign-up:
  everyone with an account gets a house on the gateway's Worker, which is hers to pay for. **The same link works for
  their AI:** the sign-up page says what to do, and a `POST /signup` with JSON `{"invite", "handle", "password"}`
  makes the account and answers `{"handle", "key", "mcp"}`, its first agents' key shown once, for the person's
  sessions and agents (`CATIO_TOKEN`, or the MCP server's bearer).
- **Another account:** an admin, signed in to the café, `POST /api/users` with `{"id": "<handle>", "password":
  "<16+ characters>"}`: from the browser's console, `fetch("/api/users", {method: "POST", headers: {"X-Catio": "1",
  "Content-Type": "application/json"}, body: JSON.stringify({id: "…", password: "…"})}).then(r => r.json()).then(console.log)`.
  Never with a key: a key sits in every session's environment, and what a key can do, a leaked key can do. A
  handle is 2 to 31 lower-case letters, digits or dashes. The account gets a house named after it, and signs in
  to the café and the connector with that handle and password. An invite (above) lets them choose both themselves.
- **A key:** from a signed-in café, `POST /api/keys` with `{"name": "laptop"}` (the page sends `X-Catio: 1`;
  until it has a button, the browser's console does: `fetch("/api/keys", {method: "POST", headers: {"X-Catio": "1",
  "Content-Type": "application/json"}, body: JSON.stringify({name: "laptop"})}).then(r => r.json()).then(console.log)`).
  The key is in the answer once, and the registry keeps only its hash. It goes in `CATIO_TOKEN` wherever that
  user's sessions and agents run. Names are unique per user. `GET /api/keys` lists them by name,
  `DELETE /api/keys/<name>` kills one: a leaked key is dropped that way, the `bootstrap` key included, and it
  stays dropped.
- **A forgotten or leaked password:** an admin, signed in to the café, resets it with `PUT /api/users/<handle>`
  and `{"password": "…"}` (the same `fetch` shape), which signs that user's browsers out, takes back every
  connector they let in (their OAuth grants), kills every key they minted, and lets a locked-out user back in.
  Whoever had the old password is out everywhere; the user mints new keys. The handle `house` is kept: it names
  the first house.
- **Guessing:** wrong passwords make a sign-in wait for a quarter of an hour, counted by the address they came from
  (`CF-Connecting-IP`): five at one handle, or twenty at any handles, lock that address out, so a stranger who knows
  a handle can't lock its owner out. A hundred at one handle from anywhere lock everyone, the backstop against a
  spread-out guesser. An impossible handle costs no hash. Known limit: every password check runs in the one
  registry object, so a flood of guesses from many addresses slows every sign-in and key lookup behind it. A
  rate-limiting rule on `/login` and `/authorize` in Cloudflare (Security → WAF, one rule on the free plan) is the
  gateway's to add.
- **One house each:** cats, conversations, files and the café's documents are the house's. The licensed art,
  uploaded by an admin, is served to the first house alone (`/art/licensed/*` is a 404 to anyone else).
- **The art's licences are personal.** The packs the café is drawn with allow personal use and no redistribution,
  so another account's café is drawn without them (the page draws plain panels), until it has art of its own.

## The café on its own address

The gateway's own address is the KittyChat Café, the way OpenClaw's gateway serves its Control UI: the same page as
in claude.ai (`catio/index.html`), behind her password, with `cafe/runtime.js` standing in for what claude.ai gives a
page (`src/cafe.js` serves both).

- **Sign-in:** handle and password, with the same lock as the connector's (above). A
  browser stays signed in for a month (`__Host-catio`, `HttpOnly`, `SameSite=Strict`; only its hash is kept, in
  the registry), or until `POST /logout` ends it.
- **Her data:** the café's documents (rooms, renames, adopted chats, looks, queens, the brain, notes) live in the
  house (`docs`), and every change reaches an open café over a WebSocket at once. Her browser writes them only with
  the `X-Catio` header and from the café's own address.
- **Files:** the brain's files and the licensed art live in the `FILES` KV namespace. Art is served only once she is
  signed in, so the packs are never public; a brain file opens in a sandbox (`Content-Security-Policy: sandbox`),
  where nothing in it can run as the café.
- **Moving in (once):** `CATIO_URL=… CATIO_TOKEN=… python3 harness/gateway/cafe/move-in.py docs.json` uploads the art
  from a checkout that has it (`catio/art/licensed`, never committed; an admin's key) and imports the claude.ai
  artifact's database, which Claude exports with `ArtifactData`, into the key's own house. The import is taken only
  while that café is empty. Re-run it without `docs.json` after rebuilding the art.
- **The sessions:** the cats come from the gateway, live, and from Claude's saved copy (`snapshot/sessions`). What
  only claude.ai can do says so: opening a session's full conversation, pausing, archiving, renaming it, starting
  one, and posting into a session that doesn't report. A session that reports is told through the gateway.
- **Not here (yet):** the file sorter (Claude in claude.ai) and starting sessions.

## The queen and her runner

The queen of the house is the cat in the entrance hall that Charlotte talks to, like a character in a game: she
speaks or types to her in the café, and the queen answers aloud, looks after the cats for her (who needs her, what
first, the short version), tells them things and manages them. Her brain is `harness/runner/queen.py`, on
Charlotte's own PC (`harness/runner/README.md`), holding **the queen's key**: a key in the registry whose role is
`queen`. For the first account it is the `CATIO_QUEEN` secret, kept in step with it at every start (adding or
changing the secret is a deploy away; removing it retires the key). Any account can mint one from its signed-in
café instead, `POST /api/keys {"name": "pc", "role": "queen"}` (shown once; no form for it yet). Each account's
queen runner acts in that account's house:

- `POST /api/runner/wait` is held up to 25 seconds and comes back with what Charlotte said to her (the cat
  `queen`'s notes, each handed out once), a routine come due, a stop, her character (`queens/house`: name,
  manner, greeting), and `homework`: the open quizzes counted by kind (`{litterbox: 2, decision: 1}`), which her
  runner says on her own desktop when it grows.
- `POST /api/runner/say` `{turn, text, done, routine, steps}` streams her answer: every open café gets a `queen` push
  as she speaks, and `done` stores it as her note (author `queen`, with the routine that asked it). The runner says
  once as soon as she is up (empty `text`), and again each time she reaches for a tool: `steps` is the last twelve
  `{tool, cat, action}` this turn, which the café's loading strip names. They are passed on, never kept.
- With her key on `/mcp`, the queen uses the same tools as everyone, as `queen`: she may `comment` as `queen`
  (a cat's hook hands it in as `[Catio] The queen says: …`), `manage` and `drop_file`, never write as `owner`.
  The agents' key may do none of it: the cats act on what she says.
- `manage {cat: "queen", action: "pause"}` (Stop in the café) ends the turn she is on.
- **Homework.** `quiz` (the queen, or Charlotte) sets Charlotte a quiz to unblock a cat: a title, `for` the cat, 1 to
  5 questions with concrete options or a written answer, kept as `quizzes/<id>` documents; `quizzes` lists the open
  ones; `answer` (Charlotte only) hands one in, posts her answers to the cat as her words (`Homework handed in: …`,
  through its hook) and tells the queen.
- **Routines** are `routines/<id>` documents written by the café (`name`, `time`, `days`, `tz`, `prompt`, `on`,
  `last`). One is due when its latest firing is newer than `last`; the House's alarm wakes a waiting runner on
  time, and a missed one runs once when the runner is back. The gateway keeps `handed` (when it went out), and
  `finished` once the runner's answer to it is done; a firing handed out and never finished goes out once more
  after ten minutes (`retried`).
- `list_agents` gives every cat its `said`, the last thing its session or agent said: the café shows a cat
  carrying it to the queen, and her card lists it.

## How a session uses it

`harness/hooks/report.py`, in the house-rules plugin, reports the session on SessionStart and UserPromptSubmit
(busy), Notification (needs her), Stop (review) and SessionEnd (done). Without `CATIO_URL` and `CATIO_TOKEN` it
does nothing; a call that fails or takes over two seconds is dropped. Its cat's id is the claude.ai session id
(`CLAUDE_CODE_REMOTE_SESSION_ID`), so the page can match it with the session it lists.

What she sends reaches a session when its turn ends: the Stop hook hands in her notes, a pause or wrap-up, and
files, once each, and the session carries on with them (the `catio` skill). It answers with
`report.py say "…"` and fetches files with `report.py pick <id>`. An idle session can't be woken from outside
claude.ai, so a message to one waits for its next turn.

## Other agents

Any MCP client that speaks Streamable HTTP and can send a header: the URL `<address>/mcp`, with
`Authorization: Bearer <CATIO_TOKEN>`. Codex, in `~/.codex/config.toml`:

```toml
[mcp_servers.catio]
url = "https://catio-gateway.<subdomain>.workers.dev/mcp"
bearer_token_env_var = "CATIO_TOKEN"
```

Then tell the agent, as for the local server: read `house_rules`, call `report_status` when you start, need her
or finish, and check `inbox` between tasks.

## How it differs from `catio_mcp.py`

- **Wake commands.** It can't run commands, so a `wake` is ignored: an agent finds what's waiting in `inbox`.
- **Files** are capped at 1 MiB. A free Worker gets 10 ms of CPU a request, so bigger files go through the brain.
- **Who writes.** Only the owner writes as `owner`; the owner and the queen's runner (as `queen`) drop files and
  manage cats.
- **`inbox` takes `mark`**, which returns only what hasn't been handed over yet and counts it as handed over.
  The server on her computer takes it too.
- **Sign-in.** Only Claude's connectors can register: a redirect to anywhere but `claude.ai` or `claude.com` is
  refused. Wrong passwords lock the guessing address out for a quarter of an hour (see Guessing). Passwords are kept as PBKDF2
  hashes (100,000 rounds, Workers' cap, computed in the registry object where the CPU budget allows it), keys and
  cookies as SHA-256 hashes, OAuth tokens as hashes too (`@cloudflare/workers-oauth-provider`), and a grant lives
  as long as claude.ai keeps refreshing it.

It costs nothing on the Workers free plan: 100,000 requests a day, against a few hundred.

## Decisions: the `decide` tool

The café has questions whose answer was always one bit or one label: which cat a dropped file belongs to, whether a
task is easy enough for a small cat, who needs her first. `decide` (`src/decide.js`) hands them to a System One
model, which takes a *state* (text or JSON) and named typed questions, and returns a probability for every allowed
answer in milliseconds, with no prose to parse:

- `noul`: yes/no, the probability of yes;
- `choice`: `criteria: {option: what it means}`, the chosen option, a probability each and a confidence;
- `score`: `criteria: [ordered levels]`, a probability-weighted score.

Where it is answered is one switch, none of it required:

| | |
|---|---|
| nothing set | `@cf/cloudflare/clef-flash` through the Worker's `AI` binding: Cloudflare's own System One model, open weights, inside the free plan's 10,000 neurons a day |
| `DECIDE_MODEL` | another Workers AI model id: `@cf/cloudflare/clef` (27B), or `typesafe/jev`, Jev itself, paid from prepaid AI Gateway credits |
| `DECIDE_URL` (+ `DECIDE_KEY`) | any server speaking the System One API (`POST /v1/systemone`): `laya-serve` on a machine of hers, or Jev's own endpoint |

Anyone in the house may ask. `preset: "easy"` asks the six yes/no questions of the easy-task rubric
(`docs/delegation.md`) about a task's text. With `kind` (a label) and `old` (what the caller would have chosen
without it), the decision is kept as `decisions/<id>` in the house's documents with `agree`, the latest 500: the
observe log, read with `/api/db`, that says after a week whether to trust it. A refused question costs nothing; a
decider that doesn't answer in 8 s is a tool error, and the caller does what it did before.

The tests don't reach Workers AI (wrangler dev would need a Cloudflare sign-in for it): they run the Worker from a
copy of `wrangler.jsonc` without the binding, with `DECIDE_URL` pointing at a stand-in System One server in the test.

## Working on it

```sh
cd harness/gateway
npm install
npm test     # wrangler dev in workerd, then claude.ai's sign-in, the tools and the hook, end to end
npx wrangler dev --var CATIO_TOKEN:<a test key> --var CATIO_PASSWORD:<a test password>
```

Session titles and notes are private. They live only in the Durable Object, never in this repo or its tests.
