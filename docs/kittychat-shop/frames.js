// The KittyChat Café shop: Shopify storefront wireframes, drawn by Figma's own Plugin API (use_figma, or a
// development plugin). Plain grey boxes and Inter: no art from the packs, no kits, no prices that are decided.
// docs/kittychat-shop/README.md says what each frame is.
const INK = { r: 0.13, g: 0.12, b: 0.11 }, GREY = { r: 0.55, g: 0.53, b: 0.5 }, LINE = { r: 0.78, g: 0.76, b: 0.73 };
const PAPER = { r: 0.97, g: 0.96, b: 0.94 }, BOX = { r: 0.9, g: 0.89, b: 0.87 }, DIM = { r: 0.82, g: 0.8, b: 0.78 };
const WHITE = { r: 1, g: 1, b: 1 };
const REG = { family: "Inter", style: "Regular" }, BOLD = { family: "Inter", style: "Bold" };
await figma.loadFontAsync(REG); await figma.loadFontAsync(BOLD);
const solid = (c) => [{ type: "SOLID", color: c }];
const text = (s, size = 14, font = REG, color = INK, width) => {
  const t = figma.createText(); t.fontName = font; t.characters = s; t.fontSize = size; t.fills = solid(color);
  if (width) { t.resize(width, 10); t.textAutoResize = "HEIGHT"; }
  return t;
};
const box = (w, h, fill = BOX, name = "box") => {
  const r = figma.createRectangle(); r.name = name; r.resize(w, h); r.fills = solid(fill);
  r.strokes = solid(LINE); r.strokeWeight = 1; r.cornerRadius = 4; return r;
};
const button = (label, primary = false) => {
  const b = figma.createAutoLayout("HORIZONTAL", { name: "button " + label, paddingLeft: 16, paddingRight: 16, paddingTop: 8, paddingBottom: 8, cornerRadius: 4 });
  b.fills = solid(primary ? INK : PAPER); b.strokes = solid(primary ? INK : LINE); b.strokeWeight = 1;
  b.appendChild(text(label, 14, BOLD, primary ? PAPER : INK)); return b;
};
const field = (placeholder, w = 320) => {
  const f = figma.createAutoLayout("HORIZONTAL", { name: "field", paddingLeft: 10, paddingRight: 10, paddingTop: 8, paddingBottom: 8, cornerRadius: 4 });
  f.fills = solid(WHITE); f.strokes = solid(LINE); f.strokeWeight = 1;
  f.appendChild(text(placeholder, 14, REG, GREY)); f.resize(w, f.height); return f;
};
const row = (gap = 12, name = "row") => figma.createAutoLayout("HORIZONTAL", { name, itemSpacing: gap, counterAxisAlignItems: "CENTER" });
const col = (gap = 12, name = "column") => figma.createAutoLayout("VERTICAL", { name, itemSpacing: gap });
const tick = (label) => { const r = row(8, "tick"); r.appendChild(box(16, 16, WHITE, "checkbox")); r.appendChild(text(label, 13, REG, INK, 480)); return r; };
const card = (w, pad = 16, name = "card") => {
  const c = figma.createAutoLayout("VERTICAL", { name, itemSpacing: 10, paddingLeft: pad, paddingRight: pad, paddingTop: pad, paddingBottom: pad, cornerRadius: 6 });
  c.fills = solid(WHITE); c.strokes = solid(LINE); c.strokeWeight = 1; c.resize(w, c.height); return c;
};

const ids = [];
let x = 0;
const NAV = ["Pricing", "How it works", "Docs", "Account", "Cart (0)"];

// A storefront page: header with the name and the nav, a content column, the legal footer.
function page(name, width = 1280, height = 900) {
  const f = figma.createFrame(); f.name = name; f.resize(width, height); f.x = x; f.y = 0; x += width + 100;
  f.fills = solid(PAPER); figma.currentPage.appendChild(f); ids.push(f.id);
  const phone = width < 600;
  const head = row(phone ? 10 : 24, "header"); head.appendChild(box(28, 28, BOX, "logo")); head.appendChild(text("KittyChat Café", 16, BOLD));
  if (phone) head.appendChild(text("☰", 18, BOLD, INK)); else for (const n of NAV) head.appendChild(text(n, 13, REG, GREY));
  f.appendChild(head); head.x = phone ? 16 : 40; head.y = 20;
  const body = col(phone ? 16 : 24, "content"); f.appendChild(body); body.x = phone ? 16 : 120; body.y = 80;
  const foot = row(phone ? 10 : 20, "footer: legal");
  for (const l of ["Mentions légales", "CGV", "Confidentialité", "Rétractation", "Contact"]) foot.appendChild(text(l, phone ? 10 : 12, REG, GREY));
  f.appendChild(foot); foot.x = phone ? 16 : 120; foot.y = height - 44;
  return { f, body, w: phone ? width - 32 : 1040 };
}

