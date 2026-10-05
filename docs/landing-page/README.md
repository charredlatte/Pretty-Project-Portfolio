# The KittyChat Café landing page: the draft, and every decision on it

Charlotte's ask (4 October 2026): a landing page for the SaaS that welcomes you like Stardew Valley or The Legend of
Zelda, for an audience raised in the late 90s and early 2000s; a cosy fireside scene in pixel art as the stage; every
button, motion, loading frame and UX vibe thought through and **waiting for her approval**; the wireframes in Figma.

This folder is that. Nothing here is final until she ticks it.

| | |
| --- | --- |
| `landing/index.html` | the draft itself: one static page, no framework, no build. Open it from a double-click or any static server |
| `landing/tools/scene.py` | draws the whole scene in code: `python3 landing/tools/scene.py --preview` rewrites `landing/art/` and a 2× preview to look at |
| `landing/art/` | the layers it draws (ours: nothing from the packs) and `scene.js`, which says where the animated pieces go |
| `landing/fonts/` | Press Start 2P, Pixelify Sans and Nunito, each with its SIL Open Font License |
| `docs/landing-page/frames.js` | the Figma wireframes, as the shop's and the onboarding's: run it with `use_figma`, or as a development plugin. The file is "KittyChat Café · Landing page wireframes" in her drafts (https://www.figma.com/design/umjtL8zfgDoLzdDIga7tbl) |
| this file | every decision, each with a box for her to tick, change or strike |

How to read it: **☐** is a decision waiting on her. Tick it, or write what to change next to it. Where a line says *ref:* it
names the game the convention comes from, so a change can be judged against the real thing.

## 1. What was fixed before any design

- **The scene is hers, word for word.** A campfire with logs; around it, logs; a mountainous pine forest and a milky-way
  sky; the glow of the fire on the faces of two cats sitting side by side on the log bench to the left of the fire; a
  tent glowing from inside, camped out from last night; smoke in light little trails.
- **No pack art, at all.** Every pack the café uses is non-commercial, no-redistribution or personal-use only
  (`docs/kittychat-shop/support-pages.md`, "Before either page goes up"), and a landing page that sells is commercial
  use. So the scene, the panels, the paw and the two portraits are drawn by `scene.py`, pixel by pixel, and are the
  repository's own. The fonts are SIL OFL, which allows a website to embed and redistribute them with their licence
  file (it is in `landing/fonts/`).
- **Honest about where it stands** (the onboarding's rule of 3 October): running your own café is open today; the
  hosted café is early access and says "not open yet"; nothing says "sign in". Prices stay in brackets (`[monthly]`,
  `[setup-plus]`) until she picks them; the two mailto links and the two support links carry `[email]`, `[handle]`
  and `[campaign]` until the addresses exist.
- **Plain words.** Cats, rooms, the front desk, the queen; never MCP, API, gateway, hook or LLM in a sentence that
  explains (the onboarding's rule).
- **Nothing credits Claude** as the page's author (CLAUDE.md, "Shipping"). The product copy names Claude because the
  product shows Claude chats.

## 2. The page, screen by screen

The page is a sequence of game screens, in the order a game would show them, and then an ordinary page that can be
scrolled at any time (PRESS START gates nothing: a visitor who scrolls past the title sees everything).

1. **Loading frame.** Black, "NOW LOADING", a bar that fills as the fifteen pictures really load, three paws stepping
   in turn. Never shorter than half a second, so it never flashes; fades to the title in three steps. *ref:* the PS1
   and GameCube era's loading screens; honest because it waits for something real. ☐
2. **Title screen.** The fireside scene fills the screen (scaled by a whole number, cropped at the sides; the sky colour
   continues above it on tall screens). The logo "KittyChat Café" top centre with the tagline under it, and PRESS START
   blinking under them. Top right: SOUND OFF and SKIP. *ref:* A Link to the Past's "PRESS START", Stardew's logo over an
   animated title. ☐
3. **Dialogue.** PRESS START (or Enter, Space, a tap) opens a night-blue dialogue box at the bottom with a cat's
   portrait, its name and typewriter text, and ▼ to turn the page. Four pages: Brioche, Pepper, Brioche, Pepper.
   *ref:* Stardew's dialogue box with portraits; Zelda's blinking advance triangle. ☐
4. **Main menu.** The last page, "Where would you like to go?", becomes the menu in the same box: NEW CAFÉ (run your
   own, free), JOIN THE CAFÉ (early access), HOW IT WORKS, SUPPORT THE WORK, with the pointer ▶ on the item under the
   mouse or the arrow keys. *ref:* Stardew's New / Load / Co-op / Exit. ☐
5. **How it works.** Three tan cards, one portrait each: your chats become cats; the café asks who's awake; you
   answer from the page. One honest line under them: your private chats stay in your account, the café never reads
   your code. ☐
6. **Choose your file.** The three ways to get the café as three save slots: FILE 1 · RUN YOUR OWN (free, open today,
   three hearts), FILE 2 · THE HOSTED CAFÉ (`[monthly]` € a month, early access, hearts outlined: not open yet), FILE 3 ·
   SET UP FOR YOU (from 90 €, once). Each with one button. *ref:* Zelda's file select. ☐
7. **Ask the queen.** Five questions that open like menu items: do I need to code, does it read my code, is this
   Claude, who sees my data, can I stop. The queen is the house's assistant in the product, so the FAQ is hers. ☐
8. **Support the work.** A short note in Charlotte's voice (one person, open source, the app planned for December
   2027), BUY ME A COFFEE and BACK THE APP. ☐
9. **Footer.** Mentions légales, CGV, Confidentialité, Rétractation, Contact; one line of credits for the art (ours) and
   the fonts. ☐

## 3. Every control

| Control | Where | Idle | Hover | Pressed | Focus | Sound | ref | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PRESS START | title | gold, blinking | steady, white | opens the dialogue | steady, gold ring | confirm | ALttP title | ☐ |
| SOUND OFF / ON | top right | small outlined button | – | toggles, remembered in the browser | gold ring | confirm | – | ☐ |
| SKIP | top right | small outlined button | – | straight to the menu | gold ring | – | every intro since the 90s | ☐ |
| ▼ (next) | dialogue, bottom right | bobbing triangle | – | turns the page; a press while it types shows the whole line | gold ring | confirm | Zelda / Pokémon | ☐ |
| Menu item | the box | cream text | pointer ▶, white text | bleep, wipe to black, jump to the section | same as hover | move / confirm | Stardew, Zelda's hand cursor | ☐ |
| Button (`.btn`) | files, support | cream face, ink outline, 4 px shadow | white face, ▶ shows | drops 4 px, shadow gone | gold ring | move / confirm | 16-bit menus | ☐ |
| Primary button | FILE 1 | the café's green face | lighter green | same | same | same | – | ☐ |
| File slot | files | night panel | pointer ▶ at its left | its button | its button's ring | – | Zelda file select | ☐ |
| FAQ question | ask the queen | cream text, a rule under it | pointer ▶ | opens the answer under it | gold ring | move / confirm | menu grammar | ☐ |
| Legal links | footer | cream | underline | – | gold ring | – | – | ☐ |
| Pointer | anything clickable | a 16 × 16 cat paw (ours), tip top left | – | – | – | – | Zelda's hand, OoT's | ☐ |

Keyboard: Tab reaches everything in order; Enter or Space starts and turns the pages (also Z and X, the emulator
habit); ↑ ↓ move the menu pointer and wrap; Enter confirms; the first link, hidden until focused, skips the title. ☐

## 4. Every motion

Every change is a step, never a slide: the games had no easing, and a step reads as pixel art where a tween reads as a
web page. Timings are in `index.html` beside the thing they time.

| What | Timing | With reduced motion | ref | |
| --- | --- | --- | --- | --- |
| Loading frame | ≥ 500 ms; bar fills with the real loads; out in 3 steps over 300 ms | no minimum, no fade | – | ☐ |
| PRESS START | 530 ms on, 530 ms off, no fade | steady | The Minish Cap draws it 32 frames on, 32 off at 60 fps: 533 ms each | ☐ |
| Fire | 8 frames at 10 fps | frame 1, still | – | ☐ |
| Firelight | flicker between 3 baked light levels every 90 ms (no blending: three pictures) | the middle level, still | – | ☐ |
| Smoke | a particle every 380 ms; rises 26–40 px over 3–5 s, sine wobble, 3 opacity steps, 1 px wide then 2 | none | – | ☐ |
| Stars | each of 47 stars flips dim / bright on its own 0.4–3.5 s clock; a shooting star every 25–50 s, 450 ms | still | – | ☐ |
| Tent glow | 3 opacity levels, one step every 800 ms | the middle level | – | ☐ |
| Cats | breathe (a pixel taller) every 1.2 s; blink 180 ms every 2.5–7 s; an ear flicks 260 ms; the tail 420 ms; the second cat out of step | still | Stardew's idle animals | ☐ |
| Dialogue box | grows open in 3 steps over 200 ms | simply there | Ocarina's box grows over 8 frames; Stardew's over ~200 ms with "breathin" | ☐ |
| Typewriter | one character every 30 ms (Stardew's exact delay), a blinking block cursor; a press completes the line | the whole line at once | Stardew; Ocarina types one a frame at 20 fps | ☐ |
| ▼ | bobs 2 px at 2 Hz in 2 steps | still | Zelda | ☐ |
| Menu items | appear one by one, 120 ms apart, no fade | all at once | Stardew's four buttons land one every 200 ms | ☐ |
| Menu pointer | snaps, no easing | same | every 16-bit menu | ☐ |
| Confirm | the screen wipes to black in 3 steps over 240 ms, the page jumps, the wipe lifts in 3 steps | a plain jump | Zelda's fade to black | ☐ |
| Landing on a file | the slot is pressed for 600 ms and its button takes focus | same | – | ☐ |
| Buttons | the press drops 4 px, no transition | same | – | ☐ |
| Sections | **none**: no scroll reveals, no parallax, no fades | same | – | ☐ |
| When hidden | the scene stops drawing when the tab is hidden or the title is scrolled away | – | – | ☐ |

**Sound** is four bleeps made by the page itself (an oscillator; no sound files, nothing to license): move 880 Hz
for 50 ms, confirm 660 then 990, back 440 then 330, and a 15 ms tick every other letter of the typewriter. **Off by
default**, because the web is not a console: a page that bleeps unasked is the thing people close. The switch
remembers. ☐

## 5. The scene

Drawn at 480 × 270, the resolution of a 16:9 pixel-art game, so that a laptop at 1440 shows it at exactly 3× and a
1080p screen at 4×; a phone at 390 wide shows it at 1× cropped to the middle 390, which is why the bench and the tent
sit inside the middle 384 pixels (`"safe"` in `scene.json`). The firelight is baked as four bands of warmer colour,
dithered at their edges, at three flicker radii, so the flicker is three pictures swapped and never a blur. The
tent's glow is its own layer at a stepped opacity. The fire is eight frames; the smoke, the twinkle and the shooting
star are the page's few lines of canvas. The cats face right, toward the fire, and their faces are drawn lit.

Things she may want to redraw by hand, in order of effect: the cats (26 px tall), the tent, the fire frames. Each is
one function in `scene.py`, and the page reads them by file name, so a hand-drawn PNG of the same size drops in. ☐

## 6. Type

| Face | Used for | Why | Sizes | |
| --- | --- | --- | --- | --- |
| Press Start 2P | the logo, PRESS START, menu items, buttons, section titles, FILE n | the arcade face everyone born in the 80s and 90s read on a cabinet; crisp only at multiples of 8 px | 8 (corner buttons), 16, 24 (section titles), 32 (logo) | ☐ |
| Pixelify Sans | the dialogue, the tagline, card titles, the FAQ questions | a pixel face with lowercase and French accents, close to Stardew's; crisp at 20 px (and 40) and nowhere else | 20 | ☐ |
| Nunito | paragraphs | the café's own body face: pixel fonts tire the eye past a sentence | 17–18 | ☐ |

All three are SIL OFL and self-hosted; nothing is fetched from a font service.

## 7. The copy

Every line the page says, for her to keep or strike:

- Logo and tagline: **KittyChat Café** · *All your Claude chats, in one cozy café.* ☐
- The two cats: **Brioche** (orange) and **Pepper** (grey). Not the packs' names. ☐
- Page 1, Brioche: "Oh! A visitor. Pull up a log, the fire's warm." ☐
- Page 2, Pepper: "Every chat you have with Claude is a cat in our café. Busy cats work. Sleeping cats are done." ☐
- Page 3, Brioche: "A cat that needs you meows. Point at it and it tells you what it wants. No terminal, ever." ☐
- Page 4, Pepper: "Where would you like to go?" ☐
- Menu: NEW CAFÉ · run your own, free / JOIN THE CAFÉ · early access / HOW IT WORKS / SUPPORT THE WORK ☐
- How it works: the three cards' titles and lines, and "Your private chats stay in your own account. The café shows
  them; it never reads your code." ☐
- The files: the three slots' names, prices and lines; the buttons START A NEW CAFÉ, JOIN THE LIST, WRITE TO CHARLOTTE;
  "Prices HT, TVA non applicable, art. 293 B du CGI" on the paid one ☐
- Ask the queen: the five questions and answers ☐
- Support: the note in her voice, "Charlotte, who runs the café.", BUY ME A COFFEE, BACK THE APP ☐
- Footer: the five legal links; "KittyChat Café · Charlotte Badot, EI. The fire, the cats, the tent and the night were
  drawn for this page. Type: Press Start 2P, Pixelify Sans and Nunito, under the SIL Open Font License." ☐

The page is in English, like the shop's home, with the legal footer in French. ☐ (A French version is one question
below.)

## 8. Accessibility

The scene is `aria-hidden` and described in one hidden sentence. Every control is a real button or link. The dialogue
is a live region, so a screen reader hears each page. Focus rings are a gold pixel outline on a dark ring. The body
text is 17 px and up; the pixel faces are never used below 16 px except the two corner buttons at 8 px ☐ (a
question below). Contrast: cream and gold on the night panel pass 4.5:1; ink on tan passes. `prefers-reduced-motion`
stops everything (section 4) and prints each page whole. The canvas stops when hidden.

## 9. Decided against

- **Parallax, scroll reveals, fades between sections.** They are web conventions, not game ones; the games cut.
- **Sound on by default**, and music. A page is not a console; a bleep unasked is a tab closed.
- **A fake "Continue" slot or a sign-in**, until the hosted café is open. The onboarding's honesty rule.
- **Testimonials, logos, counters.** There are none yet; invented ones would be lies.
- **Hearts as a health bar.** They would have meant nothing; here they say open / not open, and say so in words too.
- **The packs' paw, panels, faces and font**, however much the product uses them: non-commercial.
- **Press Start 2P for paragraphs.** Unreadable past a line.
- **A countdown, a newsletter popup, cookie banners.** Nothing on the page stores anything but the sound switch.
- **A real waitlist form.** No backend yet; a mailto until the shop's early access product exists.

## 10. Questions for Charlotte

1. The two cats' names, Brioche and Pepper: keep, or name them after cats of hers? ☐
2. Sound off by default: agreed? (On by default is one line.) ☐
3. The hosted café as "JOIN THE LIST" to a mailto, until the shop exists: agreed, or point it at the shop's early
   access product now? ☐
4. The corner buttons at 8 px: keep them tiny like a game's HUD, or 16 px for readability? ☐
5. English only, or an FR / EN switch? The shop's home is English with a French legal footer. ☐
6. "Planned for December 2027" on the page: say the date, or "planned" alone? ☐
7. The third slot says "WRITE TO CHARLOTTE": her first name on the page, or "the café"? ☐
8. Should PRESS START remember a returning visitor and skip straight to the menu, as games do after the first boot? ☐

## 11. Redrawing the Figma frames

`frames.js` draws eleven frames in a row: 1 Title screen, 2 Dialogue, 3 Main menu, 4 How it works, 5 Choose your
file, 6 FAQ, support, footer, 7 Loading frame, 8 Controls and states, 9 Motion sheet, 10 Title (phone), 11 Files
(phone). Grey boxes and Inter, annotations in grey prefixed ✎, nothing from the packs. Run it with the Figma MCP
server's `use_figma` on the file, or in Figma desktop as a development plugin (wrap it in
`(async () => { … ; figma.closePlugin(); })()` in place of the final `return`). Each run draws a fresh row.

Mind the quota: a Starter plan with a View seat gets twenty MCP calls a month that read Figma (`create_new_file` and
`whoami` are free); this draft used one for the drawing.

## 12. Checking it

- Look: `python3 landing/tools/scene.py --preview` and open `landing/art/preview.png`; open `landing/index.html` at 1440
  and at 390 wide, with and without reduced motion. The screenshots of this draft were taken with Playwright at both
  sizes, in both motion settings, with no console error.
- No pack art: `grep -rn "licensed" landing/` finds nothing.
- The fonts' coverage: each has lowercase and é è ê à ç ù (checked with fontTools).
