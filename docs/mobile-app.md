# The KittyChat Café on a phone: a C++ app, drafted

A sketch for her to judge, not an app to run. The code on this branch is
[`catio-app/`](../catio-app/): nine headers of declarations, the floor plan generated into
`catio-app/generated/manor.json`, and build files for three platforms. Nothing compiles into an app
yet, and nothing here has been run on a phone.

Drafted 3 October 2026. Her four choices before it was written: a design and stubs rather than a
prototype, SDL3 with libcurl, the gateway as the only backend, and all three platforms scaffolded.

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

## What is on this branch

```
catio-app/
  CMakeLists.txt         the header check today; the app at -DCATIO_HEADERS_ONLY=OFF
  cmake/sources.cmake    the translation units, shared by all three builds
  include/catio/*.h      the nine headers above
  generated/manor.json   written by catio/tools/furniture.py
  src/                   empty
  assets/  third_party/  the one font to commit, the one library to vendor, and why
  android/  ios/         never configured
  tools/                 fetch SDL's Android archives
docs/mobile-app.md       this
```

Verified: the nine headers each compile alone as C++20 with neither SDL nor curl installed, and
`cmake -S catio-app -B build && cmake --build build` configures and builds that check. `manor.json`
parses and is identical to the page's `MANOR` block, `furniture.check()` is empty, and `index.html` is
untouched by the new writer.

Not verified, and not pretended: **`android/` and `ios/` have never been configured.** No Android SDK or
NDK was in reach, and no Mac at all. Both were written from the documentation. Treat every version,
coordinate and gradle line in them as a guess until one of them builds on her machine.
