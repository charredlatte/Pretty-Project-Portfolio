# The KittyChat Café shop: the wireframes

The Shopify storefront that sells the KittyChat Café, drawn as basic wireframes for Charlotte's review before a
store exists. The Figma file is "KittyChat Café · Shop wireframes" in her drafts
(https://www.figma.com/design/MF730vN4uHmZ3iGlekHc2W).

Nothing in it is art: plain grey boxes and Figma's Inter. No prices either: `[monthly]` and `[annual]` stand where
the business plan's figures go once she has chosen them. The plan itself is private and lives in the café, not here.

## The frames, left to right

1. **Home.** One line on what the café is, a screenshot box, "Start free: self-host" and "Join the café: early
   access", the three ways to get it (self-host, hosted, set up for you), and the legal footer every page carries
   (mentions légales, CGV, confidentialité, rétractation, contact).
2. **Pricing.** Four columns from her paywall (2 and 3 October): Free (one repository, the page), Basic (up to five
   repositories, requests and gateway calls capped at `[cap]` a month, no sorter, quiz or homework: files dropped on a
   cat arrive unsorted), Early access (unlimited repositories, uncapped, the brain's sorter, the litter box quiz, the
   queen's homework, new features until the app ships) and Support, which is not a tier but two buttons: "Buy me a coffee" (one-off coffees and small memberships, thanks
   and a name in the credits, no promise) and "Back the app" (a crowdfunding campaign whose rewards are a year of
   Early access). No lifetime seat (her call, 3 October: no lifetime guarantee sale, an in-between instead). Prices
   HT with "TVA non applicable, art. 293 B du CGI", a grid of what each column unlocks, and the "in development"
   note: the subscription and the campaign fund the app.
3. **Product page.** The Early access plan as one Shopify product: a selling-plan selector (monthly or yearly,
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
8. **Home (phone)** and 9. **Pricing (phone)**, at 390 wide, with the tiers stacked.

## Redrawing

`frames.js` is the whole drawing, in Figma's Plugin API. Run it with the Figma MCP server's `use_figma` on the
file, which wraps it in an async function. In Figma desktop as a development plugin (Plugins → Development → Import
plugin from manifest, with a manifest whose `main` is `frames.js`), wrap the file yourself:
`(async () => { … ; figma.closePlugin(); })()` in place of the final `return`. Each run draws a fresh row of frames.

Mind the quota: a Starter plan with a View seat gets six MCP calls a month.

## Undecided

- **The prices, and Basic's cap.** The business plan proposes them (`[basic]`, `[monthly]`, `[cap]`); the frames show
  placeholders until she picks. The polling calls (`list_agents`, `comments`) are never metered; which others count is
  the plan's list.
- **The store's name and domain.** A separate store from Montfortoise (her choice, 2 October). Shopify's domain
  check on "KittyChat Café" (2 October) offered no kittychat domain; it suggested purrchat.store, whiskerchat.com
  and meowmingle.store, each available that day. An INPI search for "KittyChat" is still to do.
- **Monthly or yearly first.** Shopify Subscriptions handles both; the wireframe shows both selling plans.
- **Ulule or Kickstarter** for the campaign, and whether the coffee page is Buy Me a Coffee or Ko-fi. The business plan
  weighs them; the frame only links out.
- **The invite code's shape** and whether the Thank-you page or the gateway mints it: phase 2 of `docs/accounts.md`.