// 1. Home.
{ const { body, w } = page("1 Home");
  body.appendChild(text("Every Claude Code session is a cat. The café is where you see them all.", 32, BOLD, INK, w));
  body.appendChild(text("A pixel-art manor for your sessions and chats: who's working, who's blocked, who needs you. Your own claude.ai, your own machine; the café only shows and talks to them.", 16, REG, GREY, 640));
  const cta = row(12, "calls"); cta.appendChild(button("Start free: self-host", true)); cta.appendChild(button("Join the café: early access")); body.appendChild(cta);
  body.appendChild(box(w, 360, BOX, "screenshot: the manor, ground floor"));
  const ways = row(16, "three ways");
  for (const [t, d] of [["Self-host", "The public repo and the catio skill. Free. Your art, your artifact."], ["Hosted café", "Your café on our address, with accounts and the gateway. Monthly, while it's in development."], ["Set up for you", "An afternoon with Charlotte: rooms, repos, house rules. On quote."]]) {
    const c = card(336); c.appendChild(text(t, 16, BOLD)); c.appendChild(text(d, 13, REG, GREY, 300)); ways.appendChild(c); }
  body.appendChild(ways); }

// 2. Pricing.
{ const { body, w } = page("2 Pricing", 1280, 1000);
  body.appendChild(text("Pricing", 32, BOLD));
  body.appendChild(text("Prices HT. TVA non applicable, art. 293 B du CGI. You pay Anthropic for Claude yourself; the café never resells it.", 13, REG, GREY, w));
  const tiers = row(16, "tiers");
  for (const [t, p, lines, primary] of [
    ["Free", "0 €", ["Self-host or hosted", "One repository, one room", "Hover, menus, the saved copy", "Community help"], false],
    ["Early access", "[monthly] €/month", ["Everything in Free", "Unlimited repositories and rooms", "Requests: pause, wrap up, messages, New cat", "The gateway: comment, drop files, manage, agents", "The brain's sorter", "New features as they land, until the app ships"], true],
    ["Support", "A coffee, or back the app", ["No subscription, no promise", "One-off coffees and small memberships", "Your name in the café's credits", "The campaign funds the app: a year of Early access as its reward"], false]]) {
    const c = card(336, 20, (t === "Support" ? "support" : "tier " + t)); c.appendChild(text(t, 18, BOLD)); c.appendChild(text(p, 22, BOLD, primary ? INK : GREY, 296));
    for (const l of lines) c.appendChild(text("✓  " + l, 13, REG, INK, 296));
    if (t === "Support") { const r = row(8, "support buttons"); r.appendChild(button("Buy me a coffee")); r.appendChild(button("Back the app")); c.appendChild(r); }
    else c.appendChild(button(t === "Free" ? "Clone the repo" : "Choose " + t, primary)); tiers.appendChild(c); }
  body.appendChild(tiers);
  body.appendChild(text("What each column unlocks at the gateway", 16, BOLD));
  const grid = col(0, "feature grid");
  const rows = [["", "Free", "Early access", "Support"], ["Repositories", "1", "unlimited", "as Free, or as Early access with a campaign reward"], ["Requests into a session (pause, wrap up, message, New cat)", "–", "✓", "with a reward"],
    ["Gateway calls: comment, drop_file, manage, list_agents", "–", "✓", "with a reward"], ["The brain's sorter and the litter box quiz", "–", "✓", "with a reward"], ["Hosted café (accounts, keys, your own address)", "–", "✓", "with a reward"], ["The app, when it ships", "–", "included", "funded by the campaign"]];
  rows.forEach((r, i) => { const rr = row(0, "row"); r.forEach((cell, k) => { const t = text(cell, 12, i === 0 || k === 0 ? BOLD : REG, i === 0 ? GREY : INK, k === 0 ? 520 : 170); rr.appendChild(t); }); grid.appendChild(rr); });
  body.appendChild(grid);
  body.appendChild(text("In development: the subscription and the campaign fund the app. Cancel any month from your account.", 12, REG, GREY, w)); }

