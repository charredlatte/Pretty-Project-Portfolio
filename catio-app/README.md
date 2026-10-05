# The KittyChat Café as a native app

The café as a C++ app for a phone. **It is not an app yet**: the core is built -- the floor plan, the
house, the art, drawing and the view -- and it draws the manor; the window loop, the interface and the
network are still to come. Nothing here has run on a phone.

The case for it, the whole design, and exactly where it stands are in
**[`docs/mobile-app.md`](../docs/mobile-app.md)**. This file is how to poke at it.

## Build it

The default needs nothing installed. It compiles each header alone, which proves every one is
self-contained C++20 -- possible because no public header names an SDL, curl or JSON type:

```sh
cmake -S catio-app -B build && cmake --build build
```

The core for real fetches SDL3 and nlohmann/json and builds them from source (SDL takes about 35 s).
`CATIO_HEADLESS` builds SDL with no windowing system -- the software renderer only -- which is what a
cloud session or CI wants:

```sh
cmake -S catio-app -B catio-app/build -DCATIO_HEADERS_ONLY=OFF -DCATIO_HEADLESS=ON
cmake --build catio-app/build
ctest --test-dir catio-app/build        # catio_tests: the plan, the house and the draw list, no window
```

## Look at it

`catio_look` draws a floor, or one room, to a PNG -- no window, no GPU:

```sh
catio-app/build/catio_look catio catio-app/generated/manor.json catio-app/test/fixtures \
    catio-app/.look/ground.png ground          # or upper, or a room key: hall, study, brain…
```

It reads the art from `catio/art/`, so it needs `catio/art/licensed/` -- gitignored, and fetched back
from the artifact as CLAUDE.md's "Republishing" says. Without it the house is missing and says which
files. **The frames it writes contain the licensed art**, which is why `catio-app/.look/` is gitignored:
never commit one. The cats are the invented ones in `test/fixtures/`, never her real data.

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
CMakeLists.txt        the header check by default; the core, catio_look and catio_tests with -DCATIO_HEADERS_ONLY=OFF
cmake/sources.cmake   the core's sources, and the app's still to come
include/catio/        the nine headers; each says what of it is implemented
src/                  the core, and catio_look
test/                 catio_tests, and invented fixtures
generated/manor.json  the floor plan, written by catio/tools/furniture.py
assets/               the one OFL font to commit, and why
third_party/          why nothing is vendored
android/  ios/        never configured
tools/                fetch SDL's Android archives
```
