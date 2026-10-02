# Onboarding: the wireframes

The first run of someone's own KittyChat Café, drawn as basic wireframes for Charlotte's review before anything
is built. The Figma file is "KittyChat Café · Onboarding" in her drafts
(https://www.figma.com/design/wDi412a6ixNljNqVXXWWsG).

Nothing in it is art: plain grey boxes and Figma's Inter. Nothing from `catio/data/`, the packs or any kit.

## The frames, left to right

1. **Layout.** The shell: the house filling the screen, the brand and House button top left, the map panel top
   right. The wizard sits centred over the dimmed house.
2. **Welcome.** Name your café.
3. **Rooms.** How many rooms (− N +). The manor's ten rooms as a grid: N open from the front of the house, the rest
   closed, and a name field per open room. The house itself never changes: a closed room is dimmed and gets no
   cats, and opens later under Edit rooms.
4. **GitHub.** Connect GitHub, then each repository with the room it lives in. **3b** is the not-connected state.
5. **Sessions.** What `list_sessions` found. **4b** is the blocked state, with the saved copy in one line.
6. **Litter box.** What it is and a drop zone. (The frame's switch for holding pull requests was dropped in
   the build: holding is the merging rule's doing, `harness/README.md`, not a page setting.)
7. **How it works.** The harness in five plain lines: sessions are cats, house rules are locks (hooks), skills
   are training, messages wait on the mat, the litter box holds loose ends.
8. **Done.** The summary and "Open the doors".

Every wizard frame has the same skeleton: step dots, title, content, Back and Next.

## Redrawing

`frames.js` is the whole drawing, in Figma's Plugin API. Run it with the Figma MCP server's `use_figma` on the
file, or in Figma desktop as a development plugin (Plugins → Development → Import plugin from manifest, with a
manifest whose `main` is `frames.js`). Each run draws a fresh row of frames.

Mind the quota: a Starter plan with a View seat gets six MCP calls a month.

## Decided, and built

- The litter box is **both**: the brain's unsorted tray in the page, and `litterbox/` in a clone (Charlotte,
  2 October 2026).
- The build is in the page (`openSetup()` in `catio/index.html`, `rooms/<k>.closed`, `list_repos` in the
  capabilities) and in the public `catio` skill, which asks the same questions. CLAUDE.md, "Onboarding".
