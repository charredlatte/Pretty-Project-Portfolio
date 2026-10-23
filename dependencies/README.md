# What each part needs installed

One page, because the café is four toolchains in one repository and each declares its dependencies
somewhere else. Nothing here is a new source of truth: where a manifest already exists this file points at
it and says what it pins. The one thing it declares is the Python packages, which had no manifest at all.

| Part | What it needs | Where that is declared |
|---|---|---|
| The café page (`catio/index.html`) | **nothing.** One HTML file, no build step, no packages. It fetches Nunito and Fredoka from Google Fonts when it is online, and draws in a round font when it isn't | — |
| The art build and the landing scene (`catio/tools/`, `landing/tools/`) | **Pillow**, and **fontTools** for the pixel font's accents | [`requirements.txt`](requirements.txt), here |
| The app's font cuts (`catio-app/tools/fonts.py`) | **fontTools** | the same file |
| The harness: the hooks, the queen's runner, the MCP server and the bridge (`harness/`) | **nothing but Python 3.** Standard library only, on purpose: a cat joins from any computer without installing a thing. The runner also wants `claude` on the PATH (or `CATIO_CLAUDE`), and the hooks shell out to `git` | — |
| The litter box (`litterbox/`) | **nothing but Python 3** | — |
| The gateway (`harness/gateway/`) | **Node** and two packages: `@cloudflare/workers-oauth-provider` 1.2.1, and `wrangler` 4.146.0 for `npm test` and `npx wrangler deploy`, which brings `workerd` with it | [`harness/gateway/package.json`](../harness/gateway/package.json), pinned exactly, with `package-lock.json` beside it |
| The app (`catio-app/`) | **by default nothing**: the header check compiles each header alone. For the real build, **CMake 3.24+**, a **C++20** compiler and **libcurl** (`libcurl4-openssl-dev` on Debian and Ubuntu); CMake then fetches SDL3 `release-3.4.18`, SDL3_ttf `release-3.2.2` (with FreeType, without HarfBuzz or plutosvg) and nlohmann/json `3.12.0`. No SDL_image: SDL's own core loads PNG. `ctest`'s network test wants a Python 3 interpreter | [`catio-app/CMakeLists.txt`](../catio-app/CMakeLists.txt), and why nothing is vendored in [`catio-app/third_party/README.md`](../catio-app/third_party/README.md) |
| The page's test suite | **sh**, **Python 3**, **Node**, a **Playwright** package and a **Chromium** for it to drive, and a free port for its own server | [`CONTRIBUTING.md`](../CONTRIBUTING.md), "Running the tests", which names the three variables |
| Project maps (the `graphify` skill) | **graphify**, PyPI `graphifyy`, which the skill installs itself the first time it runs | [`harness/README.md`](../harness/README.md), "Digesting a repo: graphify" |

## The Python packages

```sh
pip install -r dependencies/requirements.txt
```

Two packages, and only tools need them: the café itself, the harness and the litter box run on a bare
Python 3. `pillow` is imported at the top of `catio/tools/build-art.py`, `manor.py`, `furniture.py` and
`landing/tools/scene.py`, so without it the art build stops on `ModuleNotFoundError: No module named 'PIL'`
before it draws anything. `fonttools` is wanted in two narrower places: the accents French names need
(`pixel_font()` in `build-art.py`, imported inside the function, so the rest of the build runs without it)
and the app's three Nunito cuts.

Neither is pinned. Nothing here calls anything that has moved in years — `Image.open`, `paste`, `crop` and
`resize`, and fontTools' subsetter and pens — so a pin would cost more than it saves. Pin one in
`requirements.txt` if a release ever breaks the art build.

## What CI installs, and what it doesn't

[`.github/workflows/tests.yml`](../.github/workflows/tests.yml) installs **nothing with pip**: the harness
suite it runs on Linux and Windows is standard library only, and the gateway suite gets `npm ci`. So the art
build, the landing scene and the page's own suite are only ever checked on a person's computer, never by CI.
A change to a tool that imports Pillow is yours to run before you push.
