# Pretty-Project-Portfolio

**The Catio** is one page where every Claude project Charlotte has on the go lives as a cat in a
little pixel-art manor with a fenced catio. Each Claude Code session is a cat that plays while it
works, sleeps when it's done, and **meows**, with a speech bubble saying what it needs, when it's
waiting on her. Chats on claude.ai, like business plans and legal questions, can't be read by any
connector, so she adopts those as cats by hand.

The page is a private claude.ai artifact; its link is in [`artifacts.json`](artifacts.json).

## What's on the page

- **The manor fills the screen**, seen from above in a meadow, **one floor at a time**. Downstairs
  is the cat café; upstairs are her own rooms, with the ground floor faded underneath. Each room is
  a space for one kind of work, with its name on a cream sign on its back wall and a badge (the
  mood's cat face and a count) when cats in it need you; on a phone, just the badge.
- **The stair** in the entrance hall goes up and down, and so do the floor buttons in the bottom
  corner and Page Up / Page Down. The stair's sign and the floor button carry a badge when cats on
  the other floor need you, so nothing hides upstairs.
- **Moving around**: drag the house to pan it (with the left, right or middle button), and use the
  wheel or a pinch to zoom around the pointer. The corner buttons zoom in, out and back to the whole
  house. Zoom in until one room fills the screen and you're in that room: its cats' bubbles say what
  they need.
- **Hover over a room or a cat** and it lights up and says its name. **Click it** for its menu,
  beside it, until you click elsewhere or press Escape. On a phone a tap does the same. A room's menu
  shows who needs you, its queen, **Look in** (zoom to it), Files, Add files, Add a cat (a new session
  or an adopted chat) and Edit room. A cat's shows what it needs, its project, room and branch,
  **Open session** (or chat), and Talk for the full card, to rename it or move it. Double-click a
  room to look in, or a cat for its card.
- **The map panel**, top right (bottom right on a phone), is the one control on screen:
  - **House** holds what belongs to the whole house: the brain, the house rules, Edit rooms, the
    sound, Check now, and the cats napping in the attic;
  - zoom out, zoom in and the whole house;
  - the floor tabs;
  - a **minimap** of the floor you're on, with the part you're looking at framed. Click it to go
    somewhere, drag the frame to move around, double-click a room to look in. It folds away with
    its arrow (or M) and remembers.
- **With a keyboard**, Tab lands on the house once. Arrow keys move the brackets from room to room
  on the floor you're on (or, inside a room, walk into the next one). Enter steps into the room's
  menu and Escape steps back out. Page Up / Page Down change floor, + / − / 0 zoom, and Shift with
  the arrows moves the view.
- **Edit rooms** opens the manor as a plan in a wooden frame, a floor at a time. Pick a room (its
  brackets and a green sign show which) to rename it, say what lives there and list the repositories
  whose cats move in. Choose once which room new cats come in to; it's marked on the plan with an
  arrow.
- **Every room has a queen**, a cat in a crown who is nobody's session and never leaves.
  - Click her for the room in one line: who needs you and why, or the thing she is keeping for you.
  - Open her to give her something to keep, take it back, or have her say it out loud in her room
    until you take it.
  - She is never counted among the cats that need you; she is the one who tells you about them.
- **The sign** in the top corner counts the cats that need you, are at work and are asleep, on both
  floors. It only speaks up when something is wrong, and then it says how to fix it.
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
| Ground | Craft room | the Montfortoise shop, bottom left. Its bay window is its shop window on the drive |
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
- **Rooms, renames, moves, adopted chats and what each queen keeps** live in the artifact's own
  database, so they follow her between phone and PC. Nothing she does on the page is written back
  to this repo.
- **When the live read is blocked**, the page shows the copy of her sessions Claude last saved,
  with the time it was saved. Claude Code Remote is built into claude.ai, so it is not in her
  Connectors list and has no per-tool switch she can flip; the copy is refreshed by Claude.

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing, with a bubble |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working or running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions older than a week and archived sessions nap in the attic, out of sight. Turn on
Sound and a cat that starts meowing makes a small meow.

## On her own computer

The page also runs from a folder, off a USB stick, in VS Code, with no claude.ai at all.
`python3 catio/tools/bundle.py` makes `catio/dist/catio-local/` (and a zip of it): the page as a
complete HTML file, all the art, the rooms from `catio/data/rooms.json`, and
`catio/data/sessions.json`, the copy of her sessions Claude saved. Serve the folder with VS
Code's Live Server, `python -m http.server 8000` or `php -S localhost:8000`, and open
<http://localhost:8000>. It's plain HTML: there is no PHP, and no server code of its own.

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
artifact, and the folder that runs off a USB stick.

**It cannot give you the cats, or the interface.** Five of the six packs below forbid redistributing
their files, so `catio/art/licensed/` is gitignored and a fresh clone draws the manor on plain
panels and nothing else — the page says so on its own sign, and tells you the three steps. You buy the packs yourself and run
`catio/tools/build-art.py` over your own zips. Only Cosy Cabin, whose licence allows it, is in this
repository.

## Made from nine asset packs

Every piece of the picture and the interface comes from packs Charlotte chose. The interface is
Cup Nooble's Sprout Lands UI pack: its tan panels hold every menu and card, its cream buttons,
grey fields and speech bubbles do the rest, its cat emoji show each cat's mood, its white brackets
light up the room you point at, its switch turns the sound on, the pointer is its cat paw, and
titles and buttons are in its pixel font (with the French accents added).

| Pack | Artist | In this repo? |
|---|---|---|
| [Cosy Cabin](https://marie-pepo.itch.io/cosy-cabin) | Marie Pepo | Yes: `catio/art/furniture.png`. The house mixes every pack, so it is not |
| [Cat Pack Mochi](https://toffeecraft.itch.io/cat-pack) and [Pochi](https://toffeecraft.itch.io/cat-retro), Cat UI | ToffeeCraft | No: the licence forbids redistribution |
| [Top Down Garden Castle](https://heosphorus.itch.io/) | Heosphorus | No: the licence forbids distribution |
| [Wood Garden](https://rowdy41.itch.io/wood-garden) | rowdy41 | No: it is baked into the same file as Heosphorus's pieces |
| [Pixel Art Top Down – Basic](https://cainos.itch.io/pixel-art-top-down-basic) | Cainos | No: the licence forbids redistribution |
| [Sprout Lands UI Pack – Basic](https://cupnooble.itch.io/) | Cup Nooble | No: the licence forbids redistribution, even modified |
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
  it writes the page's MANOR block.
- `catio/tools/build-art.py`: draws both floors from the plan, the furniture atlases and the grounds,
  and cuts the UI pieces, from the nine zips (`pip install pillow fonttools`, then see the script's
  docstring).
- `catio/tools/bundle.py`: the folder that runs on localhost.
- `catio/tools/save-sessions.py`: trims a `list_sessions` result to the saved copy.
- `catio/data/rooms.json`: the rooms, for the localhost copy. `sessions.json` is never committed.
- `catio/art/`: the committed art. `licensed/` is rebuilt, not committed.
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`).
- `CLAUDE.md`: how to change and republish the page.
