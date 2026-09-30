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

**What it draws.** A plan of the current floor, not a shrunk copy of the picture. At about 200 px wide the
pixel art shrinks to mush. Room boxes read at a glance, and they are the thing the minimap is for.

- The panel is the Sprout Lands tan panel, and the map inside it sits in the pack's picture frame
  (`frame.png`).
- Each room is a box from `GEOM[k].r`. Its colour comes from the pack's button faces:
  - cream for an ordinary room;
  - white (`button-hover`) for the room under the pointer, on the map or in the house;
  - green (`button-green`) for the room you're in (`S.focus`).
- The other floor's rooms show faintly underneath, the same way the house fades the ground floor under the
  upper one.
- A room where a cat needs Charlotte gets a small pink pip (`button-pink`'s face colour), and a red one when a
  cat there is upset. No text and no faces: the badge on the room's sign already says the rest.
- The stair is marked (`MANOR.stairs`), and so is the landing upstairs (`MANOR.landing`), so the floors line up
  in your head. Upstairs is only the Library, the bedroom and the bathroom, so the upper plan is mostly
  landing and faded ground floor. That's honest, and fine.
- **The camera's view** is a rectangle drawn with the pack's white selection brackets (`corners.png`), the same
  brackets that light up a room. It is drawn at one pixel per art pixel, whatever the zoom.
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

1. **You can move without touching the mouse.** WASD pans. Holding a key keeps it moving, a little faster the
   longer you hold it, smoothed on `requestAnimationFrame`. Arrow keys stay as they are, walking from room to
   room (the map is one Tab stop and that must not break); Shift+arrows keeps panning, as now.
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
  off single-key shortcuts.
- Pressing `?` lists the keys in the tip line.

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
  Space-drag, or WASD. That's why the keys matter.
- A catalogue bar along the bottom holds the pieces from `MANOR.pieces`, grouped by room kind. Drag one in, or
  drag one out to the bar to store it.
- Undo and redo (`Ctrl+Z` / `Ctrl+Shift+Z`) apply to the layout changes made in this Build session.
- The map panel stays. The minimap outlines the rooms only, and a click on a room there frames it for building.
- Edit rooms (names, repositories, where new cats come in) moves under Build, where it belongs.

## Iterations

Each iteration ends with the e2e test green, screenshots at 1440×900 and 390×844 in light and dark, and one
commit. Only then does the next start.

**1. The map panel and the minimap**
- Merge the House button, the floor switch and the zoom buttons into the panel, and draw the minimap.
- Add click-to-jump, drag-the-view, double-click to look in, fold, and `M`.
- Keep menus clear of the panel.
- *Checks:*
  - the view rectangle matches the camera after a drag, a wheel zoom and Look in;
  - a click on the minimap moves the camera there;
  - folding is remembered across a reload;
  - the phone starts folded;
  - a room menu on the right never opens under the panel;
  - the no-art copy still draws the panel on plain tan.

**2. The camera**
- Add WASD with acceleration, zoom steps with settling, the flick glide, `F`, `Home`, and the shortcuts
  switch.
- *Checks:*
  - holding `D` moves the view right, and stops at the meadow's edge;
  - `Z` and `X` land exactly on the steps, and the scale times 2 is a whole number from the first zoom-in step
    upwards;
  - letter keys do nothing inside an input;
  - the shortcuts switch turns them off;
  - reduced motion means no glide.

**3. Build mode**
- Add the Live / Build switch, the grid, moving furniture with undo, the catalogue bar, and Edit rooms moved
  under Build.
- It needs `layouts/<room>` in the database, the stub, `localRuntime()` and `data/`, as
  `docs/renovation-mode.md` lists. It also needs the answer to whether a filing cabinet can leave its room.
- *Checks:*
  - a pointer drag moves a piece and saves one document on drop;
  - a snapshot arriving mid-drag doesn't destroy the piece;
  - undo puts it back;
  - no cat stands on furniture after a move;
  - a view-only visitor gets the "look but not change" toast.

The optional edge scroll and saved views come after iteration 2, if Charlotte wants them.

## Decisions for Charlotte

1. **A plan of rooms, or a tiny picture, for the minimap.** Recommended: the plan of rooms. It's crisp at that
   size and shows only what matters.
2. **WASD.** Recommended: yes, behind the shortcuts switch.
3. **The Game UI Pastel pack.** Its licence is still unknown, so it stays out. Iterations 1 and 2 need nothing
   beyond Sprout Lands. The catalogue bar in iteration 3 is where a second UI pack would be most useful.
4. **Can a filing cabinet leave its room in Build?** This is still open from `docs/renovation-mode.md`.
