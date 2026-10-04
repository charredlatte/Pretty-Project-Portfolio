# MCPWay: the café's gateway, made to order

Written 4 October 2026, from Charlotte's ask: "Make the KittyChat Cafe into a real business plan. A framework that
sells a harness gateway product in the form of MCP, but have it your way. Drive with whatever model you want and
adapt to any environment." This is the product side. The business plan, with its prices, figures and the legal
setup, is private and lives in the café, not here.

## In plain words

MCPWay makes agent harnesses to order. You send in your rules, your tools and the model you want driving each
agent, and you get back a working harness on one MCP gateway. The name follows PCBWay: PCBWay takes a circuit
design, quotes it, fabricates the board and assembles the parts. MCPWay takes a harness design (house rules,
skills, agents, which model drives what), deploys the gateway, and installs the pieces into the clients the buyer
already uses.

- **Any model.** Claude today; OpenAI, Gemini, Mistral and a local model through Ollama once the runner's
  drivers are in (below), and a small model for typed decisions (yes/no, a choice, a score). Buyers bring their own keys and plans: MCPWay
  never resells Claude, OpenAI or Gemini access. The one model it runs itself is the decider's, on its default
  small model, inside the price (once buyers' keys can't pick another, below).
- **Any environment.** Claude Code, Codex, Gemini CLI, Cursor, Claude Desktop, claude.ai. On a laptop, a Raspberry
  Pi or a cloud container. One gateway everywhere. The owner's tools (handing in homework, dropping files,
  managing cats) need the owner's sign-in, which only claude.ai and Claude Desktop have today.
- **Any face.** The KittyChat Café is the flagship: a pixel-art manor where every session is a cat. Teams who
  want a plain dashboard will get one from the same gateway (not built yet).

The line to use: *your harness, your way*. Not "have it your way", which is Burger King's slogan.

## What is already built

Most of it, for one house: Charlotte's.

| Part | What it does | Where |
| --- | --- | --- |
| The gateway | A Cloudflare Worker that speaks MCP at `/mcp`, with 14 tools | `harness/gateway/` |
| Accounts | A house per user, OAuth for claude.ai, hashed agent keys | `harness/gateway/src/registry.js`, `docs/accounts.md` |
| House rules | The Claude Code plugin whose hooks enforce the rules | `harness/rules.json`, `harness/hooks/` |
| The runner | Waits on the gateway and runs one model turn per message or routine | `harness/runner/queen.py` |
| The decider | Typed decisions from a small model, logged beside the old path | `harness/gateway/src/decide.js` |
| Other agents | The stdio twin of the gateway, for Codex, Gemini CLI, Cursor and Claude Desktop on the same machine | `harness/mcp/catio_mcp.py` |
| The café | The manor, the onboarding, the queen, served from the gateway behind a sign-in | `catio/index.html`, `harness/gateway/cafe/` |

Still missing for a product:

- self sign-up and a keys button in the page (phase 2 of `docs/accounts.md`; keys themselves are built);
- runner drivers for models other than Claude;
- a plain face, for teams;
- metering, and a house several people can share;
- the decider's model locked for buyers' keys (today any caller can pass `model`, a paid one included);
- OAuth for clients other than Claude's (the gateway only lets claude.ai and claude.com connectors sign in);
- art Charlotte owns (`docs/drawing-plan.md`). Until it is in, the café serves the licensed packs to every
  signed-in account (`harness/gateway/src/cafe.js`), so no other account may open: the packs forbid it.

## Your way, concretely

A driver is a command the runner starts, or a client that joins over MCP. Each needs a little runner code once;
after that, choosing one is configuration.

| Driver | How it is driven | Status |
| --- | --- | --- |
| Claude (Claude Code) | `claude -p` turns from the runner; hooks enforce the rules | Built, for the queen; other agents report but aren't run by it |
| OpenAI (Codex CLI) | `codex exec`: woken by `catio_mcp.py`'s `wake` command on the same machine; on the hosted gateway it checks its inbox | Joins today; runner driver to build |
| Gemini (Gemini CLI) | `gemini -p`, the same way | Joins today; runner driver to build |
| Any OpenAI-compatible endpoint (OpenRouter, Mistral, Ollama) | A small tool-calling loop in the runner, with the gateway's tools | To build |
| Typed decisions (yes/no, a choice, a score) | Workers AI on the gateway, or any server in `DECIDE_URL` | Built |

