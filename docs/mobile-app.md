# The KittyChat Café on a phone: a C++ app, drafted

The design for the café as a C++ app on a phone, and the first of it built. The code is
[`catio-app/`](../catio-app/): nine headers, a working core that draws the manor, the floor plan
generated into `catio-app/generated/manor.json`, and build files for three platforms. **It is not an
app yet** -- there is no window loop, no interface and no network -- and nothing here has run on a phone.
"Where it stands", at the end, says exactly what exists.

Drafted 3 October 2026. Her four choices before it was written: a design and stubs rather than a
prototype, SDL3 with libcurl, the gateway as the only backend, and all three platforms scaffolded. The
same evening she asked for it to be built, first milestone "it opens a window".

## In plain words

The café is one web page. On a laptop it is lovely. On a phone it is not, and her own audit says why.

> **On a phone, the house is tiny, has no room names, and cats can't be tapped.** At 390×844 the house
> fills about an eighth of the screen… Measured tap targets: cats 6–12px, rooms 38–92px… `--u` is 1px
> on phones, so a `.btn` is 32px tall. The Sound switch is 22px.
>
> — `docs/from-the-litterbox.md`, her UI/UX audit

A native app is one way to fix that, and this is what it would take.

## First, the cheaper answer

The gateway already serves the whole unmodified page at its own address behind her password. A native
shell with a web view pointed at it would be a phone app this week, for almost no code — and it would
not fix any of the above, because that is the page's CSS, not its container. A C++ app can fix it, at
the price of a second implementation of a 4,248-line page.

That price is the first hard problem below, and the reason the recommendation there is to build
deliberately less. Everything else in this document assumes she wants the native one.

## What the app talks to

Only her gateway (`harness/gateway/`), as the owner, over HTTPS. It cannot take the path claude.ai
takes: the Worker's client registration refuses any redirect URI outside `claude.ai` and `claude.com`
(`harness/gateway/src/index.js`), so **no native client can ever hold an OAuth token for this gateway.**
The owner's path is her password and the cookie, which is what the café page on the gateway's own
address already uses.

| | |
|---|---|
| `POST /login` — form `user`, `password` | → `__Host-catio`, 64 hex, Secure, HttpOnly, SameSite=Strict, 30 days |
| `GET /api/db` | → `{"docs": {"<collection>/<id>": {…}}}` |
| `PUT\|PATCH\|DELETE /api/db/<collection>/<id>` | `{"data": {…}}`, ≤1 MB |
| `POST /api/tools/<tool>` | the arguments object → the tool's result, run as `owner` |
| `POST /api/files`, `DELETE /api/files/<id>` | the brain's files, ≤20 MB |
| `GET /art/<path>` | the packs' bytes |

Errors are `{code, error}`. `401 {code:"signed_out"}` means sign in again. Writes need the header
`X-Catio: 1` and no cross-origin `Origin`; a native client sends no `Origin` at all, so `fromCafe()`
(`harness/gateway/src/cafe.js`) passes. There is no CORS configuration to fight — the gateway blocks
browsers positively instead, which a native client simply is not.

`/api/tools/*` reaches all fourteen tools as owner, a superset of what `/mcp` allows. One of them is
destructive: `inbox` with `mark: true` advances `handedNotes` and stamps files as handed, so the app
passes `mark` only when it will really deliver what it takes.

### `GET /api/db` is not the whole house

This is the thing to get right before writing any code. `House.docs()` returns **only** the `docs`
table (`harness/gateway/src/house.js:488`). **The cats are not documents.** `list_agents` reads the
`agents` table, and joins the `files` and `notes` tables for each cat's `waiting` count and its latest
`said` (`:127`). Dropped files and conversations are those same tables, reached through `drop_file`,
`comment`, `comments` and `inbox`.

So **start-up is two reads, not one**: `GET /api/db` and `POST /api/tools/list_agents`, together.

The app reads these collections: `house`, `rooms`, `cats`, `projects`, `queens`, `quizzes`, `routines`,
`graphs`, `dashboard`, `rules`, `audits`, `layouts`. It reads and writes **none** of `snapshot/sessions`,
`sessions/<id>`, `notes/<id>`, `brain/<id>` or `outbox/<id>`: those are claude.ai's write path, keyed off
`list_sessions` ids a native client never sees.

### Live, or polled: polled

The gateway pushes changes over `GET /ws` — `{type:"doc"}`, `{type:"agents"}`, `{type:"queen"}` — and a
native client could take the same socket, provided it sends an `Origin` exactly equal to the gateway's
origin, which `/ws` requires and rejects anything else for.

