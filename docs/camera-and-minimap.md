# The camera and the minimap: the plan

Asked for on 30 September 2026: click-and-drag to move around the map, a minimap of the manor in the top-right
corner that folds away, and a camera and controls that feel like The Sims' build mode. This is the plan only.
Nothing is built yet.

It is written against the **live page**: version 12 (`1790787324-9d33`), the two-floor manor, published on
30 September 2026 at 16:56 from `ccr-bfc398ff-3gh5wb`. That branch isn't merged into `main` yet, and Charlotte
asked for the redesign to wait until it is finished. Build on it once it is merged, not on `main` as it stands.

## Where the camera stands in version 12

Version 12 already does a lot of this:

| Already there | How |
|---|---|
| Drag to pan | Left-drag on the house (after 4 px, so a click is still a click); right, middle or Space-drag from anywhere; one finger on touch |
| Zoom around the pointer | Wheel and trackpad pinch (`zoomAt`), two-finger pinch on touch |
| Zoom buttons and keys | `+` `−` `0` and the corner cluster (`#controls`, bottom right) |
| Floors | The floor switch in the same cluster, the stair, Page Up / Page Down |
| The room you're in | `settleFocus()` picks the room that fills the view, and its bubbles speak |
| Limits | `clampCam()` never shows past the meadow; zoom is capped by `limits()` |
| The whole house's menu | The House button (`#houseBtn`), top right |
| Keys | Arrows walk between rooms; Shift+arrows pan; Page Up / Page Down change floor; `+` `−` `0` zoom; Escape backs out; Space-drag pans. No letter keys are taken, and neither is Home on the map |
| Corners | The sign top left, House top right, the floor and zoom cluster bottom right, the credits bottom left |

What it lacks: any sense of where you are once zoomed in, keyboard panning that isn't Shift+arrows, zoom that
lands on crisp pixel sizes, and a quick way to jump across the house. The top-right corner is also taken by the
House button, which is exactly where the minimap is wanted.

## What goes on screen

When this plan is done, there are three things on screen and nothing else:

1. **The sign**, top left. It is unchanged: the tally, plus the warning when something is wrong.
2. **The map panel**, top right. It takes the place of both the House button and the bottom-right cluster:

   ```
   ┌───────────────────────────────┐
   │ [House ▾]  [G | U]       [–]  │  ← header: House menu, floor tabs, fold
   │ ┌───────────────────────────┐ │
   │ │  ▢▢▣▢    ░ catio          │ │  ← the floor as a plan, in the pack's frame
   │ │  ▢[▢▢]▢  ░                │ │     [ ] = what the camera sees
   │ │  ▢▢▢▢•                    │ │     •   = a room where a cat needs you
   │ └───────────────────────────┘ │
   │ [−] [+] [⌂]                   │  ← zoom out, zoom in, whole house
   └───────────────────────────────┘
   ```

   Folded, only the header row stays. The fold button then carries the badge (the mood face and a count) when
   a cat that needs Charlotte is off screen or on the other floor.
3. **The mode switch**, bottom left: `Live` / `Build`. It only appears in iteration 3 (below), when build mode
   exists. The credits move back to the bottom right, which the old corner cluster frees up. They stay hidden
   on a phone, as they are now.

Together, that's one fewer cluster of controls than version 12 has, and every control that moves the camera is
in one place.

## The minimap

**What it draws** (decided 30 September): a plan of the current floor's rooms, not a shrunk copy of the
picture. At about 200 px wide the pixel art shrinks to mush. Room boxes read at a glance, and they are the
thing the minimap is for.

- The panel, its frame and its icon buttons come from Game UI Pastel (see "The two UI packs" below).
- Each room is a box from `GEOM[k].r`. It takes one of three flat fills, from Game UI Pastel's palette (or
  Sprout Lands' button faces, if the Pastel pack has no piece to take the colours from):
  - a plain fill for an ordinary room;
  - a lighter one for the room under the pointer, on the map or in the house;
  - the green one for the room you're in (`S.focus`).
