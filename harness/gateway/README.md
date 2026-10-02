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

Two kinds of caller, told apart by how they sign in:

- **Charlotte, through claude.ai.** The gateway is a custom connector, signed in once with her password
  (`CATIO_PASSWORD`, OAuth). She reads every cat, writes as herself, drops files and manages cats.
- **Agents and the sessions' hooks.** They send the agents' key (`CATIO_TOKEN`) as a bearer token. They report,
  read and answer, but never as her: only she writes as `charlotte`, drops files and manages. So a key that leaks
  out of a session can't put words in her mouth to another one.

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
2. **Two secrets.** On the Worker, go to Settings → Variables and Secrets → Add, type *Secret*, under
   *Production*, then Deploy:
   - `CATIO_TOKEN`: the agents' key, 32 random characters or more.
   - `CATIO_PASSWORD`: a different one, the password she signs in with (16 characters or more). It goes into her
     password manager and nowhere else.

   Never paste either into a chat.
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

To check: the address alone asks for her password (the café's sign-in), so it says the Worker is up. Both sign-ins
say when `CATIO_PASSWORD` is missing. The key is right when an agent's call to `/mcp`
gets an answer instead of a 401 `invalid_token`. Once a session has started in an environment with the two
variables and the plugin, it is in `list_agents`.

## The café on its own address

The gateway's own address is the KittyChat Café, the way OpenClaw's gateway serves its Control UI: the same page as
in claude.ai (`catio/index.html`), behind her password, with `cafe/runtime.js` standing in for what claude.ai gives a
page (`src/cafe.js` serves both).

- **Sign-in:** `CATIO_PASSWORD`, with the same lock as the connector's (five wrong in a quarter of an hour). A
  browser stays signed in for a month (`__Host-catio`, `HttpOnly`, `SameSite=Strict`; only its hash is kept).
- **Her data:** the café's documents (rooms, renames, adopted chats, looks, queens, the brain, notes) live in the
  house (`docs`), and every change reaches an open café over a WebSocket at once. Her browser writes them only with
  the `X-Catio` header and from the café's own address.
- **Files:** the brain's files and the licensed art live in the `FILES` KV namespace. Art is served only once she is
  signed in, so the packs are never public; a brain file opens in a sandbox (`Content-Security-Policy: sandbox`),
  where nothing in it can run as the café.
- **Moving in (once):** `CATIO_URL=… CATIO_TOKEN=… python3 harness/gateway/cafe/move-in.py docs.json` uploads the art
  from a checkout that has it (`catio/art/licensed`, never committed) and imports the claude.ai artifact's database,
  which Claude exports with `ArtifactData`. The import is taken only while the café is empty. Re-run it without
  `docs.json` after rebuilding the art.
- **The sessions:** the cats come from the gateway, live, and from Claude's saved copy (`snapshot/sessions`). What
  only claude.ai can do says so: opening a session's full conversation, pausing, archiving, renaming it, starting
  one, and posting into a session that doesn't report. A session that reports is told through the gateway.
- **Not here (yet):** the file sorter (Claude in claude.ai) and starting sessions; the runner (docs/plan.md, phase 6)
  brings the second.

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
- **Who writes.** Only Charlotte writes as `charlotte`, drops files and manages cats.
- **`inbox` takes `mark`**, which returns only what hasn't been handed over yet and counts it as handed over.
  The server on her computer takes it too.
- **Sign-in.** Only Claude's connectors can register: a redirect to anywhere but `claude.ai` or `claude.com` is
  refused. Five wrong passwords lock the sign-in for a quarter of an hour. Tokens are stored only as hashes
  (`@cloudflare/workers-oauth-provider`), and a grant lives as long as claude.ai keeps refreshing it.

It costs nothing on the Workers free plan: 100,000 requests a day, against a few hundred.

## Working on it

```sh
cd harness/gateway
npm install
npm test     # wrangler dev in workerd, then claude.ai's sign-in, the tools and the hook, end to end
npx wrangler dev --var CATIO_TOKEN:<a test key> --var CATIO_PASSWORD:<a test password>
```

Session titles and notes are private. They live only in the Durable Object, never in this repo or its tests.
