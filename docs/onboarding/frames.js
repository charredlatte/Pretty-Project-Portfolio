// The onboarding wireframes, drawn by Figma's own Plugin API (use_figma, or a development plugin).
// Plain grey boxes and Inter: no art from the packs, no kits. docs/onboarding/README.md says what each frame is.
const INK = { r: 0.13, g: 0.12, b: 0.11 }, GREY = { r: 0.55, g: 0.53, b: 0.5 }, LINE = { r: 0.78, g: 0.76, b: 0.73 };
const PAPER = { r: 0.97, g: 0.96, b: 0.94 }, BOX = { r: 0.9, g: 0.89, b: 0.87 }, DIM = { r: 0.82, g: 0.8, b: 0.78 };
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
  f.fills = solid({ r: 1, g: 1, b: 1 }); f.strokes = solid(LINE); f.strokeWeight = 1;
  f.appendChild(text(placeholder, 14, REG, GREY)); f.resize(w, f.height); return f;
};
const row = (gap = 12, name = "row") => figma.createAutoLayout("HORIZONTAL", { name, itemSpacing: gap, counterAxisAlignItems: "CENTER" });
const col = (gap = 12, name = "column") => figma.createAutoLayout("VERTICAL", { name, itemSpacing: gap });

const ids = [];
let x = 0;
const STEPS = ["Welcome", "Rooms", "GitHub", "Sessions", "Litter box", "How it works", "Done"];

// The screen: house, brand, map panel. Returns the frame and the dialog's column, when asked for.
function screen(name, withDialog) {
  const f = figma.createFrame(); f.name = name; f.resize(1280, 800); f.x = x; f.y = 0; x += 1380;
  f.fills = solid(PAPER); figma.currentPage.appendChild(f); ids.push(f.id);
  const house = box(1280, 800, withDialog ? DIM : BOX, "house: the manor fills the screen"); f.appendChild(house);
  const h = text(withDialog ? "" : "the house (one floor at a time)", 14, REG, GREY); f.appendChild(h); h.x = 560; h.y = 390;
  const brand = row(8, "brand / House button"); brand.appendChild(box(32, 32, BOX, "logo")); brand.appendChild(text("KittyChat Café", 16, BOLD));
  f.appendChild(brand); brand.x = 16; brand.y = 16;
  const map = col(6, "map panel"); map.appendChild(box(160, 100, BOX, "minimap"));
  const mr = row(6, "map buttons"); for (const l of ["−", "+", "⌂", "1", "2"]) mr.appendChild(button(l)); map.appendChild(mr);
  f.appendChild(map); map.x = 1280 - 16 - map.width; map.y = 16;
  return f;
}

// A wizard step: dots, title, content, Back and Next.
function step(n, title, content, nextLabel = "Next") {
  const f = screen("Wizard " + n + ": " + title, true);
  const d = figma.createAutoLayout("VERTICAL", { name: "dialog", itemSpacing: 20, paddingLeft: 32, paddingRight: 32, paddingTop: 24, paddingBottom: 24, cornerRadius: 8 });
  d.fills = solid(PAPER); d.strokes = solid(LINE); d.strokeWeight = 2;
  const dots = row(8, "steps");
  STEPS.forEach((s, i) => { const e = figma.createEllipse(); e.resize(10, 10); e.fills = solid(i === n - 1 ? INK : LINE); e.name = s; dots.appendChild(e); });
  d.appendChild(dots);
  d.appendChild(text(title, 24, BOLD));
  d.appendChild(content);
  const nav = row(12, "nav"); nav.appendChild(button("Back")); nav.appendChild(button(nextLabel, true)); d.appendChild(nav);
  f.appendChild(d); d.resize(640, d.height); d.x = 320; d.y = Math.max(40, (800 - d.height) / 2);
  nav.layoutSizingHorizontal = "FILL"; nav.primaryAxisAlignItems = "SPACE_BETWEEN";
  return f;
}

