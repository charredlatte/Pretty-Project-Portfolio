# What Charlotte has asked for

Everything she has asked for across the Catio, the manor, this repo and the KittyChat Cafe, compiled and
compressed. Read this before starting something new. Last updated 2 October 2026 (evening).

## Where the project's information lives

| Place | What's there |
|---|---|
| `CLAUDE.md` | The operating brief: how to work on the page, the licences, the data, publishing |
| `README.md` | What the page is, the rooms, the packs |
| `docs/requests.md` | This file: her requests |
| `docs/from-the-litterbox.md` | Everything the litter box held, sorted: open questions, ideas not built (with the art and sound still missing: what to buy, what to draw, and at what sizes), facts learned, the compressed 29 September harness chat and the UI/UX audit |
| `docs/plan.md` | The roadmap: phases in order, what's waiting on her, how to publish |
| `docs/audit-2026-10-01.md` | The project audit of 1 October: what's broken, what's stale, what to fix first |
| `docs/history.md` | How it got here, version by version |
| `docs/camera-and-minimap.md` | The map panel, the minimap and the Sims-style camera |
| `docs/renovation-mode.md` | The renovation mode spec: moving, adding and removing furniture, the cabinets' looks |
| `docs/drawing-plan.md` | Every asset she will draw herself, at what size and scale, and the new pieces (litterbox, café tables…) |
| `litterbox/` | The back burner: new notes land here, `litterbox/sort.py` piles them by project for her to check, then files each checked pile into its project's own repo and pushes it |
| `catio/art/CREDITS.md` | Every pack, its artist and its licence |
| `harness/README.md`, `harness/rules.json` | The KittyChat house rules and the Catio MCP server |
| `artifacts.json` | The one artifact's URL |
| GitHub | Issue #3 (the KittyChat Cafe); the merged PRs, whose descriptions record each round |
| The artifact's database | Her private data: rooms, renames, adopted chats, queens' notes, the brain's files, notes, the outbox. Never in git |
| Her Drive folder "KittyChat Cafe Assets" | The asset-pack zips |

Claude keeps no memory between sessions, so anything worth keeping goes in one of these.

## The idea

- One pretty place for all her projects: code, business plans, legal questions.
  - Every conversation, agent and live session is a cat in a room of a catio.
  - A cat meows when it needs her.
- Issue #3: "An AI harness that presents itself as a cat cafe. The KittyChat Cafe."

## The page

- **One private artifact.** Cats follow their session's state: meowing, upset, to review, working or asleep.
- **Chats:** claude.ai chats are adopted by hand.
- **Cats:** they can be renamed and moved between rooms.
- **A project's look** is its cats' coat, set from its filing cabinet. No emblems: the fur colours are enough
  (29 September).
- **The house fills the screen**, with no toolbars. Everything opens from hover menus, two taps on a phone,
  or the keyboard.
- **Rooms by use** (she can rename and reassign them):

  | Room | Holds |
  |---|---|
  | Kitchen | The grocery app |
  | Dining room | Business plans |
  | Sunroom | TikTok saves |
  | Craft room | The Montfortoise shop |
  | Bedroom | Legal |
  | Hall | Snail mail |
  | Catio | This portfolio |

- **A saved copy of her sessions** shows when the live read is blocked. A Routine refreshes it every two
  hours, from 07:59 to 19:59 Paris time.
