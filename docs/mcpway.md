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

- **Any model.** Claude, OpenAI, Gemini, Mistral, a local model through Ollama, a small model for yes/no
  decisions. Buyers bring their own keys and plans: MCPWay never resells Claude, OpenAI or Gemini access. The one
  model it runs itself is the decider's small one, inside the price.
- **Any environment.** Claude Code, Codex, Gemini CLI, Cursor, Claude Desktop, claude.ai. On a laptop, a Raspberry
  Pi or a cloud container. One gateway, the same tools everywhere.
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
| Other agents | The stdio twin of the gateway, for Codex, Gemini CLI, Cursor and Claude Desktop | `harness/mcp/catio_mcp.py` |
| The café | The manor, the onboarding, the queen, served from the gateway behind a sign-in | `catio/index.html`, `harness/gateway/cafe/` |

Still missing for a product: self sign-up and keys (phase 2 of `docs/accounts.md`), runner drivers for models
other than Claude, a plain face, metering, a house several people can share, OAuth for clients other than
Claude's (the gateway only lets claude.ai and claude.com connectors sign in), and art Charlotte owns
(`docs/drawing-plan.md`).

## Your way, concretely

A driver is a command the runner starts, or a client that joins over MCP. Adding one is configuration, not a new
product.

| Driver | How it is driven | Status |
| --- | --- | --- |
| Claude (Claude Code) | `claude -p` turns from the runner; hooks enforce the rules | Built |
| OpenAI (Codex CLI) | `codex exec`: woken by `catio_mcp.py`'s `wake` command on the same machine; on the hosted gateway it checks its inbox | Joins today; runner driver to build |
| Gemini (Gemini CLI) | `gemini -p`, the same way | Joins today; runner driver to build |
| Any OpenAI-compatible endpoint (OpenRouter, Mistral, Ollama) | A small tool-calling loop in the runner, with the gateway's tools | To build |
| Small yes/no decisions | Workers AI on the gateway, or any server in `DECIDE_URL` | Built |

| Environment | What runs there |
| --- | --- |
| A laptop or PC | The runner, any CLI, the local café |
| A Raspberry Pi or a small VPS | The runner, always on |
| Cloudflare Containers, on the buyer's own account | The runner, asleep when idle |
| Claude Code on the web | Cloud sessions with the rules plugin, reporting by hook |
| claude.ai, Claude Desktop | The gateway as a connector, signed in as the owner |
| Cursor, other MCP clients | The gateway with an agent key: report and read, never write as the owner |

The runner and its drivers stay open source and free in every tier: they run on the buyer's machine. What is
sold is what is hosted (the gateway, the house, the café) and what costs a model call (the decider, the litter
box, homework). Model keys stay with the runner, on the buyer's machine or their own cloud account; the gateway
never holds them.

## Who it is for

1. **Developers who run agents from more than one vendor.** Each vendor's dashboard shows its own sessions only:
   Claude Code's Agent View (May 2026) and `codex agents` (Codex v0.149, August 2026).
2. **Teams of two to five**, who can't see what the others' agents are waiting on, once a house can be shared
   (the Team plan, from April 2027).
3. **Small business owners new to AI**, the café's first audience, through the manor and a harness built for them.
4. **Makers of rule packs, skills and skins**, later, through a parts gallery.

## Competition

Every MCP gateway in the 2026 roundups governs which tools an agent may call. None shows sessions, runs agents
on a model of your choice, or enforces rules on how they work. MCPWay is the gateway agents report to.

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
| Make it a product | October 2026 | Sign-up and keys, runner drivers, a plain face, the name and domain | A stranger's cat reports within 10 minutes |
| Ten by invite | November and December 2026 | Her own art, the legal pages, metering, the store | Ten paying houses, no data lost |
| Public launch | January to March 2027 | MCP registries and the plugin marketplace, a launch post, Builds on sale, café videos | A hundred paying houses |
| Parts and teams | From April 2027 | The Team plan, the parts gallery, the app campaign | |

October's work is under `harness/`, so each pull request waits for Charlotte, as the merging rule says.
