# Third-party sources

Nothing is vendored, and nothing should be.

The build fetches what it needs, pinned to a release, with CMake's `FetchContent`: **SDL3** (3.4.18) and
**nlohmann/json** (3.12.0, MIT). On Android SDL3 comes from its official `.aar` instead, found by prefab.
Both licences sit fine under this repo's GPL.

There is no SDL_image: since 3.4 SDL's own core loads and saves PNG, and every pack file is a PNG. SDL_ttf
joins when there is text to draw.

## Asked and answered: tinyfiledialogs

[tinyfiledialogs](https://sourceforge.net/projects/tinyfiledialogs/) is one `.c` and one `.h` under the zlib
licence, with native open, save, folder, message, input and colour dialogs and no dependencies. LibreSprite
vendors it, so it is the obvious thing to copy in here. It does not belong in this app:

- **Its file dialogs are SDL's already.** SDL3 ships `SDL_ShowOpenFileDialog`, `SDL_ShowSaveFileDialog`,
  `SDL_ShowOpenFolderDialog` and `SDL_ShowMessageBox`. `CMakeLists.txt` already names that feature: it
  switches `SDL_DIALOG` off for the headless build. A second dialog library beside it is the duplication
  the audits exist to find.
- **It has no phone.** Windows, macOS, Linux and the BSDs only. This app is for a phone first, so on the
  target platform it does nothing at all.
- **It works by building a command line.** On macOS and Linux it shells out to `osascript`, `zenity`,
  `kdialog` and friends. Any text the café would put in a title or a message -- a cat's name, a file name,
  a note the queen wrote -- is data an agent's key can write. That is the wrong place for it.

The one thing it has that SDL does not is `tinyfd_colorChooser`, and that only matters if The look ever
reaches this app (`docs/mobile-app.md`, "Not built yet").
