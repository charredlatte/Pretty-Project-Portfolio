# Pretty-Project-Portfolio

**The KittyChat Café** (the Catio page) is one page where every Claude project Charlotte has on the go lives as a cat in a
little pixel-art manor with a fenced catio. Each Claude Code session is a cat that plays while it
works, sleeps when it's done, and **meows** when it's
waiting on her: point at it and it says what it needs. Chats on claude.ai, like business plans and legal questions, can't be read by any
connector, so she adopts those as cats by hand.

The page is a private claude.ai artifact; its link is in [`artifacts.json`](artifacts.json).

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
A hosted café with nothing to install is planned and not open yet. The pixel art comes from third-party packs that
cannot be shared, so check each pack's terms before posting screenshots.

Everything below is the detail.

## What's on the page

- **The manor fills the screen**, seen from above in a meadow, **one floor at a time**. Downstairs
  is the cat café; upstairs are her own rooms, with the ground floor faded underneath. Each room is
  a space for one kind of work. There are no signs on the map: a room says its name when you point
  at it. Nothing is drawn on the cats: point at one and it says what it needs.
- **The stair** in the entrance hall goes up and down, and so do the floor tabs under the minimap
  and Page Up / Page Down. The other floor's tab carries a badge when cats there need you, so nothing
  hides upstairs.
- **Moving around**: drag the house to pan it (with the left, right or middle button), and use the
  wheel or a pinch to zoom around the pointer. The map panel's buttons zoom in, out and back to the
  whole house. Zoom in until one room fills the screen and you're in that room.
- **Hover over a room or a cat** and it lights up and says its name. **Click it** for its menu,
  beside it, until you click elsewhere or press Escape. On a phone a tap does the same. Every menu is
  short: the name and one line, who needs you (and the queen, when she has something to say), then a
  list of actions with the pack's little triangle pointing at the one you're on. A room's are **Look
  in**, Files, Add files, Add a cat and Edit room; a cat's are **Open session**, Talk, Add files and
  Look in. Talk opens the cat's card: its conversation first, and everything else (the facts,
  pausing, archiving, its name, room and title) folded under Manage. Double-click a room to look in,
  or a cat for its card.
