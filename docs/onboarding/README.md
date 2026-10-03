# Onboarding: the wireframes

The first run of someone's own KittyChat Café, drawn as basic wireframes for Charlotte's review before anything
is built. The Figma file is "KittyChat Café · Onboarding" in her drafts
(https://www.figma.com/design/wDi412a6ixNljNqVXXWWsG).

Nothing in it is art: plain grey boxes and Figma's Inter. Nothing from `catio/data/`, the packs or any kit.

## The frames, left to right

1. **Layout.** The shell: the house filling the screen, the brand and House button top left, the map panel top
   right. The wizard sits centred over the dimmed house.
2. **Welcome.** The tagline, then name your café.
3. **Rooms.** How many rooms (− N +). The manor's ten rooms as a grid: N open from the front of the house, the rest
   closed, and a name field per open room. The house itself never changes: a closed room is dimmed and gets no
   cats, and opens later under Edit rooms.
4. **GitHub.** Connect GitHub, then each repository with the room it lives in. **3b** is the not-connected state.
5. **Sessions.** What `list_sessions` found. **4b** is the blocked state, with the saved copy in one line.
6. **Litter box.** What it is and a drop zone. (The frame's switch for holding pull requests was dropped in
   the build: holding is the merging rule's doing, `harness/README.md`, not a page setting.)
7. **How it works.** The harness in five plain lines: chats are cats, the café asks who's awake, some rules
   can't be talked around, messages wait on the mat, the queen and the litter box.
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

## Decided 3 October 2026: plain words first

Someone arriving for the first time may not know what MCP, an API or an LLM is, and the wizard must not
need them to. The README's "In plain words" section and the explainer page ("What is KittyChat Café", a private
artifact) are the reference; the onboarding follows them.

- **Say it like the café,** wherever the wizard is explaining rather than instructing. Chat or session: a cat.
  Project: a room. A chat waiting on you: a cat that meows. Assistant: the queen. No MCP, API, gateway, runner,
  hooks or LLM in a sentence whose job is to explain. A step that tells someone what to *do* still names the real
  thing, because they have to type or find it: Claude Code Remote, `list_repos`, `data/sessions.json`,
  `litterbox/sort.py`, the two install lines.
- **The Welcome step opens with the tagline:** "All your Claude chats, in one cozy café."
- **How it works says the connection start to finish** in the five lines of frame 7 (chats are cats, the café asks
  who's awake, rules can't be talked around, messages wait on the mat, the queen and the litter box). `frames.js`
  and `openSetup()` hold the same five, word for word: change both, and quote neither here beyond its title.
  Hooks and skills stay behind the House menu, for the people who ask.
- **Be honest about where it stands.** Running your own café is open today (a clone, the public `catio` skill, a
  Cloudflare Worker for the front desk). A hosted café with nothing to install is planned and not open yet:
  nothing in the onboarding says "sign in" or "create an account" until it is. The art packs cannot be shared,
  so the first step says the cats are the person's to bring, before anything else.
- **Nothing credits Claude** in what the onboarding writes or publishes (her rule, CLAUDE.md "Shipping").

Frames 2 and 7 are redrawn in `frames.js`, and the Welcome and How-it-works steps of `openSetup()` in
`catio/index.html` say the same, word for word (3 October). The other five steps are unchanged: they instruct,
so they still name the real tools and commands. The suite passes; the look is `sh catio/test/run.sh look setup`.

## Still to build

- Republish the page to its one artifact, so the wizard's new wording reaches the café in claude.ai.
- Where the litter box lives in the page: the brain's unsorted tray and the repo's `litterbox/`.