**v1 should not.** libcurl's WebSocket API is still experimental, opt-in at build time, and curl's own
documentation discourages it in production; and a phone drops the socket every time the app goes to the
background, so the reconnect logic is the feature, not the socket. So v1 polls, at the page's own
cadences: `list_agents` every 30 s, and `comments` every 5 s while the queen's card is open — which is
exactly what the page in claude.ai already does. The one thing lost is watching the queen type; her
answer arrives whole instead.

### What the app cannot do, and says so

The page has an honesty mode for the gateway's address (`VIA_GATEWAY`), because some things only
claude.ai can do. A native app is in that mode permanently, and the list is short, because without
`list_sessions` there is no live-session machinery to apologise for at all — no blocked live read, no
saved copy, none of the eleven connector error codes in `problem()`.

What is simply absent: her claude.ai session list; posting into a session that does not report to the
gateway; starting, archiving or retitling one; and the LLM file sorter (`use("sample")` is null outside
claude.ai), so a dropped file the keywords cannot place goes to the brain's tray.

Those menu items are **drawn, disabled, with the reason under them** — the page's rule, and
`ui::cannot()` is the whole of it: one table of six sentences, not a mode.

## The art, and the licence wall

**The app ships with no pack art, and none of it is ever committed.**

`catio/art/licensed/` is gitignored because every pack but Cosy Cabin forbids redistribution. Game UI
Pastel adds *no uploading to a repository*, *no redistribution even modified*, and asks that its files
not be easily extractable.

**An APK or an IPA on a store would redistribute the lot.** So:

- the app fetches the art from `GET /art/*` on first run, behind her own sign-in, into app-private
  storage — the same footing as the café the gateway already serves her;
- on Android that means `allowBackup="false"` and no external storage, both already in the manifest on
  this branch;
- a **store release needs her own art first.** `docs/drawing-plan.md` is already that plan. Until then
  the only honest release is a build she sideloads herself.

Be straight about the limit: cached PNGs in app-private storage satisfy "never without the sign-in" but
are no harder to extract than the artifact's are. That is accepted and stated, not solved.

