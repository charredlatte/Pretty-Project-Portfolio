# Renovation mode: constraints

Collected from the rooms-redesign session's heads-up (29 September 2026). Read this before building
drag-and-drop furniture. The UX spec from that session comes first; these are the traps under it.

## Decisions already made (Charlotte)

- The room UI from the rooms redesign stays exactly as it is:
  - the signs and badges on each back wall;
  - the Sprout Lands brackets;
  - the map as one Tab stop (arrows, Enter, Esc);
  - Edit rooms as a cabin plan with tabs;
  - hover menus that open only on a real pointer move (`moved()`).
- Furniture is no longer drawn into the art at build time. It becomes pieces that renovation mode places.
- The asset zips are in her Drive folder "KittyChat Cafe Assets". Their names have spaces where CLAUDE.md's
  `build-art.py` command has underscores, so pass them in the documented order.

## Taking the furniture out of the pictures

- `house.png` becomes the shell only: floors, walls, wallpaper, doorways and glass.
- `decor.png` becomes the outdoors only.
- Furniture becomes sprite atlases split by licence. The Cosy Cabin atlas can be committed; the others ship
  only in the artifact under `art/licensed/`.
- Today's positions in `cabin.py` (`FURNITURE`, plus the indoor pieces in `decor()`) become the default
  layout data, so the defaults have one source.
- Draw order becomes z-order:
  - rugs first, then wall pieces, then everything else by its bottom edge;
  - at runtime pieces share the cats' z-space, `zIndex = 1000 + feetY*2`, or cats end up over tables and under rugs;
  - wall pieces (windows, mirrors, frames) live in the 32 px back-wall band (`FACE`);
  - floor, rug and wall pieces each have their own drop rules;
  - fixtures (the fireplace, glass and doorways) most likely don't move.
- Update CLAUDE.md's publish file list, `bundle.py`, and `run.sh`'s no-art copy to match.

## Geometry follows the furniture

- The cat spots, the queen seats (`GEOM[room].queen`, held back from the spots) and the filing-cabinet
  hit boxes were placed by hand to keep clear of furniture.
  - After a piece moves, work out the free floor again, or re-check the seats.
  - Decide whether a filing cabinet can leave its room.
- Layout becomes data, on purpose. Add it everywhere the data lives:
  - a `layouts/<room>` collection in CLAUDE.md's data table;
  - `runtime-stub.js`;
  - `localRuntime()`;
  - `data/rooms.json` (or a sibling file).
- Changing a room's floor and wallpaper is cheap once the shell is data. Moving or resizing rooms is far
  bigger: it needs a JS port of `house()`. Every piece keyed to `GEOM[k].r` would then change at runtime:
  - hit boxes, signs and brackets;
  - `NEXT`;
  - the Rooms plan's `PLAN` crop;
  - `layout()`'s focus boxes;
  - `PROPS`.

## Interaction (the page is all hover menus)

- Enter the mode from a menu. While it's on:
  - suppress hover menus;
  - drag with `setPointerCapture` and a threshold;
  - make sure the stage's click doesn't close menus or zoom out after a drop;
  - put `touch-action: none` on pieces only, because `armed()` would eat touch drags.
- Convert pointer to world coordinates with `S.cam {s, tx, ty}`, snap to art pixels or 16 px tiles, and
  block drops during the 0.55 s camera move.
- After a drop the piece sits under a still pointer. `moved()` keeps menus shut then, which is correct:
  don't work around it.
- WCAG 2.5.7 needs a way to move pieces without dragging:
  - keyboard nudges on the selected piece (these clash with the arrows that walk between rooms);
  - a "Move to…" menu item;
  - announcements in `#say`.
- On phones (about 0.27 scale on the whole house), edit only inside a zoomed-in room.

## Data and rendering

- Write on drop, never on pointermove.
- A snapshot calls `render()`, which rebuilds `#cats` and the overlay and would destroy a piece being
  dragged. Hold renders during a drag.
- View-only viewers get `invalid_argument`: reuse `save()`'s toast.
- Extend `catio/test/e2e.mjs` with pointer-event drags, and keep the no-art copy passing. Never paste
  real sessions into the stub.