- The other floor's rooms show faintly underneath, the same way the house fades the ground floor under the
  upper one.
- A room where a cat needs Charlotte gets a small pink pip, and a red one when a cat there is upset. No text
  and no faces: the badge on the room's sign already says the rest.
- The stair is marked (`MANOR.stairs`), and so is the landing upstairs (`MANOR.landing`), so the floors line up
  in your head. Upstairs is only the Library, the bedroom and the bathroom, so the upper plan is mostly
  landing and faded ground floor. That's honest, and fine.
- **The camera's view** is a rectangle drawn with Game UI Pastel's selection outline. If the pack has none, it
  uses Sprout Lands' white brackets (`corners.png`), the ones that light up a room. It stays the same size on
  screen at any zoom.
- The map covers `WORLD`, the whole grounds, so the view rectangle is always inside it. The manor fills most of
  it.

**What it does.**

| On the minimap | Does |
|---|---|
| Click or tap | The camera glides there, at the same zoom |
| Drag the view rectangle, or drag anywhere on the map | The camera pans live, with no glide |
| Double-click a room | Look in (`go(k)`) |
| Wheel | Zooms the camera about the point under the pointer on the map |
| Hover a room | Names it in the tip line, as hovering in the house does |
| `G` / `U` tabs | Change floor (`setFloor`) |
| Fold button, or `M` | Folds or unfolds the panel |

**Cost.** The rooms are redrawn in `render()`, which already runs on every data change. The view rectangle is
one element moved by `transform` from inside `setCam()`, so dragging the house stays smooth.

**Remembered.** Folded or open is kept in `localStorage` as `catio.minimap`, wrapped in `try`. It's a
per-viewer convenience, like `catio.sound`. It starts open on a laptop and folded on a phone (560 px wide or
less), where the house is small enough already.

**Menus keep clear of it.** `showMenu()` and the hover tip must treat the panel's box as off limits, the same
way they already keep inside the stage. Otherwise a room menu on the right-hand side opens underneath it.

**Accessibility.**
- The minimap is a faster way to do what the keyboard can already do (arrows between rooms, Enter, Look in,
  Page Up / Page Down), so its drawing is `aria-hidden`.
- The fold button has `aria-expanded`, and the floor tabs are real buttons with `aria-pressed`.
- Dragging the view has a single-click alternative (click to jump), which WCAG 2.5.7 asks for.

## The camera, in the manner of The Sims' build mode

The Sims' build camera feels good for four reasons, and each has an equivalent here:

1. **You can move without touching the mouse** (decided 30 September): WASD and the arrow keys both pan.
   - Holding a key keeps the view moving, a little faster the longer it's held, smoothed on
     `requestAnimationFrame`.
   - Two keys held together go diagonally, and W and ↑ (and so on) are the same key.
   - Moving the view closes an open menu and the tip, as dragging does.

   The arrows have a second job they must keep: for someone using only the keyboard, the map is one Tab stop and
   the arrows walk from room to room (`arrows()`, the tested keyboard map). They do one or the other:

   | Where focus is | Arrow keys | Shift+arrows | WASD |
   |---|---|---|---|
   | Nowhere, or on the house after a mouse click or a tap | Pan | Pan | Pan |
   | On a room, arrived at by Tab, an arrow or Escape from its menu | Walk to the room next door; the camera glides after it when that room is partly off screen | Pan | Pan |
   | In a menu, a field, a dialog or a select | Left to that control | Left to that control | Typing |

   How the page tells which: a `keyNav` flag, set when a room takes focus straight after a keydown, and
   cleared on any pointerdown. Don't use `:focus-visible` at the moment of the keypress, because browsers
   don't agree on it after a mouse click. So a mouse user who clicks a room and presses → pans, and a
   keyboard user who tabs onto the map walks the rooms, exactly as the e2e test expects now.
