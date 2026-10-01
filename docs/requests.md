# What Charlotte has asked for

Everything she has asked for across the Catio, the manor, this repo and the KittyChat Cafe, compiled and
compressed. Read this before starting something new. Last updated 30 September 2026.

## Where the project's information lives

| Place | What's there |
|---|---|
| `CLAUDE.md` | The operating brief: how to work on the page, the licences, the data, publishing |
| `README.md` | What the page is, the rooms, the packs |
| `docs/requests.md` | This file: her requests |
| `docs/from-the-litterbox.md` | Everything the litter box held, sorted: open questions, ideas not built (with the art and sound still missing: what to buy, what to draw, and at what sizes), facts learned, the compressed 29 September harness chat and the UI/UX audit |
| `docs/plan.md` | The roadmap: phases in order, what's waiting on her, how to publish |
| `docs/audit-2026-10-01.md` | The project audit of 1 October: what's broken, what's stale, what to fix first |
| `docs/history.md` | How it got here, version by version |
| `docs/camera-and-minimap.md` | The map panel, the minimap and the Sims-style camera |
| `docs/renovation-mode.md` | The renovation mode spec: moving, adding and removing furniture, the cabinets' looks |
| `litterbox/` | Where new notes land; `litterbox/sort.py` files them into each project's own repo |
| `catio/art/CREDITS.md` | Every pack, its artist and its licence |
| `harness/README.md`, `harness/rules.json` | The KittyChat house rules and the Catio MCP server |
| `artifacts.json` | The one artifact's URL |
| GitHub | Issue #3 (the KittyChat Cafe); PRs #1, #2, #4 and #5, whose descriptions record each round |
| The artifact's database | Her private data: rooms, renames, adopted chats, queens' notes, the brain's files, notes, the outbox. Never in git |
| Her Drive folder "KittyChat Cafe Assets" | The asset-pack zips |

Claude keeps no memory between sessions, so anything worth keeping goes in one of these.

## The idea

- One pretty place for all her projects: code, business plans, legal questions.
  - Every conversation, agent and live session is a cat in a room of a catio.
  - A cat meows when it needs her.
- Issue #3: "An AI harness that presents itself as a cat cafe. The KittyChat Cafe."

## The page

- **One private artifact.** Cats follow their session's state: meowing, upset, to review, working or asleep.
- **Chats:** claude.ai chats are adopted by hand.
- **Cats:** they can be renamed and moved between rooms.
- **A project's look** is its cats' coat, set from its filing cabinet. No emblems: the fur colours are enough
  (29 September).
- **The house fills the screen**, with no toolbars. Everything opens from hover menus, two taps on a phone,
  or the keyboard.
- **Rooms by use** (she can rename and reassign them):

  | Room | Holds |
  |---|---|
  | Kitchen | The grocery app |
  | Dining room | Business plans |
  | Sunroom | TikTok saves |
  | Craft room | The Montfortoise shop |
  | Bedroom | Legal |
  | Hall | Snail mail |
  | Catio | This portfolio |

- **A saved copy of her sessions** shows when the live read is blocked. A Routine refreshes it every two
  hours, from 07:59 to 19:59 Paris time.
- **A copy that runs off a USB stick**, on localhost.
- **A queen in every room** keeps notes and can say one aloud. She is never counted.
- **The Sprout Lands interface everywhere**, in its pixel font, with French accents.
- **A plugin** so other people can run their own Catio.

## The harness (29 September)

- **The brain:** drop chats and files on the page, and each is filed to the right cat.
- **"A true harness":** the page pushes to a session, comments on it and manages it.
- **Other models and agents join through MCP:**
  - Claude breeds;
  - other models doing the sorting;
  - other agents' sessions;
  - any MCP client.
- **House rules, as a plugin for every repo:**
  - preflight before any browser;
  - a read-only ponytail audit when a session opens;
  - semi-automatic shipping.
- **Privacy:** private matters stay out of git. They're fine in the Catio's own storage.
- **Renovation mode:** drag furniture around, and add or remove the non-essential pieces.
- **A cat's position** shows its state, not a mood face.
- **Cats walk** (29 September): an archived cat walks away upstairs, and cats can walk around.
- **Livelier grounds** (29 September): more variety from the packs she has, a spruce forest like the photos.
- **The KittyChat Cafe** as a terrace in the garden (29 September).
- **A UI/UX audit with her Game UI plugin** (29 September): in `docs/from-the-litterbox.md`, under Findings. She picks what to fix.
- **Sounds:** she is finding some herself.
- **How to work:** build the manor a room at a time; compress chats; leftovers go in the litterbox.

## The manor's look

- **A storybook feel.** The manor is a Transylvanian Baroque castle:
  - limewashed ochre and pastel render;
  - white stucco;
  - stone plinths and quoins;
  - green painted shutters;
  - arched doors;
  - **no turrets** (29 September).
- **Every pack mixed freely**, for personal use. Licences are sorted out later.
  - That includes Sprout Lands Sprites and Little Dreamyland.
- **`house.png` becomes licensed art.** A clone without the zips shows no house.
- **Apply her Game UI / UX plugin.** Received 29 September as a zip (MCPmarket's `ui` skill). Its Game UI Designer
  rules are applied to the manor: map layers stay quiet under cats and signs, never colour alone, no motion,
  integer scaling.
- **Inspired by her photos of Peleș and Sinaia** (29 September). The pastel Baroque stays the base, with
  touches from the photos:
  - stained glass;
  - gilt trellis on white panels;
  - wrought-iron scrollwork;
  - carved dark oak;
  - Art Nouveau.

## The interface, 30 September

- **"Take everything about the UI and make it better"**: less bloated menus, less noise, redesigned with the
  licensed packs.
- **"I hate the signs on every room and the large The Catio name."** The page is **the KittyChat Cafe**: "the
  harness and UI SaaS that I am making here". No signs on the map; a small brand, top left.
- Done in version 13: see `docs/plan.md`.
- **"Use the Game UI Pastel pack anyway"**: its licence turned up inside the zip (SC_siosio, credit required).
  Version 14 uses its icons, pixelated, on the corner controls and a cat's Manage buttons.

## Decided 30 September

- The minimap is a plan of rooms; WASD and the arrows both pan; Game UI Pastel is used.
- A filing cabinet never leaves its room, and she chooses what it looks like in each room.
- Renovation mode stays in the plan as its own phase (1 October): `docs/renovation-mode.md`.

## Still waiting on her

The list is kept in one place: "Waiting on Charlotte" in `docs/plan.md`.
