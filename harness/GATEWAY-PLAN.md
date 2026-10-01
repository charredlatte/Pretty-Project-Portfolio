# Plan: the Catio as a gateway (draft, 1 October 2026)

## The problem

A page on her own domain can't read her Claude Code sessions: only claude.ai can list them, and it
even refuses the artifact page's own `list_sessions` (`approval_required`). Right now the cats are
"as live as the last saved copy", and the routine that saved it stopped at her weekly limit.

## The idea: push, don't pull

OpenClaw works because one always-on **gateway** is the hub: channels, agents, tools and sessions
all connect *to it*, so it never has to ask anyone for a list. Do the same with what we already have:
`harness/mcp/catio_mcp.py` already keeps agents, an inbox, notes and wake commands. Make it the
always-on hub on her server, and have **every agent report to it**, Claude Code sessions included.
Then the gateway knows who is working without asking claude.ai.

```
 Claude Code sessions ──(plugin hooks)──┐
 Codex / Gemini / Cursor ──(MCP)────────┤
 OpenClaw, if she runs it ──(mcporter)──┼──►  Catio gateway  ◄──── the Catio page (her domain)
 Agent SDK / OpenRouter cats ───────────┘    mcp.<domain>    ◄──── the claude.ai artifact (connector)
```

## Steps

1. **Remote MCP.** Add a Streamable HTTP endpoint (`POST /mcp`, the same JSON-RPC `handle()`) to
   `catio_mcp.py`, next to stdio and `/api/*`. Still standard library only. Run it on the server
   (Oracle free, Hetzner, or her PC behind a Cloudflare Tunnel) at `mcp.<domain>`, state in `~/.catio`.
2. **Claude Code sessions report themselves.** `kittychat-house-rules` gets a `report.py` hook on
   `SessionStart` (arrived), `UserPromptSubmit` (busy), `Notification` (needs her), `Stop` (review or done)
   and `SessionEnd`, calling `report_status` with the session's title, repo, branch and link. It reads
   `CATIO_URL` and `CATIO_TOKEN` from the environment and does nothing when they're missing or the call fails
   (a two-second timeout, never blocking a turn). The environment's network policy must allow `mcp.<domain>`.
3. **Messages back.** What she sends goes to the gateway's inbox. A session that is **running** gets it at its
   next `Stop`: the hook holds the stop once and hands the message in, `[Catio] Charlotte says: …`. An
   **idle** cloud session can't be woken from outside claude.ai, so the message waits: the claude.ai artifact
   delivers it with `fire_trigger` (as today), or the session's catch-up finds it when it next starts.
4. **The page on her domain.** A `gatewayRuntime()` beside `localRuntime()`: rooms, renames, adopted chats,
   queens and notes live on the gateway instead of one browser's `localStorage`, so her phone and PC agree,
   and an `/events` stream (server-sent events) moves cats as soon as a hook reports. Behind Cloudflare Access.
5. **The claude.ai artifact joins too.** Add the gateway as a custom connector in claude.ai. The artifact
   then shows the gateway's cats next to the live sessions, and every Claude chat can call `report_status`.
6. **Cats the gateway runs itself** (the real OpenClaw part). Agents that belong to her server, so they're
   always live there: Claude Agent SDK sessions (Anthropic API key, billed per token, separate from her
   subscription), Codex and Gemini through `wake` commands, OpenRouter models for the sorter and small jobs.
   A "New cat" on her domain starts one of these. Later, a Telegram bot as a channel, so she can answer a
   cat from her phone, as OpenClaw does with WhatsApp and Telegram.

## Why not just run OpenClaw?

It's a large TypeScript gateway built around chat apps, and its third-party skills have a poor security
record. Ours is 361 lines with no dependencies and already speaks the Catio's language. Borrow the shape;
if she wants OpenClaw itself, it joins as one more cat through its MCP skill (mcporter).

## To check before building

- Which value in a cloud session's hooks gives the **claude.ai session id** (for the cat's link and for
  matching the cat to `list_sessions`); the hook input's `session_id` is the CLI's own.
- How claude.ai custom connectors authenticate (OAuth vs. none), and whether Cloudflare Access can sit in
  front without locking claude.ai's servers out.
- Whether an artifact's `mcp` capability may name a custom connector (load `artifact-capabilities`).

## Rules that still hold

- Session titles and notes are private: the gateway is behind auth, its state never goes in git.
- The licensed art is never public: the site stays behind Cloudflare Access.
- Tokens go in environment settings, never in the chat or the repo.

## What she needs to provide

The domain, the server (or the tunnel on her PC), the Cloudflare token already asked for, and two
environment variables, `CATIO_URL` and `CATIO_TOKEN`, plus `mcp.<domain>` allowed in the network policy.
