# KittyChat on Steam: what it would take, and what would go wrong

Charlotte's asks, 2 and 3 November 2026: first a Blender cat-modelling video — "Tell me what it would take
to make Kitty Chat Cafe 3D instead of 2D" — then, partway through that costing, "I want you to forsee the
problems we would have in releasing kittychat as a game on steam", and then "Cost the Steam game."

This page is the answer to both, because they share a root. Nothing here is built, and nothing should be
started on it: her words, 3 November, "We will move forward with this when I'm out of the hospital."

Primary source for every Steam rule quoted below: Valve's
[Steamworks onboarding page](https://partner.steamgames.com/doc/gettingstarted/onboarding), read 2 November
2026. Where this page says something was *not* checked, it was not checked.

## The decisive constraint: Steam has no category for what KittyChat is

Valve: "Non-game software may be accepted for distribution if it fits into one of the following categories"
— Animation & Modeling, Audio/Video Production, Design & Illustration, Photo Editing, Educational &
Tutorials, Finance & Accounting, Player Tools, SteamVR Tools.

There is no developer-tools, productivity or software-development category. An agent harness fits none of
the eight. **So the café cannot ship on Steam as the tool it is.** It can only ship as a game, which means
it has to be one. Everything below follows from that.

## The decision that removes most of the risk: the game contains no harness

If the game is a self-contained simulation — no account, no gateway, no API key, no network — then four of
the five worst problems disappear by construction.

| Problem | Why it goes away |
|---|---|
| Steam's two-hour, no-questions refund window against a Cloudflare setup | Nothing to set up: it launches and plays |
| Live-generated AI disclosure, and Valve holding the developer responsible for AI output | There is no AI in the build. The content survey's AI questions become a clean "no" |
| "Applications that modify customer's computers in unexpected or harmful ways" (Valve's rule 9) | The game runs no agents and executes no commands |
| GDPR: strangers' data in her Worker, and adopted chats that may hold legal matters | The game stores nothing off the player's machine |

So **"connect your real café" must not ship in v1.** If it ever ships, the AI disclosure and rule 9 come
straight back, and it belongs in a separate free app rather than inside a paid game.

What remains is the art, which is problem 1 and is already on the harness's critical path for a different
reason (`docs/engine.md`: "art Charlotte owns before anyone else signs up"). The game and the roadmap want
the same work. That is the main argument for doing this at all.

## The mechanics are already modelled

The café's data model is most of a management sim already, because it was built as one metaphorically.

- **Stations.** `catio/tools/furniture.py` already types every piece's stations — `work`, `sleep`, `queen`,
  `review`, `fail`, `needs`, `upstairs`. That is The Sims' "object advertises a need" model. A cat walking
  to a cushion to sleep is implemented.
- **The level.** `MANOR` holds a 960 × 576 world on a 32 px face: ten rooms plus the landing, fourteen
  doorways, the stair, per-room floor rects, and a hand-placed layout of **76 furniture pieces**.
  `catio/tools/manor.py` (863 lines) draws both floors and the grounds from that plan.
- **Cat behaviour.** `walk()` routes cats through `MANOR.doors` between rooms and floors; `placeLine()`
  already queues waiting cats at the front door; moods already drive their look.
- **Progression.** Closed rooms already exist (`rooms/<k>.closed`: dimmed, no cats, still walked through),
  and `OPENING` already orders the rooms public to private. Ten rooms is ten unlocks, built.
- **The shop.** Renovation mode — moving furniture, a catalogue bar, undo and redo — is already specified in
  `docs/renovation-mode.md`, with its pieces chosen.
- **The quest giver.** Ninine and her quest log already exist.
- **Pause and play icons** are already cut into `pastel.png`.

**What is missing is the economy and time:** a day cycle, needs that decay, money, customers, prices, goals
and a fail state, and save files. That is a much shorter list than "build a management sim".

## Architecture: the same page, a third runtime, in Electron

The page already has a runtime seam, tested on both sides. `window.claude` is the gateway; with none,
`localRuntime()` runs the whole café against a `localStorage` database; and `catio/test/runtime-stub.js`
(230 lines) runs it against an in-memory database with invented cats. **The game is one more
implementation of that seam** — `gameRuntime()` — with a simulation behind it instead of a gateway.

That reuses, unchanged:

- `catio/index.html`, 5,897 lines: the manor, the camera, the minimap, the menus, the dialogs, the tokens
  and slots, and the keyboard and screen-reader paths;
- `catio/test/e2e.mjs`, 3,683 lines of checks, which only work against this DOM page and which any rewrite
  throws away;
- the tooling: `manor.py`, `furniture.py`, `build-art.py`, `skin.py` — 2,246 lines together;
- her 22 hand-drawn interface pieces in `catio/art/skin/`.

`catio-app/` (7,716 lines of C++ and SDL3) is the native alternative, but `docs/mobile-app.md` says it has
never opened a window, and it would mean a second implementation of everything. Keep it a draft.

**Electron rather than Tauri.** Tauri uses the system webview, so Linux means WebKitGTK and a different
renderer from Windows; Electron bundles Chromium, so the game renders identically everywhere, which matters
when the art is pixel-exact. The cost is binary size.

**Not checked, and it must be before this is committed to:** there are developer reports of Electron apps
failing inside the **Steam Linux Runtime** (a libcups problem) and of native Linux builds behaving better
than Proton ones. Plan on a native Linux build for the Deck rather than relying on Proton, and test inside
the Steam Linux Runtime early rather than at submission. This needs real hardware, not research.

## The art

`docs/drawing-plan.md` is the authority here and supersedes any estimate: it lists every asset, its size and
the file it replaces, with the house style and the Aseprite settings. Two numbers matter, and they are
different numbers for different goals.

**Her full ownership plan** (drawing-plan.md): about 60 furniture drawings, 11 cat sheets and ~60 frames,
seven floor textures, nine wall textures, ~25 kinds of grounds piece, ~20 interface files, and sound. That
retires all ten packs.

**The Steam legal minimum** is smaller, because her own skin already covers most of the interface:

| Must be replaced | Why | Scale |
|---|---|---|
| The cats | ToffeeCraft: personal use only | 6 sheets minimum (five moods and the side walk), 11 at most |
| `licensed/house.png`, `house-upper.png` | Mixes Cosy Cabin, Cainos and Little Dreamyland | Not two images: the **tileset** — 7 floors, 9 walls, the window. `manor.py` redraws the house from them |
| `licensed/decor.png` (the grounds) | Mixes Heosphorus, Wood Garden, Cainos, Sprout Lands, Little Dreamyland | ~25 kinds (section 5) |
| 23 of the 76 furniture pieces | The ones on the `lic` atlas, from the restricted packs | `furniture.py`'s `COMMITTABLE = {"cc"}` is the split |
| `corners`, `status`, `faces`, `crown`, `stars`, `cursor`, `cursor-point`, `logo` | Sprout Lands and ToffeeCraft. `logo` is the **brand mark** | ~10 small pieces |
| `pastel.png` icons | SC_siosio | 10 cells of 20 × 20 |
| `sprout.ttf` | Sprout Lands | drawing-plan.md's own advice: take an OFL pixel font. "This is the one asset where drawing it yourself buys the least" |
| Sound | None exists | A meow, a purr, paw steps, a door |

**What does *not* need replacing:** the 22 pieces in `catio/art/skin/` (panel, the five buttons, field,
bubble, frame, divider, toggle, arrow, pointer, wallpaper and the map panel's six) are hers and ship as they
are. And the 53 furniture pieces on the `cc` atlas are Cosy Cabin, which `catio/art/CREDITS.md` records as
"Free for personal and commercial use with credit; copying and modifying allowed; no resale." That reads as
permitting a commercial game that is not itself an asset pack — **confirm it against the pack's own LICENSE
before relying on it.** If it turns out otherwise, the furniture bill goes from 23 to 76.

### A correction about the 3D route

The costing that started this recommended pre-rendering: model in Blender, render flat with an orthographic
camera, drop the sheets into the slots `ART` and `misfit()` already provide. The *technical* half of that
stands — drawing-plan.md section 9 confirms it: "Nothing, for most of it", every piece is a slot and a cat
slot takes any frame size and count.

The *incremental* half was wrong, and drawing-plan.md is why. Its house style asks for three-quarter
top-down, light from the top left, a 1 px outline in the piece's own darker shade, and one indexed master
palette; and section 1 says plainly "Never draw at 2× and shrink it… a downscale breaks pixel art." A
rendered sprite and a hand-drawn one will not sit together: rendering to a 32 × 32 frame needs no
anti-aliasing and a palette quantisation step, and even done well it reads as a different hand.

So **pre-rendered 3D is all-or-nothing stylistically**, not a slot-at-a-time swap. Either the whole world is
rendered or it is hand-drawn. That is a real decision rather than a detail, and it is hers.

## Licensing, to decide deliberately

- **Keep the code AGPL-3.0 and licence the art separately,** all rights reserved, kept out of the public
  repo exactly as `art/licensed/` is today. Otherwise the game's own licence makes it rebuildable and
  redistributable by anyone, art included. (drawing-plan.md already leaves this open: "Whether the repo stays
  public with her art in it is her call.")
- **Ship no Steamworks SDK in v1.** That avoids the copyleft-versus-SDK conflict entirely. Steam Auto-Cloud
  covers saves without it. Achievements would need it, and then a GPL §7 additional-permission exception has
  to be granted deliberately — she can, as the copyright holder, and vendored graphify (Apache-2.0 and MIT)
  does not block it.
- **Do not enable Steam DRM** on an AGPL binary: it is an additional restriction.
- **Credit** Marie Pepo if the Cosy Cabin pieces ship, and keep CREDITS.md honest as packs leave.
- The trademark search already planned in `docs/engine.md` — INPI and EUIPO, classes 9 and 42 — matters more
  as a store listing than as a web page.

## Steam's own chores

Steam Direct is $100 per app, credited back at $1,000 adjusted gross revenue, and wants tax and banking
details (a French resident files a W-8BEN) plus a waiting period before release. Then the store page (capsule
art at several sizes, five or more screenshots, a trailer — routinely underestimated), the content survey,
SteamPipe depots for Windows and native Linux, and a review pass.

Steam Deck is its own gate. Her own audit in `docs/from-the-litterbox.md` measured cats at 6–12 px tap
targets and the house filling an eighth of a phone screen. Deck verification wants controller navigation and
legibility at 1280 × 800, so gamepad input and a bigger scale are required work, not polish.

## What to build first

A vertical slice, before any art is commissioned and before any store page exists: **one room, one cat, one
need, one day.** `gameRuntime()` behind the existing seam; a cat whose sleep need decays and who walks to a
cushion station to satisfy it; a clock that runs a day; a money counter that changes. Drawn with the current
pack art, locally, never shipped.

That proves the architecture claim — that the game is this page on a simulated runtime — in a few days, and
it is the thing to abandon the plan over if it turns out false.

## Checking it

As `CLAUDE.md` asks: look first, test second.

1. **Get `art/licensed/` first.** Without it the screenshots show the no-art fallbacks and the skin checks
   fail for the wrong reason.
2. `sh catio/test/run.sh look ground upper kitchen study`, and open each against the current page at the same
   size.
3. `sh catio/test/run.sh` — the whole suite, unchanged. A new runtime behind the existing seam should change
   **no** existing check, so any failure is a regression. New checks for the simulation are written from the
   agreed mechanics, never to match the code.
4. `python3 catio/tools/furniture.py`, and confirm `furniture.check()` is empty and no cat stands on
   furniture.
5. The two things research cannot settle: an Electron build inside the Steam Linux Runtime on a Deck, and
   whether a reviewer accepts the content survey.

## Open decisions for Charlotte

1. **Does the game share the fiction?** The same manor and the cats-as-work metaphor, or a plain cat café
   where cats are just cats? This decides how much of the existing interface copy survives.
2. **Hand-drawn pixel art or rendered 3D?** All-or-nothing, per the correction above. drawing-plan.md assumes
   Aseprite.
3. **Who draws it** — her own time, or a commission budget? This is the schedule.
4. **Price, and whether there is a demo** (a demo is a separate app for Steam Direct purposes).
5. **Does "connect your real café" ever ship?** The recommendation is never in the paid game, and only as a
   separate free app if at all.
6. **A separate repo for the game?** Recommended, so the art can stay unpublished while the code stays AGPL.
