#!/usr/bin/env python3
"""The queen's runner: the brain of the queen of the KittyChat Café, on Charlotte's own computer.

The queen is the cat in the café's entrance hall that Charlotte talks to. This waits on the gateway
(harness/gateway) for what she says to the queen and for the routines she set up, runs one Claude Code turn for
each, signed in with her own plan, with the Catio's tools as the queen's only tools, and streams what the queen
says back, so every open café shows it as she speaks. Stop, in the café, ends the turn.

    python3 harness/runner/queen.py

Environment:
    CATIO_URL        the gateway's address, https://catio-gateway.<name>.workers.dev
    CATIO_QUEEN      the queen's own key (the CATIO_QUEEN secret on the Worker), never the agents' key
    CATIO_QUEEN_DIR  where she keeps her state and works from (default ~/.catio/queen)
    CATIO_CLAUDE     the claude command, when it isn't on the PATH as "claude"
    CATIO_NOTIFY     a program to say homework on her desktop instead of the platform's own; it is called
                     with the text as its one argument. Set it empty for no notifications at all.

README.md says how to set it up. Standard library only; Python 3.9 or later.
"""
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
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHARACTER = HERE / "queen.md"     # who she is: the part that doesn't change
WAIT_TIMEOUT = 40                 # the gateway holds a wait up to 25 s
SAY_EVERY = 0.4                   # seconds between streamed updates to the café
GRACE = 10                        # seconds a stopped turn gets to end on its own
MAX_TURNS = "30"
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


class Runner:
    def __init__(self, gateway, home, claude):
        self.gw, self.home, self.claude = gateway, home, claude
        self.jobs = queue.Queue()      # what to do, in order: ("note", {...}) or ("routine", {...})
        self.child = None              # the turn in progress
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
        pause = 5
        while True:
            try:
                got = self.gw.post("/api/runner/wait", {}, WAIT_TIMEOUT)
                pause = 5
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:200]
                if e.code in (401, 503):
                    log("the gateway refused the queen's key:", detail)
                    os._exit(2)
                log("the gateway answered", e.code, detail)
                time.sleep(pause)
                pause = min(pause * 2, 60)
                continue
            except (OSError, ValueError) as e:
                log("no gateway:", e)
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

    # ---- one turn of Claude Code for each thing to do ----
    def run(self):
        threading.Thread(target=self.watch, daemon=True).start()
        log("the queen's runner is up:", self.gw.url, "· working from", self.home)
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

    def prompt_file(self):
        """queen.md, with what Charlotte set in the café (her name, manner and greeting) under it, in her folder."""
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
        path = self.home / "prompt.md"
        path.write_text(text, encoding="utf-8")
        return path

    def mcp_file(self):
        """The gateway as the queen's MCP server, with her key, in a file: a path crosses any shell unharmed."""
        path = self.home / "mcp.json"
        path.write_text(json.dumps({"mcpServers": {"catio": {"type": "http", "url": self.gw.url + "/mcp",
                                                            "headers": {"Authorization": "Bearer " + self.gw.key}}}}), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return path

    def args(self):
        args = [self.claude, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--append-system-prompt-file", str(self.prompt_file()), "--mcp-config", str(self.mcp_file()), "--strict-mcp-config",
                "--restricted", "--allowedTools", "mcp__catio", "--permission-prompts", "none", "--max-turns", MAX_TURNS]
        if self.state.get("session"):
            args += ["--resume", self.state["session"]]
        return args

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

    def turn(self, prompt, routine, retry=True):
        turn_id = str(int(time.time() * 1000))
        resumed = bool(self.state.get("session"))
        env = {k: v for k, v in os.environ.items() if not k.startswith("CATIO_")}   # the house-rules hook mustn't report her as a cat
        flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {}
        try:
            child = subprocess.Popen(self.args(), cwd=str(self.home), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **flags)
        except OSError as e:
            log("couldn't start claude:", e)
            self.say(turn_id, SORRY + " (claude didn't start)", True, routine)
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
        text, final, session, failed, last_sent, steps, awake = "", None, None, None, 0.0, [], False
        for line in child.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "system" and ev.get("session_id"):
                session = ev["session_id"]
                if not awake:   # she is up: the café shows her thinking before her first word
                    awake = True
                    self.say(turn_id, "", False, routine, steps)
            elif kind == "stream_event":
                e = ev.get("event") or {}
                if e.get("type") == "message_start":
                    text = ""   # a new message of hers: the café's bubble shows the one being written
                elif e.get("type") == "content_block_delta" and (e.get("delta") or {}).get("type") == "text_delta":
                    text += e["delta"].get("text") or ""
                    if time.time() - last_sent >= SAY_EVERY:
                        self.say(turn_id, text, False, routine, steps)
                        last_sent = time.time()
            elif kind == "assistant":   # a whole message at a time, when there are no partial ones
                blocks = (ev.get("message") or {}).get("content") or []
                parts = [b.get("text") or "" for b in blocks if b.get("type") == "text"]
                tools = [step(b) for b in blocks if b.get("type") == "tool_use"]
                steps += tools
                if parts and not text:
                    text = "".join(parts)
                    self.say(turn_id, text, False, routine, steps)
                elif tools:   # each tool she reaches for is told at once, not on the text's beat
                    self.say(turn_id, text, False, routine, steps)
            elif kind == "result":
                session = ev.get("session_id") or session
                if isinstance(ev.get("result"), str):
                    final = ev["result"]
                if ev.get("is_error") or (ev.get("subtype") and ev["subtype"] != "success"):
                    failed = str(ev.get("subtype") or "error")
        code = child.wait()
        with self.lock:
            self.child = None
        if session and session != self.state.get("session"):
            self.state["session"] = session
            self.remember()
        stderr = (errors[0] if errors else "").strip()
        if final is None and not text and code != 0 and resumed and retry:   # her session is gone: start afresh, once
            log("couldn't resume the queen's session; starting a new one.", stderr[-200:])
            self.state.pop("session", None)
            self.remember()
            return self.turn(prompt, routine, retry=False)
        said = (final if final is not None else text).strip()
        if not said:
            said = SORRY + ((" (" + (failed or stderr[-200:] or "exit %d" % code) + ")") if (failed or stderr or code) else "")
        self.say(turn_id, said, True, routine)
        log("said %d characters%s" % (len(said), " (stopped)" if code and final is None and text else ""))


def main():
    url, key = os.environ.get("CATIO_URL", "").strip(), os.environ.get("CATIO_QUEEN", "").strip()
    if not url or not key:
        sys.exit("Set CATIO_URL (the gateway's address) and CATIO_QUEEN (the queen's key): harness/runner/README.md says how.")
    claude = shutil.which(os.environ.get("CATIO_CLAUDE") or "claude")
    if not claude:
        sys.exit("claude isn't on the PATH: install Claude Code and sign in, or set CATIO_CLAUDE to where it is.")
    home = Path(os.environ.get("CATIO_QUEEN_DIR") or (Path.home() / ".catio" / "queen")).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    runner = Runner(Gateway(url, key), home, claude)
    try:
        runner.run()
    except KeyboardInterrupt:
        runner.interrupt()
        log("the queen's runner is down: she sleeps until it runs again.")


if __name__ == "__main__":
    main()
