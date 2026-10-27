#!/usr/bin/env python3
"""The queen's runner: the brain of the queen of the KittyChat Café, on Charlotte's own computer.

The queen is the cat in the café's entrance hall that Charlotte talks to. This waits on the gateway
(harness/gateway) for what she says to the queen and for the routines she set up, runs one model turn for each,
with the Catio's tools as the queen's only tools, and streams what the queen says back, so every open café shows it
as she speaks. Stop, in the café, ends the turn.

    python3 harness/runner/queen.py

Her brain is one of two drivers, chosen by the environment:

- Claude Code (the default): one `claude -p` turn per thing to do, signed in with her own plan, held to the Catio's
  tools by restricted mode and --strict-mcp-config (ClaudeDriver).
- Any OpenAI-compatible model, when CATIO_MODEL_URL is set: OpenAI, OpenRouter, Together, Groq, or Ollama and
  llama.cpp on this very computer, so she can run with no company in the loop at all. A tool-calling loop over
  POST /v1/chat/completions, with the gateway's tools and nothing else (ModelDriver).

Environment:
    CATIO_URL        the gateway's address, https://catio-gateway.<name>.workers.dev
    CATIO_QUEEN      the queen's own key (the CATIO_QUEEN secret on the Worker), never the agents' key
    CATIO_QUEEN_DIR  where she keeps her state and works from (default ~/.catio/queen)
    CATIO_CLAUDE     the claude command, when it isn't on the PATH as "claude"
    CATIO_MODEL_URL  an OpenAI-compatible server instead of Claude Code: http://localhost:11434/v1 (Ollama),
                     http://localhost:8080/v1 (llama.cpp), https://api.openai.com/v1, https://openrouter.ai/api/v1
    CATIO_MODEL_KEY  its API key, when it wants one (Ollama and llama.cpp don't)
    CATIO_MODEL      the model's name (llama3.1, gpt-4o...); left out of the request when unset, for a server that
                     serves one model
    CATIO_NOTIFY     a program to say homework on her desktop instead of the platform's own; it is called
                     with the text as its one argument. Set it empty for no notifications at all.

README.md says how to set it up. Standard library only; Python 3.9 or later.
"""
import http.client
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHARACTER = HERE / "queen.md"     # who she is: the part that doesn't change
WAIT_TIMEOUT = 40                 # the gateway holds a wait up to 25 s
SAY_EVERY = 0.4                   # seconds between streamed updates to the café
GRACE = 10                        # seconds a stopped turn gets to end on its own
MAX_TURNS = "30"                  # rounds of tools in one turn, for either driver
MODEL_TIMEOUT = 120               # seconds a model may stay silent before the turn is given up
TOOL_RESULT = 4000                # characters of a tool's result a model is shown
HISTORY = 40                      # messages ModelDriver keeps of her conversation, the counterpart of --resume
WINDOWS = os.name == "nt"
SORRY = "Forgive me, my lady: my turn ended before I could answer."
TITLE = "KittyChat Cafe"           # a notification's title, and never anything from the café: see notify()
# Her quest log, in words, by the kind the gateway counts: one, then more than one. A kind that isn't here is
# not said at all -- give it its words, rather than letting a document's own text reach a notification.
HOMEWORK = {"unblock": ("quiz to hand in", "quizzes to hand in"),
            "litterbox": ("note to sort", "notes to sort"),
            "decision": ("decision", "decisions")}
WIN_TOAST = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
             "$n = New-Object System.Windows.Forms.NotifyIcon; "
             "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
             "$n.ShowBalloonTip(10000, '%s', '%s', 'Info'); Start-Sleep 11; $n.Dispose()")


def log(*words):
    print(time.strftime("%H:%M:%S"), *words, flush=True)


