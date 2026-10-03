# Third-party sources

Empty in this draft, and meant to stay nearly so.

The app needs **one** library the standard library does not give it: a JSON reader, for `GET /api/db`,
the tool replies and `generated/manor.json`. A single-header one (nlohmann/json, MIT) vendored here is
the laziest thing that works, and MIT sits fine under this repo's GPL.

It is not vendored yet because nothing parses JSON yet. Twenty-odd thousand lines of someone else's
header in a branch with no code to call it is exactly the kind of thing the repo's audits delete.

Everything else the app needs is SDL3 (window, input, 2D renderer, 9-grid panels, the per-app directory,
opening a link, the on-screen keyboard), its image and ttf companions, and one HTTPS client per
platform. Those are found by the build, not vendored.
