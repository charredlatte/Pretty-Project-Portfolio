# KittyChat Café

Every AI session you have on the go, as a cat in a little pixel-art café. Each session is a cat that plays while it
works, sleeps when it's done, and **meows** when it's waiting on you: point at it and it says what it needs. Chats in
an app that no connector can read, like a business plan or a legal question, you adopt as cats by hand. One queen cat,
Ninine, runs the place for you.

**It is not tied to one AI company.** Anything that speaks MCP joins as a cat: Claude Code, Codex, Gemini CLI, Grok,
Cursor, Antigravity, or a script of your own. The café page itself runs in a plain browser and needs no assistant at
all, and the small model that makes the café's own judgement calls isn't Claude either.
[Which assistants it works with](#which-assistants-it-works-with) is the honest table, part by part.

Made in the open by Charlotte Badot. [Which assistants it works with](#which-assistants-it-works-with) ·
[Run your own](#running-your-own) · [What you get](#what-you-get) ·
[Open source, and the hosted café](#open-source-and-what-stays-behind-the-paywall)

## In plain words

**All your AI chats, in one cozy café.** Using AI means a dozen chats open at once, often across two or three
different assistants, and you forget which one is waiting for you. KittyChat Café turns each chat into a cat in a
little café. You see who is busy, who is done and who needs you, and one friendly queen cat helps you run the place.
You never need to know what's under the hood.

| In real life | In the café |
|---|---|
| An AI chat or coding session, whoever makes it | A cat |
| A project (a website, a shop, a legal file) | A room, with a filing cabinet |
| A chat waiting for your answer | A cat that meows; point at it and it says what it needs |
| A chat that has finished | A cat asleep |
| Your main assistant | The queen, who sits in the entrance hall and does the errands |
| You | The owner of the café |

How it connects, start to finish:

1. You work with your assistants as usual. Each coding session becomes a cat on its own, and its project decides its
   room. A chat in an app, which no connector can read, you add as a cat by hand from a room's menu.
2. Each cat checks in at a small always-on online front desk (the gateway) with a short note: working, finished, or
   stuck and needs you. The front desk doesn't care which company made the cat.
3. The café page shows what the front desk knows. Busy cats look busy, sleeping cats sleep, and a badge counts the
   ones that need you.
4. You answer from the same page: click a cat, type a line or drop a file on it. The cat finds it the next time it
   checks in.
5. The queen handles the rest: she keeps what you give her, runs your routines, and can set a stuck cat's homework as
   a short quiz. She thinks on your own computer.

**Or think of it as a car.** A model on its own is a stripped car: a brilliant engine and nothing else. No seatbelts,
no windshield, no brakes, no tires. You can drive it if you know engines. The café is the rest of the car. **The
engine is yours and you bring your own** — Claude, Gemini, Grok, Codex, or several at once, each paid to its own
provider; the café never resells anyone's tokens. Your repositories are the tires, where the work meets the road. The
café page and the front desk are the windshield and the dashboard. The house rules are the seatbelts and brakes:
checks an agent can't skip, and anything guessed waits for you. The litter box is the glovebox, for loose notes and
held pull requests. And Ninine, the queen cat, drives.

Your private chats stay in your own account, never in this repository.

**Where it stands.** The code is open source and you can run your own café today (see
[Running your own](#running-your-own)). A hosted café with nothing to install is planned and not open yet.
Separately, Charlotte plans to launch the KittyChat Café app in December 2027. The pixel art comes from third-party
packs that cannot be shared, so check each pack's terms before posting screenshots.

**Invited to someone's café?** An invite is a café of your own on someone else's front desk, so most of
[Running your own](#running-your-own) is done for you. Open the invite link, pick a handle and a password, and keep
the key it shows you in your password manager: it is your cats' key, yours alone. Then do step 1 (your assistant) and
step 4 (the check-ins), with `CATIO_URL` set to the café's address (your invite link up to `/signup`) and
`CATIO_TOKEN` set to your key. Skip steps 2 and 3: your café is at that address, behind your handle and password. It
draws no house and no cats: the art packs' licences are personal, so only the café owner's own café is given them.
Ninine's runner (step 5) needs a queen's key of your own:
[`harness/gateway/README.md`](harness/gateway/README.md#the-queen-and-her-runner) says how to make one.

Everything below is the detail.

## Which assistants it works with

Three parts of the café answer this question differently, so here they are apart:

- **The café page** needs no AI at all. It is one HTML file with no build step and no dependencies. It runs in any
  browser, from your own front desk's address or a folder on your computer.
- **The cats** are whatever you run. Any client that speaks MCP reports to the front desk and becomes a cat, with its
  own provider and model shown on its card (`report_status` carries them: `openai`, `google`, `anthropic`, `local`,
  and a model like `gpt-5` or `gemini-2.5-pro`). This is the part that makes the café compatible with any agentic AI
  distributor, and it is true today.
- **The queen's runner** drives Claude Code today, and only that. She is one program on your own computer
  (`harness/runner/queen.py`) that runs one model turn per thing you say to her; the command it builds is one
  function, `Turn.args()`, and another CLI means writing that function for it once. Codex, Gemini and the rest are on
  the roadmap as *drivers* in [`docs/engine.md`](docs/engine.md); until then they are cats, not the driver.

| Your assistant | Joins as a cat | Checks in by itself | Drives the queen |
|---|---|---|---|
| **Claude Code** (terminal, cloud, IDE) | Yes | Yes, automatically: the house-rules plugin's hooks | Yes, today |
| **Codex CLI** | Yes, over MCP | When its `AGENTS.md` tells it to | Not yet |
| **Gemini CLI** | Yes, over MCP (an address and a header) | When its `GEMINI.md` tells it to | Not yet |
| **Antigravity** (Google's agent editor) | Yes, through `catio_bridge.py` | When its rules file tells it to | Not yet |
| **Cursor** | Yes, over MCP | When its Cursor rules tell it to | Not yet |
| **Anything else that speaks MCP** (Grok, Windsurf, Zed, a script of your own) | Yes, the same two lines of config | When its own instructions file tells it to | Not yet |
| **A chat in any app** (ChatGPT, Gemini, Grok, Claude) | Adopt it by hand, from a room's menu | — | — |

"Checks in by itself" is the one real difference between Claude Code and the rest, and it is a difference of
plumbing, not of welcome. Claude Code has a plugin whose hooks report every session without being asked. Every other
client is told to report in its own instructions file, and then does. A check-in for other agents as easy as the
plugin is on the roadmap ([`docs/plan.md`](docs/plan.md); the first person other than Charlotte to run a café reached
for Gemini first, which is how the bridge came to exist — he wrote it).

**How any agent joins.** Two lines of configuration, then one paragraph of instructions.

- A client that takes an address and a header (Gemini CLI's `"httpUrl"` and `"headers"`, or
  `claude mcp add --transport http catio <gateway>/mcp --header "Authorization: Bearer <key>"`) points straight at
  your front desk's `/mcp`, with one of your agents' keys.
- A client that can only start local programs (Antigravity, Cursor, Claude Desktop) runs
  `harness/mcp/catio_bridge.py` with `CATIO_URL` and `CATIO_TOKEN` in its environment, which passes everything on to
  the front desk. Standard library Python, nothing to install.
- Then, in the client's own instructions file (`AGENTS.md`, `GEMINI.md`, Cursor rules): *"You are a cat in my
  KittyChat Café. Read `house_rules` from the catio server and follow them. Call `report_status` when you start, when
  you need me, and when you finish, and check `inbox` between tasks."*

The exact config per client, and the no-front-desk case (`harness/mcp/catio_mcp.py` as a local stdio server, which
keeps its cats on one computer), are in
[`harness/README.md`](harness/README.md#other-agents-and-models-the-catio-mcp-server), "Which server, for which
café". If an agent registers a `wake` command — `["codex", "exec", "resume", "{session}", "{message}"]`,
`["gemini", "-p", "{message}"]` — the local server runs it the moment something is dropped on that cat.

**The house rules reach every agent, not just Claude Code.** The rules themselves are plain text
(`harness/rules.json`), and any cat reads them with the `house_rules` tool. Claude Code is the one client where they
are *enforced* rather than read, because hooks exist there to enforce them.

**Two models in the café that are nobody's assistant.** The café makes its own small judgement calls with a
decision model that answers typed questions rather than prose — Clef by default, and
[the decider](#the-judgement-calls-it-makes-itself) below says what it is. And the brain's file sorter, on your own
computer, takes any OpenAI-compatible endpoint: Ollama, LM Studio, OpenAI, Gemini's. Neither is Claude.

**What is Claude-shaped, honestly.** The queen's runner, as above. The house rules' enforcement, as above. And one of
the three places the café page can run: a private claude.ai artifact, which was Charlotte's original and is still
hers. The other two places — your front desk's own address, and a folder on your computer — involve no Claude at all.

**Walked through end to end so far:** Claude Code, and Antigravity through the bridge. The rest are the same two
lines, and `report_status` was built for them from the start. If one of them trips, open an issue and say where: that
is how the bridge got written.

## Running your own

You can run your own café today, from this repository, for free. It needs a terminal (steps 2 to 5): if you only use
assistants in a browser, the hosted café is the one for you, and it isn't open yet. The engine is yours already; this
section fits the rest of the car around it, one part at a time. Each step says what to click or type and how you know
it worked. Stop after step 3 and you have a café of your own with your rooms in it; step 4 fills it with cats, and
step 5 brings Ninine.

**Before you start, you need:**

- an **AI assistant you already use**, with a CLI or a client that speaks MCP (the table above). For the queen, and
  for the automatic check-ins, that means Claude Code on a Claude plan that includes it (Pro or Max);
- a **GitHub** account, with your projects in repositories (the café files each project by its repository);
- **Git** (git-scm.com; on Windows, Git for Windows), for step 2's `git clone`;
- a computer with **Python 3** (python.org, or the Microsoft Store on Windows) and, for the Claude Code plugin,
  **Node.js** (nodejs.org). On Windows, type `python` wherever this README says `python3` (the plugin's own hooks pick
  `py` or `python` there by themselves);
- a free **Cloudflare** account (cloudflare.com) for the front desk;
- the **cat art**: the packs are not in this repository and cannot be (their licences forbid sharing). Most have a
  free tier; the list is in [`catio/art/CREDITS.md`](catio/art/CREDITS.md). Without them the café draws no house and
  no cats and says so on its sign. Today the house and the cats need all ten packs at once, and one of them,
  `plants.zip`, has no public source yet, so a full build is Charlotte's alone for now. The interface alone builds
  from the Sprout Lands UI pack, and the café works without the rest, on plain panels.

### Step 1: your assistant

Whatever you already use. If that is Claude Code, in a terminal (Terminal on a Mac, PowerShell on Windows):

```bash
npm install -g @anthropic-ai/claude-code
claude
```

Type `/login` if it asks. If it is Codex, Gemini CLI, Cursor, Antigravity or anything else, install it as its own
maker says; step 4 is where you point it at your café. **It worked when** your assistant answers you.

### Step 2: your projects, and your copy of the café

The café files each cat into a room by its GitHub repository, so your projects want to be in repositories. Then fork
this one: on GitHub, open <https://github.com/charredlatte/Pretty-Project-Portfolio> and press **Fork**. Your fork is
the copy the later steps change, push to and deploy.

```bash
git clone https://github.com/<your GitHub name>/Pretty-Project-Portfolio
cd Pretty-Project-Portfolio
```

The art packs' zips go in one folder, and `python3 catio/tools/build-art.py <that folder>` draws the house and the
cats from them, naming each zip by what is inside it. **It worked when** you have the repository and, if you have the
packs, `catio/art/licensed/` is full.

### Step 3: the front desk, on Cloudflare

The gateway is a small program that runs on Cloudflare's free plan and never sleeps. Every cat checks in at it,
whoever made that cat, so the café shows live cats from every assistant at once; it is also where your café page
lives, behind your own password, and what Ninine answers through. The five steps with every screenshot's worth of
detail are in [`harness/gateway/README.md`](harness/gateway/README.md). In short:

1. On Cloudflare, **Workers & Pages → Create → Import a repository → your fork**. Name the Worker `catio-gateway`,
   root directory `harness/gateway`, branch `main`, and deploy. Its address looks like
   `https://catio-gateway.<your name>.workers.dev`. Another name works if `name` in `harness/gateway/wrangler.jsonc`
   on your fork says the same, or Workers Builds refuses the build.
2. On the Worker, **Settings → Variables and Secrets** (not Settings → Build, whose variables never reach the running
   Worker), add four **Secrets** in one go, then deploy again. Add each as a Secret, not a Text variable: every
   deploy from GitHub wipes the Text ones.
   - `CATIO_HANDLE` — the name you sign in with, 2 to 31 lower-case letters, digits or dashes;
   - `CATIO_TOKEN` — a long random string: the key your cats check in with;
   - `CATIO_PASSWORD` — your own sign-in, 16 characters or more;
   - `CATIO_QUEEN` — another long random string: the driver's key.

   **Add the handle together with the password, not after.** The very first request that reaches the Worker with
   `CATIO_PASSWORD` set makes the first account — even just opening the address in a browser — and names it
   `CATIO_HANDLE`, or `charlotte` if that isn't there yet, for good.

   Keep all four in your password manager, and give them out only as these steps say: the cats' key to your agents
   (step 4), the driver's key to your own computer (step 5), the password to nobody.
3. Upload the art to it from your clone (and again whenever you rebuild the art). On a Mac or Linux:

   ```bash
   CATIO_URL="https://catio-gateway.<your name>.workers.dev" CATIO_TOKEN="<your cats' key>" python3 harness/gateway/cafe/move-in.py
   ```

   On Windows, in PowerShell, in the folder you cloned:

   ```powershell
   $env:CATIO_URL = "https://catio-gateway.<your name>.workers.dev"
   $env:CATIO_TOKEN = "<your cats' key>"
   python harness\gateway\cafe\move-in.py
   ```

**It worked when** opening the Worker's address in a browser asks for your handle and password, and then opens on a
seven-step wizard: your café's name, your rooms, your repositories. If the address shows warning lights instead, the
account isn't made yet, and each light says which secret the Worker can't see or what's wrong with it.

**What is still Charlotte's.** The page and the harness were built for one café first, and a few of her values are
written into them: her café's link, her GitHub name, her install lines.
[`docs/self-hosting.md`](docs/self-hosting.md) lists each one and what to set it to in your fork.

**Make it yours without touching the code.** Your café's name is the wizard's first step; rooms are *Edit rooms*;
colours, fonts and art are *The look*, or your own drawings beside the page in `catio/art/skin/`. All three are in the
House menu, and the look travels as a design tokens file that Figma's variables import and export.
[`CONTRIBUTING.md`](CONTRIBUTING.md) says what stays on your fork and what comes back here. Press **Sync fork** on
GitHub now and then, and always before reporting a problem.

### Step 4: the check-ins, so your cats are live

Now tell your assistants where the front desk is. Two values do it everywhere: `CATIO_URL` (your café's address — the
Worker's, or the address of the café you were invited to) and `CATIO_TOKEN` (your own cats' key, never someone
else's).

**Claude Code** has a plugin that reports every session by itself, and brings the house rules with it: a read-only
audit before any change, a check before any browser, nothing pushed to your default branch, and anything guessed held
for you to review. Install it once (use your fork's address if you changed it):

```bash
claude plugin marketplace add https://github.com/charredlatte/Pretty-Project-Portfolio.git
claude plugin install kittychat-house-rules@kittychat --scope user
```

Then put the two values where your sessions see them: on your computer, in `.claude/settings.json` in your home
folder (`C:\Users\<you>\.claude\settings.json` on Windows; make the file if it isn't there) as
`{ "env": { "CATIO_URL": "https://…", "CATIO_TOKEN": "…" } }`, or add the `"env"` part beside what is already there.
For sessions on claude.ai, open the environment menu in a session's title bar → Edit, add the same two, allow the
Worker's address under Network access, and put the two install lines above in the setup script, since a cloud session
starts fresh each time ([`harness/README.md`](harness/README.md#in-cloud-sessions)).

Two of the rules call skills that aren't in this repository: the read-only audit calls `ponytail-audit` (from
[ponytail](https://github.com/DietrichGebert/ponytail)) and the check before any browser calls
`browser-agent-preflight`. Install them, or switch their rules off in a repository's own
`.claude/catio-rules.json`, such as `{"opening_audit": false, "preflight": false}`. To update the plugin later:
`claude plugin update kittychat-house-rules@kittychat`.

**Every other assistant** joins over MCP, as [Which assistants it works with](#which-assistants-it-works-with)
describes: point it at `<your address>/mcp` with an agents' key, or run `harness/mcp/catio_bridge.py` if it can only
start local programs, and add the one paragraph to its instructions file. Make a key per agent in the House menu →
**Keys**, so you can retire one without touching the others.

**It worked when** a new session of any of your assistants turns up in the café as a cat, and goes busy as it works.
For Claude Code, `claude plugin list` shows `kittychat-house-rules` and a new session opens with its read-only audit.

### Step 5: Ninine's runner, on your computer

The queen thinks on your own computer, on your own plan, so she costs nothing extra and runs only while your computer
does. She drives Claude Code today (see [Which assistants it works with](#which-assistants-it-works-with)). Give her
the address and her key, then start her from the repository's folder.

On Windows, in PowerShell (`setx` keeps the two for every new window but doesn't change the one it ran in, so open a
new window afterwards):

```powershell
setx CATIO_URL "https://catio-gateway.<your name>.workers.dev"
setx CATIO_QUEEN "<the driver's key>"
cd <the folder you cloned in step 2>
python harness\runner\queen.py
```

On a Mac or Linux (`export` lasts only for that window; put the two lines in `~/.zshrc` or `~/.bashrc` to keep them):

```bash
export CATIO_URL="https://catio-gateway.<your name>.workers.dev"
export CATIO_QUEEN="<the driver's key>"
python3 harness/runner/queen.py
```

**It worked when** the window says *the queen's runner is up* and, in your café, pointing at Ninine says she is here.
Keep the window open; close it and she falls asleep. [`harness/runner/README.md`](harness/runner/README.md) has the
details and how to start her with the computer.

### Step 6: open the doors

Open your café, say hello to Ninine, drop a file on a cat and watch it pick the file up at its next turn. The sign
under the brand shows only when something is wrong, and then it says how to fix it.

### Other places the page can run

The café page is one HTML file, so it runs in three places. Your front desk's address, above, is the one that needs
no assistant and shows live cats from every vendor. The other two:

- **A folder on your own computer**, with no account anywhere: `python3 catio/tools/bundle.py`. See
  [On your own computer](#on-your-own-computer).
- **A private claude.ai artifact**, which was the original. `claude --plugin-dir catio-plugin`, then *set up my café*;
  the skill walks you through rooms, repositories and publishing. There the cats come from claude.ai's built-in Claude
  Code Remote connector, which refuses a page's read often enough that the café falls back to a saved copy of your
  sessions ([`docs/live-sessions.md`](docs/live-sessions.md)). It is the most Claude-shaped way to run the café and
  the least capable one; the front desk is better.

The three keep their own data and don't share changes.

## What you get

- **A manor that fills the screen**, seen from above in a meadow, one floor at a time: a cat café downstairs, private
  rooms upstairs, with the ground floor faded underneath. Each room is a space for one kind of work, and each project
  files into a room. There are no signs on the map and nothing is drawn on the cats: point at a room and it says its
  name, point at a cat and it says what it needs.
- **Cats that show what your sessions are doing**, whichever assistant runs them. A working session plays, a finished
  one sleeps and one waiting on you meows. Every cat waiting on you lines up at the front door, the longest wait
  first, and the brand counts them. Cats walk: through the doorways when they change room, up the stair to nap in the
  attic, and in by the front door when they're new. Every cat of one project wears the same coat, which you choose
  from the project's cabinet, and its card names the model and provider behind it.
- **Answer from the café.** Click a cat to talk to it, drop a file on it, pause it or wrap it up. Drop a file on a
  room or the house instead and the brain sorts it to the right cat, or keeps it in its tray.
- **A queen who runs the place.** Ninine sits in the entrance hall, is nobody's session and never leaves. She keeps
  what you give her, looks after the other cats for you, runs the routines you set her and talks in the manner you
  give her, aloud if you turn her voice on. Cats bring her what they have to say. Anything waiting on you, a stuck
  cat's question, a loose note to file or a decision, comes to her as homework: a card you answer with a tap. She is
  never counted among the cats that need you; she is the one who tells you about them.
- **Filing cabinets** in the rooms hold their projects with all their cats, archived and napping ones included, and
  each project's map: its main ideas, how they connect, and questions you can ask a cat with one click. Project maps,
  in the House menu, lays every map out as a dashboard you can pin and arrange.
- **Make it yours.** Every colour, font and size, and most of the art, can be swapped with no code change, from The
  look in the House menu or a skin file beside the page (`art/skin.json`), so the café can wear your own drawings.
  The look exports and imports as a W3C design tokens file, which is what Figma's variables speak.
- **House rules** that every session under them follows and can't talk its way around: a read-only audit before any
  change, a check before any browser, and nothing pushed to your default branch. A repository can let its sessions
  merge their own pull requests; then anything guessed is held for you to review
  ([`harness/README.md`](harness/README.md)).

### Getting around

- **Moving**: drag the house to pan it (with any mouse button) and use the wheel or a pinch to zoom around the
  pointer. The map panel, top right (bottom right on a phone), zooms in, out and back to the whole house, and holds a
  minimap of the floor you're on with your view framed: click it to go somewhere, drag the frame, double-click a room
  to look in. It starts folded away as a little map icon; its button (or M) unfolds it.
- **Floors**: the stair in the entrance hall, the floor tabs under the minimap, or Page Up / Page Down. The other
  floor's tab carries a badge when cats there need you, so nothing hides upstairs.
- **Hover and click**: a room or a cat lights up and says its name when you point at it; click it for its menu,
  beside it, until you click elsewhere or press Escape. On a phone a tap does the same. Every menu is short: the name
  and one line, who needs you, then a list of actions. A room's are Look in, Files, Add files, Add a cat and Edit
  room; a cat's are Open session, Talk, Add files and Look in. Double-click a room to look in, or a cat for its card.
- **The brand**, top left, is the House button: whether the cats are live, then Quest log when anything waits, the
  brain, the house rules, Project maps, Edit rooms, The look, Set up again…, the cats napping in the attic, Keys
  (on your café's own address, where your agents' keys are made and retired), Check now, sound and still cats.
- **With a keyboard**, Tab lands on the house once. The arrow keys move from room to room, Enter steps into a room's
  menu and Escape steps back out. + / − / 0 zoom, and Shift with the arrows moves the view.
- **Edit rooms** shows the manor as a plan, a floor at a time: rename a room, say what lives there, list the
  repositories whose cats move in, open or close it, and choose the room new cats come in to.
- **The sign** under the brand shows only when something is wrong, and then it says how to fix it.

### The manor

A real two-storey plan, drawn in a storybook Transylvanian Baroque: ochre limewash with stucco corners outside,
plaster and oak inside, stained glass, and a pediment over the front door. It stands among spruce woods, with lamp
posts along the drive, a fountain, a well and a pond. Both floors stand on one grid, so every upstairs wall stands on
a downstairs wall. It runs from public to private: the café downstairs, the quiet rooms upstairs.

| Floor | Room | What's there |
|---|---|---|
| Ground | Café | tables, and a big one for plans |
| Ground | Kitchen | the counter, straight ahead from the front door, behind the stair |
| Ground | Cat lounge | a fireplace between tall windows, and a cat tree. New cats arrive here unless you choose another room |
| Ground | Craft room | bottom left. Its bay window is a shop window on the drive |
| Ground | Entrance hall | the front door, the stair up the middle, and the queen's seat |
| Ground | Terrace | a glass verrière, with the cat flap out to the catio |
| Outdoors | Catio | fenced decking at the bottom right, with a cat tree, a shade tree and a rose-arch gate |
| Upstairs | Library | over the café: the brain, where dropped files are sorted, and the litter box |
| Upstairs | Bedroom and ensuite | over the cat lounge, for what is kept quiet |
| Upstairs | Landing | open over the kitchen and the hall, round the stairwell. The attic ladder is here |

Every room can be renamed, closed, or pointed at your own repositories. Outside, the drive runs from the front steps
round a fountain with a praying statue to a stone archway with its wooden doors open, with parterres, a bench and a
signpost to the catio either side.

## How it works

### How it knows what the cats are doing

- **Every cat checks in at the front desk** (`harness/gateway/`) when it starts, when it needs you and when it
  finishes, so its cat is live wherever you open the café. Claude Code sessions do it from the plugin's hooks; every
  other agent does it by calling `report_status`. Its state decides its mood; its GitHub repository decides its room.
- **Rooms, renames, moves, adopted chats and what the queen keeps** live in the café's own database, so they follow
  you between phone and computer. Nothing you do on the page is written to a repository.
- **In the claude.ai artifact café only**, sessions can also come from claude.ai's built-in Claude Code Remote
  connector (`list_sessions`), read as you from inside the page. claude.ai refuses that read often (it did when last
  checked, 2 October), and there is nothing for you to switch on, because Claude Code Remote is built in rather than
  added as a connector: the cats then come from a copy of your sessions that a session saved to the database, and the
  sign gives its time, "Saved copy · 17:02". Cats that report to the front desk stay live either way. Each refusal,
  and how to refresh the copy: [`docs/live-sessions.md`](docs/live-sessions.md).

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working or running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions and ones waiting for review, once they're a week old, and archived sessions nap in the attic, out
of sight: the brand's count is only what really waits on you. Turn on Sound and a cat that starts meowing makes a
small meow.

### How what you send reaches a session

In the car, this is **the intercom**. You speak from the driver's seat (the café page); a cat hears you where it sits.
Everything you send — a line typed to a cat, a file dropped on it, a Pause or Wrap up — is **written down the moment
you send it**, so nothing is lost if the cat is asleep. From there it takes one of three roads, by who it is for:

- **To a cat, with the front desk.** The front desk keeps the note in that cat's pigeonhole. Each cat checks in every
  time it finishes a turn, and the desk hands over whatever is in the pigeonhole, once: the cat's **next turn is your
  note**, so a cat that is working gets your words as soon as it finishes what it is saying. Its reply comes back
  through the same desk and shows in its conversation on the page at once. A cat that was already asleep still waits
  for its next turn. If it registered a `wake` command on a local server, it is started then and there instead.
- **To a cat, with no front desk.** The note is left on the cat's seat, in the café's own database. Nobody can shake a
  sleeping cat awake, so it reads the note the next time it is up, at the start of its next turn: the house rules make
  it look at its seat first, do what the note asks, answer on the cat and tick the note as read.
- **To Ninine, the driver.** The queen is not a cat you hired; she is the one driving. When you talk to her, the front
  desk rings **her runner** on your own computer. The runner is where she thinks: it starts one locked-down turn for
  each thing you say or each routine that comes due (she can use the café's tools and nothing else: no commands, no
  files), and streams her answer back through the desk so the page shows her talking as she goes. The front desk is
  her face, ears and memory; your computer is her brain. What she tells another cat reaches it by the road above, like
  your own words would.

What no road can do: wake a cloud session that has stopped. Only its own service can start a session's next turn, and
claude.ai doesn't let a web page do it; why is in
[`harness/README.md`](harness/README.md#why-the-café-cant-push-into-a-session). A CLI agent on your own computer has
no such limit, which is what a `wake` command is for. Each hop, program by program, and how the design holds up on
scale, speed, extensibility, security, debugging and tests: [`docs/delivery.md`](docs/delivery.md).

### The judgement calls it makes itself

Some of what the café does is a decision rather than a task: which project a dropped file belongs to, whether a note
is settled or still waiting on you, which cat needs you first, whether a task is easy enough for a cheap model. Those
go to **the decider** (`harness/gateway/src/decide.js`), never to one of your assistants.

It *answers* those questions and never acts on them. In particular it does not pick the model for a piece of work,
which its name invites you to assume: a session asks it, weighs the answer against a confidence floor, and names the
model itself — and a separate rule refuses any assignment that names none
([`docs/delegation.md`](docs/delegation.md)).

It is a different kind of model, and the difference is the point. You hand it a state and a set of named, typed
questions — yes/no, a choice between options, a score on a scale — and it hands back numbers and nothing else: no
prose, no tool calls, no turn to take. Up to sixty-four questions about one state, in a
single call with an eight-second budget. That is also why the decider can never be the thing that *drives* a cat: it
cannot write a sentence or call a tool. Driving a cat with her runner is Claude Code's job today, and other CLIs'
in time ([`docs/engine.md`](docs/engine.md)); deciding is the decider's.

- **It needs no setting up.** With nothing set it is Clef on Cloudflare's Workers AI — Cloudflare's own model, open
  weights, inside the free plan. `DECIDE_MODEL` swaps in another Workers AI model, Jev among them; `DECIDE_URL`
  points at any server speaking the same API, such as a Laya on a machine of your own. The switches are in
  [`harness/gateway/README.md`](harness/gateway/README.md#decisions-the-decide-tool).
- **It is the one model the café runs for itself.** Everything else runs on your own key, paid to your own provider:
  the café never resells tokens.
- **It is watched before it is trusted.** Each answer can be logged beside what the old code path would have chosen,
  and how sure it was, so you can read a week of the log before letting it decide anything for real. The rubric and
  the rollout: [`docs/delegation.md`](docs/delegation.md).

### The litter box, and the one thing it will not do

Not everything a session finds is work it can finish. A loose end, a question only you can answer, a fact learned the
hard way, a pull request the rules held back: each lands in `litterbox/` as a note, and the sifter
(`python3 litterbox/sort.py`, a dry run until you add `--write`) does the sorting. It compresses what is finished,
drops what repeats another note, and piles the rest on its project's pile, `litterbox/<project>.md`.

The pile is where it stops, because **working out which project a note belongs to is a guess, and the sifter says so
in the pile's own header.** A pile marked that way is never filed, however many runs go by; new notes for that
project simply join it. It waits until you open it and delete that one comment, which is you saying the project is
right. Only then does the next run empty it into that project's own repository, under *Waiting on Charlotte*,
*Ideas not built*, *Facts learned* or *Findings*, and commit what it wrote. The sifter's own words for the rule:
*nothing filed is guessed.*

So the box is a one-way valve and you are the valve. It is also the reason a note that needs your decision is written
with no project at all: that is what sends it to a pile to wait, rather than out of the box. In the café the same
notes reach you as cards in the queen's quest log, one note a card, from the library's chest or the House menu — the
other way to check a pile, a tap an answer. Which header does what, dealing the cards, and how held pull requests get
here: [`litterbox/README.md`](litterbox/README.md).

## On your own computer

The café also runs from a folder, with no account anywhere. `python3 catio/tools/bundle.py` makes
`catio/dist/catio-local/` (and a zip of it): the page as one HTML file, all the art, the rooms in
`catio/data/rooms.json` (a browser takes them once, then Edit rooms or Set up again… changes them), and
`catio/data/sessions.json`, the last saved copy of your sessions. Go into the folder
(`cd catio/dist/catio-local`) and serve it with any static server, such as VS Code's Live Server or
`python3 -m http.server 8000` (`python -m http.server 8000` on Windows), and open <http://localhost:8000>.
Double-clicking `index.html` won't work: it needs the server.

The folder also carries the Catio MCP server, which serves the page and lets agents from any vendor join as cats
without a front desk: from inside the folder, `python3 harness/mcp/catio_mcp.py --serve . --port 8791`, then open
<http://localhost:8791>. Agents that join it are live; Claude Code sessions there are the saved copy, and adopted
chats, room names and project looks are kept in that browser.

Only a Claude Code session on claude.ai can make that saved copy (`claude` in your terminal can't read your list of
sessions): ask it to save your sessions for the café and send you the file (it runs `list_sessions`, then
`catio/tools/save-sessions.py`), put it in `catio/data/`, and run `bundle.py` again. Without it the café opens with no
Claude Code cats; cats from other vendors don't need it.

The folder holds your licensed art and your session titles, so it is for your own use: never commit it or share it.

## Open source, and what stays behind the paywall

The code is open source: the page, the harness, the gateway and the queen's runner, under the
[GNU AGPL-3.0](LICENSE). Anyone with GitHub can run their own café, free, with the clone above and a Cloudflare Worker
for the front desk. The licence asks one thing back: whoever runs a changed gateway as a service publishes the
change.

What is not open is the art, and what the hosted café sells is the running. The custom assets — the cat breeds, the
house and the interface drawn for the café — are Charlotte's, all rights reserved, and ship only to the hosted cafés
(the packs the page is built from today have their own terms, below). The hosted café adds accounts, keys, an address
of your own, and a runner you don't have to keep a computer on for. The repository is the developers' door; the hosted
café is everyone else's. The plans planned for it — Free, Basic, Early access and Set up for you — are drawn in
[`docs/kittychat-shop/README.md`](docs/kittychat-shop/README.md); their prices come with the hosted café. Building on
it, or setting cafés up for other people? The engine underneath, which model drives what, and what it still lacks as
a product, is [`docs/engine.md`](docs/engine.md).

**Support the work.** The café is built by one person, in the open, while it is in development:

- **Buy me a coffee**: https://buymeacoffee.com/[handle] *(page coming)*. One-off coffees and small memberships; they
  pay for the gateway's hosting and the médiateur, and put your name in the café's credits.
- **Back the app on Ulule**: https://ulule.com/[campaign] *(campaign coming, once the first cafés are open)*. It
  funds the app; the rewards are a year of the hosted café and a drawn cat of your own.

## Made from ten asset packs

Every piece of the picture and the interface comes from packs Charlotte chose; which pack drew what is in
[`catio/art/CREDITS.md`](catio/art/CREDITS.md), and the footer credits them all.

| Pack | Artist | In this repo? |
|---|---|---|
| [Cosy Cabin](https://marie-pepo.itch.io/cosy-cabin) | Marie Pepo | Yes: `catio/art/furniture.png`. The house mixes every pack, so it is not |
| [Cat Pack Mochi](https://toffeecraft.itch.io/cat-pack) and [Pochi](https://toffeecraft.itch.io/cat-retro), Cat UI | ToffeeCraft | No: the licence forbids redistribution |
| [Top Down Garden Castle](https://heosphorus.itch.io/) | Heosphorus | No: the licence forbids distribution |
| [Wood Garden](https://rowdy41.itch.io/wood-garden) | rowdy41 | No: it is baked into the same file as Heosphorus's pieces |
| [Pixel Art Top Down – Basic](https://cainos.itch.io/pixel-art-top-down-basic) | Cainos | No: the licence forbids redistribution |
| [Sprout Lands UI Pack – Basic](https://cupnooble.itch.io/) | Cup Nooble | No: the licence forbids redistribution, even modified |
| Game UI Pack – Pastel Edition | SC_siosio | No: the licence forbids redistribution, even modified |
| [Sprout Lands Sprites – Basic](https://cupnooble.itch.io/) | Cup Nooble | No: the same terms |
| [Little Dreamyland](https://starmixu.itch.io/little-dreamyland-asset-pack) | Starmixu & Utaskuas | No: the licence forbids redistribution, even modified |
| plants.zip | (no licence came with it) | No: treated as licensed |

The uncommitted art (`catio/art/licensed/`) ships only to a café's owner, signed in.

## The pieces

- `catio/index.html`: the whole page, with no build step and no dependencies.
- `catio/tools/`: the two floor plans and the furniture that write the manor (`manor.py`, `furniture.py`), the art
  build (`build-art.py`, `pip install pillow fonttools`), the localhost folder (`bundle.py`) and the skin
  (`skin.py`).
- `harness/`: the harness behind the page — the front desk (`gateway/`, with the decider in `gateway/src/decide.js`),
  the queen's runner (`runner/`), the Catio MCP server and bridge for every other agent (`mcp/`), and the
  `kittychat-house-rules` plugin. See [its README](harness/README.md).
- `catio-plugin/`: the plugin that sets up your own café; `.claude-plugin/marketplace.json` lists it and the harness
  plugin as the `kittychat` marketplace.
- `litterbox/`: the back burner, where loose notes land, piled by project and filed once checked. See
  [its README](litterbox/README.md).
- `catio-app/`: the café as a native C++ app for a phone, in progress. It draws the manor matching the page pixel for
  pixel, signs in to your front desk on a desk, and has not run on a phone. It ships with no pack art: the app
  fetches that from the front desk, behind your sign-in, on first run.
  [`docs/mobile-app.md`](docs/mobile-app.md) says exactly where it stands.
- `docs/`: the plan, the specs, the shop and the record, each listed by what it is for in
  [`docs/README.md`](docs/README.md). [`docs/engine.md`](docs/engine.md) is the one on models and drivers.
- `CLAUDE.md`: how to work on the page. `CONTRIBUTING.md`: how to send a change back, and how to run the tests.

The tests: `sh catio/test/run.sh` (the page, about seven minutes),
`python3 -m unittest discover harness/test`, `(cd harness/gateway && npm install && npm test)` (the front desk), and
`python3 -m unittest litterbox/test_sort.py litterbox/test_quiz.py`. The page's suite drives a headless browser;
what to set outside Charlotte's cloud sessions, and why a run without the licensed art is not a verdict, is in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

The code is © 2026 Charlotte Badot, under the [GNU Affero General Public License v3.0](LICENSE), except
`harness/skills/graphify/`, which is [graphify](https://github.com/Graphify-Labs/graphify)'s own, by Safi Shamsi and
the Graphify contributors, vendored unmodified under its Apache-2.0 licence and notice in that folder. The art is not
covered: the packs keep their own terms (`catio/art/CREDITS.md`), and the café's own drawings are all rights
reserved.

**Whose idea each piece is.** The manor with a room per repository, the queen who keeps what matters, cats that walk,
the litter box and the quizzes filed back into each project are Charlotte's as written. The genre is not hers: a
pixel cat or pet that watches a coding session exists elsewhere ([Nekode](https://nekode.dev/),
[claude-cat-mod](https://github.com/matthlh/claude-cat-mod),
[claude-token-cat](https://github.com/lylaminju/claude-token-cat),
[cc-tamagotchi](https://github.com/davidurco/cc-tamagotchi), [codachi](https://github.com/vincent-k2026/codachi)),
and hooks that gate edits and merges are a common pattern. Three skills the house rules call are not in this
repository and are not hers: `ponytail-audit` (from [ponytail](https://github.com/DietrichGebert/ponytail), Dietrich
Gebert, MIT), `browser-agent-preflight` (a community skill) and `code-review` (Claude Code's own).