// 1. The layout, with no dialog.
screen("Layout: the shell", false);

// 2. Welcome.
{ const c = col(12); c.appendChild(text("All your Claude chats, in one cozy café. Each chat becomes a cat, each project a room. Claude on its own is a stripped car: a brilliant engine, with no seatbelts, no windshield and no tires. The café is the rest of the car, and Simone, the queen cat, drives. Give the café a name.", 14, REG, INK, 560));
  c.appendChild(text("Name your café", 12, BOLD, GREY)); c.appendChild(field("KittyChat Café", 400)); step(1, "Welcome", c); }

// 3. Rooms.
{ const c = col(16);
  const n = row(12, "how many"); n.appendChild(text("How many rooms?", 14, BOLD)); n.appendChild(button("−")); n.appendChild(text("4", 20, BOLD)); n.appendChild(button("+")); c.appendChild(n);
  const grid = col(8, "rooms grid"); const names = ["Lounge", "Café", "Kitchen", "Craft room", "Terrace", "Catio", "Library", "Bedroom", "Bath", "Hall"];
  for (let r = 0; r < 2; r++) { const rr = row(8); for (let i = 0; i < 5; i++) { const k = r * 5 + i; const cell = figma.createAutoLayout("VERTICAL", { name: "room " + names[k], paddingLeft: 8, paddingRight: 8, paddingTop: 8, paddingBottom: 8, cornerRadius: 4 });
    cell.fills = solid(k < 4 ? { r: 1, g: 1, b: 1 } : DIM); cell.strokes = solid(LINE); cell.strokeWeight = 1; cell.resize(104, 56);
    cell.appendChild(text(names[k], 12, k < 4 ? BOLD : REG, k < 4 ? INK : GREY)); cell.appendChild(text(k < 4 ? "open" : "closed", 10, REG, GREY)); rr.appendChild(cell); } grid.appendChild(rr); }
  c.appendChild(grid); c.appendChild(text("The first rooms open from the front of the house. Closed rooms stay dark until you open them under Edit rooms.", 12, REG, GREY, 560));
  const nm = col(6, "names"); nm.appendChild(text("Name the open rooms", 12, BOLD, GREY));
  for (const r of ["Lounge: new cats come in here", "Café", "Kitchen", "Craft room"]) nm.appendChild(field(r, 400)); c.appendChild(nm);
  step(2, "Rooms", c); }

// 4. GitHub, connected, and the not-connected state beside it.
{ const c = col(12); c.appendChild(text("The tires. Your repositories are where the work meets the road.", 14, BOLD, INK, 560)); c.appendChild(text("Each repository lives in a room. Its sessions are that room's cats.", 14, REG, INK, 560));
  c.appendChild(button("Connect GitHub", true));
  const list = col(6, "repos"); for (const r of [["my-portfolio", "Lounge"], ["grocery-app", "Kitchen"], ["shop-theme", "Craft room"], ["tiktok-saves", "Lounge"]]) {
    const li = row(12, "repo"); li.appendChild(text(r[0], 14, REG, INK, 240)); li.appendChild(field(r[1] + " ▾", 160)); list.appendChild(li); }
  c.appendChild(list); c.appendChild(text("Anything not listed goes to the lounge.", 12, REG, GREY)); step(3, "GitHub", c); }
{ const c = col(12); c.appendChild(text("The tires. Your repositories are where the work meets the road.", 14, BOLD, INK, 560)); c.appendChild(text("Not connected.", 14, BOLD)); c.appendChild(text("Connect GitHub in claude.ai (Settings → Connectors), and install the Claude GitHub App on your repositories. Then check again.", 14, REG, INK, 560));
  c.appendChild(button("Check again", true)); const f = step(3, "GitHub", c, "Skip for now"); f.name = "Wizard 3b: GitHub, not connected"; }

