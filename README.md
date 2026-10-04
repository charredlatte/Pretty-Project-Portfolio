# KittyChat Café

Every Claude project you have on the go, as a cat in a little pixel-art café. Each Claude Code session is a cat that
plays while it works, sleeps when it's done, and **meows** when it's waiting on you: point at it and it says what it
needs. Chats on claude.ai that no connector can read, like a business plan or a legal question, you adopt as cats by
hand. One queen cat runs the place for you.

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

Your private chats stay in your own account, never in this repository.

**Where it stands.** The code is open source and you can run your own café today (see [Running your own](#running-your-own)).
A hosted café with nothing to install is planned and not open yet. Separately, Charlotte plans to launch the KittyChat
Café app in December 2027. The pixel art comes from third-party packs that cannot be shared, so check each pack's terms before
posting screenshots.

Everything below is the detail.

## Running your own

`catio-plugin/` is a Claude Code plugin. Point Claude Code at it and ask it to set up your café:

```bash
git clone https://github.com/charredlatte/Pretty-Project-Portfolio
claude --plugin-dir Pretty-Project-Portfolio/catio-plugin
```

The skill walks you through your rooms, your sessions, publishing the page as your own private claude.ai artifact,
and a folder that runs on your own computer. The page does the same on its own: a café with no rooms yet opens a
seven-step wizard (name it, open the rooms you need, file your repositories, see your sessions, the litter box, how
it works), and "Set up again…" in the House menu replays it.

Then give your sessions the house rules, and the `catio` skill that collects what you send them from the café (the
same two lines the wizard shows):

```bash
claude plugin marketplace add https://github.com/charredlatte/Pretty-Project-Portfolio.git
claude plugin install kittychat-house-rules@kittychat --scope user
```

For cats that stay live wherever you open the café, and a queen you can talk to, add the gateway: a free Cloudflare
Worker that every session checks in at, set up in five steps ([`harness/gateway/README.md`](harness/gateway/README.md)).
The queen's brain runs on your own computer ([`harness/runner/README.md`](harness/runner/README.md)).

**Bring your own cats.** Eight of the ten art packs the café is drawn from forbid sharing their files (and plants.zip
came with no licence), so `catio/art/licensed/` is not in this repository. A fresh clone draws the manor on plain
panels, says so on its own sign, and gives the three steps to fix it: buy the packs yourself and run
`catio/tools/build-art.py` over your own zips. Only Cosy Cabin, whose licence allows it, is included.

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
- **A queen who runs the place.** She sits in the entrance hall, is nobody's session and never leaves. She keeps what
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
- **The brand**, top left, is the House button: whether the cats are live, the brain, the house rules, Project maps,
  The look, Edit rooms, the cats napping in the attic, Check now and sound.
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
- **When the live read is blocked**, the page shows the last copy of your sessions Claude saved, and the time it was
  saved, on one line.

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

Files dropped on a cat, messages written to it, and pause or wrap-up requests are saved the moment you send them.
With the gateway, a running session gets them when its current turn ends. Without it they wait on the mat, and the
session collects them when it next starts: sessions in your repositories run the house-rules plugin, whose `catio`
skill handles what's there, answers on the cat and marks it delivered. Only claude.ai can wake a session that has
stopped, and it doesn't let a page do it; why is in
[`harness/README.md`](harness/README.md#why-the-café-cant-push-into-a-session).

## On your own computer

The café also runs from a folder, with no claude.ai at all. `python3 catio/tools/bundle.py` makes
`catio/dist/catio-local/` (and a zip of it): the page as one HTML file, all the art, your rooms from
`catio/data/rooms.json`, and `catio/data/sessions.json`, the last copy of your sessions Claude saved
(`catio/tools/save-sessions.py`). Serve the folder with any static server, such as VS Code's Live Server or
`python -m http.server 8000`, and open <http://localhost:8000>. It's plain HTML, with no server code.

The folder also carries the Catio MCP server, which serves the page and lets agents that aren't Claude Code
sessions join as cats: from inside the folder, `python3 harness/mcp/catio_mcp.py --serve . --port 8791`, then open
<http://localhost:8791>. On localhost the cats are the saved copy, not live, and adopted chats, room names and
project looks are kept in that browser.

The folder holds your licensed art and your session titles, so it is for your own use: never commit it or share it.

## Open source, and what stays behind the paywall

The code is open source: the page, the harness, the gateway and the queen's runner, under the
[GNU AGPL-3.0](LICENSE). Anyone with GitHub can run their own café, free, with the two lines above and a
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
- `catio/data/rooms.json`: the rooms, for the localhost copy. `sessions.json` is never committed.
- `catio/art/`: the committed art. `licensed/` is rebuilt, not committed.
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`), and screenshots to look at
  (`sh catio/test/run.sh look kitchen study`, into `catio/test/.look/`).
- `CLAUDE.md`: how to change and republish the page.
- `catio/tools/digest.py`: compiles the saved sessions and adopted chats into a per-project digest of
  what needs her (`catio/data/digest.md`, never committed).
- `artifacts.json`: the published page's one URL.
- `harness/`: the KittyChat harness, the `kittychat-house-rules` plugin (hooks, the `catio` skill,
  graphify), on in all seven of her repos, and the Catio MCP server for other agents. See [its README](harness/README.md).
- `catio-plugin/`: the plugin that sets up your own café; `.claude-plugin/marketplace.json` lists it and the
  harness plugin as the `kittychat` marketplace.
- `litterbox/`: the back burner, where loose notes land; `litterbox/sort.py` piles them up by project
  and files a pile into that project's repo once it has been checked. See [its README](litterbox/README.md).
- `docs/`: the plan, her requests compiled, the camera and minimap plan, renovation mode's constraints,
  the drawing plan for her own art, the engine under the café ([`docs/engine.md`](docs/engine.md)), and
  what the litter box filed here.
- `catio-app/`: the café as a native C++ app for a phone, in progress. Its core draws the manor --
  matching the page's own render pixel for pixel -- but there is no window loop, interface or network
  yet, and it has not run on a phone. It ships with no pack art: the app fetches that from her gateway
  on first run, because the packs may not be redistributed. The design and where it stands are in
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
