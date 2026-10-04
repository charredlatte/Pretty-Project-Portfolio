# Onboarding: the wireframes

The first run of someone's own KittyChat Café, drawn as basic wireframes for Charlotte's review before anything
is built. The Figma file is "KittyChat Café · Onboarding" in her drafts
(https://www.figma.com/design/wDi412a6ixNljNqVXXWWsG).

Nothing in it is art: plain grey boxes and Figma's Inter. Nothing from `catio/data/`, the packs or any kit.

## The frames, left to right

1. **Layout.** The shell: the house filling the screen, the brand and House button top left, the map panel top
   right. The wizard sits centred over the dimmed house.
2. **Welcome.** The tagline, the stripped car and who drives it, then name your café.
3. **Rooms.** How many rooms (− N +). The manor's ten rooms as a grid: N open from the front of the house, the rest
   closed, and a name field per open room. The house itself never changes: a closed room is dimmed and gets no
   cats, and opens later under Edit rooms.
4. **GitHub.** The tires. Connect GitHub, then each repository with the room it lives in. **3b** is the not-connected state.
5. **Sessions.** The windshield: what `list_sessions` found. **4b** is the blocked state, with the saved copy in one line.
6. **Litter box.** The glovebox: what it is and a drop zone. (The frame's switch for holding pull requests was dropped in
   the build: holding is the merging rule's doing, `harness/README.md`, not a page setting.)
7. **How it works.** The whole car, part by part (below): the stripped car, then five parts: Simone drives, the
   windshield and the dashboard, seatbelts and brakes, the intercom, the glovebox. Then the two lines that fit the
   seatbelts and brakes.
8. **Done.** "Your car is ready, and Simone has the keys", the summary and "Open the doors".

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
- **How it works says the connection start to finish** in the five lines of frame 7 (since 4 October, the five parts
  of the car: Simone drives, the windshield and the dashboard, seatbelts and brakes, the intercom, the glovebox). `frames.js`
  and `openSetup()` hold the same five, word for word: change both, and quote neither here beyond its title.
  Hooks and skills are not named: the step is five sentences and the two install lines, for whoever wants them.
- **Be honest about where it stands.** Running your own café is open today (a clone, the public `catio` skill, a
  Cloudflare Worker for the front desk). A hosted café with nothing to install is planned and not open yet:
  nothing in the onboarding says "sign in" or "create an account" until it is. The art packs cannot be shared,
  so the first step says the cats are the person's to bring, before anything else.
- **Nothing credits Claude** in what the onboarding writes or publishes (her rule, CLAUDE.md "Shipping").

Frames 2 and 7 are redrawn in `frames.js`, and the Welcome and How-it-works steps of `openSetup()` in
`catio/index.html` say the same (3 October). How it works is word for word the same in both; Welcome differs by
its last sentence alone, because the wireframe ends on the name field and the page counts its seven steps. The other five steps are unchanged: they instruct,
so they still name the real tools and commands. The look is `sh catio/test/run.sh look setup`. The suite stands where it stood: 225 pass and one fails, "on its
own address the café is live through the gateway, with no warning sign", the same on the merge base. In a checkout
with no `art/licensed/` the sign shows what is missing, so it shows in gateway mode too. It is a real failure and
someone's to fix; this change neither caused it nor hides it.

## Decided 4 October 2026: the harness is a car

Charlotte's words, the first time: "It's like driving a really nice car in perfect weather. Whereas driving regular
code UIs requires knowledge a regular schmuck like me doesn't have." And what she meant: "The car is the harness. The
driver is Simone (AI runner) the queen cat. And the way you normally drive Claude is comparable to starting a totally
stripped car. No seatbelts. No windshield. No tires. Etc. Explain and onboard tooling."

So the car isn't a line beside the explanation: it **is** the explanation, and the wizard fits it part by part.
Claude on its own is the engine of a stripped car: brilliant, and nothing else. Everything the harness adds is a
part, and each step that sets one up names it first.

| The car | The harness | Where the wizard fits it |
|---|---|---|
| The engine | Claude: the same in both, still the person's own | Welcome (named, not fitted) |
| The driver | Simone, the queen cat: her runner (`harness/runner/queen.py`) on the person's computer. Routines, homework, passing words on | Welcome, How it works, Done |
| The tires | GitHub: the repositories, where the work meets the road, each parked in a room | GitHub |
| The windshield | The café page: every session a cat, in view (`list_sessions`, the saved copy when blocked) | Sessions |
| The dashboard | The gateway, where every cat checks in (`report.py`), and the badge that counts who needs you | How it works |
| The seatbelts | The house rules' enforced hooks (`gates.py`, `ship_gate.py`): the browser preflight, the opening audit, no pushes to the default branch | How it works, with the two install lines |
| The brakes | The merging rule: anything guessed waits for her (`ship_gate.py`, the litter box) | How it works |
| The intercom | Notes, the inbox and the outbox: what she says waits for a cat until it checks in | How it works |
| The glovebox | The litter box: the brain's tray in the page, `litterbox/` in a clone | Litter box |
| The keys | Opening the doors: nothing is written until Done | Done |

- **The driver has a name.** The page says the queen's own name (`queenOf().name`), which is Simone in every café
  that hasn't named her: `QUEEN_NAMES[hash("queen:house")]`. The wireframe says Simone.
- **The steps that instruct still name the real thing** ("Say it like the café", above): a part's name opens the step,
  then the step says what to click or type, as before. The Rooms step has no part: rooms are the café's, not the car's.
- **The page and the wireframe say the same,** word for word for How it works (its intro, the five parts and the line
  before the install lines), the part lines of GitHub, Sessions and Litter box, and Done's keys. Welcome differs by its
  last sentence alone, as before.
- **The check:** the suite's How it works step wants the stripped car and a first part that is "<her name> drives.",
  still five parts and the install lines; Done wants the keys.

## Still to build

- Republish the page to its one artifact, so the wizard's new wording (the plain words of 3 October and the car of
  4 October) reaches the café in claude.ai.
- Where the litter box lives in the page: the brain's unsorted tray and the repo's `litterbox/`.
