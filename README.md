# KittyChat Café

Every Claude project you have on the go, as a cat in a little pixel-art café. Each Claude Code session is a cat that
plays while it works, sleeps when it's done, and **meows** when it's waiting on you: point at it and it says what it
needs. Chats on claude.ai that no connector can read, like a business plan or a legal question, you adopt as cats by
hand. One queen cat, Ninine, runs the place for you.

Made in the open by Charlotte Badot. [Run your own](#running-your-own) ·
[What you get](#what-you-get) · [Open source, and the hosted café](#open-source-and-what-stays-behind-the-paywall)

## In plain words

**All your Claude chats, in one cozy café.** Using AI means a dozen chats open at once, and you forget which one is
waiting for you. KittyChat Café turns each chat into a cat in a little café. You see who is busy, who is done and who
needs you, and one friendly queen cat helps you run the place. You never need to know what's under the hood.

| In real life | In the café |
|---|---|
| A Claude chat or coding session | A cat |
| A project (a website, a shop, a legal file) | A room, with a filing cabinet |
| A chat waiting for your answer | A cat that meows; point at it and it says what it needs |
| A chat that has finished | A cat asleep |
| Your main assistant | The queen, who sits in the entrance hall and does the errands |
| You | The owner of the café |

How it connects, start to finish:

1. You work with Claude as usual. Each chat becomes a cat, and its project decides its room.
2. Each cat checks in at a small always-on online front desk (the gateway) with a short note: working, finished, or
   stuck and needs you.
3. The café page shows what the front desk knows. Busy cats look busy, sleeping cats sleep, and a badge counts the
   ones that need you.
4. You answer from the same page: click a cat, type a line or drop a file on it. The cat finds it the next time it
   checks in.
5. The queen handles the rest: she keeps what you give her, runs your routines, and can set a stuck cat's homework as a
   short quiz. She thinks on your own computer.

**Or think of it as a car.** Claude on its own is a stripped car: a brilliant engine and nothing else. No seatbelts,
no windshield, no brakes, no tires. You can drive it if you know engines. The café is the rest of the car, and Ninine,
the queen cat, drives.

| The car | What it is here |
|---|---|
| The engine | Claude, your own |
| The driver | Ninine, the queen cat: she runs your routines and passes your words on, from your own computer |
| The tires | Your GitHub repositories, where the work meets the road |
| The windshield and the dashboard | The café page, and the front desk every cat checks in at: who's busy, who needs you |
| The seatbelts and brakes | The house rules: checks Claude can't skip, and anything guessed waits for you |
| The glovebox | The litter box: loose notes and held pull requests |

Your private chats stay in your own account, never in this repository.

**Where it stands.** The code is open source and you can run your own café today (see [Running your own](#running-your-own)).
A hosted café with nothing to install is planned and not open yet. Separately, Charlotte plans to launch the KittyChat
Café app in December 2027. The pixel art comes from third-party packs that cannot be shared, so check each pack's terms before
posting screenshots.

Everything below is the detail.

## Running your own

You can run your own café today, from this repository, for free. The engine (Claude's models in Charlotte's case) is yours already; this section
fits the rest of the car around it, one part at a time, in the order a novice should take them. Each step says what
to click or type and how you know it worked. The parts after the windshield are optional: stop after step 3 and you
have a café that shows your sessions; add the desk, the seatbelts and the driver when you want live cats, house rules
and Ninine.

The current cafe framework uses Claude Code to run the queen; other models (Grokbot, Codex, etc.) will be made available very soon. 

**Before you start, you need:**

- a **Claude** account on a plan that includes Claude Code (Pro or Max), signed in at claude.ai;
- a **GitHub** account, with your projects in repositories (the café files each project by its repository);
- a computer with **Python 3** (python.org, or the Microsoft Store on Windows) and **Node.js** (nodejs.org), for
  the plugin and the driver. On Windows, type `python` wherever this README says `python3`;
- for the front desk, a free **Cloudflare** account (cloudflare.com);
- the **cat art**: the packs are not in this repository and cannot be (their licences forbid sharing). Most have a
  free tier; the list is in [`catio/art/CREDITS.md`](catio/art/CREDITS.md). Without them the café draws no house
  and no cats and says so on its sign. Buy or download them first, so step 3 has something to show.

### Step 1: the engine. Claude Code, on your computer

Open a terminal (Terminal on a Mac, PowerShell on Windows) and run:

```bash
npm install -g @anthropic-ai/claude-code
claude
```

Type `/login` if it asks and sign in with your Claude account. **It worked when** `claude` opens a prompt that
answers you.

### Step 2: the tires. GitHub, connected to Claude

On claude.ai, open Settings, then Connectors (or the Code tab), and connect your GitHub account, giving it the
repositories you want as rooms. **It worked when** Claude Code on claude.ai lists your repositories to start a
session in.

### Step 3: the windshield. The café page, with your cats in view

Get the code and let Claude set the café up with you:

```bash
git clone https://github.com/charredlatte/Pretty-Project-Portfolio
cd Pretty-Project-Portfolio
claude --plugin-dir catio-plugin
```

Then say: *set up my café*. The skill walks you through your rooms, your repositories and publishing the page as
your own private claude.ai artifact, and tells you where to put the art packs' zips
(`python3 catio/tools/build-art.py <your zips>` draws the house and the cats from them). The page does the same on
its own: a café with no rooms yet opens a seven-step wizard. **It worked when** you open your café's link and your
sessions are cats in rooms. If the sign under the brand says *"The cat art isn't here"*, step back to the art.

If you would rather not use claude.ai at all, `python3 catio/tools/bundle.py` makes a folder that runs from any
static server on your own computer ([On your own computer](#on-your-own-computer)).

**What is still Charlotte's.** The page and the harness were built for one café first, and a few of her values
are written into them: her café's link, her GitHub name, her install lines. [`docs/self-hosting.md`](docs/self-hosting.md)
lists each one and what to set it to in your fork. Change them **before you publish** in this step, because the
page carries them, and the house rules of step 5 read them.

**Make it yours without touching the code.** Your café's name is the wizard's first step; rooms are *Edit rooms*;
colours, fonts and art are *The look*, or your own drawings beside the page in `catio/art/skin/`. All three are in
the House menu. Keep that on your fork: [`CONTRIBUTING.md`](CONTRIBUTING.md) says what stays there and what comes back
here. Press **Sync fork** on GitHub now and then, and always before reporting a problem: fixes land here first.

### Step 4: the dashboard. The front desk on Cloudflare

The gateway is a small program that runs on Cloudflare's free plan and never sleeps. Every cat checks in at it, so
the café shows live cats without asking claude.ai, and it is what Ninine answers through. The five steps, with
screenshots' worth of detail, are in [`harness/gateway/README.md`](harness/gateway/README.md). In short:

1. On Cloudflare, Workers & Pages → Create → Import a repository → your fork of this repository. Name the Worker
   `catio-gateway`, set the root directory to `harness/gateway`, the branch to `main`, and deploy. Its address
   looks like `https://catio-gateway.<your name>.workers.dev`. Another name works too, if `name` in
   `harness/gateway/wrangler.jsonc` on your fork says the same: Workers Builds refuses a build when the two differ.
2. On the Worker, Settings → Variables and Secrets (not Settings → Build, whose variables never reach the running
   Worker), add your handle and three **secrets** in one go, then deploy
   again. The handle is `CATIO_HANDLE`, the name you will sign in with, 2 to 31 lower-case letters, digits or
   dashes; add it as a **Secret** too, not a Text variable, because each deploy from GitHub wipes the Text ones
   and keeps the secrets. The secrets are `CATIO_TOKEN` (a long random string: the key your cats
   check in with), `CATIO_PASSWORD` (your own sign-in, 16 characters or more) and `CATIO_QUEEN` (another long
   random string: the driver's key). Keep the three secrets in your password manager, and give them out only as the steps below say: the cats' key
   to your sessions (step 5), the driver's key to your own computer (step 6), the password to nobody. **Add the
   handle with the password, not after:** the very first request that reaches the Worker with `CATIO_PASSWORD`
   set makes the first account, even just opening its address in a browser, and names it `CATIO_HANDLE` or, if
   that isn't there yet, `charlotte`, for good.
3. On claude.ai, Customize → Connectors → Add → Custom → Web. Name it `CATIO`, URL `<the address>/mcp`, sign in
   with your handle and `CATIO_PASSWORD` (five wrong tries lock the handle for a quarter of an hour), then open
   the connector and set its tools to **Always allow**.

**It worked when** opening the Worker's address in a browser asks for your handle and password, and the café's House
menu says the cats are live. If it shows warning lights instead, the account isn't made yet: each light says which
secret this Worker can't see, or what's wrong with it. Fix the crosses and reload.

### Step 5: the seatbelts and brakes. The house rules, in every session

The house rules are a Claude Code plugin. They make every session check in at the desk, collect what you sent, open
with a read-only audit, never push to your main branch, and hold anything guessed for you to review. Install it
once (use your fork's address if you changed what step 3 lists):

```bash
claude plugin marketplace add https://github.com/charredlatte/Pretty-Project-Portfolio.git
claude plugin install kittychat-house-rules@kittychat --scope user
```

Then tell your sessions where the desk is, with two environment variables: `CATIO_URL` (the Worker's address) and
`CATIO_TOKEN` (the first secret). On your computer they go under `"env"` in `~/.claude/settings.json`; for sessions
on claude.ai, open the environment menu in a session's title bar → Edit, add the same two variables, allow the
Worker's address under Network access, and put the two install lines above in the setup script, since a cloud
session starts fresh each time ([`harness/README.md`](harness/README.md#in-cloud-sessions)).

**It worked when** `claude plugin list` shows `kittychat-house-rules`, a new session opens with its read-only audit,
and its cat in the café turns busy as it works.

### Step 6: the driver. Ninine's runner, on your computer

Ninine thinks on your own computer, with your own Claude plan, so she costs nothing extra and runs only while your
computer does. Give her the desk's address and her key, then start her from the repository's folder.

On Windows, in PowerShell (`setx` keeps the two variables for every new window, so open a new one before the last
line):

```powershell
setx CATIO_URL "https://catio-gateway.<your name>.workers.dev"
setx CATIO_QUEEN "<the third secret>"
python harness\runner\queen.py
```

On a Mac or Linux, in the same terminal window (`export` lasts only for that window; put the two lines in
`~/.zshrc` or `~/.bashrc` to keep them):

```bash
export CATIO_URL="https://catio-gateway.<your name>.workers.dev"
export CATIO_QUEEN="<the third secret>"
python3 harness/runner/queen.py
```

**It worked when** the window says *the queen's runner is up* and, in the café, pointing at Ninine says she is
here. Keep the window open; close it and she falls asleep in the café. [`harness/runner/README.md`](harness/runner/README.md)
has the details and how to start her with the computer.

### Step 7: the keys. Open the doors

Open your café, say hello to Ninine, drop a file on a cat and watch it pick it up at its next turn. The sign under
the brand shows only when something is wrong, and then says how to fix it. Other agents (Codex, Gemini CLI, Cursor)
can join as cats too, through the Catio MCP server ([`harness/README.md`](harness/README.md#other-agents-and-models-the-catio-mcp-server)).

## What you get

- **A manor that fills the screen**, seen from above in a meadow, one floor at a time: a cat café downstairs, private
  rooms upstairs, with the ground floor faded underneath. Each room is a space for one kind of work, and each project
  files into a room. There are no signs on the map and nothing is drawn on the cats: point at a room and it says its
  name, point at a cat and it says what it needs.
- **Cats that show what your sessions are doing.** A working session plays, a finished one sleeps and one waiting on
  you meows. Every cat waiting on you lines up at the front door, the longest wait first, and the brand counts them.
  Cats walk: through the doorways when they change room, up the stair to nap in the attic, and in by the front door
  when they're new. Every cat of one project wears the same coat, which you choose from the project's cabinet.
- **Answer from the café.** Click a cat to talk to it, drop a file on it, pause it or wrap it up. Drop a file on a
  room or the house instead and the brain sorts it to the right cat, or keeps it in its tray.
- **A queen who runs the place.** Ninine sits in the entrance hall, is nobody's session and never leaves. She keeps what
  you give her, looks after the other cats for you, runs the routines you set her and talks in the manner you give
  her, aloud if you turn her voice on. Cats bring her what they have to say. Anything waiting on you, a stuck cat's
  question, a loose note to file or a decision, comes to her as homework: a card you answer with a tap. She is
  never counted among the cats that need you; she is the one who tells you about them.
- **Filing cabinets** in the rooms hold their projects with all their cats, archived and napping ones included, and
  each project's map: its main ideas, how they connect, and questions you can ask a cat with one click. Project maps,
  in the House menu, lays every map out as a dashboard you can pin and arrange.
- **Make it yours.** Every colour, font and size, and most of the art, can be swapped with no code change, from The
  look in the House menu or a skin file beside the page (`art/skin.json`), so the café can wear your own drawings.
- **House rules** that every session with the house-rules plugin follows, and Claude can't talk its way around: a
  read-only audit before any change, a check before any browser, and nothing pushed to your default branch. A
  repository can let its sessions merge their own pull requests; then anything guessed is held for you to review
  ([`harness/README.md`](harness/README.md)).
- **Other agents too.** Codex, Gemini CLI, Cursor or anything else that speaks MCP joins as a cat through the Catio
  MCP server.

### Getting around

- **Moving**: drag the house to pan it (with any mouse button) and use the wheel or a pinch to zoom around the
  pointer. The map panel, top right (bottom right on a phone), zooms in, out and back to the whole house, and holds a
  minimap of the floor you're on with your view framed: click it to go somewhere, drag the frame, double-click a room
  to look in. It folds away with its arrow (or M) and remembers.
- **Floors**: the stair in the entrance hall, the floor tabs under the minimap, or Page Up / Page Down. The other
  floor's tab carries a badge when cats there need you, so nothing hides upstairs.
- **Hover and click**: a room or a cat lights up and says its name when you point at it; click it for its menu, beside
  it, until you click elsewhere or press Escape. On a phone a tap does the same. Every menu is short: the name and one
  line, who needs you, then a list of actions. A room's are Look in, Files, Add files, Add a cat and Edit room; a
  cat's are Open session, Talk, Add files and Look in. Double-click a room to look in, or a cat for its card.
- **The brand**, top left, is the House button: whether the cats are live, then Homework when anything waits, the
  brain, the house rules, Project maps, Edit rooms, The look, Set up again…, the cats napping in the attic, Check now,
  sound and still cats.
- **With a keyboard**, Tab lands on the house once. The arrow keys move from room to room, Enter steps into a room's
  menu and Escape steps back out. + / − / 0 zoom, and Shift with the arrows moves the view.
- **Edit rooms** shows the manor as a plan, a floor at a time: rename a room, say what lives there, list the
  repositories whose cats move in, open or close it, and choose the room new cats come in to.
- **The sign** under the brand shows only when something is wrong, and then it says how to fix it.

### The manor

A real two-storey plan, drawn in a storybook Transylvanian Baroque: ochre limewash with stucco corners outside,
plaster and oak inside, stained glass, and a pediment over the front door. It stands among spruce woods, with lamp
posts along the drive, a fountain, a well and a pond. Both floors stand on one grid, so every upstairs wall stands
on a downstairs wall. It runs from public to private: the café downstairs, the quiet rooms upstairs.

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

- **Claude Code sessions** come live from claude.ai's built-in *Claude Code Remote* connector (`list_sessions`),
  read as you from inside the page every minute. A session's state decides its mood; its GitHub repository decides
  its room.
- **With the gateway**, every session also checks in at your own front desk (`harness/gateway/`) when it starts,
  when it needs you and when it finishes, so its cat is live wherever you open the café.
- **Rooms, renames, moves, adopted chats and what the queen keeps** live in the café's own database, so they follow
  you between phone and computer. Nothing you do on the page is written to a repository.
- **When claude.ai refuses that read** (it did when last checked, 2 October), the cats come from a copy of your
  sessions that a Claude session saved to the database, and the sign under the brand gives its time: "Saved copy ·
  17:02". There is nothing for you to switch on: Claude Code Remote is built into claude.ai rather than added as a
  connector, so it has no setting in your Connectors list. The copy only changes when a session saves a new one, so
  ask a session to refresh it. Sessions that report to the gateway stay live either way. Each refusal, and how to
  refresh the copy: [`docs/live-sessions.md`](docs/live-sessions.md).

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

In the car, this is **the intercom**. You speak from the driver's seat (the café page); a cat hears you where it
sits. Everything you send, a line typed to a cat, a file dropped on it, a Pause or Wrap up, is **written down the
moment you send it**, so nothing is lost if the cat is asleep. From there it takes one of three roads, by who it
is for:

- **To a cat, with no front desk (no gateway).** The note is left on the cat's seat, in the café's own database.
  Nobody can shake a sleeping cat awake, so it reads the note the next time it is up, at the start of its next
  turn: the house rules make it look at its seat first, do what the note asks, answer on the cat and tick the
  note as read.
- **To a cat, with the front desk (the gateway).** The front desk, a small always-on program on Cloudflare, keeps
  the note in that cat's pigeonhole. Each cat checks in at the desk every time it finishes a turn, and the desk
  hands over whatever is in the pigeonhole, once: the cat's **next turn is your note**, so a cat that is working
  gets your words as soon as it finishes what it is saying. Its reply goes back through the same desk and shows
  up in its conversation on the page at once. A cat that was already asleep still waits for its next turn.
- **To Ninine, the driver.** The queen is not a cat you hired; she is the one driving. When you talk to her, the
  front desk rings **her runner**, a small program you keep running on your own computer. The runner is where she
  thinks: it starts one locked-down Claude turn for each thing you say or each routine that comes due (she can use
  the café's tools and nothing else: no commands, no files), and streams her answer back through the desk so the
  page shows her talking as she goes. The front desk is her face, ears and memory; your computer is her brain.
  What she tells another cat reaches it by the road above, like your own words would.

What no road can do: wake a cat that has stopped. Only claude.ai can start a session's next turn, and it doesn't
let a web page do it; why is in [`harness/README.md`](harness/README.md#why-the-café-cant-push-into-a-session).
Each hop, program by program, and how the design holds up on scale, speed, extensibility, security, debugging and
tests: [`docs/delivery.md`](docs/delivery.md).

## On your own computer

The café also runs from a folder, with no claude.ai at all. `python3 catio/tools/bundle.py` makes
`catio/dist/catio-local/` (and a zip of it): the page as one HTML file, all the art, the rooms in
`catio/data/rooms.json` (Charlotte's; a browser takes them once, then Edit rooms or Set up again… changes them), and
`catio/data/sessions.json`, the last copy of your sessions Claude saved (`catio/tools/save-sessions.py`). Serve the
folder with any static server, such as VS Code's Live Server or `python -m http.server 8000`, and open
<http://localhost:8000>. The page is plain HTML and needs no server of its own.

The folder also carries the Catio MCP server, which serves the page and lets agents that aren't Claude Code
sessions join as cats: from inside the folder, `python3 harness/mcp/catio_mcp.py --serve . --port 8791`, then open
<http://localhost:8791>. On localhost the sessions' cats are the saved copy, not live (agents that join the MCP
server are), and adopted chats, room names and project looks are kept in that browser. For newer cats, have a session
refresh `catio/data/sessions.json` and send it to you, then copy it into the folder's `data/`.

The folder holds your licensed art and your session titles, so it is for your own use: never commit it or share it.

## Open source, and what stays behind the paywall

The code is open source: the page, the harness, the gateway and the queen's runner, under the
[GNU AGPL-3.0](LICENSE). Anyone with GitHub can run their own café, free, with the clone and the plugin above and a
Cloudflare Worker for the gateway (`harness/gateway/README.md`). The licence asks one thing back: whoever runs a
changed gateway as a service publishes the change.

What is not open is the art, and what the hosted café sells is the running. The custom assets, the cat breeds, the
house and the interface drawn for the café, are Charlotte's, all rights reserved, and ship only to the hosted cafés
(the packs the page is built from today have their own terms, below); the hosted café adds accounts, keys, an address
of your own, and the calls that reach your sessions without a terminal. The repository is the developers' door; the
hosted café is everyone else's. The plans planned for it, Free, Basic, Early access and Set up for you, are drawn in
[`docs/kittychat-shop/README.md`](docs/kittychat-shop/README.md); their prices come with the hosted café. Building on it, or setting
cafés up for other people? The engine underneath, and what it still lacks as a product, is
[`docs/engine.md`](docs/engine.md).

**Support the work.** The café is built by one person, in the open, while it is in development:

- **Buy me a coffee**: https://buymeacoffee.com/[handle] *(page coming)*. One-off coffees and small memberships;
  they pay for the gateway's hosting and the médiateur, and put your name in the café's credits.
- **Back the app on Ulule**: https://ulule.com/[campaign] *(campaign coming, once the first cafés are open)*. It funds
  the app; the rewards are a year of the hosted café and a drawn cat of your own.

## Made from ten asset packs

Every piece of the picture and the interface comes from packs Charlotte chose. The interface is
Cup Nooble's Sprout Lands UI pack: its tan panels hold every menu and card, its cream buttons,
grey fields and speech bubbles do the rest, its cat emoji show each cat's mood, its white brackets
light up the room you point at, its switch turns the sound on,
its little triangle points at the menu item you're on, the pointer is its cat paw, and titles and
buttons are in its pixel font (with the French accents added). The logo is the cat-face speech
bubble from ToffeeCraft's Cat UI. The corner controls and a cat's Pause, Wrap up and Archive buttons carry
icons from SC_siosio's Game UI Pack (Pastel Edition), pixelated to match.

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

The uncommitted art (`catio/art/licensed/`) ships only inside the private artifact. See
[`catio/art/CREDITS.md`](catio/art/CREDITS.md).

## Files

- `catio/index.html`: the whole page, with no build step and no dependencies.
- `catio/tools/manor.py`: the two floor plans, meaning rooms on one grid, walls, doorways and glass,
  and the grounds.
- `catio/tools/furniture.py`: the furniture catalogue, where each piece stands, and where cats go;
  it writes the page's MANOR block, and the same plan as `catio-app/generated/manor.json`.
- `catio/tools/build-art.py`: draws both floors from the plan, the furniture atlases and the grounds,
  and cuts the UI pieces, from the ten zips (`pip install pillow fonttools`, then see the script's
  docstring).
- `catio/tools/bundle.py`: the folder that runs on localhost.
- `catio/tools/save-sessions.py`: trims a `list_sessions` result to the saved copy.
- `catio/data/rooms.json`: Charlotte's rooms, for the localhost copy. `sessions.json` is never committed.
- `catio/art/`: the committed art. `licensed/` is rebuilt, not committed.
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`), and screenshots to look at
  (`sh catio/test/run.sh look kitchen study`, into `catio/test/.look/`).
- `CLAUDE.md`: how to change and republish the page.
- `catio/tools/digest.py`: compiles the saved sessions and adopted chats into a per-project digest of
  what needs you (`catio/data/digest.md`, never committed).
- `artifacts.json`: the published pages' URLs: the café, and two retired quiz pages.
- `harness/`: the KittyChat harness, the `kittychat-house-rules` plugin (hooks, the `catio` skill,
  graphify), on in all of Charlotte's repos, and the Catio MCP server for other agents. See [its README](harness/README.md).
- `catio-plugin/`: the plugin that sets up your own café; `.claude-plugin/marketplace.json` lists it and the
  harness plugin as the `kittychat` marketplace.
- `litterbox/`: the back burner, where loose notes land; `litterbox/sort.py` piles them up by project
  and files a pile into that project's repo once it has been checked. See [its README](litterbox/README.md).
- `docs/`: the plan, the specs, the shop and the record, each listed by what it is for in
  [`docs/README.md`](docs/README.md).
- `catio-app/`: the café as a native C++ app for a phone, in progress. Its core draws the manor --
  matching the page's own render pixel for pixel -- but there is no window loop, interface or network
  yet, and it has not run on a phone. It ships with no pack art: the app fetches that from the gateway,
  behind your sign-in, on first run, because the packs may not be redistributed. The design and where it stands are in
  [`docs/mobile-app.md`](docs/mobile-app.md).

The tests: `sh catio/test/run.sh` (the page), `python3 -m unittest discover harness/test`,
`(cd harness/gateway && npm install && npm test)` (the gateway), and `python3 -m unittest litterbox/test_sort.py
litterbox/test_quiz.py`.

The page's test and its screenshots drive a headless Chromium through Playwright. `run.sh` is set up for the copies
preinstalled in Claude's cloud sessions. Elsewhere (it needs `sh`, `python3` and Node), set `PLAYWRIGHT` to the
absolute path of a `playwright` package folder (after `npm i -g playwright`, that is `$(npm root -g)/playwright`), and
either set `CHROMIUM` to a Chromium executable or run `node "$PLAYWRIGHT/cli.js" install chromium` so that Playwright
has its own browser. Each run
starts a fresh temporary profile with no logins or saved passwords, and as the page stands it loads only local files
and the page's Google Fonts, plus, for the test (not the screenshots), its own server on 127.0.0.1 port 8791. Set
`PORT` if something else, like `catio_mcp.py --serve`, holds that port: `run.sh` doesn't notice. Without the licensed art (see
[Running your own](#running-your-own)), the check "on its own address the café is live through the gateway, with no
warning sign" fails, as `run.sh` warns.
Sessions under the house rules run the browser preflight first ([`harness/README.md`](harness/README.md)).

## Licence

The code is © 2026 Charlotte Badot, under the [GNU Affero General Public License v3.0](LICENSE), except
`harness/skills/graphify/`, which is graphify's own, under its Apache-2.0 licence and notice in that folder. The art is
not covered: the packs keep their own terms (`catio/art/CREDITS.md`), and the café's own drawings are all rights reserved.

### Whose idea each skill is

The repository ships four skills. What is Charlotte's and what is not:

| Skill | Ownership |
|---|---|
| `harness/skills/graphify/` | Not hers. [graphify](https://github.com/Graphify-Labs/graphify) by Safi Shamsi and the Graphify contributors, vendored unmodified under its Apache-2.0 licence and notice. |
| `harness/skills/catio/` and `catio-plugin/skills/catio/` | Hers as written: the manor with a room per repository, the queen who keeps what matters, cats that walk, and messages and files dropped into live sessions. The genre is not hers: a pixel cat or pet that watches a coding session exists elsewhere ([Nekode](https://nekode.dev/), [claude-cat-mod](https://github.com/matthlh/claude-cat-mod), [claude-token-cat](https://github.com/lylaminju/claude-token-cat), [cc-tamagotchi](https://github.com/davidurco/cc-tamagotchi), [codachi](https://github.com/vincent-k2026/codachi)). |
| `catio-plugin/skills/litterbox-quiz/` | Hers. Loose notes piled by project, each pile a guess until it is checked as a round of flashcards in a private page, and the answers filed back into each project's repository. Flashcard skills and inbox-triage skills exist on their own; this joins the two. The litter box itself (`litterbox/`) is her concept too. |

The house rules (`harness/rules.json`) are hers, but three of the skills they call are not in this repository and
are not hers: `ponytail-audit` (from [ponytail](https://github.com/DietrichGebert/ponytail), Dietrich Gebert, MIT),
`browser-agent-preflight` (a community skill) and `code-review` (Claude Code's own). Hooks that gate edits and
merges are a common pattern; the particular rules here, the Checks and Guesses trailer, the strong-model
condition and the hold list, are her own writing.
