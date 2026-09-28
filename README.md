# Pretty-Project-Portfolio

**The Catio** is one page where every Claude project Charlotte has on the go lives as a cat in a
little pixel-art cabin with a fenced catio. Each Claude Code session is a cat that plays while it
works, sleeps when it's done, and **meows**, with a speech bubble saying what it needs, when it's
waiting on her. Chats on claude.ai, like business plans and legal questions, can't be read by any
connector, so she adopts those as cats by hand.

The page is a private claude.ai artifact; its link is in [`artifacts.json`](artifacts.json).

## What's on the page

- **The cabin**, seen from above in a meadow. Each room is a space for one kind of work. Tap a
  room to zoom in; tap a cat for what it's doing, a link to open the session, and to rename it
  or move it to another room.
- **The hotbar** under the cabin: Rooms, Sound, **Adopt a cat** in the middle, Check now, and
  Whole house.
- **Meowing for you**: every cat waiting on her, most urgent first, then the cats at work.
- **Filing cabinets** in the kitchen, dining room, living room, study and bedroom, and a chest
  on the catio deck. Each holds the projects filed in that room with all their cats, including
  the ones archived or napping upstairs.

Cats wear their project: every cat of one project has the same coat and carries the same
emblem (a tin of cat food for the grocery app, a coin for the shop, books for legal matters, a
star for the portfolio, a plant, or yarn). The look can be changed from the project's cabinet.

The cabin is a real floor plan, laid out the way small cabins usually are:

| Room | Who lives there (her rooms can be renamed and reassigned) |
|---|---|
| Kitchen and dining room | one open-plan run. The grocery app lives in the kitchen, business plans at the table |
| Living room | floor-to-ceiling glass either side of a stone fireplace. New cats arrive here |
| Sunroom | glass on three sides, with a cat flap into the catio |
| Catio | fenced decking against the sunroom, with a shade tree, flower shelves to climb, a table and bench, and a rose-arch gate. This portfolio lives here |
| Study | the Montfortoise shop |
| Bedroom and ensuite | legal questions, and a spare |
| Hall | the front door, between two stone lanterns, and the stepping stones out to the catio |

Outside, a stone archway with its wooden doors open marks the way in, and the south-east meadow
has a small garden square: a fountain with a praying statue, a bench and a signpost to the catio.

## How it knows what the cats are doing

- **Claude Code sessions** come live from the built-in *Claude Code Remote* connector
  (`list_sessions`), called as Charlotte from inside the page and checked every minute. A
  session's state decides its mood; its GitHub repository decides its room.
- **Rooms, renames, moves and adopted chats** live in the artifact's own database, so they
  follow her between phone and PC. Nothing she does on the page is written back to this repo.

| Mood | Session state | Cat |
|---|---|---|
| Meowing | blocked, or its last turn asked for input | Pochi meowing, with a bubble |
| Upset | failed | Pochi crying |
| Something to review | review ready | Mochi in a box |
| Working | working or running | Mochi, tail swishing |
| Asleep | finished or idle | Pochi curled up |

Sleeping sessions older than a week and archived sessions nap upstairs, out of sight. Turn on
Sound and a cat that starts meowing makes a small meow.

## Made from five asset packs

Every piece of the picture and the interface comes from packs Charlotte chose: the frames,
buttons, signs and wallpaper are cut from the cabin's own tile sheet, and the hotbar icons and
mood faces are ToffeeCraft's cat UI.

| Pack | Artist | In this repo? |
|---|---|---|
| [Cosy Cabin](https://marie-pepo.itch.io/cosy-cabin) | Marie Pepo | Yes: `catio/art/house.png` and `catio/art/ui/` |
| [Cat Pack Mochi](https://toffeecraft.itch.io/cat-pack) and [Pochi](https://toffeecraft.itch.io/cat-retro), Cat UI | ToffeeCraft | No: the licence forbids redistribution |
| [Top Down Garden Castle](https://heosphorus.itch.io/) | Heosphorus | No: the licence forbids distribution |
| [Wood Garden](https://rowdy41.itch.io/wood-garden) | rowdy41 | No: it is baked into the same file as Heosphorus's pieces |
| [Pixel Art Top Down – Basic](https://cainos.itch.io/pixel-art-top-down-basic) | Cainos | No: the licence forbids redistribution |

The uncommitted art (`catio/art/licensed/`) ships only inside the private artifact. See
[`catio/art/CREDITS.md`](catio/art/CREDITS.md).

## Files

- `catio/index.html`: the whole page, with no build step and no dependencies.
- `catio/tools/cabin.py`: the floor plan, meaning rooms, doorways, glass and furniture.
- `catio/tools/build-art.py`: draws the cabin from the plan and cuts the UI pieces, from the
  five zips (`pip install pillow`, then see the script's docstring).
- `catio/art/`: the committed art. `licensed/` is rebuilt, not committed.
- `catio/test/`: the end-to-end test (`sh catio/test/run.sh`).
- `CLAUDE.md`: how to change and republish the page.
