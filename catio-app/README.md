# The KittyChat Café as a native app — a draft

A sketch of the café as a C++ app for a phone, for her to judge. **It is not an app yet:** the headers
are declarations, `src/` is empty, and nothing here runs.

The case for it, and the whole design, is **[`docs/mobile-app.md`](../docs/mobile-app.md)**. Read that
first; this file is only how to poke at what is here.

## What actually works today

The one thing a declaration-only branch can honestly verify — that every header is self-contained,
real C++20, and free of SDL and libcurl:

```sh
cmake -S catio-app -B build && cmake --build build
```

That configures and compiles with neither library installed, because the public headers name no type
from either (they carry their own `Rect`/`Colour` and opaque handles). It is also the seam that lets the
net layer be libcurl on a desktop and the platform's own HTTPS on a phone.

The floor plan is generated, not written here:

```sh
python3 catio/tools/furniture.py        # writes the page's MANOR block AND generated/manor.json
```

## What does not work, and has never been tried

- **The app.** `-DCATIO_HEADERS_ONLY=OFF` wants `src/*.cpp`, which do not exist.
- **Android** (`android/`). Written from SDL's documentation. No Android SDK or NDK was anywhere near
  the session that wrote it, so no version, coordinate or gradle line here has been configured once.
  `tools/fetch-sdl-android.sh` has never been run.
- **iOS** (`ios/`). The same, more so: there is no Mac in this picture at all.

## The art is not here, and must never be

Every pack but Cosy Cabin forbids redistribution, and Game UI Pastel adds "no uploading to a
repository". The app ships with **no** pack art and fetches it from the gateway's `GET /art/*` on first
run, behind her own sign-in, into app-private storage. An APK or IPA on a store would redistribute the
lot; a store release needs her own art first (`docs/drawing-plan.md`). See `include/catio/art.h`.

## The tree

```
CMakeLists.txt        the header check today, the app once src/ fills in
cmake/sources.cmake   the translation units, shared by all three builds
include/catio/        the nine headers — the design, in C++
generated/manor.json  the floor plan, written by catio/tools/furniture.py
src/                  empty
assets/               the one OFL font to commit, and why
third_party/          one JSON header, when something needs it
android/  ios/        never configured
tools/                fetch SDL's Android archives
```
