# Empty on purpose

This is a draft branch: `include/catio/*.h` are declarations and doc comments, and there are no bodies
yet. `../cmake/sources.cmake` already names every file that will live here, so the desktop, Android and
iOS builds cannot drift apart the moment the first one lands.

What builds today is the header self-containment check — `cmake -S catio-app -B build && cmake --build
build`, which needs neither SDL nor libcurl. See `../README.md`.
