# What's missing: art and sound for the Catio

Everything the Catio shows today, and what it would take to make it what you picture: what to buy, and what
to draw (or commission) because no pack has it. Checked against the packs' itch.io pages on 29 September 2026.

## How to draw anything for it

So a piece drops straight in without scaling or blur:

- **Tile grid:** 16 px, Cosy Cabin's. A back wall is 32 px tall, and a wall seen from above is a 5 px band.
- **View:** three-quarter top-down. You see the tops of things and their south faces.
- **Light:** from the top left. Highlights go on the top and left edges, shade on the bottom and right, and
  the drop shadow falls to the south-east.
- **Cats:** 32 × 32 frames with the feet at the bottom middle (Mochi's size), or 64 × 64 (Pochi's size).
  Keep one size for every cat.
- **Palette:** Sprout Lands' creams and tans for anything near the interface: `F3E5C2`, `E8CFA6`, `C49A6C`,
  `AA7959`, `90625D`, ink `3F2A20`. Keep the accents muted: gilt `D9B45A`, and soft jewel tones for glass.
- **Format:** PNG with a transparent background, one piece per file, or a sheet on the 16 px grid. Tell me
  each piece's box.

## 1. Buy first: cheap, and each fixes something visible

| Pack | Price | What it fixes |
|---|---|---|
| [Cat Pack – Pochi](https://toffeecraft.itch.io/cat-retro), paid | $1.80+ | **The walk.** Its *Run* animation replaces today's hopping sitter. It also has **six real coat colours** (brown, white, black, grey, orange, grey-white). Coats are now the only way to tell projects apart, so real colours beat today's colour filters. It also adds Happy, Chilling, Surprised, Sleeping and Dance for the moods. |
| [Sprout Lands UI Pack](https://cupnooble.itch.io/sprout-lands-ui-pack), premium | $3.99+ | Emote bubbles for meowing cats, a bigger emoji set (more mood faces), and more expressions for its cat |
| [Sprout Lands Asset Pack](https://cupnooble.itch.io/sprout-lands-asset-pack), premium | $3.99+ | Doors, windows and roofs that could replace the facade I drew in code, plus interior furniture |

**Worth knowing before you buy:**
- **Mochi has no walk cycle.** The paid [Cat Pack – Mochi](https://toffeecraft.itch.io/cat-pack) ($1.90+)
  has no walk or run; its own page says so. Buy it only for its colours and poses (eating, licking,
  bathing, dancing), not for walking.
- **Sizes:** Pochi is 64 px and Mochi 32 px. If Pochi's Run becomes the walk, the working cat (today a
  32 px Mochi) should become Pochi too, so every cat is one size.
- **Directions:** Pochi's Run is most likely side-on only. Walking up and down the screen, and climbing
  the stairs, would still need drawing (section 2).
- **Catio furniture:** ToffeeCraft's [CatRoomPaid](https://toffeecraft.itch.io/cat-pack) ($1) adds cat
  furniture and decorations for the catio.

## 2. Draw or commission: no pack has these

### The cats

| Piece | Where it goes | Frames |
|---|---|---|
| **Walk, 4 directions** (side, towards you, away) | Every walk between spots | 4–6 a direction |
| **Climbing stairs, from behind** | Going upstairs when archived | 4 |
| **Coming downstairs, from the front** | Coming back down | 4 |
| **Working**: at a laptop, a desk or yarn | A working cat's station | 4–8, looping |
| **Sitting on a step** | If napping cats ever sit on the stairs instead of vanishing | 2 |

The Pochi Run from section 1 covers "side". The rest match whichever cat you choose.

### The manor, after Peleș and Sinaia

Today these are drawn in code (`catio/tools/manor.py`). They work, but hand-drawn pieces would be richer.

**Outside:**

| Piece | Size |
|---|---|
| Limewashed wall, ochre and one or two pastels | 16 × 32 repeating |
| Stucco pilaster and cornice | 5 × 32, and a 16 × 3 cornice |
| Arched window with painted shutters, open and closed | about 18 × 16 |
| Baroque double door with a pediment and a stained-glass fanlight | about 36 × 32 |
| Stone plinth and corner quoins | 16 × 7, and 5 × 5 blocks |
| Wrought-iron stair rail with scrolls | 2 × 16 |
| Window box of red geraniums | 16 × 6 |

**Inside, walls and floors:**

| Piece | Size |
|---|---|
| Gilt trellis panel on white (photo 3) | 16 × 32, and a 6 × 32 pilaster |
| Carved walnut panelling (library) | 32 × 32 repeating |
| Art Nouveau wallpapers (lily, iris, peacock) | 16 × 20 repeating |
| Stained-glass window, lily or fleur | 30, 40 and 76 wide × 32 |
| Parquet or herringbone floor (drawing room) | 16 × 16 |
| Marble chequer (orangery) | 16 × 16 |

**Inside, furniture** (each is a piece renovation mode can move):
- **Library:** a carved walnut bookcase with an iron grille and gilt scalloped shelves, after photo 2.
- **Great hall:** a marble bust on a pedestal (photo 3), a chandelier seen from above, a carved oak
  settle.
- **Drawing room:** an ornate fireplace and a grand piano.
- **Bedroom:** a four-poster bed.
- **Bathroom:** a claw-foot bath.
- **Kitchen:** a copper pan rack.
- **Everywhere:** carved chairs.
- **Catio:** a cat flap. Today it's a dark rectangle.

**Outdoors:**
- ~~Spruce and fir trees~~: done from Little Dreamyland's spruces (29 September); a forest now edges the grounds.
- ~~Lanterns on posts~~: done from Little Dreamyland's lamp posts, along the drive and at the cafe.
- Cobblestone paving, after photos 1 and 4. No pack has it.
- A stone balustrade (photo 4). No pack has it.

### The cafe (KittyChat Cafe)

**Built (29 September):** a terrace on the lawn west of the drive, from the packs:
- Cosy Cabin cabinets as the counter;
- Little Dreamyland's notice board as the house-rules board;
- barrels, planters and a lamp;
- two Cosy Cabin tables with checked cloths, with chairs.

**Still missing:**
- an espresso machine;
- cups and cakes on the counter;
- a real chalkboard (the notice board stands in).
- If cats are ever to sit there, it would also need to become a place in the page, not only decor.

## 3. Sound: nothing yet (Charlotte is finding some)

The meow is made in code (a filtered tone). Real sounds would be better:
- a short meow;
- a purr for a cat that finishes;
- soft paw steps;
- a door, for new cats coming in.

For free sounds, search [freesound.org](https://freesound.org) filtered to the **CC0** licence, and keep
each under a second.

## 4. Licences to sort out

These aren't art to get, but they're open questions on what you already have:

- **Unknown makers or terms:**
  - `plants.zip`: who made it? It's credited as unknown.
  - `Game_UI_Pack_Pastel.zip`: settled. SC_siosio's, credit required, no redistribution; now in use.
- **If the Catio ever becomes commercial** (sold, or used for the shop), several free versions don't
  allow it:
  - ToffeeCraft free: personal use only.
  - Sprout Lands basic (UI and sprites): non-commercial.
  - Little Dreamyland free: non-commercial.
  - Top Down Garden Castle: no distribution at all.
- **The premium Sprout Lands packs and the paid ToffeeCraft packs** all allow commercial use.
