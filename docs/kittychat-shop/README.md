# The KittyChat Café shop: the wireframes

The Shopify storefront that sells the KittyChat Café, drawn as basic wireframes for Charlotte's review before a
store exists. The Figma file is "KittyChat Café · Shop wireframes" in her drafts
(https://www.figma.com/design/MF730vN4uHmZ3iGlekHc2W).

Nothing in it is art: plain grey boxes and Figma's Inter. No prices either: `[monthly]` and `[annual]` stand where
the business plan's figures go once she has chosen them. The plan itself is private and lives in the café, not here.

## The frames, left to right

1. **Home.** The headline speaks to someone who has never opened a terminal ("Your projects as a cat café. Every task
   is a cat; it meows when it needs you. No terminal required."): her ask of 3 October, to advertise to small business
   owners using AI for the first time, with the café as a video-game way into a coding environment. Then "Start free: self-host" and "Join the café: early
   access", a screenshot box, the two cars side by side (below, "The car"), the three ways to get it (self-host, named as the developers' door since the headline promises no terminal; hosted;
   set up for you from 90 €), and the legal footer every page
   carries (mentions légales, CGV, confidentialité, rétractation, contact).
2. **Pricing.** Opens on the car: every plan is the whole car and Ninine drives, Claude is its engine, and the buyer
   buys the fuel from Anthropic. Then four columns from her paywall (2 and 3 October), each with its place in the car under its
   price: Free (one repository, the page), Basic (up to five
   repositories, requests and gateway calls capped at `[cap]` a month, no sorter, quiz or homework: files dropped on a
   cat arrive unsorted), Early access (unlimited repositories, uncapped, the brain's sorter, the litter box quiz, the
   queen's homework, new features until the app ships) and Support, which is not a tier but two buttons: "Buy me a coffee" (one-off coffees and small memberships, thanks
   and a name in the credits, no promise) and "Back the app" (a crowdfunding campaign whose rewards are a year of
   Early access). No lifetime seat (her call, 3 October: no lifetime guarantee sale, an in-between instead). Prices
   HT with "TVA non applicable, art. 293 B du CGI", a grid of what each column unlocks, and the "in development"
   note: the subscription and the campaign fund the app. Under the grid, **Set up for you**: a one-time payment from
   90 € that is lifetime access plus the DIY course on customizing your own plugin (house rules, skills, the queen's
   manner), and from `[setup-plus]` € an afternoon with Charlotte (her ask, 3 October: no "sur devis").
3. **Product page.** The Early access plan as one Shopify product (Basic is a second product with the same page: the
   same selling plans, its own "what you get" list, and "Choose Basic" lands here): a selling-plan selector (monthly or yearly,
   Shopify's own Subscriptions app), "what you need first" (claude.ai with Claude Code, GitHub, the buyer's own cat
   art), and the FAQ (the café never reads code or resells Claude; cancelling; whose data).
4. **Checkout.** Shopify's checkout as the fields it owns: email, billing address, Shopify Payments, and the two
   ticks French law wants before a digital service starts at once: the CGV, and the express waiver of the 14-day
   right of withdrawal (art. L221-28 C. conso.). The order summary shows the VAT line as not applicable.
5. **Thank you.** The order confirmation delivers the invite code (one per order) and the café's address, the two
   `claude plugin` lines, and where to get help. The gateway's sign-up takes the code: phase 2 of `docs/accounts.md`.
6. **Account.** The subscription (pause, switch to yearly, cancel, next billing), the café's address with its keys
   and an export, and the orders with their invoices.
7. **Legal pages.** Four tiles: mentions légales (EI, SIREN, host), CGV (object, price, renewal, withdrawal,
   médiateur), politique de confidentialité (what the gateway stores, sub-processors, RGPD rights), and the model
   withdrawal form.
10. **About.** The promotion's brief, as Charlotte set it on 4 October: the point of contact (her, as EI, with
   the email, address and hours as placeholders and a Write button), the due date (when the early-access promotion
   ends, with launched and last-updated dates), a short description of the promotion (the launch price held for as
   long as the subscription stays open), the links in their original form (full addresses, never a shortener: the
   hosted café, the repository, Buy Me a Coffee, Ulule and the shop), and the mentions légales on the page itself
   (éditeur, directrice de la publication, hébergeurs, TVA, médiateur), pointing to the Legal page for the rest.
   "About" joins the nav.
8. **Home (phone)** and 9. **Pricing (phone)**, at 390 wide, with the tiers stacked. The phone's home says the car
   in one line ("Claude is the engine. The café is the rest of the car, and Ninine drives."), and each stacked tier keeps its line.

## The car

Her ask of 4 October, in two goes: "It's like driving a really nice car in perfect weather. Whereas driving regular
code UIs requires knowledge a regular schmuck like me doesn't have." Then: "The car is the harness. The driver is
Simone (AI runner) the queen cat. And the way you normally drive Claude is comparable to starting a totally stripped
car. No seatbelts. No windshield. No tires." Then the queen's new name: "Rename her everywhere to Ninine."

The home page sets the two side by side (`STORM` and `SUN` in `frames.js`): **Claude on its own**, a stripped car,
and **Claude in the café**, the whole car with Ninine at the wheel. Which part is which piece of the harness is the
table in `docs/onboarding/README.md`, "Decided 4 October 2026: the harness is a car"; the wizard fits them one step
at a time. The shop adds only what a price needs:

| The car | What it is in the shop |
|---|---|
| The engine | Claude, the same on every plan |
| The fuel, bought at the pump | The buyer's Claude plan, paid to Anthropic: the café never resells it |
| Mileage | Requests and gateway calls (`[cap]` a month on Basic) |
| The sat-nav | The brain's sorter, the litter box quiz and the queen's homework: at a junction it asks you which way |
| Driving lessons | Set up for you: the DIY course, and the afternoon with Charlotte |

So the tiers read: **Free**, take it round the block (one repository); **Basic**, your own car with a mileage cap (no
sat-nav); **Early access**, unlimited mileage and the sat-nav; **Support**, chip in for the next model (the app). The
lines are `DRIVE` in `frames.js`.

## Redrawing

`frames.js` is the whole drawing, in Figma's Plugin API. Run it with the Figma MCP server's `use_figma` on the
file, which wraps it in an async function. In Figma desktop as a development plugin (Plugins → Development → Import
plugin from manifest, with a manifest whose `main` is `frames.js`), wrap the file yourself:
`(async () => { … ; figma.closePlugin(); })()` in place of the final `return`. Each run draws a fresh row of frames.

Mind the quota: a Starter plan with a View seat gets six MCP calls a month.

## Undecided

- **The prices, and Basic's cap.** The business plan proposes them (`[basic]`, `[monthly]`, `[cap]`, `[setup-plus]`); the frames show
  placeholders until she picks. The polling calls (`list_agents`, `comments`) are never metered; which others count is
  the plan's list.
- **The store's domain.** A separate store from Montfortoise (her choice, 2 October), named KittyChat Café, the
  one name for the café and its engine (4 October, `docs/engine.md`). On 4 October Shopify's check found
  kittychatcafe.com available. An INPI search for "KittyChat" comes before buying it.
- **Monthly or yearly first.** Shopify Subscriptions handles both; the wireframe shows both selling plans.
- ~~Ulule or Kickstarter, Buy Me a Coffee or Ko-fi~~: Ulule and Buy Me a Coffee (her pick, 4 October). The sign-up kit,
  copy and rewards included, is `support-pages.md`.
- **The invite code's shape** and whether the Thank-you page or the gateway mints it: phase 2 of `docs/accounts.md`.
