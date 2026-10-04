# MCPWay: the engine under the KittyChat Café

Written 4 October 2026, from Charlotte's asks that day: "Make the KittyChat Cafe into a real business plan. A
framework that sells a harness gateway product in the form of MCP, but have it your way. Drive with whatever model
you want and adapt to any environment", then: "like Cursor, but for every day people who need a coding environment
but don't know how to code. In other words, a business automation DIY kit that comes with maintenance and extra
features at flexible price points and allows for coworking."

The café is what buyers see and buy: they never need to hear "MCP". MCPWay is the engine underneath, and this page
is for the people who build on it: developers, kit makers, and the freelancers who set cafés up and maintain them.
The business plan, with its prices, figures and the legal setup, is private and lives in the café, not here.

## In plain words

MCPWay makes harnesses to order. Someone describes what they want automated, and gets back a working café: one
MCP gateway every agent reports to, house rules that keep the agents safe, a runner that does the work with the
model they choose, and kits that package one business automation each. The name follows PCBWay: PCBWay takes a
circuit design, quotes it, fabricates the board and assembles the parts. MCPWay takes a harness design (rules,
kits, which model drives what), deploys the gateway, and installs the pieces.

- **Any model.** Claude through Claude Code today. Anthropic, OpenAI or any OpenAI-compatible provider once the
  hosted runner is in (below), each on the buyer's own API key, paid to that provider directly: MCPWay never resells
  tokens. A small model makes typed decisions (yes/no, a choice, a score); it is the one model MCPWay runs itself,
  and it can be inside the price only once its model is locked (today any caller can pick a paid one).
- **Any environment.** Claude Code, Codex, Gemini CLI, Cursor, Claude Desktop, claude.ai, and the café on its own
  address in any browser. The owner's tools (handing in homework, dropping files, managing cats) need the owner's
  sign-in on the hosted gateway: claude.ai, Claude Desktop, or the café. The local stdio twin has no roles.
- **Any face.** The KittyChat Café is the face buyers get: a pixel-art manor where every task is a cat. A plain
  dashboard for teams can come from the same gateway (not built yet).

## What is already built

Most of it, run so far for one house: Charlotte's. Accounts with a house each are built; only an admin creates
them.

| Part | What it does | Where |
| --- | --- | --- |
| The gateway | A Cloudflare Worker that speaks MCP at `/mcp`, with the tools in `src/tools.js` | `harness/gateway/` |
| Accounts | A house per user, OAuth for claude.ai, hashed agent keys | `harness/gateway/src/registry.js`, `docs/accounts.md` |
| House rules | The Claude Code plugin whose hooks enforce the rules | `harness/rules.json`, `harness/hooks/` |
| The runner | Waits on the gateway and runs one model turn per message or routine, on the owner's computer | `harness/runner/queen.py` |
| The decider | Typed decisions from a small model, logged beside the old path | `harness/gateway/src/decide.js` |
| Other agents | The stdio twin of the gateway, for Codex, Gemini CLI, Cursor and Claude Desktop on the same machine; it has no roles, so whoever runs it acts as the owner | `harness/mcp/catio_mcp.py` |
| The café | The manor, the onboarding, the queen, served from the gateway behind a sign-in | `catio/index.html`, `harness/gateway/cafe/` |

The first kit exists too, outside this repository: Charlotte's shop runs its catalogue through agents that rename,
describe and fill in products, reviewed in a bulk editor before anything reaches Shopify. It needs packaging before
a stranger can install it.

Still missing for a product:

