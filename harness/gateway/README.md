# The Catio's gateway

The always-on hub every agent reports to, so the KittyChat Café knows who is working without asking claude.ai
for a list (claude.ai refuses the page's `list_sessions`, and the Routine that saved a copy stops at her weekly
limit). It is the shape OpenClaw's gateway has, built from what the Catio already had.

It is a Cloudflare Worker on the free plan, at `https://catio-gateway.<her subdomain>.workers.dev`. It needs no
server and no domain of her own. It speaks MCP at `/mcp`, with the same tools as `harness/mcp/catio_mcp.py`, and
keeps its cats, their conversations and the files waiting for them in one SQLite-backed Durable Object.

```
 Claude Code sessions ── report.py hook ──┐
 Codex, Gemini, Cursor… ── MCP + key ─────┼──►  catio-gateway (Cloudflare)  ◄── claude.ai: the "Catio" connector,
 her PC's sessions ── report.py hook ─────┘      /mcp, /authorize, /token        which the page reads as her
```

It has accounts (`src/registry.js`): each user has a handle, a password and a house of their own, and sees only
their own cats and café. Two kinds of caller, told apart by how they sign in:

- **A user, through claude.ai.** The gateway is a custom connector, signed in once with their handle and password
  (OAuth). They read every cat in their house, write as its owner, drop files and manage cats.
- **Agents and the sessions' hooks.** They send one of the user's agents' keys as a bearer token. They report,
  read and answer, but never as the owner: only the owner writes as `charlotte` (the owner's name on the wire),
  drops files and manages. So a key that leaks out of a session can't put words in her mouth to another one.

The first account is `charlotte`'s, made from the two secrets below the first time the gateway runs with accounts;
it is the admin, which uploads the café's art and creates the other accounts.

## Setting it up (once)

1. **Cloudflare.** Workers & Pages → Create → Import a repository → `charredlatte/Pretty-Project-Portfolio`.
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

   Never paste any of them into a chat.
3. **Claude's environments.** In a cloud session, open the environment menu in the session's title bar → Edit. In
   each environment her sessions use:
   - add two environment variables, `CATIO_URL` = the address above and `CATIO_TOKEN` = the agents' key;
   - under Network access, add `catio-gateway.<subdomain>.workers.dev` to the allowed domains;
   - install the house-rules plugin in its setup script (`harness/README.md`, *In cloud sessions*): the hook that
     reports is in it, and a cloud session doesn't install it by itself.

   On her PC, the same two variables go under `"env"` in `~/.claude/settings.json`, for local sessions.
4. **claude.ai.** Customize → Connectors → Add → Custom → Web. Name it `Catio`, with the URL `<address>/mcp`. A
   window opens on the gateway's sign-in page: type `CATIO_PASSWORD` and choose *Let it in*. Then open the
   connector and set its tools to **Always allow**. That setting is the one Claude Code Remote, being built in,
   doesn't have, and the reason the page's live read is refused today.
5. Tell Claude it's done. The page is then republished to read the `Catio` connector (docs/plan.md, phase 5).

To check: the address alone asks for her handle and password (the café's sign-in), so it says the Worker is up. Both sign-ins
say when `CATIO_PASSWORD` is missing. The key is right when an agent's call to `/mcp`
gets an answer instead of a 401 `invalid_token`. Once a session has started in an environment with the two
variables and the plugin, it is in `list_agents`.

## Accounts

- **Another account:** an admin, signed in to the café, `POST /api/users` with `{"id": "<handle>", "password":
  "<16+ characters>"}`: from the browser's console, `fetch("/api/users", {method: "POST", headers: {"X-Catio": "1",
  "Content-Type": "application/json"}, body: JSON.stringify({id: "…", password: "…"})}).then(r => r.json()).then(console.log)`.
  Never with a key: a key sits in every session's environment, and what a key can do, a leaked key can do. A
  handle is 2 to 31 lower-case letters, digits or dashes. The account gets a house named after it, and signs in
  to the café and the connector with that handle and password. There is no sign-up form yet.
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
- **Guessing:** five wrong passwords lock that handle for a quarter of an hour, at once or in a row; an
  impossible handle costs no hash. Known limit: every password check runs in the one registry object, so a
  flood of guesses at made-up handles slows every sign-in and key lookup behind it. A rate-limiting rule on
  `/login` and `/authorize` in Cloudflare (Security → WAF, one rule on the free plan) is the gateway's to add.
- **One house each:** cats, conversations, files and the café's documents are the house's; the licensed art is
  shared, uploaded by an admin.
- **The art's licences are personal.** The packs the café is drawn with allow personal use and no redistribution,
  so a café served to other people needs their own packs, or none (the page draws plain panels without them).

## The café on its own address

The gateway's own address is the KittyChat Café, the way OpenClaw's gateway serves its Control UI: the same page as
in claude.ai (`catio/index.html`), behind her password, with `cafe/runtime.js` standing in for what claude.ai gives a
page (`src/cafe.js` serves both).

- **Sign-in:** handle and password, with the same lock as the connector's (five wrong in a quarter of an hour). A
  browser stays signed in for a month (`__Host-catio`, `HttpOnly`, `SameSite=Strict`; only its hash is kept, in
  the registry).
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
  `queen`'s notes, each handed out once), a routine come due, a stop, and her character (`queens/house`: name,
  manner, greeting).
- `POST /api/runner/say` `{turn, text, done, routine}` streams her answer: every open café gets a `queen` push
  as she speaks, and `done` stores it as her note (author `queen`, with the routine that asked it).
- With her key on `/mcp`, the queen uses the same tools as everyone, as `queen`: she may `comment` as `queen`
  (a cat's hook hands it in as `[Catio] The queen says: …`), `manage` and `drop_file`, never write as `charlotte`.
  The agents' key may do none of it: the cats act on what she says.
- `manage {cat: "queen", action: "pause"}` (Stop in the café) ends the turn she is on.
- **Routines** are `routines/<id>` documents written by the café (`name`, `time`, `days`, `tz`, `prompt`, `on`,
  `last`). One is due when its latest firing is newer than `last`; the House's alarm wakes a waiting runner on
  time, and a missed one runs once when the runner is back.
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
- **Who writes.** Only Charlotte writes as `charlotte`; she and the queen's runner (as `queen`) drop files and
  manage cats.
- **`inbox` takes `mark`**, which returns only what hasn't been handed over yet and counts it as handed over.
  The server on her computer takes it too.
- **Sign-in.** Only Claude's connectors can register: a redirect to anywhere but `claude.ai` or `claude.com` is
  refused. Five wrong passwords lock that user's sign-in for a quarter of an hour. Passwords are kept as PBKDF2
  hashes (100,000 rounds, Workers' cap, computed in the registry object where the CPU budget allows it), keys and
  cookies as SHA-256 hashes, OAuth tokens as hashes too (`@cloudflare/workers-oauth-provider`), and a grant lives
  as long as claude.ai keeps refreshing it.

It costs nothing on the Workers free plan: 100,000 requests a day, against a few hundred.

## Working on it

```sh
cd harness/gateway
npm install
npm test     # wrangler dev in workerd, then claude.ai's sign-in, the tools and the hook, end to end
npx wrangler dev --var CATIO_TOKEN:<a test key> --var CATIO_PASSWORD:<a test password>
```

Session titles and notes are private. They live only in the Durable Object, never in this repo or its tests.
