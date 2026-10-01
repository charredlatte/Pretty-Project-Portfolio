# Renovation mode: the spec

Phase 3 of `docs/plan.md`. Move the furniture around, add and remove the decorative pieces, and choose what
each room's filing cabinet looks like, in a Build mode like The Sims'. Rewritten on 1 October 2026 from
the first constraints note (29 September), the Build section of `docs/camera-and-minimap.md`, and her
decisions since.

## What she has asked for

- "Renovation mode: drag furniture around, and add or remove the non-essential pieces" (29 September).
- Live and Build modes, in the manner of The Sims' build mode, with Game UI Pastel dressing Build's tools
  (30 September).
- A filing cabinet never leaves its room, but she chooses what it looks like, room by room (30 September).

## What is already true (so this is not a rewrite)

- **The furniture is already sprites,** not baked into the house. `catio/tools/furniture.py` has the
  catalogue (`MANOR.pieces`: atlas cell, kind, layer, footprint, stations) and each room's default layout
  (`MANOR.layout`, `[key, x, y]` in native pixels). The page draws each piece in the cats' z-space
  (`drawFurniture()`).
- **Cats already sit by the furniture:** `stationsOf(room)` and `freeFloor(room)` are worked out from the
  layout, and `furniture.check()` proves no station is in furniture or off the floor.
- So renovation mode makes the layout data that the page edits. The art pipeline doesn't change.

## Kinds: what may move

`furniture.py` gives every piece a kind:

| Kind | Examples | In renovation mode |
|---|---|---|
| **essential** | the stair, the front door mat, the brain's desk and chest, the fireplace | Never moves. It's bracketed with the lock icon when pointed at |
| **filing cabinet** (essential, with a job) | `filing_cabinet` in each room, `catio_chest` on the catio | Moves within its own room only. Its look can be any floor piece (below) |
| **connected** (carries a station) | desks, cushions, armchairs, rugs, the cat tree | Moves anywhere on a floor, its own room or another. Can't be stored: cats need its station |
| **decor** | plants, lamps, bookcases, bowls, chests | Moves anywhere. It can be stored in the catalogue, and brought back as many times as she likes |

Walls, doorways, glass and the floors are the house itself (`manor.py`) and don't move. Moving or resizing
rooms is out of scope: it would need the house drawn at runtime, and everything keyed to a room's box
would change.

## Getting in and out

- **In:** the Live / Build switch on the map panel (Game UI Pastel: the round knob on a rectangle track),
  or Renovate in the House menu. On a phone, Build opens only when zoomed into one room (about 0.27 scale on
  the whole house is too small to place anything).
- **Out:** the same switch, Escape with nothing selected, or Done in the catalogue bar. There is no Save:
  each change was saved when it was dropped.
- **View-only visitors** see no switch. A refused write shows `save()`'s "You can look but not change things
  on this page."

## What the screen does in Build

- Cats fade and clicks pass through them, bubbles and menus are off, and the brand's badge stays.
- A 16 px floor grid shows from the "1 art pixel = 2 screen pixels" zoom step upwards.
- Hovering a piece brackets it (Sprout Lands' corners, as rooms light up). Essential pieces show the lock.
- A Ribbon (Game UI Pastel, Apple Green) says "Build" at the top centre.
- The map panel stays. The minimap outlines rooms only, and a click frames that room for building.
- **The catalogue bar** runs along the bottom: a Game UI Pastel horizontal panel, with tabs by kind of piece
  (seating, tables and desks, storage, plants, rugs, wall pieces, cat things). Each tab holds thumbnails of
  the decor pieces, drawn small from the atlas cells. It also holds what is stored, Undo, Redo, Reset room
  and Done.

## Moving a piece

**With the pointer**
- Drag with `setPointerCapture` past a 4 px threshold.
- It snaps to 4 native pixels, or 1 with Alt held, and shows red where it can't go.
- It's written on the drop, never on pointermove.
- Panning in Build is a drag on empty floor, a right or middle drag, Space-drag, or WASD and the arrows
  (phase 2), because a drag on a piece moves the piece.

**Without dragging** (WCAG 2.5.7)
- Click or Tab to select a piece, then use the arrows to nudge it (4 px, or 16 with Shift).
- Enter opens its small menu: Move to… (a room), Store, Looks like… (cabinets only), Done.
- Every move is said in `#say`.
- While a piece is selected, the arrows nudge it rather than walking rooms. Escape deselects, and the arrows
  walk rooms again.

**Where a piece may land**, by layer:
- **floor** pieces: the footprint must be inside the room's floor (`MANOR.floors`), clear of other floor
  pieces' footprints, and clear of a doorway's path (`MANOR.doors`, with a 10 px margin);
- **rug** pieces: anywhere on the floor, under everything;
- **wall** pieces (mirror, towel, basin): in the room's back-wall band (`MANOR.face`, the 32 px at the top
  of the room);
- **top** pieces (the sink, yarn, the tin of buttons): on top of a floor piece's footprint;
- **every piece**: no station may end up in furniture or off the floor. That's the same rule as
  `furniture.check()`, run in the page. A drop that breaks it is refused and the piece goes back.