- **A copy that runs off a USB stick**, on localhost.
- **One queen of the house** (2 October: "merge the queen cats to make one main character queen cat that you
  chat with that does everything for you. The way you would interact with a real harness"), in the entrance
  hall: chat with her like an NPC in an RPG, voice to text, a voice that turns on and off, a proper Elizabethan
  English accent, a character you customise and set routines with, and cats with handoffs visibly passing things
  to her for you to read. She keeps notes and can say one aloud. She is never counted.
- **The Sprout Lands interface everywhere**, in its pixel font, with French accents.
- **A plugin** so other people can run their own Catio.

## The harness (29 September)

- **The brain:** drop chats and files on the page, and each is filed to the right cat.
- **"A true harness":** the page pushes to a session, comments on it and manages it.
- **Other models and agents join through MCP:**
  - Claude breeds;
  - other models doing the sorting;
  - other agents' sessions;
  - any MCP client.
- **House rules, as a plugin for every repo:**
  - preflight before any browser;
  - a read-only ponytail audit when a session opens;
  - semi-automatic shipping.
- **Privacy:** private matters stay out of git. They're fine in the Catio's own storage.
- **Renovation mode:** drag furniture around, and add or remove the non-essential pieces.
- **A cat's position** shows its state, not a mood face.
- **Cats walk** (29 September): an archived cat walks away upstairs, and cats can walk around.
- **Livelier grounds** (29 September): more variety from the packs she has, a spruce forest like the photos.
- **The KittyChat Cafe** as a terrace in the garden (29 September).
- **A UI/UX audit with her Game UI plugin** (29 September): in `docs/from-the-litterbox.md`, under Findings. She picks what to fix.
- **Sounds:** she is finding some herself.
- **How to work:** build the manor a room at a time; compress chats; leftovers go in the litterbox.

## The litter box (1 October)

- **An audit of the harness, and a first real test of the sifter** (`litterbox/sort.py`). Fix everything it
  found, including the server's hole: any web page could wake an agent as her.
- **Every note needs a `project:` header, and the sifter writes it**, not her.
- **Keep guessing to a minimum before deletion.** "The litterbox is the back burner": it finds what needs
  dealing with and lumps it together under a header. A guess waits until it's checked; nothing is filed,
  or deleted from the box, on a guess.
- **It semi-auto pushes** what it files, by the house rule for shipping.

## The manor's look

- **A storybook feel.** The manor is a Transylvanian Baroque castle:
  - limewashed ochre and pastel render;
  - white stucco;
  - stone plinths and quoins;
  - green painted shutters;
  - arched doors;
  - **no turrets** (29 September).
- **Every pack mixed freely**, for personal use. Licences are sorted out later.
  - That includes Sprout Lands Sprites and Little Dreamyland.
- **`house.png` becomes licensed art.** A clone without the zips shows no house.
- **Apply her Game UI / UX plugin.** Received 29 September as a zip (MCPmarket's `ui` skill). Its Game UI Designer
  rules are applied to the manor: map layers stay quiet under cats and signs, never colour alone, no motion,
  integer scaling.
- **Inspired by her photos of Peleș and Sinaia** (29 September). The pastel Baroque stays the base, with
  touches from the photos:
  - stained glass;
  - gilt trellis on white panels;
  - wrought-iron scrollwork;
  - carved dark oak;
  - Art Nouveau.

## The interface, 30 September

- **"Take everything about the UI and make it better"**: less bloated menus, less noise, redesigned with the
  licensed packs.
- **"I hate the signs on every room and the large The Catio name."** The page is **the KittyChat Cafe**: "the
  harness and UI SaaS that I am making here". No signs on the map; a small brand, top left.
- Done in version 13: see `docs/plan.md`.
- **"Use the Game UI Pastel pack anyway"**: its licence turned up inside the zip (SC_siosio, credit required).
  Version 14 uses its icons, pixelated, on the corner controls and a cat's Manage buttons.

## Decided 30 September

- The minimap is a plan of rooms; WASD and the arrows both pan; Game UI Pastel is used.
- A filing cabinet never leaves its room, and she chooses what it looks like in each room.
- Renovation mode stays in the plan as its own phase (1 October): `docs/renovation-mode.md`.

## Her own art (1 October)

- **She will draw every asset herself in Aseprite** before publishing the working project, replacing the
  downloaded packs, and adding new pieces: a litterbox, café tables and more. The list and the scale are in
  `docs/drawing-plan.md`.

## Making it honest, and the house rules everywhere (1 and 2 October)

- **"Audit the project and revise the plan"**, with renovation mode in it: `docs/audit-2026-10-01.md`, and the
  roadmap in `docs/plan.md`. Then **"go ahead and get started in order"** and **"push as you go"**: phase 0.
- **Publish phase 0** (version 17): it stopped the stray sessions.
- **Yes to the `send_message` test** on a test session (version 18): claude.ai refused it, so a page can't post
  into a session.
- **Yes to deleting the 14 old branches**; she deleted them herself, since this session's git access can't.
- **"Use the house-rules plugin on all of the repos"**, then **"merge the 7 PRs"**: on in all seven since
  1 October.
- **`intermarche-grocery-data` is deleted**: "there is no need for a private repo", it was surface-level grocery
  data. The Kitchen lists only the grocery app.
- **"Update the READMEs with the correct information, and tell me again why it isn't an MCP or some server."**
  The answer is in `harness/README.md`: nothing outside claude.ai can wake a session; the gateway makes the cats
  live and hands a running session her message at the end of its turn.
- **"Update plan and compile"** (2 October): `docs/plan.md` rewritten to where things stand, and this file.
- **Issue #24, "Cafe reading the gateway"** (2 October): "The kittychat cafe is still not able to read live
  sessions. Wait for the PonyTail Audit of the gateway's current state before continuing to work on the
  gateway. When done, compile and sift my recent sessions using the litterbox and update the plan." The audit
  found the gateway lean. The cause was that the gateway wasn't set up yet. She set it up that afternoon, and
  version 21 reads it. Then **"put this through the litter box"**: the round's report, sifted into
  `docs/from-the-litterbox.md`.
- **No Claude co-author or session links** in commits on her public repos or forks (1 October, from another
  session; the rule is on `claude/cool-cannon-wh25u6`).

## Semi-automatic merging (2 October)

- **"Audit the KittyChat Cafe House Rules."** Done in this round: the house rules weren't running in cloud
  sessions at all, and "no merge", "never the default branch" and "no force-push" were only words. The audit is
  in the PR's description.
- **"A semi-automatic mode in the plugin that allows merges and pushes to be semi-automatic. Merge and delete
  after audits when the model has a very high confidence and is using a strong model for the task at hand.
  Anything that is guess work gets sifted through the litterbox for human review."** The merging rule
  (`harness/README.md`, "Semi-automatic merging"), on in this repo and the grocery app.
- **"This line confuses me: Your house rules forbid me from merging, so the merge is yours to do."** It came from
  the old shipping rule ("never … merge"). A session now says "PR #N is ready for you to merge", or "PR #N is
  waiting for your review" with the reason, and nothing about rules.
## Nothing on the cats (2 October)

- **"I don't like the letters over the cats. Remove all icons on top of the moving cats. Only show menus on
  hover."** Asked, she chose: hovering a cat shows what it needs, a click still opens its menu, and "remove
  everything. The crowns, the letters etc." So no model letters, file counts, faces, bubbles, pile numbers,
  crowns or "z Z" on the map.
- **"I hate the cat food."** The bowls and the food bag are gone from the kitchen, and the bowls from the catio.
- **Her local copy lives in Google Drive**, My Drive › Claude › KittyChat Cafe (local copy): "my google drive,
  which is where I tell you to save everything".

## Still waiting on her

The list is kept in one place: "Waiting on Charlotte" in `docs/plan.md`.

## 2 October, evening

- **Sell the KittyChat Café.** A Shopify wireframe for distributing it (`docs/kittychat-shop/`, drawn in Figma like
  the onboarding frames), and a business plan grounded in French law and her legal status. The plan is private
  (her status, ARE, VAT): a private artifact, linked from the Café's queen, never in git.
- **The litter box quiz as a skill on GitHub**: `catio-plugin/skills/litterbox-quiz/`, with the licensed interface
  art left out ("for the UI, just drop the assets that are licensed").
- **No lifetime seat** (3 October): "Instead of relying on a lifetime guarantee sale, maybe there could be an in between
  and I could set myself up on Kickstarter or buy me a coffee." The pricing's third column is Support: a coffee page and a
  campaign to fund the app.
- **A Basic plan** (3 October): "without the automatic litter box (quiz and easy unblocking handling)", up to 5 repos,
  and a cap on the calls to the MCP. Between Free and Early access.
- **Set up for you, from 90 €** (3 October): no "sur devis". A one-time payment that is a lifetime subscription and the
  plugin's customizable features taught as a DIY Claude customization course; the afternoon of setup on top.
- **Two audiences** (3 October): developers who lose track of sessions, and "small business owners looking to use AI for
  the first time. This should be like a video game accessible coding environment." The home page speaks to the second.
- **Open source, with a paywall on the hosted café and the art** (3 October): the gateway's code "is open source for
  anyone with GitHub to use" (AGPL-3.0, her choice); "certain features should stay behind the paywall like certain
  breeds of cats (or all custom assets)"; the Buy Me a Coffee and Ulule links in the README, to help with crowdfunding.

## The queen's quest log (3 October)

- **"Where do I take the litter box quiz in the cafe UI?"** Nowhere yet: it was a page of its own. Then: **"Re work the
  workflow using the UI game skill and all of my previous chats about my vision for the layout of the cafe UI."** Her
  Game UI skill wasn't in the session or her Drive, so its recorded rules were used (quiet map, never colour alone, short
  menus) with her layout decisions (no signs, nothing on the cats, two controls on screen, every menu the same shape).
- **Asked, she chose:** the queen keeps one quest log of everything waiting on her (quizzes that unblock cats, litter box
  notes to sort, decisions), like an NPC quest giver; the litter box is a piece on the map with no sign that opens the
  same list at its notes; the two quiz pages are retired; the cards live in her gateway, so both cafés read them.