// 3. Product page: one plan, Shopify's selling plans.
{ const { body, w } = page("3 Product: Early access");
  const two = row(40, "two columns");
  const left = col(12, "gallery"); left.appendChild(box(520, 390, BOX, "screenshot carousel")); const thumbs = row(8); for (let i = 0; i < 4; i++) thumbs.appendChild(box(80, 60, DIM, "thumb")); left.appendChild(thumbs); two.appendChild(left);
  const right = col(14, "buy"); right.appendChild(text("KittyChat Café · Early access", 26, BOLD, INK, 480));
  right.appendChild(text("[monthly] € / month HT", 20, BOLD));
  right.appendChild(text("Selling plan", 12, BOLD, GREY));
  const plans = col(6, "selling plans (Shopify Subscriptions)"); for (const [p, on] of [["Monthly · [monthly] €, cancel any time", true], ["Yearly · [annual] €, ten months for twelve", false]]) { const r = row(8); r.appendChild(box(16, 16, on ? INK : WHITE, "radio")); r.appendChild(text(p, 13)); plans.appendChild(r); } right.appendChild(plans);
  right.appendChild(button("Subscribe", true));
  right.appendChild(text("What you need first", 12, BOLD, GREY));
  for (const l of ["A claude.ai account with Claude Code", "GitHub connected to Claude", "Your own cat art, or the packs' free versions for personal use"]) right.appendChild(text("•  " + l, 13, REG, INK, 480));
  right.appendChild(text("After checkout you get an invite code and the café's address. Your sessions stay on claude.ai and your machine.", 12, REG, GREY, 480));
  two.appendChild(right); body.appendChild(two);
  body.appendChild(text("FAQ", 16, BOLD));
  for (const q of ["Does the café read my code? No: it reads session titles, states and what you drop on a cat.", "Can I stop? Yes, from Account: the subscription ends at the period's end, your café stays readable for 30 days.", "Who sees my data? You, on your own house in the gateway. Cloudflare hosts it; the privacy policy says where."]) body.appendChild(text(q, 13, REG, INK, w)); }

// 4. Cart and checkout: Shopify's own checkout, with the fields it owns.
{ const { body } = page("4 Checkout (Shopify)");
  const two = row(40, "checkout");
  const left = col(14, "fields"); left.appendChild(text("Contact", 16, BOLD)); left.appendChild(field("Email", 480));
  left.appendChild(text("Billing address", 16, BOLD)); left.appendChild(field("Country: France ▾", 480)); const nm = row(8); nm.appendChild(field("First name", 236)); nm.appendChild(field("Last name", 236)); left.appendChild(nm); left.appendChild(field("Address", 480));
  left.appendChild(text("Payment (Shopify Payments)", 16, BOLD)); left.appendChild(field("Card number", 480)); const cc = row(8); cc.appendChild(field("MM / YY", 236)); cc.appendChild(field("CVC", 236)); left.appendChild(cc);
  left.appendChild(tick("I accept the CGV and the privacy policy."));
  left.appendChild(tick("I ask for the service to start now and acknowledge that I lose my 14-day right of withdrawal once it has started (art. L221-28 C. conso.)."));
  left.appendChild(button("Pay [monthly] €", true)); two.appendChild(left);
  const right = card(440, 20, "order summary"); right.appendChild(text("Order", 16, BOLD)); const li = row(12); li.appendChild(box(56, 56, BOX, "thumb")); li.appendChild(text("KittyChat Café · Early access\nMonthly, renews on the same day", 13, REG, INK, 300)); right.appendChild(li);
  for (const [k, v] of [["Subtotal", "[monthly] €"], ["TVA", "non applicable, art. 293 B"], ["Total", "[monthly] €"]]) { const r = row(0); r.appendChild(text(k, 13, REG, GREY, 240)); r.appendChild(text(v, 13, k === "Total" ? BOLD : REG, INK, 160)); right.appendChild(r); }
  two.appendChild(right); body.appendChild(two); }

// 5. Thank-you: the order confirmation delivers the invite code.
{ const { body } = page("5 Thank you: your invite");
  body.appendChild(text("Thank you. Your café is ready to open.", 32, BOLD));
  const c = card(640, 20, "invite"); c.appendChild(text("Your invite code", 12, BOLD, GREY)); c.appendChild(text("KC-XXXX-XXXX", 28, BOLD)); c.appendChild(text("Sign up at the café's address with this code. One code, one account.", 13, REG, GREY, 600)); c.appendChild(button("Open the café and sign up", true)); body.appendChild(c);
  body.appendChild(text("Then, in your terminal", 16, BOLD));
  const code = card(640, 14, "install lines"); code.fills = solid(BOX);
  for (const l of ["claude plugin marketplace add charredlatte/Pretty-Project-Portfolio", "claude plugin install catio@kittychat"]) code.appendChild(text(l, 13, REG, INK, 600)); body.appendChild(code);
  body.appendChild(text("Where to get help: the docs, the café's House menu, or reply to this email. Your receipt is attached (facture, EI, SIREN, TVA non applicable).", 13, REG, GREY, 640)); }