- A filing cabinet dropped outside its room goes back where it was, and the toast says why.

## Adding and removing

- **Store** sends a decor piece to the catalogue's stored row.
- **Adding:** drag a piece from the catalogue onto a floor. It comes from the stored row or a fresh one from
  the catalogue.
- Connected and essential pieces have no Store.
- A room holds at most 40 pieces. Past that, the toast says so.

## The filing cabinet's look

- Clicking a room's cabinet in Build (or Looks like… in its menu) opens a small Game UI Pastel panel beside
  it. It shows a row of thumbnails: every floor piece in the catalogue except the stair, storage first.
- Picking one swaps the piece in place. **It keeps its job:**
  - the Files hit box takes the new piece's size (`GEOM[k].cabinet` is read from the layout's `cabinet`, no
    longer found by the key `filing_cabinet`);
  - the review spot moves in front of it: its own `review` station if the piece has one, else the free
    floor nearest the middle of its front edge;
  - a screen reader hears its job: "the Bedroom's files, a dresser".
- A look too big for its spot moves to the nearest free floor that fits. If there's none, the choice is
  refused and the old look stays.
- Defaults: `filing_cabinet` indoors, `catio_chest` on the catio.

## Undo, redo and reset

- Undo and redo (`Ctrl+Z` / `Ctrl+Shift+Z`, and Game UI Pastel's `Reload` icon on circle buttons, mirrored
  for undo) step through the changes made since Build was switched on. Each step is itself a saved layout.
- **Reset room** puts back `MANOR.layout` and the default cabinet, after one "Are you sure?".

## Cats and queens follow the furniture

- `stationsOf(room)`, `freeFloor(room)` and `GEOM` are worked out from the room's current layout, not from
  `MANOR.layout`. A cat whose station moved walks to its new spot when Build ends; with reduced motion it
  is simply there.
- A queen sits on the queen station of her room's piece (an armchair, a chair, the bath mat). If that piece
  moves, she moves with it. If it goes to another room, the next queen station in her room is hers, and if
  there's none, she sits on the free floor nearest the middle of the room.
- Renders are held during a drag, because a database snapshot calling `render()` would destroy the piece
  in her hand. They catch up on the drop.

## Data

- **`layouts/<room>`**: `{ pieces: [[key, x, y], …], cabinet: { look, x, y }, updatedAt }`. Stored pieces are
  absent from `pieces`. With no document, the room uses `MANOR.layout` and the default cabinet. CLAUDE.md's
  data table already has the row.
- **`layouts/_stored`**: `{ pieces: [key, …] }`, what she has put away.
- The same collection in `runtime-stub.js`, `localRuntime()` and `catio/data/` (a `layouts.json` beside
  `rooms.json`, for the localhost copy).
- One write per drop, pinned to the version read, so two open tabs can't overwrite each other.

## Steps

Each step is a commit, with its checks, the e2e test green, and screenshots.

1. **Layouts as data, read only.** The page reads `layouts/*` and draws from it; the stub and
   `localRuntime()` hold it. GEOM, stations, free floor and queens come from it.
   - *Checks:*
     - with no documents the page is unchanged (every existing check passes);
     - a stub layout with a moved desk moves the cat that works there.
2. **Build, and moving.** The switch, the grid, drag with snap, the drop rules, the keyboard and
   Move to…, undo and redo, reset, and held renders.
   - *Checks:*
     - a pointer drag moves a piece and saves one document on the drop;
     - a drop on another piece, off the floor or across a doorway goes back;
     - an essential piece won't move;
     - a filing cabinet dragged into the next room goes back and nothing is saved;
     - arrows nudge the selected piece, and Escape gives the arrows back to the rooms;
     - undo puts it back;
     - a snapshot mid-drag doesn't destroy the piece;
     - no cat stands on furniture after a move;
     - a view-only visitor gets the toast.
3. **The catalogue and the cabinet's look.** Store and bring back, adding a fresh decor piece, and
   Looks like….
   - *Checks:*
     - storing a plant removes it and lists it, and bringing it back places it;
     - a desk has no Store;
     - choosing a dresser for the Bedroom's cabinet:
       - draws it;
       - saves `cabinet.look` in `layouts/bedroom` only;
       - its Files still lists the Bedroom's projects;
       - a cat with something to review waits in front of it;
       - it's still there after a reload, on localhost too.
4. **Phones.** Build only inside a zoomed-in room; touch drags on pieces only (`touch-action: none` on
   pieces, so a drag on the floor still pans).
   - *Checks:* on 390×844, the switch only appears inside a room, and a touch drag moves a piece.

## Traps (from the first note, still true)

- A drop leaves the piece under a still pointer. `moved()` keeps menus shut then, which is correct: don't
  work around it.
- Block drops during the 0.55 s camera glide.
- The stage's click must not close or zoom out after a drop (swallow the click, as panning does).
- Keep the no-art copy working: every Build piece has a plain colour under it.
- Never paste her real sessions or layouts into the stub.