def notify(body):
    """Say something on Charlotte's own desktop with whatever the platform already has: notify-send, osascript, or
    PowerShell's balloon. Nothing is installed for this and nothing has to be -- a desktop with none of them
    simply gets no notification, and CATIO_NOTIFY="" turns them off.

    The words are always this file's own, built from counts. macOS and Windows take them inside a quoted string,
    so café data -- a cat's name, a note's text, a kind nobody gave words to -- must never reach here, and the
    quotes that would end that string are dropped on the way in besides."""
    body = "".join(c for c in body if c not in "\\\"'")
    own = os.environ.get("CATIO_NOTIFY")
    if own is not None:
        argv = [own, body] if own.strip() else None
    elif sys.platform == "darwin":
        argv = ["osascript", "-e", 'display notification "%s" with title "%s"' % (body, TITLE)]
    elif WINDOWS:
        argv = ["powershell", "-NoProfile", "-Command", WIN_TOAST % (TITLE, body)]
    else:
        argv = ["notify-send", TITLE, body]
    if not argv:
        return
    try:
        said = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        log("no desktop notification here:", e)
        return
    threading.Thread(target=said.wait, daemon=True).start()   # reaped, so months of these leave nothing behind


def counted(kind, n):
    one, many = HOMEWORK[kind]
    return "%d %s" % (n, one if n == 1 else many)


def step(block):
    """A tool she reached for, as the café's loading strip names it: the tool without its server's prefix, and the
    cat and action it was about, when it has them."""
    args = block.get("input") or {}
    out = {"tool": str(block.get("name") or "").split("__")[-1][:60]}
    for k in ("cat", "action"):
        if isinstance(args.get(k), str):
            out[k] = args[k][:60]
    return out


