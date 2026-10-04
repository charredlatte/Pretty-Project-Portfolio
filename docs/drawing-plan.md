# Drawing the KittyChat Café yourself: every asset, and the scale to draw it at

Charlotte's plan (1 October 2026): draw every asset herself in Aseprite before the working project is published,
replacing all the downloaded packs, and adding what she wants that no pack had (a litterbox, café tables…).

This is the list. Section 1 says what scale and settings to draw at. Sections 2 to 7 list every piece the page uses
today, with its size, where it goes, and the file it replaces. Section 8 is the new pieces. Section 9 is what changes
in the code when her art arrives.

The Game UI skill (her MCPmarket `ui` plugin) is not installed in this session. Its rules come from its last run,
recorded in `docs/from-the-litterbox.md` (under Findings, the UI/UX audit) and `docs/requests.md`: integer scaling, quiet map layers under cats and
signs, never colour alone, and still map layers. Those rules are applied below.

## 1. The scale: draw at 1×, on a 16 px tile

**Recommendation: draw every piece at its native size, one Aseprite pixel per art pixel, on a 16 × 16 grid.
Never draw at 2× and shrink it.** The page does the enlarging.

Why:

- **Everything is already measured in native pixels.** The two floors are 960 × 576 (60 × 36 tiles of 16 px). Every
  room, doorway, cat spot, queen seat and furniture footprint in `manor.py` and `furniture.py` is a native
  pixel coordinate. A piece drawn at the right native size drops in with no code change.
- **The page already scales by whole numbers.** `--u` is one art pixel on screen: 2 px on a laptop, 1 px on a
  phone. A 26 × 26 button becomes 52 × 52 on screen, crisp. Drawing at 2× would make everything twice too big, or
  need a downscale, and a downscale breaks pixel art.
- **The camera goes to 4×.** Zoomed into a room, one art pixel is up to 4 screen pixels. That is the size she'll
  see her work at most, so preview it at 400 % in Aseprite.
- **A 32 px grid would mean redesigning the house.** Every coordinate would double, and the world would be
  1920 × 1152. Not worth it: 16 px is Cosy Cabin's, Sprout Lands' and Mochi's scale, so a piece can be swapped
  one at a time and still sit with the art not yet replaced.

### Aseprite settings

| Setting | Value |
|---|---|
| Canvas | the piece's exact box from the tables below (a sheet: a whole number of cells) |
| Colour mode | Indexed, from one master palette for the whole project (`catio/art/palette.gpl`: make it once, load it in every file) |
| Grid | View → Grid Settings: 16 × 16 (8 × 8 for small props and the UI) |
| Pixel ratio | 1:1 |
| Preview | 200 % (a laptop) and 400 % (zoomed into a room); also check 100 % (a phone) |
| Export | File → Export As… PNG, **scale 100 %**, transparent background. Animations: Export Sprite Sheet, horizontal strip, no padding, no trim |
| Brushes | 1 px pencil, pixel-perfect on. No anti-aliasing against transparency: the page shows it as a fringe |

### House style, so every piece belongs together

- **View:** three-quarter top-down. You see the top of a thing and its south face.
- **Light:** from the top left. Highlights on top and left edges, shade on the bottom and right, the drop
  shadow to the south-east, one pixel of darker floor colour, not black.
- **Outline:** a 1 px outline in a darker shade of the piece's own colour, with the ink `3F2A20` only at the
  very bottom where it meets the floor. Pick one rule and keep it for every piece.
- **Palette:** Sprout Lands' creams and tans near the interface: `F3E5C2`, `E8CFA6`, `C49A6C`, `AA7959`,
  `90625D`, ink `3F2A20`. The house's own ramps are in `manor.py` (`OCHRE`, `STUCCO`, `PLASTER`, `STONE`, `OAK`,
  `GILT`, `SHUTTER`, `JEWELS`): start the master palette from those, so the code-drawn walls and her art match.
- **Quiet floors and walls** (the Game UI rule "map layers stay quiet"): floors and wallpapers in low contrast
  and lower saturation, so cats, faces and bubbles always read on top of them. Strong colour belongs to cats,
  their moods and the interface.
- **Never colour alone:** the mood of a cat must read from its pose as well as its colour (a crying cat
  is hunched, a meowing one has its mouth open), because coats change colour per project.
