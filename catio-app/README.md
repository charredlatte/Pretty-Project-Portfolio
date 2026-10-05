# The KittyChat Café as a native app

The café as a C++ app for a phone. **It is a draft**: the core is built -- the floor plan, the house, the
art, drawing and the view -- and so are the window loop and the interface: the brand, the hover line, the
menus, the map panel and the Cat card, drawn from the packs as the page draws them. The network is still to
come, so it reads the house from a folder. Nothing here has run on a phone.

The case for it, the whole design, and exactly where it stands are in
**[`docs/mobile-app.md`](../docs/mobile-app.md)**. This file is how to poke at it.

## Build it

The default needs nothing installed. It compiles each header alone, which proves every one is
self-contained C++20 -- possible because no public header names an SDL, curl or JSON type:

```sh
cmake -S catio-app -B build && cmake --build build
```

The app for real fetches SDL3, SDL3_ttf and nlohmann/json and builds them from source (about a minute).
`CATIO_HEADLESS` builds SDL with no windowing system -- the software renderer only -- which is what a
cloud session or CI wants; `catio_app` then only draws to PNGs:

```sh
cmake -S catio-app -B catio-app/build -DCATIO_HEADERS_ONLY=OFF -DCATIO_HEADLESS=ON
cmake --build catio-app/build
ctest --test-dir catio-app/build        # catio_tests: the plan, the house, the view and the interface
```

## Run it, or look at it

On a desk with a windowing system, leave out `CATIO_HEADLESS` and run the window:

```sh
catio-app/build/catio_app --art catio        # the page's folder, for its art/
```

Anywhere, `--shot` draws a frame to a PNG with no window and no GPU, after playing `--do`'s steps (CSS
pixels; `include/catio/app.h` lists them):

```sh
catio-app/build/catio_app --art catio --shot catio-app/.look/desk.png --size 1280x800 --do "click 554 272"
catio-app/build/catio_app --art catio --shot catio-app/.look/phone.png --size 390x844 --touch
catio-app/build/catio_look catio catio-app/generated/manor.json catio-app/test/fixtures \
    catio-app/.look/ground.png ground          # the floor alone: or upper, or a room key
```

Both read the art from `catio/art/`, so they need `catio/art/licensed/` -- gitignored, and fetched back
from the artifact as CLAUDE.md's "Republishing" says. Without it the house is missing and the sign says
so. **The frames contain the licensed art**, which is why `catio-app/.look/` is gitignored: never commit
one. The cats are the invented ones in `test/fixtures/` (`--data` names another folder), never her real
data.

## The art is not here, and must never be

Every pack but Cosy Cabin forbids redistribution, and Game UI Pastel adds "no uploading to a
repository". The app ships with **no** pack art and fetches it from the gateway's `GET /art/*` on first
run, behind her own sign-in, into app-private storage. An APK or IPA on a store would redistribute the
lot; a store release needs her own art first (`docs/drawing-plan.md`). See `include/catio/art.h`.

## The plan is generated

`catio/tools/furniture.py` writes `generated/manor.json` and the page's `MANOR` block from one call, so
the page and the app cannot hold different plans. Never hand-copy those numbers here.

## The tree

```
CMakeLists.txt        the header check by default; catio_app, catio_look and catio_tests with -DCATIO_HEADERS_ONLY=OFF
cmake/sources.cmake   the core's and the app's sources, and what is still to come
include/catio/        the nine headers; each says what of it is implemented
src/                  the core, the interface (ui.cpp, text.cpp), the loop (app.cpp, main.cpp), catio_look
test/                 catio_tests, and invented fixtures
generated/manor.json  the floor plan, written by catio/tools/furniture.py
assets/               the one font the app ships: Nunito, OFL
third_party/          why nothing is vendored
android/  ios/        never configured
tools/                fetch SDL's Android archives; make the fonts
```