`GET /art/*` answers `private, max-age=86400` with **no `ETag` and no `Last-Modified`**
(`harness/gateway/src/cafe.js`), so there is nothing to revalidate against, and the `ART` path filter
(`:18`) only accepts `.png` and `.ttf`, so a manifest cannot even be uploaded. The app therefore
compiles the file list in (`art::files()`, the same list CLAUDE.md's publish instructions carry),
fetches what the cache lacks, and otherwise never asks again. "Fetch the art again" in the House menu
is the way back. Two small gateway additions would improve this later — an `ETag` from the KV value, and
`art/manifest.json` allowed through `ART` — and neither is worth blocking on.

### And one font, committed

`sprout.ttf` is licensed and comes down with the art. Nunito, the page's body font, comes off Google
Fonts over the network. So before it has signed in and fetched anything, **the app has nothing to draw a
single letter with** — including on the sign-in screen that does the fetching, and on any error it has
to show.

One OFL font belongs in the binary: **Nunito-Regular.ttf**, whose licence allows redistribution and
which is already the page's `--body`. See `catio-app/assets/README.md`.

### Credits are a condition of use, not polish

SC_siosio's licence requires the credit "Game UI Pack created by SC_siosio", word for word, and says it
must not be intentionally hidden. The page had this wrong on phones once — `.credits { display: none }`
under 560px, finding 6 of `docs/audit-2026-10-01.md` — and fixed it by putting the credits at the foot
of the House menu (`catio/index.html:1846`), because a phone has no room for them anywhere else.

The app has no footer at all, so **Credits is a House-menu item from the first frame.** The words are
`catio/art/CREDITS.md`.

## The phone design

Her three fixes are the starting point, not a backlog. Each names code that already exists:

| Her fix | What it uses today |
|---|---|
| Open zoomed into the most urgent room | `labelRooms()` already works out which (`catio/index.html:1581`) |
| Swipe left and right between rooms | `NEXT`, the 45° room-to-room map (`:666`) |
| Fit the camera to the house, not the grounds | `PLAN` (`:3029`) instead of `WHOLE` (`:636`) |
| Nothing under 44px | `ui::kTouch`, applied in `view::pick` before any test |

And one the native build can do that the page cannot: **one art pixel is a whole number of screen
pixels.** The page's camera scale is a float, which is why "zoom that lands on crisp pixel sizes" is
still open in `docs/camera-and-minimap.md`. Here `Cam::u` is an integer, zoom steps are `u ± 1`, panning
rounds to whole device pixels, and the pixel font is rasterised once at 18px and blitted at `× u` —
never reopened at `18 × u`, which re-hints the outlines and breaks the one thing her audit called good:
*"Pixel font kept at 18px"*.

That has a consequence worth stating: the whole-house view and a crisp phone screen are not compatible.
The grounds are 960×576 art pixels; on a 1170-pixel-wide phone the only whole scale that fits is `u = 1`,
one art pixel per device pixel, which is precisely the "house is an eighth of the screen" complaint
restated in physical millimetres. **So on a phone there is no whole-house camera at all.** The floor is
`u = 2`, the app opens on the urgent room, swipe follows `NEXT` — and the *minimap* is the whole house,
which costs nothing, because it is already drawn from room boxes rather than from the art.

Her own fix, arrived at from the other end.

### Two packs, two kinds of smoothing

The Sprout Lands pieces are pixel art and draw nearest-neighbour. The Game UI Pastel map panel is
smooth and must scale with ordinary smoothing. Never both in one panel.

SDL3 draws a 9-slice directly — `SDL_RenderTexture9Grid`, since 3.2.0 — which is why this stack suits
the job: a panel is one call, not nine. Reading the page's `border-image` rules off
`catio/index.html` turns up a distinction worth keeping:

| Panel | slice / border width | on screen |
|---|---|---|
| `ui/panel.png` | `6 fill / 6u` | corner = 6 × `u`, grows with the zoom |
| `ui/button.png` | `4 4 6 4 fill / 4u 4u 6u` | same |
| `ui/corners.png` | `9 8 / 9px 8px` | **fixed** — the selection brackets stay one size at any zoom |
| `pastel/panel.png` | `28 fill / 14px` | **fixed**, scale 0.5 |
| `pastel/button.png` | `20 22 24 fill / 10px 11px 12px` | **fixed**, scale 0.5 |

Sprout Lands scales with `--u`; Pastel and the brackets are fixed pixels — deliberately, since CLAUDE.md
says the brackets "stay one size on screen at any zoom". `draw::Panel::scales_with_u` carries it.

One caveat: `SDL_RenderTexture9Grid` takes a *single* `scale`, which works only because each of these
panels has one slice-to-width ratio throughout. A panel that ever needed two different ratios could not
use the call.

## The modules

Nine headers, in `catio-app/include/catio/`. **No SDL, curl or JSON type appears in a public header** —
they carry their own `Rect`/`Colour` and opaque handles. That is the cleaner seam (it is what lets the
net layer differ per platform), and it is what makes this branch verifiable: every header compiles
alone, with neither library installed.

| Header | Its one job |
|---|---|
| `net.h` | Every byte to and from the gateway. Bodies are strings; no JSON, no SDL. |
| `house.h` | The documents and the cats, and every derivation over them — `allCats`, `roomFor`, who really needs her. Drivable from a JSON string in a test. |
| `manor.h` | The generated floor plan, and the geometry `GEOM`, `NEXT`, `LINE` and `freeFloor` derive from it. |
| `art.h` | The packs: the cache, what is missing, textures. Does not fetch. |
| `draw.h` | Putting pixels down: 9-slice panels, sprite cells, the pixel font. Does not know what a cat is. |
| `view.h` | The camera, where every cat stands this frame, and what is under her finger. Computes; never draws. |
| `ui.h` | The hover line, the one menu shape, the cards, the map panel — and the words she reads. |
| `app.h` | The frame loop, and the one function where a press becomes a write. |
| `voice.h` | The queen's voice. Declared; **not in v1** (see below). |

Dependencies run one way, no cycles:

```
manor.h          net.h           art.h
   |          (curl only)     (no net.h)
   |               |              |
house.h            |           draw.h
   \               |              |
    `--- view.h ---+--- ui.h -----'
              \     /
               app.h
```

`house.h` must never include SDL or `net.h`. `net.h` must never include JSON or `house.h`. `art.h` must
never include `net.h` — it reports what is missing and `app.h` does the fetching, so the cache is
testable over a directory of files. `draw.h` must never include `house.h` or `view.h`.

Three things are deliberately *not* modules. There is no `platform.h`: SDL3 already is the platform
layer (its per-app directory, opening a link, the content scale, the foreground event), and a header
wrapping those earns nothing. There is no `ws.h`: v1 polls. There is no `sessions.h`: there are no
claude.ai sessions here.

### The floor plan is generated, never copied

`MANOR` is a generated literal inside `catio/index.html`, written by `write_page()` in
`catio/tools/furniture.py` from `page_data()`. A hand-copy of those numbers in C++ would be the third
copy of one truth, and the one that goes stale.

So `write_page()` now writes **both** outputs from one `page_data()` call: the page's block, and
`catio-app/generated/manor.json`. `build-art.py` already calls `write_page()`, so both paths emit it and
there is no second call site to forget. `manor.json` is committed: it is generated from committed code
and holds no art.

The *derivation* stays in `manor.h`, not in the generator. Python already has twins of those rules for
`furniture.check()`; emitting them as data too would make a third copy.

## A frame, start to finish

**Start.** One window, one renderer, the art cache over the platform's per-app directory, the net
thread over the baked-in gateway origin and a cookie jar beside the cache. The plan loads from
`generated/manor.json`. If the cookie jar still holds a live `__Host-catio`, skip the sign-in.

**Sign in.** Drawn in the bundled font and plain rectangles — no pack art exists yet. `POST /login`;
`401` says "that handle and password aren't right", `429` says she is locked out for a quarter of an
hour.

**First read.** `GET /api/db` and `list_agents` go out together. A `rooms` collection that arrives empty
is a café nobody has opened: the wizard, not the house.

**The art.** `art::missing()` queues one fetch per file, house and meadow first, and the stage says
"Fetching the café's art… (n of m)" while they land. The house fills in piece by piece. A failure shows
the code and a Retry — *not* the page's no-art message, which tells the reader to buy the packs and run
`build-art.py`, and is the wrong advice on a phone that can simply fetch.

**Every frame.** Pump the window's events → drain the net → build the scene from the house → settle the
walks → draw in the page's order (meadow, the floor's art, rugs, wall pieces, then floor pieces and cats
interleaved by bottom edge, then the upper floor lifted) → the interface over it. `list_agents` every
30 s, and on coming back to the foreground.

**A tap on a cat.** Hit-test cats before rooms, every box grown to 44px first → its menu opens beside
it: the name, one line (its mood, then its ask or its waiting files), then the actions, each absent one
disabled with its reason. A press returns an action to the one function that writes: a `comment`, a
`manage`, a `patch`. Then refresh.

Nothing is ever drawn on the cats. No letters, no counts, no crowns, no "z Z".

## The four hard problems

**1. One page, two implementations.** The café changes most days. Every change would have to be made
twice, or the app falls behind within a week — and the page is the one that has her attention.

*Recommendation: the app covers deliberately less, and says so.* The map, the cats, who needs her, the
queen's thread and her homework. Not Build mode, not Project maps, not the brain's sorter, not the
onboarding wizard beyond detecting that it is needed. It is the phone view of the café, not a port of
it. If that is not worth having, this is the point to stop — and stopping here costs only this branch.

**2. HTTPS on a phone.** Her chosen stack says libcurl, and there is no system libcurl on the Android
NDK or on iOS. Either cross-build curl and a TLS library for three ABIs and two Apple slices, or give
`net.h` a second and third body: `net_android.cpp` over `HttpsURLConnection` through JNI (which brings
the system trust store and a cookie store with it, in about 150 lines) and `net_apple.cpp` over
`NSURLSession`.

*Recommendation: the second.* It is why `net.h` names no curl type. This does not change her stack
choice; it narrows where curl runs to the desktop build.

**3. The cookie is a 30-day bearer of full owner rights, and SDL has nowhere safe to keep it.** It
authorises every write, every tool and every file. Android wants the Keystore, iOS the Keychain; both
are platform code SDL does not reach.

*Recommendation for v1:* the cookie jar in the per-app directory, with `allowBackup="false"` on Android
and complete file protection on iOS, a Sign out that deletes the file, and the trade-off written down.
Do not build a Keystore bridge on a draft branch — and do not put this app on anyone's phone but hers
until one exists.

**4. Typing, and the queen's voice.** A scrolling conversation with an on-screen keyboard is the
fiddliest thing in the whole app, and `speechSynthesis` does not exist outside a browser: natively it is
three backends, a JNI bridge and an audio-focus policy.

*Recommendation:* SDL3's own text-input API for the keyboard, and **v1 ships silent.** Her card is
perfectly readable without a voice, nothing else needs any of it, and `voice.h` declares the interface
so the switch can be in the card from the start. The backends come behind `-DCATIO_TTS=ON` when the rest
works.

## Where it stands

### Built: the core, and the first frame

The first milestone was "it opens a window". There is no display in the cloud session that built it,
so it was met the way CLAUDE.md asks of the page: draw it, then look at it. `catio_look` renders a floor
or a room to a PNG with no window and no GPU -- SDL's software renderer over a plain surface -- and
every frame was looked at against the page's own.

| | |
|---|---|
| `src/manor.cpp` | the plan, and `GEOM`, `stationsOf`, `freeFloor`, `LINE`, `NEXT`, ported line for line |
| `src/house.cpp` | the documents and `list_agents` into rooms, cats, the queen and her homework: `catFromAgent`, `catFromAdopted`, `roomFor`, `queenMood` |
| `src/art.cpp` | the cache: surfaces, not textures, so it needs no renderer |
| `src/draw.cpp` | `SDL_RenderTexture9Grid` panels, blits, and the eight coats |
| `src/view.cpp` | the camera in whole art pixels, `render()`'s placement, and the draw list in the page's one z-order |
| `src/look.cpp` | `catio_look` |
| `test/tests.cpp` | `catio_tests`: 58 checks of the plan, the house and the draw list, with no window |

How it was checked, against things the C++ did not produce:

- **The manor matches the page pixel for pixel.** The page's own `#world`, rendered by Chromium at
  scale 1 with its cats and interface hidden, against `view::world` with nobody in it: identical on 98.4%
  of 2.2 million pixels, and the rest differ by at most 2 levels in 255 -- two renderers rounding the
  soft shadows baked into the art differently. Nothing missing, nothing misplaced.
- **The coats match Chromium byte for byte.** The page's `COATS` filter strings, pulled from
  `index.html` and rendered by Chromium, against the port of the CSS filter functions' colour matrices:
  zero difference on every opaque pixel of every coat.
- **Names and coats come from the page's own hash**, run in node; `café` names its cat Réglisse only if
  the hash walks code points as JavaScript does, not bytes.
- **The `GEOM` numbers** -- the queen's seat at (348, 370), the cabinets, the litter box, the
  fourteen places in the queue -- are the ones the page computes.
- **The layering rules** are tested without a window: a cat wins an exact tie with furniture (as
  `#cats` paints after `#props`), a piece set into a counter draws one above it, queued cats are clipped
  to their middle 44 pixels as the page's `clip-path` does, and the upper floor dims the ground at 3850
  under its own plate at 3900.

Two things the build itself settled. **SDL_image is not needed**: since 3.4 SDL's core loads and saves
PNG, and every pack file is one, so it is gone from every build file. And **SDL3 is not in Ubuntu's
packages**, so it is fetched and built from source (about 35 seconds); a headless build needs
`SDL_UNIX_CONSOLE_BUILD`, or SDL refuses to build without a windowing system.

```sh
cmake -S catio-app -B build -DCATIO_HEADERS_ONLY=OFF -DCATIO_HEADLESS=ON && cmake --build build
ctest --test-dir build
build/catio_look catio catio-app/generated/manor.json catio-app/test/fixtures ground.png ground
```

The default build is still the header check, which needs nothing installed. The frames `catio_look`
writes contain the licensed art, so `catio-app/.look/` is gitignored with the build.

### Built: the window loop and the interface

Asked for on 5 October ("draft the window loop and interface"). `catio_app` opens a window, and with no
display it draws its frames to PNGs instead (`--shot`, with `--do` to play clicks, keys and drags first), so
it was checked the same way: every frame below was set beside the page's own, rendered by Chromium from the
same skeleton the e2e test uses, at 1280×800 and at her audit's 390×844.

| | |
|---|---|
| `src/ui.cpp` | the page's `showTip()`, `roomMenu`, `houseMenu`, `pileMenu`, `queenMenu`, `catMenu`, `summary`, `queenLine`, `placeMenu`, as plain data first, then laid out in the page's CSS lengths and drawn from the packs: the brand and its badge, the sign, the screen's frame, the hover line, the menus, the map panel with its minimap and floor tabs, the credits, and the Cat card |
| `src/text.cpp` | the two fonts over SDL_ttf: `sprout.ttf` once at 18px, blitted at whole multiples; Nunito at the size it is drawn |
| `src/app.cpp` | the loop: drag (any button), wheel, pinch, + / − / 0, Shift+arrows, arrows between rooms, Page Up / Down, M, Escape; hover only on a real move; a click opens the menu, a double click looks in; and `act()`, the one place a press becomes anything |
| `src/main.cpp` | the entry, through `SDL_main.h` so the same `main` runs on a phone |
| `assets/` | Nunito at the page's three body weights (500, 700, 800), Latin-1 and the punctuation she uses, 30 KB each, with its OFL; `tools/fonts.py` makes them from one pinned commit of Google Fonts |
| `test/tests.cpp` | 96 checks now: the menus' words and shapes, the hover lines, `placeMenu`, and the House menu drawn and pressed with no window and no pack art |

What looking showed, and what was done about it:

- **The menus are the page's.** Name and badge, one line, the cats that need her (three at most), the
  queen's said note under her crown, the divider, the list with the pack's triangle on the default; the
  House menu below the whole header with the credits at its foot, word for word. The cat under the pointer
  gets the page's outline, traced round its own shape in the pack's white.
- **On a phone the app opens zoomed into the room that needs her most** -- the upset cat first -- where the
  page shows the whole house at an eighth of the screen. That is her audit's first fix, now real; the second,
  a quick sideways swipe inside a room to the room next door, is in too. The map folds to one button at the
  bottom right, its pip counting only the cats out of view, as the page's does.
- **One difference is deliberate: the camera zooms in whole art pixels.** At 1280×800 the house draws at 1×
  where the page draws it at about 1.3×, so it is smaller, and crisp. Pinch and the wheel step one whole
  pixel at a time.
- **What is not built yet says so.** Every card but the Cat card -- the queen's, the brain, the filing
  cabinet, House rules, Edit rooms, The look, Set up again, adopting a chat -- and the Sound switch are drawn,
  disabled, with "not yet" beside them; `ui::Ui::cannot()` says why. Nothing is hidden and nothing pretends.
  A click on a filing cabinet or the litter box opens its room's menu, which lists them.
- **Two bugs found by looking**, fixed: the House menu opened under the status sign (the page places it
  under the whole header), and SDL's software renderer drops a scaled blit that crosses the clip rectangle,
  so the portrait in the Cat card clips its sprite by hand.

```sh
cmake -S catio-app -B catio-app/build -DCATIO_HEADERS_ONLY=OFF -DCATIO_HEADLESS=ON && cmake --build catio-app/build
catio-app/build/catio_app --art catio --shot catio-app/.look/desk.png --size 1280x800 --do "click 554 272"
catio-app/build/catio_app --art catio --shot catio-app/.look/phone.png --size 390x844 --touch
```

Until the network code is in, the house is read from a folder (`--data`; the test's invented cats by
default), and the status sign says these are example cats, not hers.

### Not built yet

- **The net layer**: `net_curl.cpp` for a desktop, then a body per phone. It is to be tested against a
  stand-in gateway, the way `harness/test/test_queen.py` tests the queen's runner -- never against hers.
  With it come the sign-in screen, fetching the art, and the writes the menus already draw: Open this room,
  a chat's mood, renaming and moving a cat.
- **The other cards**, the queen's first; **walking** (`way_to`, `Walks`); the keyboard's focus ring (Tab);
  the meow; **the voice**.
- **The window itself has never been opened**: there is no display in the cloud session. The window's
  code -- the cursor, the events, pinch -- is compiled here with everything else but has never run; every
  pixel above went through the same drawing code in the software renderer. The first desk build with a
  windowing system (`-DCATIO_HEADLESS=OFF`, the default) is its first run.
- **`android/` and `ios/` have never been configured.** No Android SDK or NDK was in reach and no Mac
  at all. The versions in them are now SDL's real current releases; the gradle lines, plist keys and
  `.aar` filenames are still read from the documentation, not tried.

```
catio-app/
  CMakeLists.txt         the header check by default; catio_app, catio_look and catio_tests with -DCATIO_HEADERS_ONLY=OFF
  cmake/sources.cmake    the core's and the app's sources, and what is still to come
  include/catio/*.h      the nine headers; each says what of it is implemented
  src/                   the core, the interface, the loop, and catio_look
  test/                  catio_tests, and invented fixtures
  generated/manor.json   written by catio/tools/furniture.py
  assets/                the one font the app ships: Nunito, OFL
  third_party/           why nothing is vendored
  android/  ios/         never configured
  tools/                 fetch SDL's Android archives; make the fonts
docs/mobile-app.md       this
```