// 6. Account: the subscription and the café's keys.
{ const { body } = page("6 Account");
  body.appendChild(text("Your account", 32, BOLD));
  const two = row(24, "account");
  const sub = card(500, 20, "subscription"); sub.appendChild(text("Subscription", 16, BOLD)); sub.appendChild(text("Early access · monthly · next billing 3 November 2026", 13, REG, GREY, 460));
  const acts = row(8); for (const a of ["Pause", "Switch to yearly", "Cancel"]) acts.appendChild(button(a)); sub.appendChild(acts);
  sub.appendChild(text("Cancelling ends the subscription at the period's end. Your café stays readable for 30 days, then its house is deleted.", 12, REG, GREY, 460)); two.appendChild(sub);
  const cafe = card(500, 20, "the café"); cafe.appendChild(text("Your café", 16, BOLD)); cafe.appendChild(text("https://catio-gateway.example.workers.dev/cafe", 13, REG, INK, 460)); cafe.appendChild(text("Agent keys: 2 · Rooms: 6 · Repositories: 4", 13, REG, GREY));
  const ca = row(8); ca.appendChild(button("Open the café", true)); ca.appendChild(button("Manage keys")); ca.appendChild(button("Export my data")); cafe.appendChild(ca); two.appendChild(cafe);
  body.appendChild(two);
  body.appendChild(text("Orders and invoices", 16, BOLD));
  for (const o of ["#1003 · 3 October 2026 · Early access, monthly · [monthly] € · Facture PDF", "#1002 · 3 September 2026 · Early access, monthly · [monthly] € · Facture PDF"]) body.appendChild(text(o, 13, REG, INK, 1000)); }

// 7. Legal pages: four tiles, one frame.
{ const { body } = page("7 Legal pages");
  body.appendChild(text("Legal", 32, BOLD));
  const grid = col(16, "tiles"); const r1 = row(16), r2 = row(16);
  const tile = (t, lines) => { const c = card(512, 20, t); c.appendChild(text(t, 16, BOLD)); for (const l of lines) c.appendChild(text("•  " + l, 12, REG, INK, 470)); return c; };
  r1.appendChild(tile("Mentions légales", ["Charlotte Badot, EI · nom commercial", "SIREN · RNE · address · email", "Host: Cloudflare, Inc. (Workers, EU data location where available)", "Directrice de la publication"]));
  r1.appendChild(tile("CGV", ["Object: a hosted subscription to the KittyChat Café, in development", "Price HT, TVA non applicable art. 293 B; monthly or yearly; renewal and cancellation", "Right of withdrawal and its express waiver at checkout", "Médiateur de la consommation: name and address", "Availability, support, what the café never does (resell Claude, read your code)"]));
  r2.appendChild(tile("Politique de confidentialité", ["What the gateway stores: session titles and states, notes, dropped files, keys (hashed)", "Why and how long; deletion 30 days after the subscription ends", "Sub-processors: Cloudflare, Shopify (orders and payment)", "Your rights (RGPD): access, export, erasure; contact"]));
  r2.appendChild(tile("Formulaire de rétractation", ["Model form of annex to art. R221-1 C. conso.", "Only before the service has started, or if the waiver wasn't ticked", "Where to send it, and the refund delay (14 days)"]));
  grid.appendChild(r1); grid.appendChild(r2); body.appendChild(grid); }

// 8 and 9. The phone: home and pricing at 390 wide.
{ const { body, w } = page("8 Home (phone)", 390, 900);
  body.appendChild(text("Every Claude Code session is a cat.", 24, BOLD, INK, w));
  body.appendChild(text("See them all in one café: who's working, who's blocked, who needs you.", 14, REG, GREY, w));
  body.appendChild(button("Start free: self-host", true)); body.appendChild(button("Join the café"));
  body.appendChild(box(w, 240, BOX, "screenshot")); }
{ const { body, w } = page("9 Pricing (phone)", 390, 1100);
  body.appendChild(text("Pricing", 24, BOLD));
  body.appendChild(text("Prices HT · TVA non applicable, art. 293 B du CGI", 12, REG, GREY, w));
  for (const [t, p, primary] of [["Free", "0 €", false], ["Early access", "[monthly] €/month", true], ["Support", "A coffee, or back the app", false]]) {
    const c = card(w, 16, (t === "Support" ? "support" : "tier " + t)); c.appendChild(text(t, 16, BOLD)); c.appendChild(text(p, 18, BOLD, primary ? INK : GREY, w - 32));
    if (t === "Support") { const r = row(8); r.appendChild(button("Buy me a coffee")); r.appendChild(button("Back the app")); c.appendChild(r); }
    else c.appendChild(button(t === "Free" ? "Clone the repo" : "Choose " + t, primary)); body.appendChild(c); } }

return { createdNodeIds: ids };