2. **Zoom lands on steps.** The + and − buttons, `Z` / `X` and the keys step through fixed levels: the whole
   house, one floor, then one art pixel as 1, 2, 3 and 4 screen pixels. Wheel and pinch stay smooth. About
   180 ms after they stop, the camera eases to the nearest step when it is close to one (within about 12%).
   Pixel art only looks sharp at whole-number sizes, so this also stops the shimmer that fractional zoom leaves
   on the furniture.
3. **Releasing a drag carries on a little.** A flick keeps gliding briefly and slows to a stop. There is no
   glide with reduced motion, and never past `clampCam()`'s edges.
4. **You can jump.**
   - `F` frames the thing whose menu is open: a cat, a room or a queen.
   - `Home` or `0` goes to the whole house.
   - Double-clicking a room looks in.
   - The minimap jumps anywhere.

Optional, both **off** by default, each with a switch in the House menu:

- **Edge scroll:** holding the pointer at the edge of the screen pans that way. It's off because the menus and
  the map panel live at the edges.
- **Saved views,** as The Sims has: `Ctrl+1`…`Ctrl+5` saves the camera and floor, and `1`…`5` goes back to it.
  They're kept in `localStorage` as `catio.views`.

**Letter keys.**
- WASD, Z, X, F and M only act when focus is on the house or the page: never in a field, a dialog or a menu.
- There's a "Keyboard shortcuts" switch in the House menu to turn them off. WCAG 2.1.4 asks for a way to turn
  off single-key shortcuts. The arrows aren't character keys, so they keep working when the switch is off.
- Pressing `?` lists the keys in the tip line.
- `#keyhelp`, the text a screen reader hears on a room, gains "WASD or the arrows move the view when no room
  is selected".

**No rotation.** In The Sims, "orientation" means turning the camera. This map can't turn. Every piece of the
art is drawn from one side:
- back walls face north;
- shadows fall one way;
- doors and windows have fixed faces.

Turned 90°, the walls would show their tops and the furniture would lie on its side. North stays up. The
minimap is what keeps you oriented instead.

## Live and Build: how the interaction changes

The Sims splits play from building, and the Catio can too. This picks up `docs/renovation-mode.md`, whose
constraints still apply.

**Live** is the page as it is. The camera moves, cats and rooms open their menus, and the bubbles speak.

**Build** swaps in a different set of tools. The camera works the same way; what a click does changes:

- The cats step aside (faded, and clicks pass through them), and menus and bubbles are suppressed.
- A 16 px floor grid shows from the "1 art pixel = 2 screen pixels" step upwards.
- Hovering a piece of furniture brackets it. Dragging it moves it (`setPointerCapture`, snapped to the grid,
  written on drop, never on every move). So in Build, panning is a drag on empty floor, a right or middle drag,
  Space-drag, WASD or the arrows. That's why the keys matter.
- **Each room's filing cabinet is a job, not a piece of furniture** (decided 30 September). It is where the
  room's files live: the Files hit box, the room menu's Files, and the spot where a cat with something to
  review waits. What it looks like is Charlotte's choice, room by room: a dresser in the bedroom, a bookcase in
  the Library, a sideboard in the dining room, the chest on the catio.
  - **Choosing the look.** In Build, clicking the room's cabinet opens a small Game UI Pastel panel beside it,
    "Looks like…". It shows a row of thumbnails: every floor piece in the catalogue, the stair excepted, with
    storage pieces first (cabinets, chests, dressers, sideboards, bookcases, desks). Picking one swaps the
    piece in place. The keyboard reaches the same panel with Enter on the selected cabinet.
  - **It keeps its job whatever it looks like.**
    - The Files hit box takes the new piece's size (`GEOM[k].cabinet` is read from the layout's cabinet, no
      longer found by the key `filing_cabinet` or `catio_chest`).
    - The review spot moves to just in front of the new piece: its own `review` station if it has one, else
      the free floor nearest the middle of its front edge.
    - Its name for a screen reader stays its job: "the Bedroom's files, a dresser".
  - **It stays in its room.**
    - It can be moved anywhere on its own room's floor, and while it's dragged the brackets stay on its room.
    - A drop outside the room puts it back where it was, and `#say` and a toast explain why.
    - It can't be stored in the catalogue.
  - **A look too big for its spot** moves to the nearest free floor in the room that takes it. If there's
    none, the choice is refused with a toast, and the old look stays.
  - **Defaults:** the filing cabinet indoors and the chest on the catio, as now.