- **A piece's box is tight:** no empty rows or columns, except the drop shadow. Its feet (the bottom of the
  part that stands on the floor) are its bottom row.

## 2. The cats (the biggest job: they are on screen all the time)

Today: ToffeeCraft's Mochi (32 × 32 frames) and Pochi (64 × 64 frames), personal use only. Neither has a walk.

**Recommendation: one size for every cat, 32 × 32 frames, the feet at the bottom middle (x 16, y 32).** The cat
itself is about 18–20 px long and 14–16 px tall, so it sits on a 14 px cushion and beside a 14 × 28 chair. The
64 px Pochi frames are mostly empty space; one size also removes the per-mood anchors in `SPR`.

Draw one cat in a **fixed fur ramp** (four or five colours used nowhere else). The coats (Cream, Ginger, Silver,
Honey, Blue-grey, Shadow, Marmalade, Smoke) then become palette swaps of that ramp, instead of today's CSS
filters, which tint everything, the eyes included.

| ☐ | Sheet | Frames | Speed | Shown for |
|---|---|---|---|---|
| ☐ | `cat-work.png` (busy) | 8–10 | 8 fps, loop | A working cat: at a laptop, desk or yarn. Replaces Mochi idle (10 frames, 1.25 s) |
| ☐ | `cat-review.png` (box) | 4 | 5 fps, loop | Brought something to review: a cat with a parcel or in a box |
| ☐ | `cat-meow.png` (needs) | 2–4 | 4 fps, loop | Needs her: sitting up, mouth open |
| ☐ | `cat-cry.png` (failed) | 4 | 6 fps, loop | Upset: hunched, ears flat, a tear |
| ☐ | `cat-sleep.png` (done) | 4 | 2 fps, loop | Asleep, curled up, breathing |
| ☐ | `cat-walk-side.png` | 6 | 10 fps | Every walk. Drawn facing right; the page mirrors it for left |
| ☐ | `cat-walk-down.png` | 6 | 10 fps | Walking towards the viewer, and coming downstairs |
| ☐ | `cat-walk-up.png` | 6 | 10 fps | Walking away, and climbing the stairs |
| ☐ | `cat-sit.png` (optional) | 2 | 2 fps | Sitting on a step, if napping cats sit on the stairs |
| ☐ | `cat-queen.png` (optional) | 4 | 4 fps | A queen sitting tall. Today she is a working cat with the crown over her |

Eleven sheets at most, about 60 frames. Start with the five moods and the side walk: that replaces everything
licensed in the cats.

## 3. The furniture (replaces `art/furniture.png` and `art/licensed/furniture.png`)

Every piece in `furniture.py`'s `CATALOGUE`, at the size the page draws it. Pieces that share a picture today are
one row. Pieces shrunk to half size today (`scale=0.5`) are listed at their final size: draw them at that size.

Kind: **E** essential (never moves), **C** carries a cat's station (keep the footprint and where cats stand),
**D** decor. "Foot" is the part that stands on the floor, which no cat may stand on.

### The hall and everywhere

| ☐ | Piece | Size (w × h) | Kind | Notes |
|---|---|---|---|---|
| ☐ | Stone staircase, going up north | 64 × 80 | E | Cats climb it: steps at y 78, 54, 30 and 6 from its top. Today Cainos's |
| ☐ | Front door mat | 30 × 10 | E | Cats who need her wait on it |
| ☐ | Filing cabinet | 16 × 27 | E | One per room, where projects are reviewed. Today it's the kitchen's drawer unit |
| ☐ | Diamond rug, red | 48 × 30 | C | |
| ☐ | Diamond rug, blue | 48 × 30 | C | |
| ☐ | Runner rugs: blue, yellow, green | 30 × 15 each | C | Where an upset cat sits |
| ☐ | Cat cushions: blue, green, orange, white | 14 × 14 each | C | Round, where a cat sleeps |
| ☐ | Writing desk | 32 × 32 | C | A cat works in front of it |
| ☐ | Armchair, facing the viewer: pink, green | 24 × 30 each | C | The queen's seat |
| ☐ | Armchair, side-on: blue facing right, blue facing left | 22 × 30 each | C/D | Two drawings, or one mirrored |
| ☐ | Floor lamp | 13 × 30 | D | |
| ☐ | Pampas grass in a vase | 15 × 43 | D | |
| ☐ | Snake plant | 11 × 31 | D | |

