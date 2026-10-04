# The Catio: operating brief

`README.md` says what the page is. This file is how to work on it.

## Republishing

The page is **one** private artifact. Its URL is in `artifacts.json`. Always republish to that
URL (`Artifact` publish with `url`, after reading it back), never a new one: the database with
her rooms, renames and adopted chats belongs to that artifact.

Publish `catio/index.html` with:

- `files`: every file the page references: `art/furniture.png`, `art/licensed/*.png` (`house.png`,
  `house-upper.png`, `decor.png`, `furniture.png`, `meadow.png`, `mochi-idle.png`, `mochi-box.png`,
  `pochi.png`) and the interface
  in `art/licensed/ui/` (`panel`, `button`, `button-hover`, `button-down`, `button-green`,
  `button-pink`, `field`, `arrow`, `frame`, `divider`, `bubble`, `corners`,
  `toggle`, `status`, `faces`, `crown`, `stars`, `cursor`, `cursor-point`, `pointer`, `logo`, `pastel` `.png`,
  and `sprout.ttf`), and the map panel in `art/licensed/pastel/` (`panel`, `panel-dark`, `frame`, `button`,
  `button-hover`, `button-down`, `icons` `.png`); and, once she has pieces of her own in `art/skin/`,
  `art/skin.json` and each file it lists (below, "Plug-and-play design");
