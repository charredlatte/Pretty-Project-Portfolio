# The queen's runner

The queen of the house is the cat in the café's entrance hall that Charlotte talks to. The café (the gateway's
own address, behind her password) is her face and her ears: this runner is her brain. It runs on Charlotte's
own computer, waits on the gateway for what she says to the queen and for the routines she set up, runs one
Claude Code turn for each, signed in with her own Claude plan, and streams what the queen says back, so the
café shows it as she speaks. Nothing here costs anything beyond the plan; routines run only while it runs.

```
 the café (gateway)  ──  what she said, routines due  ──►  queen.py  ──►  claude -p  ──►  the Catio's tools (/mcp)
                     ◄──  what the queen says, as she says it  ──┘
```

## Setting it up on her Windows PC (once)

1. **Claude Code** is installed and signed in with her plan (`claude`, then `/login` if it asks). **Python 3**
   is installed (python.org, or the Microsoft Store). This repository is on the PC.
2. **The queen's key.** Make one, as the other two secrets were made, in PowerShell:
   ```powershell
   $b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | % { $_.ToString('x2') })
   ```
   Save it in the password manager as `CATIO_QUEEN`, under the gateway's address. Then on Cloudflare, Workers &
   Pages → `catio-gateway` → Settings → Variables and Secrets → Add: type **Secret**, name `CATIO_QUEEN`, under
   **Production**, then **Deploy**. The deploy makes it her key (the registry keeps it in step with the secret).
   It is the only key that may speak as the queen: never the agents' key, since the cats act on what she says.
3. **Two variables on the PC**, in PowerShell (they stick for every new window):
   ```powershell
   setx CATIO_URL "https://catio-gateway.<her subdomain>.workers.dev"
   setx CATIO_QUEEN "<the key, pasted from the password manager>"
   ```
   Open a new PowerShell window afterwards: `setx` doesn't change the one it ran in.
4. **Run her:**
   ```powershell
   cd <the repository>
   python harness\runner\queen.py
   ```
   It says `the queen's runner is up`, and the queen in the café wakes (her hover says she is here). Keep the
   window open; `Ctrl+C` stops it, and she falls asleep in the café. Optional: Task Scheduler → Create Basic
   Task → *When I log on* → *Start a program* `python` with the arguments `harness\runner\queen.py` and the
   repository as *Start in*, so she wakes with the PC.

On a Mac or Linux the same, with `export` in place of `setx` and `python3`.

## What it does

- Waits on `POST /api/runner/wait` (held up to 25 seconds; Cloudflare holds a request while the client stays
  connected). It comes back the moment she writes to the queen, a routine comes due, or she clicks Stop.
  Each wait says `{acks: true, ack: <the newest note whose turn is finished>}`, and the gateway offers a note
  until that acknowledgement reaches it: a connection that drops mid-wait, or a runner that dies mid-turn, means
  she says a thing twice rather than it being lost. A note is acknowledged when its turn ends, not when it
  arrives. Anything but a refused key (401) is waited out, 503 included.
- For each note or routine, one turn: `claude -p --resume <her session> --output-format stream-json
  --include-partial-messages --append-system-prompt-file <queen.md + her character> --mcp-config <the gateway's
  /mcp, with the queen's key> --strict-mcp-config --restricted --allowedTools mcp__catio --permission-prompts
  none --max-turns 30`. The queen keeps one conversation across turns (`state.json` in `CATIO_QUEEN_DIR`,
  default `~/.catio/queen`); a session that is gone is started afresh. Restricted mode and `--strict-mcp-config`
  leave her the Catio's tools and nothing that runs commands or edits files; `CATIO_*` is kept out of the turn's
  environment, so the house-rules hook doesn't report her as a cat.
- Streams the text as it arrives to `POST /api/runner/say` (at most every 0.4 s), then the whole answer with
  `done`, which the gateway keeps as the queen's note. Stop (`manage pause` on the cat `queen`) sends the turn
  `Ctrl+Break` on Windows (the child runs in its own process group) or `SIGINT` elsewhere; what she had said
  so far is kept.
- Her character (`queens/house` in the café: name, manner, greeting) comes with every wait, so a change in
  her card applies on the next turn. `queen.md` is the part that doesn't change.
- **Says her homework on Charlotte's desktop.** Every wait also carries the open quizzes counted by kind, and
  when a kind grows the runner says the lot ("2 notes to sort, 1 decision waiting in the cafe") with whatever
  the computer already has: `notify-send` on Linux, `osascript` on a Mac, a PowerShell balloon on Windows.
  Nothing is installed for it, and a computer with none of them simply gets nothing. What is already waiting
  when the runner starts is never announced -- only a card that lands while it runs -- and the words are always
  the runner's own, built from counts, because a Mac and Windows take them inside a quoted string.
  `CATIO_NOTIFY` is a program to call instead (the text is its one argument); `CATIO_NOTIFY=` (empty) turns
  notifications off. Her quest log itself stays in the café: this only says that it has something new in it.

Tests: `python3 -m unittest discover -s harness/test` (`test_queen.py` runs it against a stand-in gateway and a
fake `claude`).

## The browser's part

The queen's voice and ears are the browser's own, free: voice to text is `webkitSpeechRecognition` (Chrome and
Edge), her voice is `speechSynthesis` with an English (UK) voice (Microsoft Hazel or Susan on Windows). Open the
café in Chrome or Edge for both; elsewhere the Speak button and the voice switch hide themselves. A paid voice
(ElevenLabs or OpenAI) could sit behind the same switch later, through the gateway, keyed by a secret; nothing of
it is built.