- self sign-up and a `/keys` page (phase 2 of `docs/accounts.md`; the key routes themselves are built);
- the hosted runner (below), so that nobody who buys a café has to run anything on their own computer;
- kits packaged so a stranger can install them;
- a plain face, for teams;
- metering, and a house several people can share (coworking);
- the Workers Paid plan (the free plan's KV allows 1,000 writes a day, a few dozen accounts) and a rate limit on
  sign-in, both named in `docs/accounts.md`;
- the decider's model locked for buyers (today any caller can pass `model`, a paid one included);
- each agent key kept to its own cats and files (today most agent tools take any cat's id, the queen's included;
  `comments` reads the owner's thread with the queen, `inbox` can mark her notes as handed over before her runner
  sees them, `pick_up` takes any file, `quizzes` returns every card, and `decide` writes to the decision log);
- features gated by plan (nothing checks a plan today: every account gets the quiz, homework and the decider);
- OAuth for clients other than Claude's (the gateway only lets claude.ai and claude.com connectors sign in);
- the licensed packs kept from other accounts (today one copy is served to every signed-in user,
  `harness/gateway/src/cafe.js`), and art Charlotte owns (`docs/drawing-plan.md`) before anyone else signs up.

## The hosted runner

Charlotte's choice of 4 October: for people who don't code, the runner moves off their computer and onto the
gateway, driven by an API key they paste in once. Nothing to install, it never sleeps, and any provider works.

- **How it runs.** The queen's turns become a tool-calling loop inside the gateway, calling Anthropic, OpenAI or
  OpenRouter with the buyer's key and the gateway's own tools. Kits that run scripts get a small Cloudflare
  container per house, started when needed. The Workers Paid plan includes 25 GiB-hours of container memory a
  month ([Cloudflare](https://developers.cloudflare.com/containers/pricing/)).
- **Why an API key, not a Claude subscription.** Since February 2026 Anthropic's terms allow a Pro or Max login only
  in Claude Code and claude.ai, never inside another product, and say products should use API keys
  ([Gigazine](https://gigazine.net/gsc_news/en/20260220-anthropic-third-party-block)). The hosted runner never asks
  for a subscription login.
- **The keys.** Encrypted in the buyer's own house with a secret only the Worker holds, never logged, revocable in
  one click. The setup asks buyers to set a monthly spend limit with their provider, and the café shows this
  month's spend.
- **The step it leaves.** Creating an API account is the one technical step a buyer still takes; the onboarding
  walks through it.

`harness/runner/queen.py` stays for self-hosters, who run it themselves with Claude Code.

## Your way, concretely

Any client that speaks MCP can report to the gateway today. A driver is what lets a runner start the work itself;
each needs a little code once, and after that choosing one is configuration.

| Driver | How it is driven | Status |
| --- | --- | --- |
| Hosted runner | A tool-calling loop in the gateway with the buyer's API key (Anthropic, OpenAI, OpenRouter); a container for kits that run scripts | To build: the path for buyers |
| Claude (Claude Code) | `claude -p` turns from the self-hosted runner, held in by a tool allowlist (`--allowedTools mcp__catio`), not by the hooks; every driver needs the same | Built, for the queen; other agents report but aren't run by it |
| OpenAI (Codex CLI) | `codex exec`: woken by `catio_mcp.py`'s `wake` command on the same machine; on the hosted gateway it checks its inbox | Joins today |
| Gemini (Gemini CLI) | `gemini -p`, the same way | Joins today |
| Typed decisions (yes/no, a choice, a score) | Workers AI on the gateway, or any server in `DECIDE_URL` | Built |

| Environment | What runs there |
| --- | --- |
| The hosted gateway | The café, the house, and (to build) the runner and kits' containers |
| A laptop or PC | A self-hosted runner talking to a gateway, any CLI; or the local café over `catio_mcp.py --serve`, which has no runner |
| A Raspberry Pi or a small VPS | A self-hosted runner, always on |
| Claude Code on the web | Cloud sessions with the rules plugin, reporting by hook |
| claude.ai, Claude Desktop | The gateway as a connector, signed in as the owner |
| Cursor, other MCP clients | The gateway with an agent key: report and use the agent tools, never act as the owner |

The code is open source under the AGPL (graphify, vendored, is Apache-2.0 with parts under MIT), and anyone can
self-host it; the art is not, and a clone shows the café without it. What is sold is not having to: the hosted
plans run the gateway, the house, the café and the runner for you, and the upper plan adds the paid features (the
brain's sorter, the litter box quiz and homework). On the gateway's café the sorter is the decider, once it is
switched from observing to sorting. The model bill stays the buyer's, paid to their provider. The gateway also
spends the operator's own Workers AI account (or `DECIDE_KEY`) on decisions, which is why the decider's model must
be locked.

## Who builds on it

The café's buyers are everyday people running a small business. The engine is for the people around them:

1. **Kit makers**, who package one business automation (a shop catalogue, invoices, email replies) for others to
   install, in a kits gallery, later.
2. **Freelancers who set cafés up and maintain them** for small businesses, under their own name.
3. **Developers** who self-host, or who run agents from more than one vendor: each vendor's dashboard shows its
   own sessions only, Claude Code's Agent View (May 2026) and `codex agents` (Codex v0.149, August 2026).

Besides the hosted plans, the café sells **Builds**, cafés made to order (the shop's "Set up for you"): lifetime
access and the course on setting one up yourself; an afternoon of Charlotte doing it with you is a higher price.
Sold from the day the store opens. The shop wireframes (`docs/kittychat-shop/`) predate this page: they have no
coworking or maintenance, and they ask buyers for claude.ai with Claude Code, which the hosted runner replaces
with an API key.

## Competition, for the engine

Every MCP gateway in the 2026 roundups governs which tools an agent may call. None shows sessions, keeps one inbox
of what is waiting on a person, or enforces rules on how agents work. MCPWay is the gateway agents report to,
whichever vendor runs them. For the café's buyers the competition is different, and is weighed in the private plan.

| Category | Examples | What they leave open |
| --- | --- | --- |
| Enterprise MCP gateways | Kong, Traefik, TrueFoundry, MintMCP | Any view of agents; a small team's budget |
| Developer MCP platforms | Composio, Smithery, Docker MCP Gateway | Rules, sessions, the human in the loop |
| Vendor dashboards | Claude Code's Agent View, `codex agents` | Other vendors, phones, rules |
| Third-party agent dashboards | rejoin, CodeAgentSwarm, AgentPulse, CLI Manager | Hosting, rules, a gateway other agents call |

Sources, read 4 October 2026: [Traefik's 2026 comparison](https://traefik.io/compare/best-mcp-gateways-2026),
[Composio's](https://composio.dev/content/best-mcp-gateway-for-developers),
[MintMCP on Docker's gateway](https://www.mintmcp.com/blog/docker-mcp-gateway-alternatives),
[Agent View (MindStudio)](https://www.mindstudio.ai/blog/claude-code-agent-view-manage-multiple-agents-3),
[`codex agents`](https://codex.danielvaughan.com/2026/08/31/codex-agents-dashboard-v0149-multi-agent-session-management/).

## The name

Not settled. [mcpway](https://github.com/drvova/mcpway) is already an MIT-licensed Rust tool that runs MCP stdio
servers over SSE, WebSocket, HTTP and gRPC (0.2.1, 25 May 2026, [docs.rs](https://docs.rs/crate/mcpway/0.2.1)):
same word, same protocol. Shopify's domain check on 4 October found mcpway.com taken and mcpway.shop, .store, .org
and .net available that day. Search INPI and EUIPO in classes 9 and 42 before buying anything, and keep a second
name ready. The "-Way" echo of PCBWay is fine as a name; "the PCBWay of MCP" in an advert, or its look, is not.

## The roadmap

| Phase | When | What | Gate to the next |
| --- | --- | --- | --- |
| Make it a product | October 2026 | Pack art kept from other accounts, the decider's model locked for buyers, each agent key kept to its own cats, sign-up (closed), the keys page, the hosted runner, the shop kit, a plain face, the name and domain | A test account's first task finishes within an hour, with no pack art served to it |
| Ten by invite | November and December 2026 | Her own art first, then the legal pages, metering and plan gating, the Workers Paid plan and a sign-in rate limit, the store (Builds on sale from here) | Ten paying houses, no data lost |
| Public launch | January to March 2027 | Coworking (a house several people share), maintenance plans, OAuth for clients other than Claude's, café videos selling Builds, the app campaign | A hundred paying houses |
| Helpers and kits | From April 2027 | Freelancers reselling Builds and maintenance, the kits gallery, the app itself if the campaign funds it | |

October's work waits for Charlotte, as the merging rule says: it is under `harness/`, and the keys page is a
`/keys` page the gateway serves (phase 2 of `docs/accounts.md`). Sign-up opens to anyone only once her own art is
in.