class Gateway:
    def __init__(self, url, key):
        self.url, self.key = url.rstrip("/"), key

    def post(self, path, body, timeout):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST", headers={
            "Authorization": "Bearer " + self.key, "Content-Type": "application/json",
            "User-Agent": "kittychat-queen/1"})   # Cloudflare refuses Python's own User-Agent (error 1010)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")

    def rpc(self, method, params):
        """One call to the gateway's MCP server (/mcp: JSON-RPC in a POST, JSON back), as the queen."""
        reply = self.post("/mcp", {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, 60)
        if not isinstance(reply, dict) or "result" not in reply:
            err = (reply or {}).get("error") if isinstance(reply, dict) else None
            raise ValueError((err or {}).get("message") or "the gateway's answer has no result")
        return reply["result"]


# ---- her two brains. Each is a generator of events for Runner.turn():
#   ("awake",)                she is up: the café shows her thinking before her first word
#   ("start",)                a new message of hers begins: the bubble shows the one being written
#   ("delta", text)           more of what she is saying
#   ("text", text)            a whole message at a time, when there are no partial ones
#   ("tools", [step, ...])    the tools she reached for, for the café's loading strip
#   ("result", final, why)    the end: her answer (None when she had none), and why not when she hadn't

class ClaudeDriver:
    """Claude Code as her brain: one `claude -p` turn, read as stream-json, --resume keeping her conversation."""
    provider, model = "anthropic", "claude-code"

    def __init__(self, runner, claude):
        self.r, self.claude = runner, claude
        self.child = None              # the turn in progress
        self.lock = threading.Lock()

    def mcp_file(self):
        """The gateway as the queen's MCP server, with her key, in a file: a path crosses any shell unharmed."""
        path = self.r.home / "mcp.json"
        path.write_text(json.dumps({"mcpServers": {"catio": {"type": "http", "url": self.r.gw.url + "/mcp",
                                                            "headers": {"Authorization": "Bearer " + self.r.gw.key}}}}), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return path

    def args(self):
        args = [self.claude, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--append-system-prompt-file", str(self.r.prompt_file()), "--mcp-config", str(self.mcp_file()), "--strict-mcp-config",
                "--restricted", "--allowedTools", "mcp__catio", "--permission-prompts", "none", "--max-turns", MAX_TURNS]
        if self.r.state.get("session"):
            args += ["--resume", self.r.state["session"]]
        return args

    def stop(self):
        """End the turn in progress: Ctrl+Break on Windows (the child has its own process group), SIGINT elsewhere."""
        with self.lock:
            child = self.child
        if not child or child.poll() is not None:
            return
        log("stop: ending the turn")
        try:
            child.send_signal(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT))
        except OSError:
            return

        def harder():
            try:
                child.wait(GRACE)
            except subprocess.TimeoutExpired:
                child.terminate()
        threading.Thread(target=harder, daemon=True).start()

    def events(self, prompt, retry=True):
        state = self.r.state
        resumed = bool(state.get("session"))
        env = {k: v for k, v in os.environ.items() if not k.startswith("CATIO_")}   # the house-rules hook mustn't report her as a cat
        flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {}
        try:
            child = subprocess.Popen(self.args(), cwd=str(self.r.home), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **flags)
        except OSError as e:
            log("couldn't start claude:", e)
            yield ("result", None, "claude didn't start")
            return
        with self.lock:
            self.child = child
        errors = []
        threading.Thread(target=lambda: errors.append(child.stderr.read()), daemon=True).start()
        try:
            child.stdin.write(prompt)
            child.stdin.close()
        except OSError:
            pass
        text, final, session, failed, awake = "", None, None, None, False
        for line in child.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "system" and ev.get("session_id"):
                session = ev["session_id"]
                if not awake:
                    awake = True
                    yield ("awake",)
            elif kind == "stream_event":
                e = ev.get("event") or {}
                if e.get("type") == "message_start":
                    text = ""
                    yield ("start",)
                elif e.get("type") == "content_block_delta" and (e.get("delta") or {}).get("type") == "text_delta":
                    text += e["delta"].get("text") or ""
                    yield ("delta", e["delta"].get("text") or "")
            elif kind == "assistant":
                blocks = (ev.get("message") or {}).get("content") or []
                parts = [b.get("text") or "" for b in blocks if b.get("type") == "text"]
                tools = [step(b) for b in blocks if b.get("type") == "tool_use"]
                if tools:   # each tool she reaches for is told at once, not on the text's beat
                    yield ("tools", tools)
                if parts and not text:
                    text = "".join(parts)
                    yield ("text", text)
            elif kind == "result":
                session = ev.get("session_id") or session
                if isinstance(ev.get("result"), str):
                    final = ev["result"]
                if ev.get("is_error") or (ev.get("subtype") and ev["subtype"] != "success"):
                    failed = str(ev.get("subtype") or "error")
        code = child.wait()
        with self.lock:
            self.child = None
        if session and session != state.get("session"):
            state["session"] = session
            self.r.remember()
        stderr = (errors[0] if errors else "").strip()
        if final is None and not text and code != 0 and resumed and retry:   # her session is gone: start afresh, once
            log("couldn't resume the queen's session; starting a new one.", stderr[-200:])
            state.pop("session", None)
            self.r.remember()
            yield from self.events(prompt, retry=False)
            return
        why = (failed or stderr[-200:] or "exit %d" % code) if (failed or stderr or code) else None
        yield ("result", final, why)


class ModelDriver:
    """Any OpenAI-compatible model as her brain: a tool-calling loop over POST /v1/chat/completions, streamed, with
    the gateway's tools (tools/list on /mcp, as the queen) and nothing else -- no shell, no files, the same promise
    restricted mode makes for Claude Code. Her conversation is messages.json in her folder, the counterpart of
    --resume; her character is rebuilt into the system message every turn and never stored."""

    def __init__(self, runner, url, key, model):
        self.r, self.url, self.key, self.model = runner, url.rstrip("/"), key or "", model or None
        host = urllib.parse.urlparse(self.url).hostname or ""
        self.provider = "local" if host in ("localhost", "127.0.0.1", "::1") or host.startswith("127.") else host
        self.history = runner.home / "messages.json"
        self.stopping = threading.Event()
        self.open = None               # the response being read, closed by stop()
        self.lock = threading.Lock()

    def stop(self):
        log("stop: ending the turn")
        self.stopping.set()
        with self.lock:
            r = self.open
        if r is not None:
            try:
                r.close()
            except OSError:
                pass

    # ---- the gateway's tools, in the shape the model takes them ----
    def tools(self):
        listed = self.r.gw.rpc("tools/list", {}).get("tools") or []
        return [{"type": "function", "function": {"name": t["name"], "description": t.get("description") or "",
                                                   "parameters": t.get("inputSchema") or {"type": "object", "properties": {}}}}
                for t in listed if isinstance(t, dict) and t.get("name")]

    def call(self, name, args):
        try:
            got = self.r.gw.rpc("tools/call", {"name": name, "arguments": args})
        except (OSError, ValueError, http.client.HTTPException) as e:
            return "The gateway didn't answer: %s" % e
        parts = [c.get("text") or "" for c in (got.get("content") or []) if isinstance(c, dict)]
        return "\n".join(parts)[:TOOL_RESULT] or json.dumps(got.get("structuredContent") or {})[:TOOL_RESULT]

    # ---- one request, streamed: yields the text as it comes, fills `calls` by index ----
    def stream(self, messages, tools, calls):
        body = {"messages": messages, "stream": True}
        if tools:
            body["tools"] = tools
        if self.model:   # an OpenAI-compatible server usually wants a model named; one serving a single model does not
            body["model"] = self.model
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream", "User-Agent": "kittychat-queen/1"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self.url + "/chat/completions", data=json.dumps(body).encode(), method="POST", headers=headers)
        r = urllib.request.urlopen(req, timeout=MODEL_TIMEOUT)
        with self.lock:
            self.open = r
        try:
            for raw in r:
                if self.stopping.is_set():
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        yield delta["content"]
                    for tc in delta.get("tool_calls") or []:   # fragments by index, or whole calls as Ollama sends them
                        i = tc.get("index", len(calls))
                        c = calls.setdefault(i, {"id": None, "name": "", "arguments": ""})
                        if tc.get("id"):
                            c["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            c["name"] = fn["name"]
                        if fn.get("arguments"):
                            c["arguments"] += fn["arguments"] if isinstance(fn["arguments"], str) else json.dumps(fn["arguments"])
        finally:
            with self.lock:
                self.open = None
            r.close()

    # ---- her memory ----
    def remembered(self):
        try:
            got = json.loads(self.history.read_text(encoding="utf-8"))
            return got if isinstance(got, list) else []
        except (OSError, ValueError):
            return []

    def remember(self, messages):
        kept = messages[-HISTORY:]
        while kept and kept[0].get("role") != "user":   # a tool result never loses the call it answers
            kept.pop(0)
        self.history.write_text(json.dumps(kept), encoding="utf-8")

    def events(self, prompt):
        self.stopping.clear()
        yield ("awake",)
        try:
            tools = self.tools()
        except (OSError, ValueError, http.client.HTTPException) as e:
            log("couldn't list the gateway's tools:", e)
            yield ("result", None, "the gateway's tools didn't come: %s" % e)
            return
        history = self.remembered()
        new = [{"role": "user", "content": prompt}]
        messages = [{"role": "system", "content": self.r.prompt_text()}] + history + new
        text, final, why = "", None, None
        for _ in range(int(MAX_TURNS)):
            if self.stopping.is_set():
                break
            text, calls = "", {}
            yield ("start",)
            try:
                for more in self.stream(messages, tools, calls):
                    text += more
                    yield ("delta", more)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:200]
                log("the model answered", e.code, detail)
                why = "the model answered %d%s" % (e.code, ": CATIO_MODEL_KEY was refused" if e.code == 401 else "")
                break
            except (OSError, ValueError, http.client.HTTPException) as e:
                if self.stopping.is_set():
                    break
                log("no model:", e)
                why = "no model: %s" % e
                break
            if self.stopping.is_set():
                break
            ordered = [calls[i] for i in sorted(calls) if calls[i]["name"]]
            if not ordered:
                final = text
                new.append({"role": "assistant", "content": text})
                break
            for n, c in enumerate(ordered):
                c["id"] = c["id"] or "call_%d" % n
            asked = {"role": "assistant", "content": text or None,
                     "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}} for c in ordered]}
            messages.append(asked)
            new.append(asked)
            steps = []
            for c in ordered:
                try:
                    args = json.loads(c["arguments"]) if c["arguments"].strip() else {}
                except ValueError:
                    args = {}
                c["args"] = args if isinstance(args, dict) else {}
                steps.append(step({"name": c["name"], "input": c["args"]}))
            yield ("tools", steps)
            for c in ordered:
                out = "Stopped before this tool was called." if self.stopping.is_set() else self.call(c["name"], c["args"])
                answer = {"role": "tool", "tool_call_id": c["id"], "content": out}
                messages.append(answer)
                new.append(answer)
        else:
            why = "no answer after %s rounds of tools" % MAX_TURNS
        if self.stopping.is_set():
            why = "stopped"
            if text and final is None:   # what she had said so far is kept, in the café and in her memory
                new.append({"role": "assistant", "content": text})
        self.remember(history + new)
        yield ("result", final, why)


class Runner:
    def __init__(self, gateway, home):
        self.gw, self.home = gateway, home
        self.driver = None             # set by main(): ClaudeDriver or ModelDriver
        self.jobs = queue.Queue()      # what to do, in order: ("note", {...}) or ("routine", {...})
        self.lock = threading.Lock()
        self.character = {}            # her name, manner and greeting, as set in the café
        self.state_file = home / "state.json"
        try:
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = {}

    def remember(self):
        with self.lock:   # the waiting thread writes her homework, the main one her session
            self.state_file.write_text(json.dumps(dict(self.state)), encoding="utf-8")

    # ---- waiting on the gateway, on a thread of its own, so a Stop reaches the turn in progress ----
    def watch(self):
        pause, acked = 5, 0   # acked: the newest note she has been given; the gateway offers a note again until the next wait says so
        while True:
            try:
                got = self.gw.post("/api/runner/wait", {"ack": acked, "provider": self.driver.provider, "model": self.driver.model}, WAIT_TIMEOUT)
                pause = 5
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:200]
                if e.code == 401:
                    log("the gateway refused the queen's key:", detail)
                    os._exit(2)
                log("the gateway answered", e.code, detail)
                time.sleep(pause)
                pause = min(pause * 2, 60)
                continue
            except (OSError, ValueError, http.client.HTTPException) as e:   # a reply cut off half way is one of these too
                log("no gateway:", e)
                time.sleep(pause)
                pause = min(pause * 2, 60)
                continue
            if not isinstance(got, dict):
                log("the gateway answered with something that isn't an object:", str(got)[:80])
                time.sleep(pause)
                pause = min(pause * 2, 60)
                continue
            if isinstance(got.get("character"), dict):
                self.character = got["character"]
            if isinstance(got.get("homework"), dict):
                self.homework(got["homework"])
            if got.get("stop"):
                self.interrupt()
            for note in got.get("notes") or []:
                self.jobs.put(("note", note))
                acked = max(acked, note.get("at") or 0)
            if got.get("routine"):
                self.jobs.put(("routine", got["routine"]))

    def homework(self, counts):
        """What waits on Charlotte, as the gateway counts it by kind. When a kind grows, say the whole of it on her
        desktop: her quest log is in the café, and the runner is the part of the café always running. The first
        count after a start is only remembered, so coming back doesn't announce cards she has already seen."""
        now = {k: v for k, v in counts.items() if k in HOMEWORK and isinstance(v, int) and v > 0}
        was = self.state.get("homework")
        if now != was:
            self.state["homework"] = now
            self.remember()
        if was is None or not any(v > (was.get(k) or 0) for k, v in now.items()):
            return
        said = ", ".join(counted(k, now[k]) for k in HOMEWORK if k in now)
        log("homework:", said)
        notify(said + " waiting in the cafe")

    def interrupt(self):
        """End the turn in progress, whichever brain is on it."""
        self.driver.stop()

    # ---- one turn of her brain for each thing to do ----
    def run(self):
        threading.Thread(target=self.watch, daemon=True).start()
        log("the queen's runner is up:", self.gw.url, "· working from", self.home, "· thinking with", self.driver.provider, self.driver.model or "")
        while True:
            kind, job = self.jobs.get()
            if kind == "note":
                prompt = "[Catio] Charlotte says: " + str(job.get("text") or "")
                log("Charlotte:", str(job.get("text") or "")[:80])
                self.turn(prompt, None)
            else:
                name = str(job.get("name") or job.get("id") or "")
                log("routine:", name)
                self.turn("[Catio] Routine \"%s\": %s" % (name, job.get("prompt") or ""), {"id": str(job.get("id") or ""), "name": name})

    def prompt_text(self):
        """queen.md, with what Charlotte set in the café (her name, manner and greeting) under it."""
        text = CHARACTER.read_text(encoding="utf-8")
        c = self.character if isinstance(self.character, dict) else {}
        lines = []
        if c.get("name"):
            lines.append("Thy name is %s." % c["name"])
        if c.get("manner"):
            lines.append("How you speak, as Charlotte set it: " + str(c["manner"]))
        if c.get("greeting"):
            lines.append("Your greeting, when a conversation begins: " + str(c["greeting"]))
        if lines:
            text += "\n\n## As Charlotte set you up\n\n" + "\n".join(lines) + "\n"
        return text

    def prompt_file(self):
        """The same, in her folder, for a driver that takes a file."""
        path = self.home / "prompt.md"
        path.write_text(self.prompt_text(), encoding="utf-8")
        return path

    def say(self, turn, text, done, routine, steps=None):
        body = {"turn": turn, "text": text[-8000:], "done": done}
        if routine:
            body["routine"] = routine
        if steps is not None:   # what she is doing, for the café's loading strip: the last few tools she reached for
            body["steps"] = steps[-12:]
        try:
            self.gw.post("/api/runner/say", body, 20)
        except (OSError, ValueError) as e:
            log("couldn't tell the café:", e)

    def turn(self, prompt, routine):
        turn_id = str(int(time.time() * 1000))
        text, final, why, last_sent, steps = "", None, None, 0.0, []
        for ev in self.driver.events(prompt):
            kind = ev[0]
            if kind == "awake":
                self.say(turn_id, "", False, routine, steps)
            elif kind == "start":
                text = ""
            elif kind == "delta":
                text += ev[1]
                if time.time() - last_sent >= SAY_EVERY:
                    self.say(turn_id, text, False, routine, steps)
                    last_sent = time.time()
            elif kind == "text":
                text = ev[1]
                self.say(turn_id, text, False, routine, steps)
            elif kind == "tools":
                steps += ev[1]
                self.say(turn_id, text, False, routine, steps)
            elif kind == "result":
                final, why = ev[1], ev[2]
        said = (final if final is not None else text).strip()
        if not said:
            said = SORRY + ((" (" + why + ")") if why else "")
        self.say(turn_id, said, True, routine)
        log("said %d characters%s" % (len(said), " (stopped)" if why and final is None and text else ""))


def main():
    url, key = os.environ.get("CATIO_URL", "").strip(), os.environ.get("CATIO_QUEEN", "").strip()
    if not url or not key:
        sys.exit("Set CATIO_URL (the gateway's address) and CATIO_QUEEN (the queen's key): harness/runner/README.md says how.")
    home = Path(os.environ.get("CATIO_QUEEN_DIR") or (Path.home() / ".catio" / "queen")).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    runner = Runner(Gateway(url, key), home)
    model_url = os.environ.get("CATIO_MODEL_URL", "").strip()
    if model_url:
        runner.driver = ModelDriver(runner, model_url, os.environ.get("CATIO_MODEL_KEY", "").strip(), os.environ.get("CATIO_MODEL", "").strip())
    else:
        claude = shutil.which(os.environ.get("CATIO_CLAUDE") or "claude")
        if not claude:
            sys.exit("claude isn't on the PATH: install Claude Code and sign in, or set CATIO_CLAUDE to where it is, "
                     "or set CATIO_MODEL_URL to an OpenAI-compatible model's address instead.")
        runner.driver = ClaudeDriver(runner, claude)
    try:
        runner.run()
    except KeyboardInterrupt:
        runner.interrupt()
        log("the queen's runner is down: she sleeps until it runs again.")


if __name__ == "__main__":
    main()