### The café (dining room) and the kitchen

| ☐ | Piece | Size | Kind | Notes |
|---|---|---|---|---|
| ☐ | Big table (also the library desk) | 50 × 32 | C/E | Foot: its bottom 26 rows |
| ☐ | Chair, facing the viewer | 14 × 28 | C | |
| ☐ | Chair, from behind | 14 × 22 | C | A cat sits on it to work |
| ☐ | Chair, facing right / facing left | 14 × 27 each | C | One drawing, mirrored, is fine |
| ☐ | Sideboard (also the bedroom dresser) | 32 × 27 | D | |
| ☐ | Sunflowers in a vase | 14 × 40 | D | |
| ☐ | Fridge | 16 × 40 | D | |
| ☐ | Pantry cupboard | 16 × 42 | D | |
| ☐ | Counter: plain, drawers, cupboard door, hob | 16 × 27 each | D | Repeat side by side into a run; the kitchen island is three plain ones |
| ☐ | Sink, set into the counter | 28 × 15 | D | Drawn on top of two counters |
| ☐ | Food bowl | 22 × 19 | D | |
| ☐ | Water bowl | 22 × 19 | D | |
| ☐ | Bag of cat food | 17 × 31 | D | |

### The cat lounge, the terrace and the craft room

| ☐ | Piece | Size | Kind | Notes |
|---|---|---|---|---|
| ☐ | Fireplace, Baroque, with a mantel | 32 × 42 | E | Foot: its bottom 12 rows |
| ☐ | Sofa, from behind | 40 × 22 | C | A cat sleeps on it |
| ☐ | Cat tree | 43 × 88 | C | A cat works at its foot. Also in the catio |
| ☐ | Scratching post | 28 × 39 | C | |
| ☐ | Palm in a pot | 23 × 34 | D | |
| ☐ | Fiddle-leaf fig | 19 × 38 | D | |
| ☐ | Fern | 22 × 26 | D | |
| ☐ | Monstera | 24 × 25 | D | |
| ☐ | Trailing ivy | 23 × 17 | D | |
| ☐ | Bookcase full of books (craft room) | 46 × 52 | D | |
| ☐ | Shelves of craft supplies | 46 × 36 | D | |
| ☐ | Big worktable | 58 × 50 | C | A cat works at its south edge |
| ☐ | Balls of yarn, red and blue | 11 × 10 each | D | Set on the worktable |
| ☐ | Tin of buttons | 9 × 9 | D | |
| ☐ | Supply chest | 21 × 26 | D | |

### Upstairs: the library, the bedroom, the ensuite

| ☐ | Piece | Size | Kind | Notes |
|---|---|---|---|---|
| ☐ | Tall bookcase, dark books | 52 × 58 | D | After Peleș: carved walnut, iron grille, gilt shelves |
| ☐ | Tall bookcase, red books | 52 × 58 | D | |
| ☐ | Chest (the brain's, where dropped files land; also at the bed's foot) | 22 × 21 | E/D | |
| ☐ | Bed | 32 × 47 | C | A cat sleeps on it. A four-poster suits the manor (section 8) |
| ☐ | Nightstand | 16 × 22 | D | |
| ☐ | Toilet | 16 × 31 | D | |
| ☐ | Basin, on the wall | 14 × 14 | D | Wall piece |
| ☐ | Small mirror | 12 × 21 | D | Wall piece |
| ☐ | Shower | 12 × 25 | D | Wall piece |
| ☐ | Towel on a rail | 12 × 14 | D | Wall piece |
| ☐ | Bath mat | 16 × 10 | C | The ensuite's queen stands on it |
| ☐ | Small potted plant | 14 × 24 | D | |

### The catio

