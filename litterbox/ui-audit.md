# UI/UX audit of the Catio, with Charlotte's Game UI plugin (29 September 2026)

Run with her MCPmarket `ui` skill: role Game UI Designer, with UI Designer accessibility. References: `menu-systems`,
`game-ui-accessibility`, `game-ui-patterns`, `accessibility`, `usability-heuristics`, `interaction-patterns`.

- **How it was checked:** the reviewer read `catio/index.html`, looked at laptop and phone screenshots, and
  moved a real mouse over the test copy of the page in a headless browser.
- **What was left out:** gamepad guidance doesn't apply (no gamepad), so it was skipped.
- **Status:** report only. Nothing has been changed yet. Pick what to fix.
- **Line numbers:** they are for `catio/index.html` at commit `1d428ac`.

## Summary

The pixel UI is consistent and legible, and several things are already done well:
- dark ink on the tan panels reads at 7.3:1;
- deletes ask twice;
- empty states and connector errors are in plain language;
- reduced motion is respected.

The serious problem is hover. When you move the mouse from a room or a cat towards its menu, the pointer
passes over something else on the way, and that thing's menu replaces the one you wanted. On the phone,
the house is too small to use at the start.

## Critical

**1. Moving the mouse to a menu opens a different menu.** **Fixed** (29 September): with a menu open,
another room or cat takes over only once the pointer rests on it for 240 ms; reaching the menu cancels the
switch. Seven new e2e checks glide the mouse in small steps. Tested by moving the mouse the way a person does
(25 small steps):
- Kitchen → its menu turned into **Dining room**.
- Dining → a queen's menu (**Philomène**).
- Bedroom → **Hall**.
- A cat → its own **room's** menu (Pomme → Kitchen, Caramel → Craft room).

*Why:*
- Each menu sits 12px beside the thing it belongs to (`g = 12`, lines 1063 and 1073–1074).
- That 12px gap is covered by the next room, or by the room floor around a cat.
- `hoverable()` (1020–1023) opens a new menu the moment the pointer enters something, with no delay.
- A fast flick sometimes skips the gap, so it feels random.

*Why it matters:* hover is the only way into the page's controls. Right now she has to "sneak" onto a menu.

*Fix:*
- In `hoverable`, when a different menu is already open, wait about 200ms before opening the new one, and
  cancel if the pointer reaches `#menu`.
- Never let a cat's, pile's or queen's own room take over their menu while it is open.
- Consider `g = -4`, so the menu overlaps its anchor and there is no gap at all.
- Add a test that moves the mouse with `mouse.move(x, y, { steps: 20 })`. Playwright's `click()` jumps
  straight to the button, which is why the tests missed this.

## Warning

**2. On a phone, the house is tiny, has no room names, and cats can't be tapped.**
- At 390×844 the house fills about an eighth of the screen. The camera fits the whole grounds by width
  (`WHOLE`, 373; `layout()` 933–948).
- Room names are hidden, because signs need `room >= 56` (1216). Only the badge shows.
- Measured tap targets: cats 6–12px, rooms 38–92px (bathroom and sunroom are 38×44).
- *Fix:*
  - on narrow portrait screens, open zoomed into the most urgent room (`labelRooms` already works out
    which one);
  - add a left/right swipe that follows the existing `NEXT` map;
  - fit the camera to the house (`PLAN`) rather than the whole grounds.

**3. Buttons are too small to tap on a phone.**
- `--u` is 1px on phones (line 31), so a `.btn` is 32px tall. The Sound switch is 22px (196–197).
- *Fix:* add `@media (pointer: coarse) { .btn, .sound { min-height: 44px; } }` with padding to centre the
  text. The 9-slice art stretches to fit.

**4. The live status can only be read by hovering.**
- When all is well, the words ("Live · updated 14:02…", or the saved-copy date) are hidden unless the sign
  is hovered (92–93).
- Keyboard focus never reaches the sign, and touch has no hover.
- The tick has no text (1309), so a screen reader gets an empty status.
- In the warning state, `renderStatus()` rebuilds the status on every data update and every minute
  (1406–1421, 2355), so the same long error can be announced again and again.
- *Fix:*
  - give the tick a hidden label ("Live", "Saved copy");
  - make the sign focusable (`tabindex="0"`), or put a status line in the room menu's footer;
  - only update `#status` when its text actually changes.

**5. Errors and long confirmations vanish after 3.2 seconds.**
- `toast()` (2329) hides every message after 3.2s. That includes:
  - "Couldn't save…";
  - the 150-character "Queued: claude.ai won't let this page…" message (1878);
  - the brain's combined report for several files (2029).
- *Fix:*
  - keep error and "queued" messages until dismissed, with a close button made from the pack;
  - use a separate `role="alert"` region for errors;
  - show the brain's per-file results inside the brain dialog.

**6. The brain's Send button can stay disabled forever.**
- Send turns on only after every file has been sorted (`Promise.all`, 2010–2017).
- `endpointSort()` (1930–1939) and `S.sample.json` have no time limit, so a hung sorter leaves every row on
  "Sorting…" and she can only Cancel.
- Files over 20 MB are skipped at Send (2022), with nothing about it in the result.
- *Fix:*
  - time the sorter out with `AbortController` after about 8s, then fall back to "Nobody yet";
  - turn Send on as soon as the keyword guesses are ready;
  - list skipped files in the result.