- **The brand**, top left (ToffeeCraft's cat-face bubble and the name), is the House button. It
  carries a badge when cats need you, and its menu holds what belongs to the whole house: whether
  the cats are live, the brain, the house rules, Edit rooms, the cats napping in the attic, Check now
  and the sound.
- **The map panel**, top right (bottom right on a phone), is the only other control on screen:
  zoom out, zoom in and the whole house; the floor tabs; and a **minimap** of the floor you're on,
  with the part you're looking at framed. Click it to go somewhere, drag the frame to move around,
  double-click a room to look in. It folds away with its arrow (or M) and remembers.
- **With a keyboard**, Tab lands on the house once. Arrow keys move the brackets from room to room
  on the floor you're on (or, inside a room, walk into the next one). Enter steps into the room's
  menu and Escape steps back out. Page Up / Page Down change floor, + / − / 0 zoom, and Shift with
  the arrows moves the view.
- **Edit rooms** opens the manor as a plan in a wooden frame, a floor at a time. Pick a room (its
  brackets and a green sign show which) to rename it, say what lives there and list the repositories
  whose cats move in. Choose once which room new cats come in to; it's marked on the plan with an
  arrow.
- **The house has a queen**, in the entrance hall: a cat who is nobody's session, never leaves, and is the one
  you talk to, like a character in a game. She keeps what you give her, looks after the other cats for you,
  answers in Elizabethan English (aloud, if you turn her voice on), and runs the routines you set her. Cats
  bring her what they have to say. Her brain runs on your own computer (`harness/runner`).
  - Click her for the room in one line: who needs you and why, or the thing she is keeping for you.
  - Open her to give her something to keep, take it back, or have her say it out loud in her room
    until you take it.
  - She is never counted among the cats that need you; she is the one who tells you about them.
- **The sign** under the brand only shows when something is wrong, and then it says how to fix it.
  When Claude's saved copy is standing in for the live sessions it is one line, "Saved copy" and
  the time; point at it for why.
- **Filing cabinets** stand in every room but the terrace and the ensuite, and the catio deck has a chest. Each holds
  the projects filed in that room with all their cats, the ones needing you first, including the ones
  archived or napping in the attic. A project with a map (from graphify, made by the catio skill)
  shows it there: its main ideas and how they connect, and questions a cat of it can be asked.
- **Cats walk.** When a cat changes room it walks there through the doorways. When it goes to nap in the
  attic it climbs the stair (or, upstairs, the landing's ladder), and it comes back down when it wakes.
  New cats come in by the front door, and working cats get up for a little wander now and then.

Cats wear their project: every cat of one project has the same coat. The look can be changed from the
project's cabinet.

The manor is a real two-storey plan, drawn in a storybook Transylvanian Baroque: ochre limewash with
stucco corners outside, plaster and oak inside, stained glass, and a pediment over the front door. It
stands among spruce woods, with lamp posts along the drive, a fountain, a well and a pond. Both floors
stand on one grid, so every upstairs wall stands on a downstairs wall. It runs from public to private: the
café downstairs, her own rooms upstairs.

| Floor | Room | Who lives there (her rooms can be renamed and reassigned) |
|---|---|---|
| Ground | Café | tables, and business plans round the big one |
| Ground | Kitchen | the counter, straight ahead from the front door behind the stair. The grocery app |
| Ground | Cat lounge | a fireplace between tall windows, and a cat tree. New cats arrive here |
| Ground | Craft room | the shop (Recollée, formerly Montfortoise), bottom left. Its bay window is its shop window on the drive |
| Ground | Entrance hall | the front door, and the stair up the middle. Snail mail |
| Ground | Terrace | the café's glass verrière, with the cat flap out to the catio. TikTok saves |
| Outdoors | Catio | fenced decking at the bottom right, with a cat tree, a shade tree and a rose-arch gate. This portfolio lives here |
| Upstairs | Library | over the café: the brain, where dropped files are sorted |
| Upstairs | Bedroom and ensuite | over the cat lounge. Legal questions, kept quiet, and a spare |
| Upstairs | Landing | open over the kitchen and the hall, round the stairwell. The attic ladder is here |

Outside, the drive runs from the front steps round a fountain with a praying statue to a stone
archway with its wooden doors open. Parterres, a bench and a signpost to the catio stand either side.

## How it knows what the cats are doing

- **Claude Code sessions** come live from the built-in *Claude Code Remote* connector
  (`list_sessions`), called as Charlotte from inside the page and checked every minute. A
  session's state decides its mood; its GitHub repository decides its room.
- **Rooms, renames, moves, adopted chats and what the queen keeps** live in the artifact's own
  database, so they follow her between phone and PC. Nothing she does on the page is written back
  to this repo.
- **When the live read is blocked**, the page shows the copy of her sessions Claude last saved,
  with the time it was saved. Claude Code Remote is built into claude.ai, so it is not in her
  Connectors list and has no per-tool switch she can flip; the copy is refreshed by Claude.

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working or running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions and ones waiting for review, once they're a week old, and archived sessions nap in the
attic, out of sight; the brand's count is only what really waits on her. Turn on
Sound and a cat that starts meowing makes a small meow.

## How what she sends reaches a session

Files dropped on a cat, messages written to it, and pause or wrap-up requests are kept in the artifact's
database the moment she sends them: the file in the brain, the message as a note, the request on the
session. The page then tries to push them into the session with Claude Code Remote's `send_message`.
claude.ai refuses that call to pages (tried 1 October 2026), so the page says it is **waiting in the
outbox**, and the session collects it: sessions in her repos run the house-rules plugin, whose
`catio` skill checks the café when the session starts, handles what's there, answers on the cat and marks
it delivered. Why it can't simply be pushed, by a server or otherwise, is in
[`harness/README.md`](harness/README.md#why-the-café-cant-push-into-a-session).

## On her own computer

The page also runs from a folder, off a USB stick, in VS Code, with no claude.ai at all.
`python3 catio/tools/bundle.py` makes `catio/dist/catio-local/` (and a zip of it): the page as a
complete HTML file, all the art, the rooms from `catio/data/rooms.json`, and
`catio/data/sessions.json`, the copy of her sessions Claude saved. Serve the folder with VS
Code's Live Server, `python -m http.server 8000` or `php -S localhost:8000`, and open
<http://localhost:8000>. It's plain HTML: there is no PHP. The folder also carries the Catio MCP server:
`python3 harness/mcp/catio_mcp.py --serve . --port 8791` serves the page and lets agents that aren't
Claude Code sessions (Codex, Gemini CLI, Cursor) join as cats.

On localhost the cats come from that saved copy, not live, and adopted chats, room names and
project looks are kept in that browser. For newer cats, ask Claude to refresh
`data/sessions.json` (`catio/tools/save-sessions.py`) and copy it into the folder.

The folder holds the licensed art and her session list, so it is for her own use: it is never
committed and never shared.

## Running your own

`catio-plugin/` is a Claude Code plugin. Point Claude Code at it and ask it to set up your Catio:

```bash
git clone https://github.com/charredlatte/Pretty-Project-Portfolio
claude --plugin-dir Pretty-Project-Portfolio/catio-plugin
```

The skill walks you through your rooms, your sessions, publishing the page as your own private
artifact, and the folder that runs off a USB stick. The page does the same on its own: a café with no rooms
yet opens a seven-step wizard (name it, open the rooms you need, file your repositories, see your sessions,
the litter box, how it works), and "Set up again…" in the House menu replays it.

**It cannot give you the cats, or the interface.** Eight of the ten packs below forbid redistributing
their files (and plants.zip came with no licence), so `catio/art/licensed/` is gitignored and a fresh clone draws the manor on plain
panels and nothing else — the page says so on its own sign, and tells you the three steps. You buy the packs yourself and run
`catio/tools/build-art.py` over your own zips. Only Cosy Cabin, whose licence allows it, is in this
repository.

## Open source, and what stays behind the paywall

The code is open source: the page, the harness, the gateway and the queen's runner, under the
[GNU AGPL-3.0](LICENSE). Anyone with GitHub can run their own café, free, with the two lines above and a
Cloudflare Worker for the gateway (`harness/gateway/README.md`). The licence asks one thing back: whoever runs a
changed gateway as a service publishes the change.

What is not open is the art, and what the hosted café sells is the running. The custom assets, the cat breeds, the
house and the interface drawn for the café, are Charlotte's, all rights reserved, and ship only to the hosted cafés
(the packs the page is built from today have their own terms, below); the hosted café adds accounts, keys, an address
of your own, and the calls that reach your sessions without a terminal. The repository is the developers' door; the
hosted café is everyone else's.

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
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`).
- `CLAUDE.md`: how to change and republish the page.
- `catio/tools/digest.py`: compiles the saved sessions and adopted chats into a per-project digest of
  what needs her (`catio/data/digest.md`, never committed).
- `artifacts.json`: the published page's one URL.
- `harness/`: the KittyChat harness, the `kittychat-house-rules` plugin (hooks, the `catio` skill,
  graphify), on in all seven of her repos, and the Catio MCP server for other agents. See [its README](harness/README.md).
- `catio-plugin/`: the plugin that sets up someone else's own Catio; `.claude-plugin/marketplace.json`
  lists the harness plugin as the `kittychat` marketplace.
- `litterbox/`: the back burner, where loose notes land; `litterbox/sort.py` piles them up by project
  and files a pile into that project's repo once it has been checked. See [its README](litterbox/README.md).
- `docs/`: the plan, her requests compiled, the camera and minimap plan, renovation mode's constraints,
  the drawing plan for her own art, and what the litter box filed here.
- `catio-app/`: the café as a native C++ app for a phone, in progress. Its core draws the manor --
  matching the page's own render pixel for pixel -- but there is no window loop, interface or network
  yet, and it has not run on a phone. It ships with no pack art: the app fetches that from her gateway
  on first run, because the packs may not be redistributed. The design and where it stands are in
  [`docs/mobile-app.md`](docs/mobile-app.md).

The tests: `sh catio/test/run.sh` (the page), `python3 -m unittest discover harness/test` and
`python3 -m unittest litterbox/test_sort.py`.

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
