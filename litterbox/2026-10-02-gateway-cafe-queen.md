---
project: Pretty-Project-Portfolio
date: 2026-10-02
---

# 2 October 2026: the chat that set up the gateway, moved the café onto it and planned the queen (sifted)

## Waiting on Charlotte

- ~~**The queen's key.**~~: done, her runner answers as the queen (3 October). Once the queen's pull request merges, add a third secret, `CATIO_QUEEN`, on the
  `catio-gateway` Worker (type Secret, under Production, then Deploy; its own entry in her password manager).
  Then on her PC: `setx CATIO_URL …`, `setx CATIO_QUEEN …`, and `python harness\runner\queen.py`, keeping the
  window open. Routines run only while it runs (`harness/runner/README.md`).

- ~~**PR #31 (onboarding) and the queen's PR touch the same lines:**~~: both merged, and `main` fixed the half `placeQueen` the merge left (62312fe). `placeQueen` and the render loop (closed
  rooms get no queen, `roomOpen`), and both add a phase 6 to `docs/plan.md`. Whichever merges second resolves
  them.

- **A paid voice for the queen?** The free browser voice is what's built (Chrome or Edge's en-GB voices,
  `speechSynthesis`). A paid one (ElevenLabs or OpenAI) would go through a gateway proxy keyed by a secret;
  the page's `speak()` is one function so it can be a second branch. Her call, later.

- **Where the runner lives after her PC,** with October 2026 prices (also in `docs/plan.md`, phase 6):
  - Cloudflare Containers next to the gateway: $5/month for Workers Paid plus about 7¢ a working hour; sleeps
    when idle, and its disk empties when it sleeps. Cloudflare's own Claude Code guide uses an API key, so
    her plan's sign-in must be checked there first. Recommended.
  - Hetzner CAX11: €5.99 + €0.50 a month, keeps its files, near her in France.
  - Oracle Always Free ARM: free, 2 cores and 12 GB since June 2026; needs a card, and idle machines are
    reclaimed.
  - A Raspberry Pi: €80–100 once.

  Claude Code needs 4 GB.

- ~~**One commit on `main` carries Claude attribution lines**~~: nothing to do, history isn't rewritten. in this public repo: `8de7227` (PR #26, the hook's
  User-Agent fix), made before the house rules were installed in the session. History isn't rewritten, so it
  stays. Nothing to do.

- **Set the CATIO connector's tools to Always allow** (claude.ai → Customize → Connectors) if not done yet:
  otherwise the artifact page's live read asks before every call, and the House menu says so. A session can't
  check it.

- **Three old messages in the gateway café still carry a "queued" label.** The seven outbox posts were
  delivered from a session after the café's data was copied in, and the agents' key can't edit her data, on
  purpose. Harmless.

## Facts learned

- **Cloudflare's bot check (error 1010, `browser_signature_banned`) refuses Python's default User-Agent,** so
  every script that calls the gateway names itself (`kittychat-report/1`, `kittychat-move-in/1`, the runner
  `kittychat-queen/1`). The hook's reports were dropped silently until PR #26.

- **Cloudflare's "Import a repository" fills the Worker's name with the repo's.** It must be `catio-gateway`,
  to match `wrangler.jsonc`, or later deploys fail. A Worker under the wrong name is deleted and imported
  again (renaming is risky: the Durable Object is tied to the name), and its leftover KV namespace deleted
  too. Done 2 October.

- **A Worker secret counts only as type Secret, under Production, and after Deploy** (saving a version isn't
  live). A 401 `invalid_token` on `/mcp` means the Worker's `CATIO_TOKEN` differs from the environment's:
  copy it with the password manager's copy button (selecting the text can pick up a space) and paste it
  again. That was the cause on 2 October.

- **The gateway's old home page said one fixed line whatever the state,** so it told her nothing (now it is
  the café). Check a deploy from a session: the sign-in page's wording, `/mcp` with the key, `list_agents`.
  Never by trying a password: a wrong one from a check counts toward the five-try lock (one was spent on
  2 October).

- **Cloud sessions don't install the plugin from the repo's `.claude/settings.json`.** It goes in the
  environment's setup script, with the full `https://…git` marketplace address (the short form hung).
  Verified 2 October: the session restarted with the rules on, and the audit and browser-preflight gates held
  until their skills ran.

- **Claude Code Remote's `send_message` works from a session** where the page's call is refused: the seven
  outbox posts of 30 September were delivered that way on 2 October (four messages, one archive, two already
  done) and marked delivered.

- **Secrets on her PC:** in PowerShell,
  `$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | % { $_.ToString('x2') })`;
  in a Codespace, `openssl rand -hex 32`. Chrome's password manager has an Add button at
  `chrome://password-manager/passwords`; passwords.google.com doesn't. Both entries are filed under the
  gateway's address. Her Codespace is "symmetrical space giggle"; VS Code's Chat panel sends what's typed to
  an AI, so secrets go in the terminal. Her PC's VS Code opens in `G:\My Drive\Claude`.

- **Claude Code headless, for the runner:**
  `claude -p --resume <id> --output-format stream-json --verbose --include-partial-messages --append-system-prompt-file … --mcp-config '{"mcpServers":{"catio":{"type":"http","url":"…/mcp","headers":{"Authorization":"Bearer …"}}}}' --allowedTools mcp__catio --permission-prompts none --max-turns 30`.
  `--bare` needs an API key, so it isn't used: she signs in with her plan. SIGINT ends a turn (on Windows,
  `CTRL_BREAK_EVENT` to a child started with `CREATE_NEW_PROCESS_GROUP`). Cross-session messaging needs a
  session connected to Remote Control to pass messages on: untested.

- **A Worker holds a request as long as the client stays connected,** so the runner's 25-second long poll is
  fine on the free plan; a Durable Object alarm wakes it for a routine on time.

- **Voice in the browser:** `webkitSpeechRecognition` is Chrome and Edge only (voice to text);
  `speechSynthesis` has en-GB voices on Windows (Microsoft Hazel, Susan). Both free; hidden where the browser
  lacks them.

- **The ship check reads the branch's upstream:** a feature branch tracking `main` reports every commit as
  unpushed. `git branch --set-upstream-to=origin/<branch>` fixes it.

- **Her choices of 2 October:** the café on its own address (over talking in the cats' cards, or Managed
  Agents sessions billed per use through an API key); the runner on her PC for now; the free browser voice
  now.

## Ideas not built

- **Managed Agents sessions** started and chatted with entirely from the café: separate from her claude.ai
  sessions and billed per use through an API key. Offered 2 October, not chosen.

- **The file sorter and starting sessions from the café** (`harness/gateway/README.md`, "Not here (yet)");
  the runner brings the second.

- **Accounts** (`docs/accounts.md`): the queen's key is one more key for the Registry, with the role `queen`.

## Findings

- **The serving model fell back to Opus 5.5 for one turn** during stage 1 ("Try again"); the work was
  re-checked and nothing was lost.

- **The artifact's database and the gateway café's are two copies that don't share changes** (the "queued"
  labels above are one consequence); `CLAUDE.md` says so.
