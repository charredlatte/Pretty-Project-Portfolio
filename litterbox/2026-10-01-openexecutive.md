---
project: montfortoise-shopify
date: 2026-10-01
---

# 1 October 2026: OpenExecutive, looked at for a small shop (compressed)

## What it is

- **SenteLabsAI/OpenExecutive** is Apache 2.0, and was still being worked on (last commit 17 September 2026).
  It's FastAPI and Next.js, with ChromaDB for retrieval and SQLite for memory. One "Executive" voice sits in
  front of eight specialist agents: CSO, CFO, CHRO, General Counsel, COO, CMO, CPO and Board.
- Runs locally with `make dev`. It needs Python 3.11 or later, Node 22 or later, and `uv`.
- "Skills" means two different things in that repo: Claude Code skills in `.claude/skills/`, and the app's
  own executive playbooks.

## Findings

- **Its Claude Code skills.**
  - `anvil` (766 lines) is an evidence-first coding workflow. It pushes back on bad requirements, sizes the
    task, keeps a SQLite ledger of checks in `/tmp`, and has three reviewer agents attack its own diff. It
    is portable.
  - `openexec-api` is only curl recipes for its own backend, so it isn't portable.
- **Porting anvil.** Copy `.claude/skills/anvil/` and the three `.claude/agents/anvil-*.md`; the skill
  spawns those agents by name. Then rewrite its `## Project: Open Executive` section (`SKILL.md:567`),
  which hardcodes `make lint`, `uv run pytest` and `packages/core/**`, with the host repo's own checks. It
  is heavy: on medium tasks it spawns reviewer agents and writes an evidence bundle, so it costs a lot of
  tokens. Small tasks skip both.
- **Don't copy its `.claude/settings.json` as it is.** It enables a third-party plugin
  (`ui-ux-pro-max@ui-ux-pro-max-skill`, from `nextlevelbuilder/ui-ux-pro-max-skill`) that wasn't reviewed.
- **Its own playbooks.** It ships 15, among 97 built-in knowledge documents. They load into ChromaDB when the
  app boots, so you get them by running it, not by copying them.
  - They fit a small shop: `positioning-statement` (April Dunford), `competitive-teardown`, `market-sizing`,
    `monthly-business-review`, `quarterly-forecast`, `feature-prioritization`, `customer-interview-plan`,
    `quarterly-okr-set`.
  - They don't: `board-prep-deck`, `board-update-memo`, `fundraise-narrative`, `layoff-comms-plan`,
    `role-scorecard`, `exec-1on1-template`.
  - You can add playbooks of your own as company skills.
- **MCP, both ways.**
  - It serves MCP at `/mcp`, gated by `x-api-key`. Its tools are `consult_specialist`, `search_knowledge`,
    `list_workflows` and `ask_executive`, and its resources are the company profile, today's briefing, the
    people roster and past decisions. Another Claude Code session can consult it without re-explaining the
    business.
  - Its gateway (`orchestrator/mcp_gateway.py` and `mcp_servers.json`) lets the specialists call other MCP
    servers, a Shopify one for instance.
- **The gateway's shipped deny list is too narrow for a shop.** It blocks `*delete*`, `*drop*`,
  `*destroy*`, `*remove*` and `*trash*`, but not `update-product` or `bulk-update-product-status`. Add
  those to `filters.access_control.deny` before connecting a store.

## Facts learned

- It needs its own `ANTHROPIC_API_KEY`, billed per token, separate from a Claude subscription. Four of its
  specialists use the deep-reasoning model with extended thinking.
- The first `make dev` is slow: `uv sync` pulls ChromaDB and PyTorch, then it downloads a 90 MB embedding
  model.
- On Windows, `make` has to run from Git Bash or WSL, and `make stop` uses `lsof`, which Windows lacks.
- It writes a live SQLite file and a ChromaDB folder beside itself, so don't run it from a cloud-synced
  folder.
- `.env.example` ships `ENABLE_WEB_SEARCH=false`. Turn it on, or the strategy and marketing specialists
  can't look at competitors.
- The scheduler is single-instance. A second API replica fires every scheduled action twice.

## Ideas not built

- **Take anvil now:** four files plus a 15-line rewrite of its project section, and no new infrastructure.
- **Trial OpenExecutive locally for a week before deploying it.** Ask it three concrete questions and
  compare its answers with a plain Claude session that has the same data. What would set it apart (memory
  across months, a live store connection, scheduled follow-ups) only pays off if it keeps running.