// 5. Sessions, and the blocked state.
{ const c = col(12); c.appendChild(text("The windshield. Through it you see every chat on the road, each one a cat.", 14, BOLD, INK, 560)); c.appendChild(text("5 sessions found. They'll move in when you open the doors.", 14, REG, INK, 560));
  const list = col(6, "sessions"); for (const s of ["Fix the basket total · grocery-app · needs you", "Draw the terrace · my-portfolio · working", "Theme colours · shop-theme · done"]) { const li = row(8); li.appendChild(box(24, 24, BOX, "cat")); li.appendChild(text(s, 13)); list.appendChild(li); }
  c.appendChild(list); step(4, "Sessions", c); }
{ const c = col(12); c.appendChild(text("The windshield. Through it you see every chat on the road, each one a cat.", 14, BOLD, INK, 560)); c.appendChild(text("claude.ai didn't let the page read your sessions. A saved copy shows instead, and Claude refreshes it from a session.", 14, REG, INK, 560)); const f = step(4, "Sessions", c, "Skip for now"); f.name = "Wizard 4b: Sessions, blocked"; }

// 6. Litter box.
{ const c = col(12); c.appendChild(text("The glovebox. Loose notes, half-ideas, things for later. Drop them in. The sifter guesses whose they are, and nothing leaves until you've checked.", 14, REG, INK, 560));
  const drop = figma.createAutoLayout("VERTICAL", { name: "drop zone", paddingTop: 28, paddingBottom: 28, primaryAxisAlignItems: "CENTER", counterAxisAlignItems: "CENTER" });
  drop.fills = solid({ r: 1, g: 1, b: 1 }); drop.strokes = solid(GREY); drop.strokeWeight = 1; drop.dashPattern = [6, 4]; drop.cornerRadius = 6;
  drop.appendChild(text("Drop a note here", 14, REG, GREY)); c.appendChild(drop); drop.resize(560, drop.height);
  const sw = row(10, "switch"); sw.appendChild(box(36, 20, INK, "toggle on")); sw.appendChild(text("Hold pull requests that need my eye here too", 14)); c.appendChild(sw);
  step(5, "Litter box", c); }

// 7. How it works.
{ const c = col(10);
  c.appendChild(text("Claude on its own is a stripped car: an engine, and nothing else. The café is the rest of it:", 14, REG, INK, 560));
  for (const l of [["Simone drives.", "The queen cat at the wheel: she runs your routines, passes your words to the cats and tells you what they're up to, from your own computer."],
    ["The windshield and the dashboard.", "Each chat is a cat in its project's room, checking in as it works: busy, finished, or stuck and needs you. The badge counts who needs you."],
    ["Seatbelts and brakes.", "Checks run before a cat may change or publish anything, and Claude can't talk its way round them. Anything it guessed waits for you."],
    ["The intercom.", "The café can't wake a cat. What you say is kept, and the cat hears it the next time it checks in."],
    ["The glovebox.", "Loose notes and held pull requests wait in the litter box until you check them."]]) {
    const li = col(2, "part"); li.appendChild(text(l[0], 14, BOLD)); li.appendChild(text(l[1], 13, REG, GREY, 560)); c.appendChild(li); }
  c.appendChild(text("The seatbelts and brakes come as a Claude Code plugin. Two lines fit them:", 13, REG, GREY, 560));
  const code = col(4, "install lines"); for (const l of ["claude plugin marketplace add https://github.com/charredlatte/Pretty-Project-Portfolio.git", "claude plugin install kittychat-house-rules@kittychat --scope user"]) code.appendChild(text(l, 12, REG, INK, 560)); c.appendChild(code);
  step(6, "How it works", c); }

// 8. Done.
{ const c = col(8); c.appendChild(text("Your car is ready, and Simone has the keys.", 14, REG, INK, 560)); for (const l of ["KittyChat Café", "4 rooms open", "4 repositories filed", "5 cats at the door"]) c.appendChild(text("✓  " + l, 14));
  step(7, "Done", c, "Open the doors"); }

return { createdNodeIds: ids };
