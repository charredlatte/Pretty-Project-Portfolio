# Pretty-Project-Portfolio

**The Catio** is one page where every Claude project Charlotte has on the go lives as a cat in a
little pixel-art cabin with a fenced catio. Each Claude Code session is a cat that plays while it
works, sleeps when it's done, and **meows**, with a speech bubble saying what it needs, when it's
waiting on her. Chats on claude.ai, like business plans and legal questions, can't be read by any
connector, so she adopts those as cats by hand.

The page is a private claude.ai artifact; its link is in [`artifacts.json`](artifacts.json).

## What's on the page

- **The cabin fills the screen**, seen from above in a meadow. Each room is a space for one kind
  of work. There are no toolbars: everything opens from the picture.
- **Hover over a room** for its menu: what it's for, how many cats need you, the ones meowing,
  and Look in (zoom to that room), Files, **Adopt a cat here**, and Edit rooms. Its foot has
  Sound, Check now, and the cats napping upstairs.
- **Hover over a cat** for its menu: what it needs, its project, room and branch, and a link to
  open the session or chat. Click it for the full card, to rename it or move it to another room.
  On a phone, the first tap opens the menu and the second opens the card.
- **The sign** in the top corner counts the cats that need you, are at work and are asleep. It
  only speaks up when something is wrong, and then it says how to fix it.
- **Filing cabinets** in the kitchen, dining room, living room, craft room and bedroom, and a
  chest on the catio deck. Each holds the projects filed in that room with all their cats,
  including the ones archived or napping upstairs.

Cats wear their project: every cat of one project has the same coat and carries the same
emblem (a tin of cat food for the grocery app, a coin for the shop, books for legal matters, a
star for the portfolio, a plant, or yarn). The look can be changed from the project's cabinet.

The cabin is a real floor plan, laid out the way small cabins usually are:

| Room | Who lives there (her rooms can be renamed and reassigned) |
|---|---|
| Kitchen and dining room | one open-plan run. The grocery app lives in the kitchen, business plans at the table |
| Living room | floor-to-ceiling glass either side of a stone fireplace. New cats arrive here |
| Sunroom | glass on three sides, with a cat flap into the catio. TikTok saves |
| Catio | fenced decking against the sunroom, with a shade tree, flower shelves to climb, a table and bench, and a rose-arch gate. This portfolio lives here |
| Craft room | the Montfortoise shop: a craft table with yarn and tins, shelves of supplies, a sewing desk and glass on two walls |
| Bedroom and ensuite | legal questions, and a spare |
| Hall | the front door, between two stone lanterns, and the stepping stones out to the catio. Snail mail |

Outside, a stone archway with its wooden doors open marks the way in, and the south-east meadow
has a small garden square: a fountain with a praying statue, a bench and a signpost to the catio.

## How it knows what the cats are doing

- **Claude Code sessions** come live from the built-in *Claude Code Remote* connector
  (`list_sessions`), called as Charlotte from inside the page and checked every minute. A
  session's state decides its mood; its GitHub repository decides its room.
- **Rooms, renames, moves and adopted chats** live in the artifact's own database, so they
  follow her between phone and PC. Nothing she does on the page is written back to this repo.
- **When the live read is blocked**, the page shows the copy of her sessions Claude last saved,
  and the sign names the setting to change: in claude.ai, **Customize → Connectors → Claude Code
  Remote**, set `list_sessions` to **Allow**. If it can't be changed, an organisation admin has
  capped it.

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing, with a bubble |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working or running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions older than a week and archived sessions nap upstairs, out of sight. Turn on
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

## Made from six asset packs

Every piece of the picture and the interface comes from packs Charlotte chose. The interface is
Cup Nooble's Sprout Lands UI pack: its tan panels hold every menu and card, its cream buttons,
grey fields and speech bubbles do the rest, its cat emoji show each cat's mood, its white brackets
light up the room you point at, its switch turns the sound on, the pointer is its cat paw, and
titles and buttons are in its pixel font (with the French accents added).

| Pack | Artist | In this repo? |
|---|---|---|
| [Cosy Cabin](https://marie-pepo.itch.io/cosy-cabin) | Marie Pepo | Yes: `catio/art/house.png` |
| [Cat Pack Mochi](https://toffeecraft.itch.io/cat-pack) and [Pochi](https://toffeecraft.itch.io/cat-retro), Cat UI | ToffeeCraft | No: the licence forbids redistribution |
| [Top Down Garden Castle](https://heosphorus.itch.io/) | Heosphorus | No: the licence forbids distribution |
| [Wood Garden](https://rowdy41.itch.io/wood-garden) | rowdy41 | No: it is baked into the same file as Heosphorus's pieces |
| [Pixel Art Top Down – Basic](https://cainos.itch.io/pixel-art-top-down-basic) | Cainos | No: the licence forbids redistribution |
| [Sprout Lands UI Pack – Basic](https://cupnooble.itch.io/) | Cup Nooble | No: the licence forbids redistribution, even modified |

The uncommitted art (`catio/art/licensed/`) ships only inside the private artifact. See
[`catio/art/CREDITS.md`](catio/art/CREDITS.md).

## Files

- `catio/index.html`: the whole page, with no build step and no dependencies.
- `catio/tools/cabin.py`: the floor plan, meaning rooms, doorways, glass and furniture.
- `catio/tools/build-art.py`: draws the cabin from the plan and cuts the UI pieces, from the
  six zips (`pip install pillow fonttools`, then see the script's docstring).
- `catio/tools/bundle.py`: the folder that runs on localhost.
- `catio/tools/save-sessions.py`: trims a `list_sessions` result to the saved copy.
- `catio/data/rooms.json`: the rooms, for the localhost copy. `sessions.json` is never committed.
- `catio/art/`: the committed art. `licensed/` is rebuilt, not committed.
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`).
- `CLAUDE.md`: how to change and republish the page.
