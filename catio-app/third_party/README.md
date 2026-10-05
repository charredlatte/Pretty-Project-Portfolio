# Third-party sources

Nothing is vendored, and nothing should be.

The build fetches what it needs, pinned to a release, with CMake's `FetchContent`: **SDL3** (3.4.18, zlib),
**SDL3_ttf** (3.2.2, zlib) with its own copy of **FreeType** (FreeType licence, or GPLv2) and nothing else of
its options -- no HarfBuzz, no plutosvg -- and **nlohmann/json** (3.12.0, MIT). On Android SDL3 and SDL3_ttf
come from their official `.aar`s instead, found by prefab. All of these sit fine under this repo's GPL.

There is no SDL_image: since 3.4 SDL's own core loads and saves PNG, and every pack file is a PNG.