- A catalogue bar along the bottom holds the pieces from `MANOR.pieces`, grouped by room kind. Drag one in, or
  drag one out to the bar to store it.
- Undo and redo (`Ctrl+Z` / `Ctrl+Shift+Z`) apply to the layout changes made in this Build session.
- The map panel stays. The minimap outlines the rooms only, and a click on a room there frames it for building.
- Edit rooms (names, repositories, where new cats come in) moves under Build, where it belongs.

## The two UI packs

Charlotte decided on 30 September that `Game_UI_Pack_Pastel.zip`, from her Drive folder "KittyChat Cafe
Assets", goes in alongside Sprout Lands. Nobody has opened it yet, so its sheets are unknown. The first job of
iteration 1 is to list them and fill in the table below.

**Who does what.** Each surface is drawn from one pack only, never a mix of both inside one panel:

| Sprout Lands UI (unchanged) | Game UI Pastel (new) |
|---|---|
| Room, cat and queen menus; dialogs; speech bubbles; the sign; the room brackets; the mood faces; the crown and stars; the paw pointer; the pixel font | The map panel: its frame, header and fold button; the icon buttons (zoom in, zoom out, whole house, floor up and down); the minimap's fills; in Build: the Live / Build switch, the catalogue bar and its tabs, the cabinet's "Looks like…" panel, undo and redo; key caps for the `?` list, if it has them |

The split follows the kind of thing:
- what talks about the cats and rooms stays Sprout Lands;
- what works the camera, and what builds the house, comes from Game UI Pastel.

The switches inside the House menu stay Sprout Lands' toggle, because the House menu is a Sprout menu.

**Scale.** Check whether the Pastel pack is pixel art:
- **If it is,** it's drawn like Sprout Lands, at whole multiples (`--u`) with `image-rendering: pixelated`.
- **If it's smooth, higher-resolution art,** it's scaled down to fit, with ordinary smoothing, never
  pixelated.

Either way, check it next to the tan panels in light and dark before committing. If a role in the table has no
fitting piece in the zip, that role falls back to Sprout Lands, and the table records it.

**Getting it into a session.** At 12.5 MB, the Drive connector can't hand it over, because it returns files
inline. Charlotte attaches it in the chat of the session that builds iteration 1. Then:
- `build-art.py` takes it as one more zip (the interface alone can be rebuilt from Sprout Lands and it);
- it cuts the pieces into `art/licensed/pastel/`;
- `bundle.py` and the publish `files` list pick them up;
- `run.sh`'s no-art copy leaves them out, and every Pastel surface keeps a plain colour underneath, as the
  Sprout pieces do.

**Licence.** Charlotte chose to use it. Its maker and terms are still unknown, so it's treated like the other
licensed packs:
- the session that opens it reads any licence or readme file inside;
- it records the maker and the terms in `catio/art/CREDITS.md` and the footer credits;
- it keeps the files under `art/licensed/`, which is gitignored and ships only in the private artifact.

If those terms rule out a web page, stop and tell Charlotte before building on it.

**Rules to update.** CLAUDE.md says a new control reuses a Sprout Lands piece. It needs a line for the second
pack, following the split above. Claude's edits to CLAUDE.md have been refused before, as self-modification, so
that line goes to Charlotte. `litterbox/loose-ends.md` and `docs/plan.md` still say the pack stays out: change
them when the manor branch is merged.