| ☐ | Piece | Size | Kind | Notes |
|---|---|---|---|---|
| ☐ | Garden table | 39 × 66 | D | Today Wood Garden's, seen long; a round bistro table may read better (section 8) |
| ☐ | Garden chair | 28 × 36 | C | The catio queen's |
| ☐ | Garden chest (the catio's filing cabinet) | 22 × 21 | E | Can be the library chest, recoloured |

About 60 drawings once the mirrored and shared ones are counted once.

## 4. The house itself: floors, walls, glass (replaces `house.png` and `house-upper.png`)

`manor.py` draws the house from these textures. Some of it is already drawn in code from her palette
(the walls seen from above, the facade, quoins, stained glass, the front door, lintels, the stair rails): that
part needs nothing from her, though she may redraw it. The rest is cut from Cosy Cabin, Cainos and Little Dreamyland.

### Floors (seamless tiles)

| ☐ | Texture | Tile | Rooms |
|---|---|---|---|
| ☐ | Pale floorboards | 32 × 32 | Café, cat lounge, craft room, bedroom |
| ☐ | Dark floorboards | 32 × 32 | Library (today the pale ones, recoloured) |
| ☐ | Terracotta tiles | 16 × 16 | Kitchen |
| ☐ | Stone flags, in 32 px slabs | 64 × 64 | Entrance hall and the front steps |
| ☐ | Marble chequer, sandstone and pale | 32 × 32 | Terrace (orangery) |
| ☐ | Blue tiles | 16 × 16 | Ensuite |
| ☐ | Landing floor (optional) | 32 × 32 | The landing: today the pale boards |

### Back walls (each 32 px tall: one wall, ceiling to floor)

| ☐ | Texture | Repeat | Room |
|---|---|---|---|
| ☐ | Wallpaper, soft blue stripes | 16 × 20, plus a 16 × 12 dado rail | Café |
| ☐ | Whitewash over blue tiles | 16 × 32 | Kitchen |
| ☐ | White panels with gilt trellis | 16 × 32, and a 6 × 32 pilaster | Cat lounge |
| ☐ | Exposed brick | 16 × 20 | Craft room |
| ☐ | Dressed stone | 96 × 32 | Entrance hall |
| ☐ | Wallpaper, small pattern | 16 × 20 | Terrace |
| ☐ | Carved walnut panelling with a gilt rail | 32 × 32 | Library |
| ☐ | Wallpaper with vines (Art Nouveau) | 16 × 20 | Bedroom |
| ☐ | Glazed wall tiles | 16 × 16 | Ensuite, and the kitchen's splashback |

### Windows and fixtures

| ☐ | Piece | Size | Notes |
|---|---|---|---|
| ☐ | Cream sash window | 28 × 18 | The code stretches it into the tall windows (24–60 wide, 32 tall). Or draw a tall window directly: 28 × 32, repeating sideways |
| ☐ | Stained-glass window (optional; code-drawn today) | 36, 52 × 32 | Lily or fleur, Art Nouveau |
| ☐ | Cat flap | 6 × 16 | In the terrace's east wall. Today a dark rectangle |
| ☐ | Attic ladder (optional; code-drawn today) | about 12 × 32 | On the landing |
| ☐ | Facade pieces (optional; code-drawn today) | see *What's missing: art and sound* in `docs/from-the-litterbox.md` | Ochre limewash, quoins, shutters, the pediment door |

Draw a floor or wall as a tile that repeats with no seam: in Aseprite, View → Tiled Mode → Tile in both axes.

## 5. The grounds (replaces `decor.png` and `meadow.png`)

| ☐ | Piece | Size | Notes |
|---|---|---|---|
| ☐ | Meadow grass | 32 × 32 tile | Under everything. Quiet: it covers most of the screen |
| ☐ | Wooden decking | 32 × 32 tile | The catio's floor |
| ☐ | White fence, front and side | 28 × 16, and 8 × 36 | Repeats along the catio |
| ☐ | Rose-arch gate | about 42 × 30 | The catio's gate |
| ☐ | Stepping stones | 15 × 15, 4 kinds | The drive |
| ☐ | Stone archway with wooden doors | 80 × 64, doors 9 × 53 | The gate at the end of the drive |
| ☐ | Urns or vases | 21 × 34 | Either side of the gate |
| ☐ | Lantern, on the ground | 22 × 37 | By the front steps |
| ☐ | Lamp post | 10 × 31 | Along the drive |
| ☐ | Fountain, with its statue | 94 × 72, statue 37 × 72 | East of the drive |
| ☐ | Garden bench | 56 × 41 | Facing the fountain |
| ☐ | Parterre (a flower bed) | 102 × 86 | Before the craft room's bay |
| ☐ | Well | 21 × 29 | |
| ☐ | Barrel or planter | 15 × 19 | |
| ☐ | Signpost | 27 × 32 | To the catio |
| ☐ | Pond | 64 × 56 | |
| ☐ | Lily pads | 16 × 15, 14 × 13 | |
| ☐ | Bushes, two kinds | 34 × 30, 26 × 23 | |
| ☐ | Rocks, three kinds | about 23 × 22 | |
| ☐ | Mossy rocks | 24 × 24, 11 × 8 | |
| ☐ | Spruce, three sizes | 22 × 32, 30 × 36, 47 × 41 | The forest round the edges: about 110 of them, so make them read well when repeated |
| ☐ | Round trees, big | 81 × 121, 93 × 125 | One shades the catio |
| ☐ | Stumps and logs | about 15–26 × 14–20, 4 kinds | |
| ☐ | Lawn scatter: flowers, tufts, pebbles, leaves, mushrooms | 7–17 × 7–16, about 20 kinds | Small, many, quiet |

## 6. The interface (replaces `art/licensed/ui/` and `art/licensed/pastel/`)

The page cuts each panel and button as a **9-slice**: corners stay as drawn, edges and the middle stretch. Draw
each at the size given, and keep the **slice** (how many pixels from each edge are the border) exactly, or the
CSS has to change with it. Top, right, bottom, left.

| ☐ | File | Size | Slice | What it is |
|---|---|---|---|---|
| ☐ | `panel.png` | about 106 × 122 | 6 | Every menu, dialog and the sign. Tan |
| ☐ | `button.png` | 26 × 26 | 4 4 6 4 | The cream button. The 6 at the bottom is its raised edge |
| ☐ | `button-hover.png` | 26 × 26 | 4 4 6 4 | Lit (white) |
| ☐ | `button-down.png` | 26 × 26 | 4 | Pressed in: no raised edge |
| ☐ | `button-green.png`, `button-pink.png` | 26 × 26 | 4 4 6 4 | Today recoloured from the cream one by code: draw them only if she wants them different |
| ☐ | `field.png` | 26 × 26 | 4 4 5 4 | Text inputs: pressed in, pale grey |
| ☐ | `bubble.png` | 42 × 42 | 5 5 6 5 | A cat's ask and the replies in its thread |
| ☐ | `frame.png` | 30 × 30 | 7 | The picture frame: portraits, the Edit rooms plan |
| ☐ | `corners.png` | 20 × 20 | 9 8 | Four selection brackets in the corners, empty middle. Rooms light up with them |
| ☐ | `divider.png` | 58 × 4 | 4 1 0 1 | The line between parts of a menu |
| ☐ | `arrow.png` | 10 × 9 | | A select's arrow |
| ☐ | `pointer.png` | 7 × 12 | | The triangle beside the chosen menu item |
| ☐ | `toggle.png` | 56 × 18 (two 28 × 18 cells: off, on) | | The sound switch |
| ☐ | `status.png` | 24 × 12 (tick, cross) | | The sign's tick and cross |
| ☐ | `faces.png` | 192 × 32 (six 32 × 32 cells) | | The mood faces, in order: upset, needs you, to review, working, asleep, a queen's heart eyes. The face fills about 24 × 24 of the cell |
| ☐ | `crown.png` | 14 × 13 | | A queen's crown, gold with a brown outline |
| ☐ | `stars.png` | 20 × 8 (two 10 × 8) | | What a queen keeps: gold (said) and brown |
| ☐ | `cursor.png`, `cursor-point.png` | 16 × 16, saved doubled to 32 × 32 | | The cat-paw pointer, open and pointing. Draw at 16, export at 200 %: a cursor isn't scaled by the page |
| ☐ | `logo.png` | 21 × 18 | | The brand: a cat face in a bubble |
| ☐ | `pastel.png` | 200 × 20 (ten 20 × 20 cells) | | Control icons, in order: up, down, plus, minus, house, pause, play, check, lock, unlock |

**The map panel** (`art/licensed/pastel/`) is SC_siosio's smooth art today, the only part of the page that isn't
pixel art. **Recommendation: draw it as pixel art too**, from the same palette as the rest, so the page has
one hand. The rule "draw each panel from one pack" then simply holds. At pixel scale:

| ☐ | File | Size | Slice | What it is |
|---|---|---|---|---|
| ☐ | `pastel/panel.png` and `panel-dark.png` | about 48 × 32 | 7 | The map panel, light and for the dark theme |
| ☐ | `pastel/frame.png` | about 24 × 24 | 3 | The minimap's view frame: a border alone, empty middle |
| ☐ | `pastel/button.png`, `-hover`, `-down` | 20 × 20 | 5 5 6 5 | Its square buttons |
| ☐ | `pastel/icons.png` | 45 × 9 (five 9 × 9) | | Plus, minus, up, down, question |

Those need the CSS's slice numbers and sizes changed (section 9): the smooth pieces are drawn at twice their
screen size, the pixel ones won't be.

**Build mode** (`docs/camera-and-minimap.md`, not built yet) will also want: a house icon, a stairs icon, a
hammer or trowel for the Live / Build switch, undo and redo, a slider knob, a ribbon for "Build", the catalogue
bar's panel and tabs, and rounded key caps for the `?` list. Draw them when Build is built: 9 × 9 icons on the
same grid as above.

### The pixel font (`sprout.ttf`)

Today Sprout Lands' font: capitals only, 7 px wide letters in 2-pixel strokes, used at 18 px. Aseprite can't
make a font. Two choices:

1. **Draw it** as a sheet of glyphs (A–Z, 0–9, punctuation, and the French accents `build-art.py` adds: à â ä ç é
   è ê ë î ï ô ö ù û ü ÿ, middle dot, ellipsis), each in a 7 × 9 cell at 1 px strokes, plus 2 rows above for
   accents and 2 below for ç. A small script then turns the sheet into a `.ttf`, the way `pixel_font()` already
   builds glyphs from pixels. Ask Claude to write it when the sheet is ready.
2. **Use an open pixel font** (SIL Open Font Licence), which can be committed. This is the one asset where
   drawing it yourself buys the least.

Nunito and Fredoka (the body text) are open fonts from Google Fonts: nothing to replace.

## 7. Sound (not art, but on the same list)

None yet. A short meow, a purr, soft paw steps and a door. Recorded or made herself, under a second each, as
`.ogg` or `.mp3`.

## 8. New pieces she wants

None of these exist in the catalogue yet. Tick what to make. Sizes are suggestions on the same scale as section 3.
Pieces marked **station** would give cats a new place to show a state: say which state when it's drawn.

### Cat things

| ☐ | Piece | Size | Where | Notes |
|---|---|---|---|---|
| ☐ | **Litterbox**, open, with litter | 20 × 14 | Ensuite, catio | Decor. A covered one (22 × 20) hides better |
| ☐ | Litter scoop and a mat under the box | 8 × 10, 26 × 12 | Next to it | |
| ☐ | Cat bed, a basket with a cushion | 18 × 14 | Anywhere | **Station** (sleep): a nicer sleep spot than the cushions |
| ☐ | Wall shelves for cats, steps | 16 × 6 each | Cat lounge | Wall piece |
| ☐ | Window perch, a hammock | 24 × 12 | Under a window | **Station** (sleep or needs) |
| ☐ | Cat tunnel | 32 × 14 | Catio, lounge | Rug-like |
| ☐ | Toys: a mouse, a ball, a feather wand | 6–8 × 5–14 | Scattered | Tiny; good on the lawn and on rugs |
| ☐ | Water fountain for cats | 16 × 16 | Kitchen | Replaces the water bowl |
| ☐ | Cat carrier | 22 × 18 | Hall | Where a new cat could arrive |

### The café (so it reads as a café)

| ☐ | Piece | Size | Where | Notes |
|---|---|---|---|---|
| ☐ | **Round bistro table**, two-top | 22 × 24 | Café, terrace, catio | Marble top, iron foot |
| ☐ | **Square café table**, four-top | 32 × 28 | Café | |
| ☐ | Bistro chair, four ways | 12 × 20 | Round them | Facing you, away, left (mirror for right) |
| ☐ | Café counter with a glass pastry case | 48 × 30 | Kitchen, facing the hall | **Station** (work): where you order |
| ☐ | Espresso machine | 16 × 16 | On the counter | Top piece |
| ☐ | Cake stand with cakes | 12 × 14 | Counter or table | Top piece |
| ☐ | Cups and saucers, a teapot | 6 × 6, 10 × 9 | Tables | Top pieces |
| ☐ | Chalkboard menu on an easel | 18 × 30 | Café door, the drive | Not a sign with words: chalk doodles only, she hates signs |
| ☐ | Till, or a bell on the counter | 12 × 10 | Counter | |

### The manor (from the Peleș and Sinaia list)

| ☐ | Piece | Size | Where |
|---|---|---|---|
| ☐ | Four-poster bed | 36 × 56 | Bedroom (replaces the bed; keep its sleep station) |
| ☐ | Claw-foot bath | 36 × 22 | Ensuite |
| ☐ | Grand piano | 48 × 40 | Cat lounge |
| ☐ | Marble bust on a pedestal | 14 × 34 | Hall |
| ☐ | Chandelier, seen from above | 24 × 20 | Hall, café (an overlay over the floor) |
| ☐ | Copper pan rack | 32 × 12 | Kitchen (wall piece) |
| ☐ | Carved oak settle (a bench) | 40 × 26 | Hall |
| ☐ | Coat stand, umbrella stand | 12 × 32, 10 × 16 | Hall |
| ☐ | Letter tray and a pile of post | 16 × 10 | Hall (it holds snail mail) |
| ☐ | Laptop, open | 14 × 10 | Desks (top piece): the working station she pictured |
| ☐ | Desk lamp, a pile of books | 8 × 14, 12 × 10 | Desks |
| ☐ | Framed pictures, a mirror | 12–24 × 16 | Back walls (wall pieces) |
| ☐ | Cobblestone paving | 16 × 16 tile | The drive and the café's door |
| ☐ | Stone balustrade | 16 × 16, repeating | The terrace's edge |

## 9. What changes in the code when her art arrives

**Nothing, for most of it.** Every piece is a slot (3 October, "Allow all assets to be plug-n-plays"), and every
colour, font and size a token (4 October, "the entire design system"): pick your palette in **The look** in the House
menu, then give a slot your drawing and the café draws with it, either from The look (Replace…, a piece at a time) or
by saving it in `catio/art/skin/` under the slot's name (`panel.png`, `cat-meow.png`…) and running
`python3 catio/tools/skin.py`. A 9-slice can have its own border (say it when you replace it), a cat any frame size
and count, the map panel can be pixel art; the house, the grounds and the furniture keep their sizes, since the rooms
are measured on them. `CLAUDE.md`, "Plug-and-play design", has the rules. The slot names are the file names in the
tables above, without `.png`; the cats are `cat-work`, `cat-review`, `cat-meow`, `cat-cry`, `cat-sleep` and
`cat-walk-side`, you in the queen's scene `owner`, the map panel's pieces `map-panel`, `map-button`…, and the fonts
`font` (pixel), `font-body` and `font-display`. A pixel font of your own drawn on another grid than 18 px sets its size
in The look (Type, Pixel font size).

What is left for Claude:

- **Her art can be committed.** It is hers, so `art/licensed/` and its licence rules go away piece by piece, and
  anyone's clone shows the house. (Whether the repo stays public with her art in it is her call.) The credits
  in `catio/art/CREDITS.md` and the footer shrink as packs leave.
- **`build-art.py` and `furniture.py`** read her files instead of the zips: a folder `catio/art/source/`,
  one PNG per piece, named as in the tables above. `CATALOGUE` loses its sheet boxes and `scale=0.5`.
- **Cats:** the moods and the side walk drop in as slots. Left: the walks down and up (`cat-walk-down`,
  `cat-walk-up` are not slots yet), and coats as palette swaps instead of CSS filters.
- **The map panel:** nothing in the CSS any more (its border and pixel art are part of the slot); only the
  "smooth, never pixelated" rule in `CLAUDE.md` retires.
- **New pieces** go into `CATALOGUE` and `LAYOUT`, with stations where marked, then `furniture.check()` must be
  empty and no cat may stand on furniture.
- **Integer zoom** (the Game UI rule): the camera zooms freely today. Snapping it to whole steps (1×, 2×, 3×, 4×)
  when it settles would keep her pixels exactly square.
- `sh catio/test/run.sh` before every publish, as always.

## Order to draw in

1. **The cat:** the five moods, then the side walk. It's on screen all the time, and it's the most licensed part.
2. **The interface:** panel, buttons, field, bubble, faces, pointer, cursor. Small, and on every click.
3. **Floors and walls:** six floors, nine walls, the window. The house reads as hers from here.
4. **Furniture**, a room at a time, starting with the café and the cat lounge (where new cats arrive).
5. **The grounds**, the trees first (they repeat most).
6. **New pieces** from section 8, whenever she likes: each drops in on its own.
7. **The font** last, or an open one.
