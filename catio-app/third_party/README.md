# Third-party sources

Nothing is vendored, and nothing should be.

The build fetches what it needs, pinned to a release, with CMake's `FetchContent`: **SDL3** (3.4.18) and
**nlohmann/json** (3.12.0, MIT). On Android SDL3 comes from its official `.aar` instead, found by prefab.
Both licences sit fine under this repo's GPL.

There is no SDL_image: since 3.4 SDL's own core loads and saves PNG, and every pack file is a PNG. SDL_ttf
joins when there is text to draw.