## Iterations

Each iteration ends with the e2e test green, screenshots at 1440×900 and 390×844 in light and dark, and one
commit. Only then does the next start.

**1. The map panel and the minimap**
- Open Game UI Pastel (attached in the chat), record its maker and terms, fill in the table above, and cut its
  pieces with `build-art.py`.
- Merge the House button, the floor switch and the zoom buttons into the panel, and draw the minimap.
- Add click-to-jump, drag-the-view, double-click to look in, fold, and `M`.
- Keep menus clear of the panel.
- *Checks:*
  - the view rectangle matches the camera after a drag, a wheel zoom and Look in;
  - a click on the minimap moves the camera there;
  - folding is remembered across a reload;
  - the phone starts folded;
  - a room menu on the right never opens under the panel;
  - the no-art copy still draws the panel and its buttons on plain colour;
  - the whole house's actions (the brain, house rules, Edit rooms, sound, the attic) are still reachable
    from House in the panel.

**2. The camera**
- Add WASD with acceleration, zoom steps with settling, the flick glide, `F`, `Home`, and the shortcuts
  switch.
- *Checks:*
  - holding `D` moves the view right, and stops at the meadow's edge;
  - after a mouse click on the house, holding → pans just like `D`;
  - after Tab onto the map, → moves the ring to the room next door (the existing keyboard checks pass
    unchanged), and the camera follows when that room is off screen;
  - Shift+→ pans in both cases;
  - `Z` and `X` land exactly on the steps, and the scale times 2 is a whole number from the first zoom-in step
    upwards;
  - letter keys do nothing inside an input;
  - the shortcuts switch turns the letters off, and the arrows still pan;
  - reduced motion means no glide.

**3. Build mode**
- Add the Live / Build switch, the grid, moving furniture with undo, the catalogue bar, and Edit rooms moved
  under Build.
- It needs `layouts/<room>` in the database, the stub, `localRuntime()` and `data/`, as
  `docs/renovation-mode.md` lists. Each layout document holds the room's pieces, plus
  `cabinet: {look, x, y}`: the piece key it looks like and where it stands. A room with no layout document
  uses `MANOR.layout` and the default look. Add `cabinet` to the data table in CLAUDE.md (that line goes to
  Charlotte, as above).
- *Checks:*
  - a pointer drag moves a piece and saves one document on drop;
  - a filing cabinet dragged into the next room goes back to where it was, and nothing is saved;
  - a filing cabinet moved within its room keeps its Files;
  - choosing a dresser for the Bedroom's cabinet:
    - draws a dresser where the cabinet stood;
    - saves `cabinet.look` in `layouts/bedroom` only;
    - its Files still lists the Bedroom's projects;
    - a cat with something to review waits in front of it;
    - the Dining room keeps its own look;
    - it's still there after a reload, on localhost too;
  - a look too big for the spot moves to free floor, or is refused and the old look stays;
  - a snapshot arriving mid-drag doesn't destroy the piece;
  - undo puts it back;
  - no cat stands on furniture after a move;
  - a view-only visitor gets the "look but not change" toast.

The optional edge scroll and saved views come after iteration 2, if Charlotte wants them.

## Decided (Charlotte, 30 September 2026)

1. **The minimap is a plan of rooms**, not a tiny picture.
2. **WASD pans, and so do the arrow keys.** The letters sit behind a shortcuts switch. The arrows still walk
   between rooms for anyone who tabbed onto the map.
3. **Game UI Pastel is used**, for the map panel, the camera's controls and Build's tools. Sprout Lands keeps
   everything else.
4. **A filing cabinet never leaves its room**, but Charlotte chooses what it looks like in each room: any
   floor piece in the catalogue. It keeps its job, its Files and its review spot, whatever it looks like. This
   settles the question left open in `docs/renovation-mode.md`.

Still to come, after iteration 2, if Charlotte wants them: edge scroll and saved views.