- `capabilities`: omit it on a republish to keep what's stored: Claude Code Remote's nine tools and the
  gateway's five (below), `db`, `assets` and `sample`. Pass it only to add a tool on purpose, and then pass the whole set
  (the first republish after PR #31 must, to add `list_repos`: until it has, the wizard's GitHub step says the page
  isn't allowed to ask).

`catio/data/` is **not** published: it is for the localhost copy (below).

`art/licensed/` is not in git (licences below). In a fresh session, get it back one of two ways:

1. `Artifact` read with `path: "art/licensed/<file>"` on the published URL, for each file; or
2. get the ten zips from her Drive folder "KittyChat Cafe Assets" (or ask her for them) and run
   `python3 catio/tools/build-art.py CosyCabin.zip CatMegaFree.zip "Top down garden castle.zip" "Wood Garden Asset Pack.zip" "Pixel Art Top Down - Basic v1.2.3.zip" "Sprout Lands - UI Pack - Basic pack.zip" plants.zip "Sprout Lands - Sprites - Basic pack.zip" "Little Dreamyland - Free Pack.zip" Game_UI_Pack_Pastel.zip`
   (needs `pip install pillow fonttools`; the order matters, not the names). Given only the Sprout Lands zip, it rebuilds just the
   interface.

## Licences: what may be committed

- **Cosy Cabin** (Marie Pepo): copying and modifying allowed, with credit. `art/furniture.png` is
  committed. The house itself is not: it mixes every pack now.
- **ToffeeCraft cats** (free version): personal use only, **no redistribution**. Never commit.
- **Top Down Garden Castle** (Heosphorus): **no distribution, even modified**. Never commit.
- **Wood Garden** (rowdy41): no resale. It is baked into `decor.png` with Heosphorus's
  pieces, so that file stays uncommitted too.
- **Pixel Art Top Down – Basic** (Cainos): free for any project, **no redistribution**. Its
  stonework is also in `decor.png`. It is drawn on a 32 px grid, twice the cabin's, so its
  pieces read large: use it for garden stonework, not indoor furniture.
- **Sprout Lands UI Pack – Basic** (Cup Nooble): modifying allowed, **no redistribution or resale,
  even modified**, non-commercial use only. The whole interface (`art/licensed/ui/`). Never commit.
- **Sprout Lands Sprites – Basic** (Cup Nooble): the same terms. Flowers on the lawn. Never commit.
- **Little Dreamyland** (Starmixu & Utaskuas): changes allowed, non-commercial only, **no
  redistribution or resale, even modified**, no AI training. Glazed tiles and the forest. Never commit.
- **plants.zip**: no licence came with it, so it is treated as licensed. Never commit.
- **Game UI Pack – Pastel Edition** (SC_siosio): personal and commercial use, credit required ("Game UI Pack
  created by SC_siosio", word for word), **no redistribution, even modified, no uploading to a repository**,
  and its files must not be easily extractable. Ship only the pieces `build-art.py` cuts from it, resized and
  recoloured, never its own 500 px PNGs or SVGs: the pixelated icons (`ui/pastel.png`) and the map panel's
  smooth pieces (`art/licensed/pastel/`). The full zip is 12.5 MB, over the Drive connector's 10 MB limit:
  `Game_UI_Pack_Pastel_icons.zip` in the Drive folder (3.3 MB: the licence, the readme and `PNG/Filled/Icons`)
  is enough for the icons, but the map panel's pieces need the full zip's panels and buttons, so ask her to
  attach it in the chat. A republish needs neither: read `art/licensed/ui/pastel.png` and
  `art/licensed/pastel/*` back from the artifact. Never commit.

`catio/art/CREDITS.md` says which pack drew what. The footer credits them all. Keep it.

## The manor is a floor plan, on two floors

`catio/tools/manor.py` is the plan. It holds rooms as tile boxes with their floor (`ground` or `upper`),
floor texture and back wall; the landing; the craft room's bay; doorways; glass; the stair; and the
grounds. `shell(floor)` draws each floor, in the Storybook Baroque look, from every pack, into
`art/licensed/house.png` and `art/licensed/house-upper.png`: never committed. `grounds()` draws the catio,
the drive, the forest and the garden (`decor.png`). `catio/tools/furniture.py` places every piece of furniture and its stations, and writes
the page's `MANOR` block. The page's `GEOM` comes from that block, so change the plan and the furniture
together, re-run `build-art.py` (or `furniture.py`), and check that `furniture.check()` is empty and no cat
stands on furniture.

**Both floors stand on one grid** (columns 6, 17, 32, 43; rows 3, 13, 24): every upstairs wall stands on a
ground-floor wall, except the ensuite's light partition inside the bedroom's bay. Keep it that way. A wall
off the grid is what made the first draft's walls "not make any sense". Outside walls are ochre limewash
with stucco quoins; inside walls are plaster either side of an oak beam. A doorway is a clean cut: through
a back wall it has a carved oak lintel, through a side wall a darkened threshold. Every room has a back
wall, so a doorway never meets a bare edge. The ground floor alone has the south facade, the pediment
front door and the steps; the library, the lounge and the hall's south strips have stained glass.

`furniture.doors()` lists the doorways as the cats' routes (`MANOR.doors`): each floor's doorways, the
terrace's cat flap, the front door, and the stair as one link from the hall (its foot) to the landing (its
top). The stair piece's `upstairs` stations are its steps.

The layout runs from public to private, the way houses and game levels both do:

- **Downstairs is the cat café.** Café, kitchen and counter, and cat lounge sit across the back. The craft
  room (the shop, its bay window its shop window on the drive, bottom left), the entrance hall (the stair
  and the front door) and the glazed terrace sit across the front. The catio is fenced at the bottom right,
  reached by the terrace's cat flap.
- **Upstairs are her own rooms,** over the back of the house: the library over the café, an open landing
  over the kitchen and hall (the stairwell and the attic ladder), and the bedroom and ensuite over the
  lounge. The craft room and the terrace are single-storey wings.

The stair is in the same place on both floors, so changing floor never moves the camera.

## The UI is made of the packs

The manor fills the screen and is the page, **one floor at a time**. The ground floor stays faded under
the upper one: `S.floor`, `data-floor` on everything, upper pieces lifted by `ZUP`.

- **The page is the KittyChat Café** (September 2026: "the harness and UI SaaS that I am making here is
  called the KittyChat Cafe"). The Catio is the page's old name and the code's; the catio is still the
  fenced deck outside.
- **No signs on the map** (she hates them): no room names, badges or stair sign on the art. A room is
  named on hover (`#tip`); the other floor's button carries its badge; the brand carries the house's.
- **Nothing on the cats** ("I don't like the letters over the cats. Remove all icons on top of the moving
  cats", 2 October 2026, and "remove everything, the crowns, the letters"): no model letters, file counts,
  faces, speech bubbles, pile numbers or crowns on the map, and no "z Z" over sleeping cats (`unz()` in
  `build-art.py` erases them from the sheet). Hovering a cat or a queen says what it needs in `#tip`: its
  name and mood, then its ask, its waiting files, or the note a queen is saying. Keep it that way: a new
  fact about a cat goes in its hover line, menu or card, never on the sprite.
- **Floors**: the stair, the floor buttons and Page Up / Page Down go between them. The tally counts both
  floors.
- **Controls**: two things sit on screen, and nothing else should:
  - the brand (`#houseBtn`, top left: ToffeeCraft's cat-face bubble, the name and a badge when cats need
    her), which is the House button: its menu holds what belongs to the whole house (whether the cats are
    live, the brain, house rules, Project maps, Edit rooms, the attic, Check now and sound). **Project maps**
    (`openMaps()`, her ask of 3 October: "a customizable dashboard built on Graphify", the graphify of her house
    rules) shows every `graphs/<repo>` map as a card, pinned first, then in her order, then the newest; she pins,
    moves, widens and hides each, and `dashboard/maps` keeps it;
  - the map panel (`#controls`, top right; bottom right on a phone), in Game UI Pastel, drawn smooth:
    zoom out, zoom in, whole house and the fold (`#mapFold`, or M, remembered in `localStorage` as
    `catio.minimap`, folded at first on a phone); the minimap (`#minimap`: the floor's rooms as a plan
    over `MM.box`, the manor and catio, the other floor faint, a pip where a cat needs her, the camera's
    view framed; click goes there, drag pans, double-click looks in, the wheel zooms); and the floor
    tabs, with a pip when the other floor needs her. Menus open clear of it (`showMenu`). The plan for
    the rest (the Sims-style camera and Build) is `docs/camera-and-minimap.md`.
- **The status sign** under the brand shows only when something is wrong. When Claude's saved copy fills
  in for a blocked live read, it is one line ("Saved copy · 17:02") and the why shows on hover or focus.
- **Room controls**: a control for one room or cat goes in its menu.
- **The camera is free**: drag to pan (left, right or middle button, or Space), wheel or pinch to zoom,
  + / − / 0 and Shift+arrows. `S.focus` is the room that fills the view.
- **Hover names a thing** in a line (`#tip`). **A click opens its menu** beside it, pinned until a click
  elsewhere or Escape (`toggleMenu`); a tap does the same. Keyboard focus opens a menu only when
  `:focus-visible`, and a click never closes a menu keyboard focus opened.
- **Every menu has the same shape, as short as it can be** ("make the menus less bloated and minimize
  noise", September 2026):
  - the name, with a badge when cats need her, and one line under it (no captions, no chips);
  - what matters now, if anything does: the cats that need her (three at most), a queen's said note, a
    cat's ask;
  - the actions as a list (`mi()` in `list()`), the first the default (`.primary`), the pack's triangle
    (`pointer.png`) beside the one under the pointer or focus.

  Keep to that: a new action is a list item, and only if it earns its place. A card (dialog) puts what she
  came for first and folds the rest (a cat's facts, management, name and title under Manage).
- Hover means the pointer really moved onto the thing (`moved()`). When the camera moves or a dialog
  closes, the room that slides under a still pointer isn't named until she moves.
- **Cats walk** when their place changes: through the doorways to a new room, up the stair to nap in the
  attic (to the landing's ladder when they're upstairs), down it when they come back, and in by the front
  door when they're new. A journey that changes floor starts at the stair on the floor they're going to.
  Working cats wander a little. A cat's element must be in the page before `walk()` starts.
- **The line at the front door** (her ask, 3 October): every cat waiting on her (mood `needs`, the meowing ones)
  lines up in front of the entrance-hall door, beside the queen, the longest wait first (`LINE`, `placeLine()`,
  `WAITING` keeps when the page first saw it wait), upstairs ones included; one that stops waiting walks back to its
  room. Its room is still its own (menus, cabinets, Manage); the floor badges and the minimap count it where it
  stands. Upset and to-review cats stay in their rooms. With reduced
  motion, and for four seconds after the page opens, cats are simply in their places.
- **Onboarding** (`openSetup()`, `#setupDlg`): a café whose database has no `rooms/*` at all opens the wizard
  on its first snapshot that isn't from cache (Charlotte's has rooms, so she never sees it; the localhost copy
  seeds rooms from `data/rooms.json`). Seven steps, nothing written until Done: the café's name (`house/main`),
  how many rooms (the first N of `OPENING`, public to private: lounge, café, kitchen, craft room, terrace, catio,
  library, bedroom, ensuite, hall; a name each; the first is where new cats come in), the repositories
  (`list_repos`, each with a select of the open rooms), what the live read found, the litter box (the brain's
  tray here, `litterbox/` in a clone; holding pull requests is the merging rule's doing, not a setting), how the
  harness works with the two install lines, and the summary. "Set up again…" in the House menu replays it
  prefilled, and keeps each room's blurb and model. **A closed room** (`rooms/<k>.closed`) is dimmed with no sign,
  faint on the minimap, has no queen and gets no cats (`roomFor()` and `catchAllRoom()` skip it; the selects
  list open rooms only); cats still walk through it. Its menu is its name, "Closed", Open this room and Edit
  rooms, where each room has an Open switch and closing the front door's room moves the front door.

The interface is Cup Nooble's Sprout Lands UI pack, cut by `build-art.py` into
`art/licensed/ui/`. Menus, dialogs, the sign and the screen's frame are its tan panel; buttons are
its cream square button (white on hover, pressed in when held; `green` and `pink` are recoloured
copies); inputs are its grey pressed-in button; a cat's ask and the replies in its thread are its grey bubble;
a filing cabinet's project sits in its pressed cream well; rooms and cabinets light up with its
white selection brackets (on a room they stay one size on screen at any zoom), and so does the
chosen room on the Edit rooms plan, which sits in its picture frame with its arrow, on its white
button, pointing into the room new cats come in to. Each is a 9-slice `border-image`. The mood faces are its cat emoji
(`faces.png`, in `MOODS` order, then a queen's heart eyes), the sound control is its toggle, the
sign's tick and cross are its own, a queen's crown (in her menu and card, never on the map) is its crown icon gilded, what she keeps is
starred with its stars, and the pointer is its cat paw. Keep it that way: a new control should
reuse one of these pieces rather than a CSS border or gradient. The controls' icons are SC_siosio's Game UI
Pack (Pastel Edition), pixelated (`pastel.png`: up, down, plus, minus, Sprout Lands' house recoloured to match,
pause, play, check, lock, unlock; also on a cat's Manage buttons and enforced house rules), the menus'
cursor is its cream triangle (`pointer.png`), and the logo is ToffeeCraft's Cat UI cat-face bubble
(`logo.png`). `--u` is one art pixel on screen
(2px, or 1px on phones); room tags and the hover line are drawn at one art pixel a pixel.

**The second pack.** SC_siosio's Game UI Pack, Pastel Edition (Charlotte's choice, 30 September 2026) dresses
what works the camera and what builds the house: the map panel and minimap, its icon buttons (zoom, whole
house, floors, fold), and Build's tools (the Live / Build switch, the catalogue bar, a filing cabinet's
"Looks like…" panel, undo and redo). Everything that talks about cats and rooms stays Sprout Lands. Draw each
panel from one pack, never both. The Pastel art is smooth, not pixel art: scale it down with ordinary
smoothing, never `pixelated`. See `docs/camera-and-minimap.md`.

Titles, labels, buttons and names use the pack's pixel font (`--pixel`, `sprout.ttf`) at **18px** (`--px-size`),
where one font pixel is one screen pixel (36px for a cat's name on its card); anything else blurs.
It has capitals only (small letters draw as capitals), so body text stays in Nunito.
`build-art.py` adds the accents French names need (à â ä ç é è ê ë î ï ô ö ù û ü ÿ, a middle
dot, an ellipsis, curly quotes); other symbols fall back to Fredoka.

## Plug-and-play design

Her asks of 3 and 4 October: "Allow all assets to be plug-n-plays", then "Make sure the entire design system is
plug-n-play". The design system is **tokens and slots**, and a skin can change any of them with no code change.

**Every colour, font and size is a token** in `:root` (`TOKENS` in the page names them for The look): `--ink`,
`--tan`, `--well`, `--go`, `--grass`, the map panel's and the minimap's colours, a project map's `--hue-1`…`--hue-8`,
the owner's chair and bow, `--px-size` and `--px-line` (the pixel font, one font pixel a screen pixel: titles are
twice it), `--body-size`, and the art pixel `--u-desk` and `--u-phone` (`--u` is one of them). A see-through colour
is mixed from its token (`color-mix(in srgb, var(--glow) 14%, transparent)`), and the script reads a colour it draws
with `tok()`. Keep it that way: **a new colour, pixel-font size or art-pixel size is a new token**, never a literal in a
rule or a `"#…"` in the script (only `OWNER`'s choices, which are her look, not the café's). A check walks the page for
one. The text's smaller sizes stay `rem` steps from the browser's own size, as they always were.

**Every piece of art is a slot** (`ART` in the page, 45 of them, named as `docs/drawing-plan.md` names her files:
`panel`, `button`, `cat-meow`, `house`, `owner`, `font`, `font-body`…).
The CSS and the code name the slot, never the file: a 9-slice is `var(--art-panel) var(--panel-s) fill /
var(--panel-w)`, a sheet `var(--art-faces)`, the house `<img data-art="house">`, the furniture
`srcOf(ATLAS[…])`. So any piece swaps for her own drawing, or another pack's, with no code change. Keep it that way:
**a new piece of art is a new slot** (a line in `ART`, a `--art-<slot>` default in `:root`), never a `url(art/…)` in a
rule. A check walks the page for one.

A skin says which are hers, from two places; the second wins:

- **`art/skin.json`** beside the page: `{ "panel": { "file": "art/skin/panel.png", "slice": [8, 8, 8, 8] }, …,
  "tokens": { "--ink": "#1D3557", "--px-size": "16px" } }`. `python3 catio/tools/skin.py` writes the slots from
  whatever is in `catio/art/skin/` (each file named after its slot), keeps the tokens, and says what each file fills
  or why it can't. Her own drawings may be committed there; **never put a pack's file in `art/skin/`**. The bundle
  carries it; a publish needs `art/skin.json` and its files in `files`. The café on the gateway's address doesn't
  get it yet: `cafe/move-in.py` uploads only the packs' art, and teaching it is a change under `harness/`, so hers
  to approve. The look works there all the same.
- **The look** in the House menu (`openArt()`): her colours, type and sizes, then every slot, what it is and the size
  to draw it at. A colour has its picker, a size its field, kept in `skin/theme` when she lets go; Replace… checks
  her file, asks a 9-slice drawn at another size for its border and a cat for its frames, keeps it with `assets`
  and writes `skin/<slot>`; Put back deletes either. It works in claude.ai, on the gateway and on localhost (there the
  file stays in the browser).

A token is checked as a slot is (`tokenOk()`): a colour is six hex digits, a size a length in px or rem inside its
range (`SIZES`: the art pixel 1 to 4 px, the pixel font 8 to 48, its line 8 to 64, the text 10 to 24, a rem as 16;
`WHOLE_PX`: the art pixel and the pixel font in whole px, or the pixel art blurs), and a 9-slice's border is at most 64
of its pixels a side (256 for a smooth map piece, drawn big and shown smaller), so no skin can bury The look under its
own borders, and a name that isn't in `TOKENS` is ignored.

**Modes and tokens files, as Figma has them** (her ask of 4 October, "reevaluate plug-n-play capabilities of design
systems like Figma"; read against Figma's variables, its `figma-generate-library` skill and the W3C Design Tokens
Format 2025.10). Figma keeps a variable's value per **mode** and moves a whole palette as a **design tokens file**
(`.tokens.json`, the W3C format it imports and exports natively). The café does both:

- **Two modes**, `light` and `dark` (`MODES`): `skin/theme` is `{tokens, dark, at}` and `art/skin.json` has `tokens` and
  `dark`. Dark says only what differs; the rest stays as in light. The look edits the mode its Light / Dark switch is
  on. The whole skin is one stylesheet, `#skinCss`, after the page's own (light on `:root`, dark where the page's dark
  mode is), never inline styles, so dark mode still wins in the dark.
- **Export tokens** writes the mode on screen as `kittychat-<mode>.tokens.json` (`toDTCG()`): a group per section of
  The look (`colours`, `type`, `map-colours`), `$type` on the group, each colour as `{colorSpace: "srgb", components,
  hex}`, each size as `{value, unit}`, The look's words as `$description`. Through the `downloads` capability when
  the artifact has it, else the browser's own download. Figma imports dimensions in px only, so `body-size` (rem)
  doesn't reach it.
- **Import tokens…** (`fromDTCG()`) reads any such file into the mode on screen: Figma's export, another café's, or
  one written by hand. A token is matched by its own name (`ink`, `go`, `px-size`…, or Figma's `Ink`, `Px size`) whatever group it sits in, an
  alias (`"{primitives.navy}"`) is followed, a colour may be the object or a hex string, and what isn't the café's is
  counted and left out. A name found twice takes the one in the café's own group (`colours.grass` over
  `primitives.grass`); a see-through colour or a size out of its range is refused and counted apart. `skin.py` does the same for `*.tokens.json` dropped in `art/skin/` ("dark" in the name: the
  dark mode).

Not taken from Figma, on purpose: a primitives layer under the semantic tokens (Figma's skill keeps one collection
for under 50 to 60 tokens, and the café has 56), scopes and code syntax (Figma's own metadata; a token's name here is
already its CSS variable), and more modes than light and dark (none asked for).

What a slot takes, checked before it is drawn (`misfit()`): **exact** (the house, upstairs, the grounds, both
furniture sheets, the two cursors) only its own size, because the rooms are measured on it; a **sheet** (faces,
icons, meadow, logo…) any size of the same shape; a **slice** any size, with its border in its own pixels (a
family shares its head's: the button's hover, green and pink take the button's, so each is drawn the head's size, and
while she hasn't drawn one, her head stands in for it (`SKIN.standIn`), so a hover never turns back into the pack's;
a map piece can be drawn as pixel art, `pixel: true`, its family alone then `pixelated`, or smooth at a `scale`;
what sits inside a frame follows its border: the HUD and the map panel inside the screen's panel, the portrait inside
its frame, a plan's tag and door inside its brackets); a **cat** one row of frames, any frame size, its feet at the bottom
middle unless `anchor` says, its loop in `secs` (the generated rules go in `#skinCss`, and `SPR` takes its frame
size; `--fs` scales it to fill the pack's place in a portrait, a thumb or the queen's scene); a paw (`cursor`,
`cursor-point`) says where its tip is, `hot: [x, y]` (`--cursor-hot`); `cat-walk-side` is a new slot, empty until she draws a walk: then every walking cat uses it, drawn facing
right and mirrored going left; `owner` is her own picture of herself in the queen's scene (30 × 40 or that shape),
drawn in code from her look until she gives one; `font-body` and `font-display` go ahead of Nunito and Fredoka. A
piece that doesn't fit isn't used, and The look says why.

## Data

The artifact database, written by the page and seeded with `ArtifactData`:

| Collection | Document | Holds |
|---|---|---|
| `house` | `main` | `name`: the café's own name on the brand and the title (none: "KittyChat Café"), `onboarded`: when the wizard last opened the doors, `owner`: how she looks in the queen's scene `{hair, hairColor, top, skin, extra}` |
| `rooms` | one per room key (`garden` (the catio), `kitchen`, `dining`, `living`, `sunroom`, `study`, `bedroom`, `bath`, `hall`, `brain`) | `name`, `blurb`, `repos[]` (repo names or `owner/repo`), `catchAll`, `model`, `closed` (no key: open) |
| `sessions` | the Claude Code session id | `name`, `room`: her rename or move of one session's cat |
| `cats` | generated id | an adopted chat: `title`, `link`, `project`, `room`, `mood` (`needs` / `busy` / `done`), `note`, `name` |
| `projects` | the project's slug (repo name, or an adopted chat's project) | `name`, `coat`: the look every cat of that project shares, set from a filing cabinet |
| `graphs` | the repo's slug | its project map from graphify, saved by the catio skill's `graph_doc.py`: counts, the map, hubs, groups, surprises and questions a cat can be asked; shown in the filing cabinet |
| `skin` | `theme`, and one per art slot (`panel`, `cat-meow`, `house`…) | `theme`: `{tokens: {"--ink": "#…", …}, dark: {…}, at}`, her colours and sizes in light, and what differs in dark (keep both keys when you write it: a missing `dark` loses her night colours). A slot's: her own piece for it: `src` (`/_blob/<asset>`, a gateway `/files/` path or `local:` in a browser), `asset`, `name`, `w`, `h`, and what it needs: `slice` [t, r, b, l], `frames`, `secs`, `pixel` or `scale`. No document: the pack's piece |
| `dashboard` | `maps` | how she set the Project maps page: `order[]`, `pinned[]`, `hidden[]`, `wide[]` (graph slugs) |
| `queens` | `house` | the queen of the house: `name`, `coat`, `manner` (how she speaks; the runner reads it each turn), `greeting`, `voice: {on, name, rate, pitch, lang}`, `readAt` (when Charlotte last opened her card: older handoffs are read), `notes[]` of `{text, pinned, at}`. A pinned note is one she says out loud. Older `queens/<room>` documents are hers until her first save |
| `routines` | generated id | one of her routines: `name`, `time` ("HH:MM"), `days` (0–6, Sunday 0), `tz`, `prompt`, `on`, `last` (when the gateway last handed it to her runner). Only the gateway's copy runs: the runner reads the House, not the artifact |
| `layouts` | the room key | *(planned: Build mode, `docs/camera-and-minimap.md`)* the room's furniture, and `cabinet: {look, x, y}`: the piece its filing cabinet looks like (her choice per room) and where it stands. The cabinet never leaves its room and keeps its Files and review spot whatever it looks like. No document: `MANOR.layout` and the default look |
| `snapshot` | `sessions` | `{at, savedBy, sessions[]}`: Claude's saved copy of `list_sessions`, shown when the live read is blocked. Written only by Claude, with `ArtifactData` |

Room **geometry** (where each room is on the art and where its cats sit) is code, in `GEOM` in
the page, because it is tied to the picture. Room **names and which projects live where** are
data. Don't hardcode those.

**The house has one queen** (her call, 2 October 2026: "merge the queen cats to make one main character queen cat
that you chat with that does everything for you"). She is not a session and never leaves: she sits on the hall's
seat (`GEOM.hall.queen`, `queenRoom()`; where new cats come in when the hall is closed), she keeps what matters,
and she is the one Charlotte talks to, like an NPC in a game. She is deliberately outside `allCats()`: never in
`VIEW.cats`, a pile, a filing cabinet or the sign's count, and her runner's record (the agent `queen`) is
skipped there too, because she is not work to be done. Keep her out of the counts if you touch this — a queen
that inflates "3 need you" makes the sign a liar.

- **Her brain is her runner** (`harness/runner/queen.py`, on Charlotte's PC): it waits on the gateway, runs one
  Claude Code turn per thing she says or routine due, and streams the answer back. `queenState()` reads the agent
  record `queen`: away (no runner for two minutes: asleep, "start her runner"), busy (answering) or here.
- **Her conversation** is the gateway's notes for the cat `queen`: Charlotte's lines (`comment`, author
  `owner`) and hers (author `queen`, which only the runner's key may write). In the gateway café a `{type:
  "queen"}` push (`catio:queen`) grows her live bubble as she speaks and her voice says each sentence; in claude.ai
  her card polls `comments` every 5 s. Stop is `manage {cat: "queen", action: "pause"}`.
- **Her card is a scene** (`openQueen(section)`, her ask of 3 October, like an RPG's dialogue): the owner of the house
  on the left, seen from behind in her armchair (`ownerSVG()`, pixel art drawn in code since no pack has people,
  dressed from `house/main.owner`: hair, hair colour, top, skin and a bow, cat ears or a flower); the queen on the
  right, facing her, her sprite animated and `talking` while she answers; between them the thread as bubbles, hers
  by her and Charlotte's by Charlotte, scrolling, with her homework above it; under it Speak, Send and Stop. Behind
  them the hall's own floor from `house.png`, in the pack's picture frame. **The words come first**
  ("make this window useable", 3 October): the two of them are drawn small enough to leave the thread most of the
  scene's width (`zoom` on `.owner` and `.qchar`, in steps, each with a crown scale that lands on whole art pixels),
  and on a phone they stand side by side along the foot of the scene with the thread across the whole of it. Every
  grid column around the thread and her homework is stated, never left to the content, and every button in them
  wraps: an `auto` column grows to the longest word in a bubble or a quiz, and then her words scroll off the side.
  **Every setting is in an overlay**
  (`#queenSettings`, Settings in the card's head, "Back to her" to leave): her voice switch and voice, What she keeps,
  Her character, Routines, and You. On the map she is as before: hovering names her, a click opens her menu. `speak()` is the browser's `speechSynthesis`
  (an en-GB voice unless she picks one): one function, so a paid voice could be a second branch.
- **Handoffs.** A cat's `said` (its latest note by its session or agent, from `list_agents`) newer than
  `queens/house.readAt` is something it brought her: `refreshAgents()` diffs `said.at` and a copy of the cat walks to
  her seat (`toQueen`, the `toAttic` pattern, changing floor at the stair); her card shows it as "<cat> brought
  you" with an Open button, and opening her card writes `readAt`. Nothing is drawn on the cats.
- **Homework** (her ask, 2 October: "allow the queen to assign homework by prompting quizzes to unblock sessions,
  chats or cats"). The queen (or Charlotte) sets a quiz with the `quiz` tool: a title, `for` the cat it unblocks,
  1 to 5 questions each with concrete options or a written answer; kept as `quizzes/<id>` in the House, listed by
  `quizzes`. The page shows the open ones first in her card (`#queenHomework`: tap an option or write, Hand it
  in → `answer`), and her hover says "Homework: N to hand in" (mood `box`). Handing in posts the answers to the
  cat as Charlotte's words (its hook hands them in, `Homework handed in: …`) and to the queen's conversation, so
  she can see to the rest. Only Charlotte hands in; the agents' key sets nothing.
- **Her quest log** (3 October: "where do I take the litter box quiz in the cafe UI?", then her pick: the queen's
  quest log, the cards kept in the gateway). Everything waiting on Charlotte is homework, one `quizzes/<id>` each,
  with a `kind`: `unblock` (above), `litterbox` (one sifted note: which project is it for, or *Settled: drop it*) or
  `decision` (one decision waiting on her, Claude's recommendation in `hint`). A card carries its `note` (markdown),
  `from` and `hint`, and a `ref` deals it once (its id is `<kind>-<ref>`; dealt again it is replaced while open, and
  her answer stands once given). Her card shows the unblock quizzes first, then a deck per kind, a card at a time
  (`DECKS`, `DECKAT`): a tap on an option hands it in, Skip puts the next on top. A card's answer is only kept, never
  told to the queen (each line Charlotte says to her is a turn of her runner). Her hover counts each kind
  ("Homework: 2 notes to sort, 1 decision"); the House menu leads with Homework when anything waits; the library's
  chest is the litter box (`.cabinet.litter`, no sign): hovering says what waits, a click opens her card at its
  notes, or the brain's tray when there are none. Dealing and filing: `litterbox/README.md` and
  `catio-plugin/skills/litterbox-quiz/`; `forget` clears filed and stale cards, never an open unblock quiz. A
  litterbox or decision card is one question with 2 to 12 options (the gateway refuses others: the café couldn't answer them). `litterbox/quiz.html` stays for a café with no
  gateway; her two quiz pages are retired.
- **What she keeps** is hers alone; a note she is *saying* (`pinned`) becomes her line in her menu and hover.
  The room queens of before (`queens/<room>`) are read as hers until her first save, which writes `queens/house`
  and deletes them.

Adopted chats can hold anything she types, including legal matters. They live only in the
artifact database, never in this repo. The adopt form says so. The same goes for what a queen
keeps: her card carries the same warning.

## Shipping

Sessions here commit, push and open pull requests without asking, and **merge their own pull requests,
semi-automatically** (Charlotte's call, 2 October 2026): the house rules' merging rule (`harness/README.md`,
"Semi-automatic merging") merges only when a strong model did the work, the audits and a review of the last
commit ran and nothing is a guess, and holds the rest for her with a note in the litter box. A change under
`harness/` or `.claude/` always waits for her: those are the rules themselves, and the gateway deploys on merge.

**Nothing here credits Claude, nor in her other public repos** (her rule, 1 and 2 October): no `Co-Authored-By:
Claude` or `Claude-Session:` lines in commits, and no "Generated with Claude Code" lines or session links in pull
requests, issues or comments, whatever else asks for them. GitHub's Claude integration adds its own footer to a new
pull request, issue or comment: edit it off straight after (`update_pull_request`). The house rules enforce this only
where they run: if `claude plugin list` doesn't show `kittychat-house-rules`, this session's container is older than
the setup script that installs it, so keep the rules by hand.

## The harness (KittyChat)

`harness/` is the harness behind the page (see `harness/README.md`): the `kittychat-house-rules`
plugin (hooks: preflight before any browser, a read-only ponytail audit to open a session, a nudge to
ship unpushed work, the gate on pushes and merges; the `catio` skill) and `harness/mcp/catio_mcp.py`, the Catio MCP server other
agents join through. The rules are `harness/rules.json`; Claude seeds them into the `rules` collection.

The page now **writes** through Claude Code Remote, always on an explicit action:

- **The brain**: files dropped on a cat, a room or the house go to `assets.upload` and a `brain/<id>`
  document (`name, type, size, asset, url, cat, kind, project, room, how, reason, note, status`
  `unsorted | waiting | pushed | picked`). `route()` sorts: the cat dropped on, a session/chat link in
  the file, a keyword score, then the sorter (`sample.json` in claude.ai; an OpenAI-compatible endpoint
  on localhost, `localStorage` `catio.sorter`), else the tray.
- **Posting into a session**: Claude Code Remote's `send_message` (argument names read from its schema with
  `describeTool`, else `session_id` and `message`), on trial from
  version 18. Every `[Catio] Delivery…`, `[Catio] Charlotte says: …` and `[Catio] Request: wrap_up` that it
  can't post goes to `outbox/<id>` (`status: queued`, `why`: the error code, `detail`: its message), and the
  page says it is waiting; the session's own catch-up (catio skill) finds them. Never bind a Routine
  (`create_trigger` with `persistent_session_id`, then `fire_trigger`): it starts a stray new session instead
  (tried 30 September).
- **Talking**: `notes/<id>` `{cat, text, author: charlotte|session|agent, at, via}`; replies show live.
- **Managing**: `set_session_title` (a cat's new name retitles its session too, her call on 3 October), `interrupt_session`, `archive_session` (+ `delete_trigger`),
- **Talking**: `notes/<id>` `{cat, text, author: owner|session|agent, at, via}` (`charlotte` in notes from before
  accounts: the page reads both, writes `owner`); replies show live.
- **Managing**: `set_session_title`, `interrupt_session`, `archive_session` (+ `delete_trigger`),
  `unarchive_session`, `create_session` (New cat, model from `rooms/<k>.model`).
- **Agents, and the sessions that report**: the gateway through her `CATIO` connector (`GATEWAY` in the page),
  else `host:catio` (on localhost, `/api/*` when served by `catio_mcp.py --serve`): `list_agents` every 30 s,
  `comments`, `comment`, `drop_file`, `manage`. A session that reports to the gateway is one cat with its
  claude.ai session (`fromGateway()`: the ids match after their prefix, `cse_…` there, `session_…` in the list),
  wearing the gateway's mood when it is newer; what she writes or drops on it goes through the gateway, not the
  outbox, and its replies there show in its conversation. Breeds: the model, in the cat's card.
- `audits/<repo slug>` `{repo, at, by, summary}` shows in the filing cabinet.

The stored capabilities (the full set, to pass whole if a tool is ever added):
`{ mcp: { servers: [{ server: "Claude Code Remote", tools: ["list_sessions","list_repos","send_message","delete_trigger","create_session","set_session_title","archive_session","unarchive_session","interrupt_session"] }, { server: "CATIO", tools: ["list_agents","comment","comments","drop_file","manage","decide","quizzes","answer"] }] }, db: {}, assets: {}, sample: {}, downloads: true }`

`downloads` joined it on 4 October (The look's Export tokens): until a republish passes the whole set, Export falls
back to the browser's own download, which claude.ai's frame may not allow.

`decide` joined the set on 3 October (the decider, below): the first republish after it must pass the whole set, or in claude.ai the
page cannot ask the decider and the brain simply keeps sorting the old way. `quizzes` and `answer` joined it the same evening (her
quest log): until a republish passes the whole set, the claude.ai café shows no homework; the café on the gateway's address does.

`host:catio` (the same five tools) can only be declared from the Claude desktop app, so it isn't in the stored
set. `delete_trigger` stays only to clean up the Routines older versions bound. Posting into a session through a bound Routine doesn't reach the session
(it starts a new one): see `docs/audit-2026-10-01.md` and phase 0 of `docs/plan.md` before touching
`postToSession()`. What's next, renovation mode included, is `docs/plan.md`.

### The gateway

`harness/gateway/` is the Catio's always-on hub: a Cloudflare Worker (free plan, `catio-gateway.<her
subdomain>.workers.dev`) with the Catio server's tools at `/mcp`. Every session reports to it through
`harness/hooks/report.py`, which does nothing until `CATIO_URL` and `CATIO_TOKEN` are in the environment, and
its Stop hook hands in what she sent. Workers Builds deploys it on every merge to `main`; never deploy it by hand.

- **Three secrets, set only in Cloudflare:** `CATIO_TOKEN` (agents and hooks; also in her Claude environments),
  `CATIO_PASSWORD` (her sign-in, nowhere else) and `CATIO_QUEEN` (the queen's runner, on her PC). Never in the
  repo, the chat or a test. With accounts (`src/registry.js`), the first two make the first account once; the
  queen's is a registry key with the role `queen`, kept in step with the secret at every start.
- **Only she speaks as herself, and only her runner as the queen.** OAuth (her password, through the `Catio`
  connector in claude.ai) may write as `owner`, drop files and manage; the queen's key writes as `queen`,
  tells cats and manages them for her; the agents' key may do neither. Keep it that way: it is what stops a
  leaked key from putting instructions in her mouth, or in her assistant's, which the cats act on.
- **The queen's routes:** `POST /api/runner/wait` (held up to 25 s: her notes, a routine due, a stop, her
  character) and `POST /api/runner/say` (a turn as it streams; `done` stores her note), the queen's key only.
  Routines are `routines/<id>` documents; the House's alarm wakes a waiting runner when one comes due, and a
  missed one runs once when the runner is back. `list_agents` gives each cat its `said`; `inbox` hands a cat
  what Charlotte and the queen say (`[Catio] The queen says: …` in the hook).
- **Only Claude's connectors may register** (redirects to `claude.ai` or `claude.com`).
- **Keep its tools in step with `catio_mcp.py`**: same names, arguments and results, so the page and agents
  use either.
- **The decider** (`src/decide.js`, the tool `decide`): a typed decision from a System One model, a state and named
  questions (`noul` yes/no, `choice`, `score`) answered with probabilities, no prose. Workers AI through the Worker's
  `AI` binding, Clef (`@cf/cloudflare/clef-flash`, free plan) by default or `DECIDE_MODEL` (`typesafe/jev` is Jev
  itself, paid from AI Gateway credits); or `DECIDE_URL`, any System One server such as `laya-serve`. `preset: easy`
  is the easy-task rubric of `docs/delegation.md`. With `kind`, the decision is logged as `decisions/<id>` beside
  `old`, what the old path chose, and `agree`; with `floor`, a pick less sure than it is `sure: false` and
  `agree: null` (the decider didn't decide), and `ref` names what was decided (the page's `brain/<id>`, so a pick can
  be checked against where she sent the file). No `old` when the sorter didn't answer. The page asks it where a
  dropped file goes (`decideSort`):
  `house/main.decide` unset or `"observe"` logs beside the sorter's pick and changes nothing; `"on"` lets it sort
  first above `DECIDE_FLOOR`. Switch it on only after a week of the log agrees. The plan is `docs/delegation.md`.
- **Test** with `cd harness/gateway && npm install && npm test` (workerd, the real hook included) and
  `python3 -m unittest discover -s harness/test` (the hook, the runner against a stand-in gateway and a fake
  `claude`, the rules' hooks).

It is set up (2 October 2026): her connector is named `CATIO` in claude.ai, and the page reads it (phase 5 of
`docs/plan.md`). Setting up another is the five steps in `harness/gateway/README.md`.

**The café on its own address** (her choice, 2 October: "the catio as a UI for all of my Claude sessions", in
OpenClaw's shape). The gateway's address serves the same `catio/index.html` behind her password, with
`harness/gateway/cafe/runtime.js` as its `window.claude` (`catioGateway: true`, so the page's `VIA_GATEWAY` mode is
honest about what only claude.ai can do). Its data lives in the gateway (`docs` in the house), apart from the
artifact's: the two copies don't share changes. Its art is uploaded with `cafe/move-in.py` and served only to her,
signed in: never commit it, never serve it without the sign-in. A change to the page reaches both: the artifact by a
publish, the gateway by a merge. Check gateway mode with `?via=gateway` in the stub.

## Live sessions

The page calls `list_sessions` (limit 50) through the `mcp` capability as the viewer. Its write
tools are the harness's, above, and only ever run on her click or drop. Don't add `mine: true`: a page has no calling session, and that flag can
error without one. Every connector error code has its own message in `problem()`.

claude.ai can refuse the page's read (`approval_required`: the tool asks before every call,
which a page can't do; `blocked_by_policy`). Claude Code Remote is a built-in connector: it is
**not** in her Customize → Connectors list, so there is no `list_sessions` switch for her to set
(checked against her settings, September 2026). Don't send her looking for one. The page shows
`snapshot/sessions`. To refresh it, call `list_sessions` (limit 50) from a session, save the
result, run
`python3 catio/tools/save-sessions.py <result>.json`, and write `catio/data/sessions.json`'s
object to `snapshot/sessions` with `ArtifactData` (`set`, pinned with `if_version`). The script
keeps only what the page reads, and accepts the result as the tool returns it
(wrapped in `ccr`).

`python3 catio/tools/digest.py [cats/*.json sessions/*.json]` compiles that copy, adopted chats exported from `cats` and her moves from `sessions`,
into `catio/data/digest.md` and `digest.json`: per project, what needs her, what to review, and what to tidy
(stale asks, empty reviews, untitled sessions, reruns, duplicates, misfiled repos). Both are gitignored: never
commit them.

A Routine, "Refresh the catio", does this every two hours from 07:59 to 19:59 Paris time. It fires
into the Claude Code session it was created from, not a fresh one: a fresh routine session has
neither `list_sessions` nor `ArtifactData`, so it can't refresh anything (tried September 2026).

## Running on localhost

`python3 catio/tools/bundle.py` builds `catio/dist/catio-local/` and `catio-local.zip`: the page
wrapped in a complete HTML document, all the art (licensed included), `data/rooms.json` and
`data/sessions.json`, with a `HOW-TO-RUN.txt`. Any static server runs it (VS Code Live Server,
`python -m http.server`, `php -S localhost:8000`); there is no PHP and no server code. Send her
the zip with `SendUserFile`; Claude can't reach her USB stick.

With no `window.claude` the page uses `localRuntime()`: a database in `localStorage`
(`catio.local.db`), seeded with the rooms from `data/rooms.json` on first run, and
`snapshot/sessions` from `data/sessions.json` on every load. There is no mcp there, so the cats
are the saved copy.

- `catio/data/rooms.json` mirrors the artifact's `rooms`; keep it in step when rooms change.
- `catio/data/sessions.json` and `catio/dist/` are gitignored. Her session titles and the
  licensed art are in them: **never commit either**.

## The app draft

`catio-app/` is a **draft** of the café as a native C++ app for a phone (`docs/mobile-app.md`), written
3 October. It is not an app: the nine headers in `catio-app/include/catio/` are declarations, `src/` is
empty, and `android/` and `ios/` have never been configured. What builds is the header check,
`cmake -S catio-app -B build && cmake --build build`, which needs neither SDL nor libcurl because no
public header names a type from either.

Two things to keep if you touch it:

- **The plan is generated.** `write_page()` in `catio/tools/furniture.py` writes the page's `MANOR`
  block **and** `catio-app/generated/manor.json` from one `page_data()` call, so the page and the app
  can never hold different plans. Never hand-copy those numbers into C++. `manor.json` is committed:
  generated from committed code, and no art in it.
- **The app ships with no pack art, and never will.** It fetches the art from the gateway's
  `GET /art/*` on first run, behind her sign-in, into app-private storage. An APK or IPA on a store
  would redistribute packs that forbid it, so a store release waits for her own art
  (`docs/drawing-plan.md`). Nothing under `catio-app/` is ever a place to put a pack file.

## Checking a change

Look first, test second. A test rewritten to match the code only proves the two agree; looking is what
proves the page does what she asked. In this order:

1. **Change it.** Art too: re-run `build-art.py` (or `furniture.py`).
2. **Look at it before touching a test.** `sh catio/test/run.sh look kitchen study` (`ground`, `upper` or any
   room key; a few seconds) writes `catio/test/.look/<name>.png`: the page in the publish skeleton, with the
   stub's invented cats. Open each and hold it against her words, one ask at a time ("no z Z": find a
   sleeping cat). A sprite sheet isn't in the DOM and no test can see it: open the sheet too. Not what she
   asked for? Back to 1.
3. **Run the test unchanged:** `sh catio/test/run.sh` (about two minutes). Every failure should be something
   she asked to change. One she didn't is a regression: fix the page, not the test.
   **The suite needs `art/licensed/`.** It is gitignored, so a fresh clone or cloud session hasn't got it,
   and without it the page correctly draws its no-art warning on the status sign: the check that wants no
   warning sign then fails, and that is the missing art, not the page. `run.sh` says so when it starts.
   Get the art back the two ways under "Republishing" before trusting a red run.
4. **Rewrite only those checks, from her words:** what must be true now, not which class names went away
   (`#cats .cat > :not(.spr)`, not a list of deleted classes). Then the whole suite: all checks must pass.

**Never rewrite a test because it fails.** A failing check means the page is wrong, not the check. The only
checks that change are the ones her ask contradicts, named before the suite runs (step 2), from her words.
A check nobody planned to change that fails after a change is a regression: fix the page. Never edit a check
to match the code, loosen a selector or a count to make it pass, or delete or skip one. The same holds for
`furniture.check()`, the harness tests and the gateway tests.

The suite loads the page in the same skeleton the Artifact tool publishes, against `runtime-stub.js`
(an in-memory db with live snapshots and the real path rules, plus a sessions feed the test
changes as it runs), and walks: adopting a chat, through in progress and done, to letting it
go; a session going blocked, working, finished, archived and failed; renaming and moving a
cat; a filing cabinet and a project's look; renaming rooms; the room and cat menus by hover,
keyboard and touch; the saved copy when settings block the live read; the no-connector,
no-storage, view-only and phone cases; a copy with none of the licensed art (`.page-noart.html`,
as anyone else's clone is, whether or not this checkout has the packs); and the localhost bundle,
served on port 8791 with its own `data/`. All checks must pass.

Its example data is invented. Never paste her real session list into the stub or the page.

After publishing, read back every art file you changed (`Artifact` read with `path`) and look at it: a
republish keeps the old copy of any file it wasn't given. Then check the real database with `ArtifactData`:
list `rooms`, and create, update and delete one probe document in `cats` the way the page does.