**7. A queen's notes are lost without warning.**
- "Give it to her" and "Forget" only change a local list (1545–1564). Nothing is saved until **Save** (1577).
- Close and Escape throw the changes away silently (1436), and "Give it to her" sounds like it already saved.
- *Fix:* save straight away on Give, Forget and Say it, or ask "Keep your changes?" on close when the list
  has changed.

**8. Speech bubbles are extra keyboard stops that swap the menu.**
- Bubbles are buttons left in the tab order (1264).
- On the whole-house view, Tab went from a room to Caramel's bubble, and landing on it replaced the room's
  menu with the cat's.
- Inside a room, each meowing cat is reached twice: once on the cat, once on its bubble.
- *Fix:* set `tabIndex = -1` on bubbles and the "Files" tag (1234). Both are already reachable from the cat
  and the room menu. This keeps the "one Tab stop for the map" rule.

**9. The cats never stop moving, and there's no pause on the page.**
- Every cat loops its animation forever (138–153), and busy cats wander every 6s (919–930). Only the
  operating system's reduced-motion setting stops this (308–311).
- It's an all-day dashboard, and WCAG 2.2.2 asks for a way to pause motion that lasts more than 5 seconds.
- *Fix:* add a "Still cats" switch next to Sound in the room menu's footer, with the same toggle art. Keep
  it in `localStorage`, and have `calm()` and the CSS read it (a `.still` class on `body`).

**10. The brain and House rules are hidden in two rooms.**
- They only appear in the Hall and Library menus (1119–1123), so she has to remember where they live.
- *Fix:* put both in the footer of every room menu, as small buttons next to Sound.

## Suggestion

**11. The room menu has too many choices.**
- It can show up to 10 buttons plus a 3-control footer (1110–1134), all the same size.
- *Fix:* put Look in, Ask the queen and Files on the first row. Put Give it files, New cat, Adopt and Edit
  rooms below the divider.

**12. Some text is too small.**
- Bubble text is 12.5px (168), model plaques 10px (283), counts 11px (118, 285), notes and captions
  12–12.8px (193, 238).
- *Fix:* raise the Nunito text to at least 14px, and enlarge plaques and counts when a room is zoomed in.

**13. Screen readers can't tell a menu has opened.**
- `#menu` (328) is a plain div, and the room or cat has no `aria-expanded` / `aria-controls`.
- *Fix:* add `role="group"` and an `aria-label` from its heading, and set `aria-expanded` on the anchor in
  `showMenu` and `hideMenu`.

**14. Current names show only as faint placeholders.**
- A cat's or queen's current name is shown only as placeholder text (1476, 1570), at 3.3:1 contrast
  (`#5F6A5E` on `#C1C8B9`, line 59).
- *Fix:* show the current name as visible text under the field, and darken the placeholder to about
  `#4E574D`.

## Assessment

| Criterion | Current state | Severity | Recommendation |
|---|---|---|---|
| Hover menus | Moving to a menu opens a neighbour's (tested) | Critical | 200ms delay before switching; own room can't take over a cat's menu; stepped-move test |
| Phone layout | House is about 1/8 of the screen; no names; cats 6–12px | Warning | Start zoomed into the urgent room; swipe between rooms |
| Touch targets | Buttons 32px, switch 22px | Warning | 44px minimum on touch screens |
| Status sign | Hover-only words; tick has no text; repeated announcements | Warning | Hidden label, a way to read it, update only on change |
| Error feedback | Toasts gone in 3.2s | Warning | Keep errors until dismissed; `role="alert"` |
| Brain drop flow | Can hang on "Sorting…"; >20 MB skipped silently | Warning | Sorter time limit, earlier Send, report skipped files |
| Data safety | Queen notes lost on close; deletes confirm twice (good) | Warning | Save straight away or warn on close |
| Keyboard | Arrow map, Enter and Escape are solid; bubbles add stops | Warning | Take bubbles out of the Tab order |
| Motion | Honours reduced motion; no pause on the page | Warning | "Still cats" switch |
| Contrast | Ink on tan 7.3:1, ink-soft 4.6:1; placeholders 3.3:1 | Suggestion | Darker placeholder |
| Text size | Pixel font kept at 18px (good); body text 10–12.8px | Suggestion | 14px minimum for Nunito text |
| Empty states | Clear and helpful everywhere | — | Keep |
| Consistency with the pack | Every control uses the pack's art | — | Keep |

## Recommended order

1. Fix hover switching (`hoverable` / `showMenu`) and add a stepped mouse-move test.
2. Phone: start zoomed into the urgent room, add room swipes, and make touch targets at least 44px.
3. Keep error and queued messages until dismissed, and show the brain's results in its dialog.
4. Add the sorter time limit and an earlier Send, and report skipped files.
5. Save queen notes straight away, or warn before closing with unsaved changes.
6. Make the status sign readable without hover, and stop the repeated announcements.
7. Take bubbles out of the Tab order.
8. Add a "Still cats" switch, and put The brain and House rules in every room menu's footer.
9. Group the room menu, raise small text to 14px, add `aria-expanded` to menus, and darken placeholders.