| Environment | What runs there |
| --- | --- |
| A laptop or PC | The runner, any CLI, the local café |
| A Raspberry Pi or a small VPS | The runner, always on |
| Cloudflare Containers, on the buyer's own account | The runner, kept awake: it long-polls the gateway, so a sleeping one hears nothing |
| Claude Code on the web | Cloud sessions with the rules plugin, reporting by hook |
| claude.ai, Claude Desktop | The gateway as a connector, signed in as the owner |
| Cursor, other MCP clients | The gateway with an agent key: report and read, never write as the owner |

The code is open source under the AGPL (graphify, vendored, is Apache-2.0), and anyone can self-host it; the
art is not, and a clone shows the café without it. What is sold is not having to: the
gateway, the house and the café run for you, and on the upper tier the hosted features (the decider's sorting,
the litter box quiz, homework), which the Basic tier leaves out. The runner stays on the buyer's side in every tier. Buyers' model keys stay with the runner, on their machine or
their own cloud account; the gateway holds none of them, only the operator's own key for the decider, if set.

## Who it is for

1. **Developers who run agents from more than one vendor.** Each vendor's dashboard shows its own sessions only:
   Claude Code's Agent View (May 2026) and `codex agents` (Codex v0.149, August 2026).
2. **Teams of two to five**, who can't see what the others' agents are waiting on, once a house can be shared
   (the Team plan, from April 2027).
3. **Small business owners new to AI**, the café's first audience, through the manor and a harness built for them.
4. **Makers of rule packs, skills and skins**, later, through a parts gallery.

Besides the hosted tiers, two things are sold. **Builds** are harnesses made to order: Charlotte sets one up for
the buyer, with the course on changing it (the shop's "Set up for you"), sold from the day the store opens. **Parts** are rule packs, skills and
skins sold by their makers in a gallery, later. The shop wireframes (`docs/kittychat-shop/`) predate MCPWay and
have no Team column yet.

## Competition

Every MCP gateway in the 2026 roundups governs which tools an agent may call. None shows sessions, keeps one inbox
of what is waiting on a person, or enforces rules on how agents work. MCPWay is the gateway agents report to,
whichever vendor runs them.

| Category | Examples | What they leave open |
| --- | --- | --- |
| Enterprise MCP gateways | Kong, Traefik, TrueFoundry, MintMCP | Any view of agents; a small team's budget |
| Developer MCP platforms | Composio, Smithery, Docker MCP Gateway | Rules, sessions, the human in the loop |
| Vendor dashboards | Claude Code's Agent View, `codex agents` | Other vendors, phones, rules |
| Third-party agent dashboards | rejoin, CodeAgentSwarm, AgentPulse, CLI Manager | Hosting, rules, a gateway other agents call |

The vendor dashboards are the real threat: free and built in. MCPWay's answer is to be what no single vendor will
build, the place where all of them report.

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
| Make it a product | October 2026 | Pack art kept from other accounts, the decider's model locked for agent keys, sign-up (closed), the keys button, runner drivers, a plain face, the name and domain | A test account's cat reports within 10 minutes, with no pack art served to it |
| Ten by invite | November and December 2026 | Her own art first, then the legal pages, metering, the store (Builds on sale from here) | Ten paying houses, no data lost |
| Public launch | January to March 2027 | MCP registries and the plugin marketplace, a launch post, café videos selling Builds, the app campaign | A hundred paying houses |
| Parts and teams | From April 2027 | The Team plan, the parts gallery, OAuth for clients other than Claude's, the app itself if the campaign funds it | |

Most of October's work is under `harness/`, so those pull requests wait for Charlotte, as the merging rule says.
The keys button is a page change and merges like any other; the plain face needs a route in the gateway, so it
waits too. Sign-up opens to anyone only once
no pack art reaches other accounts.
