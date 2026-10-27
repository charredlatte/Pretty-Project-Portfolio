# The queen's runner

The queen of the house is the cat in the café's entrance hall that Charlotte talks to. The café (the gateway's
own address, behind her password) is her face and her ears: this runner is her brain. It runs on Charlotte's
own computer, waits on the gateway for what she says to the queen and for the routines she set up, runs one
model turn for each, and streams what the queen says back, so the café shows it as she speaks. The model is
Claude Code by default, signed in with her own Claude plan, or any OpenAI-compatible one she names (below):
OpenAI, OpenRouter, Together, Groq, or Ollama and llama.cpp on the computer itself. Nothing here costs anything
beyond the plan or the model's own bill; routines run only while it runs.

```
 the café (gateway)  ──  what she said, routines due  ──►  queen.py  ──►  claude -p, or /v1/chat/completions  ──►  the Catio's tools (/mcp)
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

## Another brain: any OpenAI-compatible model

Set `CATIO_MODEL_URL` and the runner thinks with that model instead of Claude Code, which then needn't be installed
at all. One code path covers OpenAI, OpenRouter, Together, Groq, and a model on the computer itself, which is the
answer to "can she run entirely on my own machine, with no company involved": yes, on Ollama or llama.cpp, with
nothing of anyone's in the loop but the gateway.

```powershell
setx CATIO_MODEL_URL "http://localhost:11434/v1"    # Ollama; llama.cpp's server is http://localhost:8080/v1
setx CATIO_MODEL "llama3.1"                          # the model's name; leave it unset for a server that serves one
setx CATIO_MODEL_KEY "sk-..."                        # only a hosted provider wants one (OpenAI, OpenRouter...)
```

| Variable | What it is |
|---|---|
| `CATIO_MODEL_URL` | the server's base address, up to and including `/v1`: `http://localhost:11434/v1` (Ollama), `http://localhost:8080/v1` (llama.cpp), `https://api.openai.com/v1`, `https://openrouter.ai/api/v1`, `https://api.groq.com/openai/v1` |
| `CATIO_MODEL` | the model's name, as the server knows it. Left out of the request when unset |
| `CATIO_MODEL_KEY` | its API key, when it wants one; Ollama and llama.cpp don't |

What it does differently from Claude Code, and what stays the same:

- **Her tools are the gateway's, and nothing else**: the runner asks `/mcp` for `tools/list` with the queen's key at
  the start of each turn, hands them to the model as functions, and runs each call it makes as `tools/call`. There
  is no shell and no file in reach, which is the promise restricted mode makes for Claude Code, kept here by
  construction. Up to 30 rounds of tools in a turn, as with Claude Code.
- **Her memory is `messages.json`** in `CATIO_QUEEN_DIR`, the counterpart of `--resume`: her conversation, kept to
  the last forty messages (trimmed at one of Charlotte's lines, so a tool's answer never loses its call). `queen.md`
  and her character go in the system message, rebuilt every turn and never stored, so a change in her card applies
  on the next turn here too.
- **Streaming, Stop and the loading strip** work the same: the text as it arrives, each tool she reaches for told to
  the café, and Stop closes the model's stream and keeps what she had said, in the café and in her memory.
- **A model that refuses or isn't there** ends the turn with her apology and the reason ("the model answered 401:
  CATIO_MODEL_KEY was refused", "no model: connection refused"); the runner stays up, since the model is hers to
  fix, where a refused *queen's key* still stops it.
- **Her card says what thinks for her**: each wait tells the gateway the provider (`local` for a server on this
  computer, else its host) and the model, and the café shows them where it shows a cat's breed.

The server must speak the OpenAI chat-completions API with **tool calling and streaming** together. Ollama does from
0.4; llama.cpp's server needs `--jinja`; the hosted providers above all do. A model too small to call tools will
answer without looking: give her at least an 8B instruct model.

## What it does

- Waits on `POST /api/runner/wait` (held up to 25 seconds; Cloudflare holds a request while the client stays
  connected). It comes back the moment she writes to the queen, a routine comes due, or she clicks Stop. Each wait carries
  `ack`, the newest note she has been given: the gateway offers a note until then, so one lost when a connection
  dropped is offered again. A 503 is waited out like any other error; only a refused key (401) stops her.
- For each note or routine, one turn of her brain (`Runner.turn()` reads one stream of events, whichever driver
  makes them). With Claude Code (`ClaudeDriver`): `claude -p --output-format stream-json --verbose
  --include-partial-messages --append-system-prompt-file <queen.md + her character> --mcp-config <the gateway's
  /mcp, with the queen's key> --strict-mcp-config --restricted --allowedTools mcp__catio --permission-prompts
  none --max-turns 30`, with `--resume <her session>` on the end once she has one (`Runner.args()`). The queen
  keeps one conversation across turns (`state.json` in `CATIO_QUEEN_DIR`, default `~/.catio/queen`); a session
  that is gone is started afresh. Restricted mode and `--strict-mcp-config`
  leave her the Catio's tools and nothing that runs commands or edits files; `CATIO_*` is kept out of the turn's
  environment, so the house-rules hook doesn't report her as a cat. With `CATIO_MODEL_URL` (`ModelDriver`): the
  loop above, over `POST <url>/chat/completions`.
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
fake `claude`, and against a stand-in OpenAI-compatible model with no `claude` anywhere).

## The browser's part

The queen's voice and ears are the browser's own, free: voice to text is `webkitSpeechRecognition` (Chrome and
Edge), her voice is `speechSynthesis` with an English (UK) voice (Microsoft Hazel or Susan on Windows). Open the
café in Chrome or Edge for both; elsewhere the Speak button and the voice switch hide themselves. A paid voice
(ElevenLabs or OpenAI) could sit behind the same switch later, through the gateway, keyed by a secret; nothing of
it is built.
