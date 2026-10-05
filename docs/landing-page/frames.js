// The KittyChat Café landing page: wireframes, drawn by Figma's own Plugin API (use_figma, or a development
// plugin). Plain grey boxes and Inter, as the shop's and the onboarding's: no art, no pixel font, no prices that
// are decided. docs/landing-page/README.md says what each frame is and lists every decision for Charlotte.
const INK = { r: 0.13, g: 0.12, b: 0.11 }, GREY = { r: 0.55, g: 0.53, b: 0.5 }, LINE = { r: 0.78, g: 0.76, b: 0.73 };
const PAPER = { r: 0.97, g: 0.96, b: 0.94 }, BOX = { r: 0.9, g: 0.89, b: 0.87 }, DIM = { r: 0.82, g: 0.8, b: 0.78 };
const WHITE = { r: 1, g: 1, b: 1 }, NIGHT = { r: 0.16, g: 0.17, b: 0.22 }, NIGHT2 = { r: 0.24, g: 0.25, b: 0.32 };
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
const button = (label, primary = false, dark = false) => {
  const b = figma.createAutoLayout("HORIZONTAL", { name: "button " + label, paddingLeft: 16, paddingRight: 16, paddingTop: 8, paddingBottom: 8, cornerRadius: 4 });
  b.fills = solid(primary ? INK : PAPER); b.strokes = solid(primary ? INK : LINE); b.strokeWeight = 1;
  b.appendChild(text(label, 14, BOLD, primary ? PAPER : INK)); return b;
};
// Containers are see-through: a new auto-layout frame is white, which would hide cream text on the night boxes.
const row = (gap = 12, name = "row") => { const r = figma.createAutoLayout("HORIZONTAL", { name, itemSpacing: gap, counterAxisAlignItems: "CENTER" }); r.fills = []; return r; };
const col = (gap = 12, name = "column") => { const c = figma.createAutoLayout("VERTICAL", { name, itemSpacing: gap }); c.fills = []; return c; };
const card = (w, pad = 16, name = "card", fill = WHITE) => {
  const c = figma.createAutoLayout("VERTICAL", { name, itemSpacing: 10, paddingLeft: pad, paddingRight: pad, paddingTop: pad, paddingBottom: pad, cornerRadius: 6 });
  c.fills = solid(fill); c.strokes = solid(LINE); c.strokeWeight = 1; c.resize(w, c.height); return c;
};
const note = (s, w = 360) => text("✎ " + s, 11, REG, GREY, w);      // an annotation for her, never on the page
const menuItem = (label, hint, on = false) => { const r = row(10, "menu item"); r.appendChild(text(on ? "▶" : "  ", 14, BOLD, INK)); r.appendChild(text(label, 14, BOLD, INK)); if (hint) r.appendChild(text(hint, 12, REG, GREY)); return r; };

const ids = [];
let x = 0;
function frame(name, width = 1440, height = 900, fill = PAPER) {
  const f = figma.createFrame(); f.name = name; f.resize(width, height); f.x = x; f.y = 0; x += width + 120;
  f.fills = solid(fill); figma.currentPage.appendChild(f); ids.push(f.id); return f;
}
function put(f, node, px, py) { f.appendChild(node); node.x = px; node.y = py; return node; }
// The title screen's shell: the dark sky, the scene box anchored at the bottom, the logo, the corner buttons.
function title(name, width = 1440, height = 900) {
  const f = frame(name, width, height, BOX);
  const phone = width < 600;
  const sceneW = phone ? width : Math.ceil(width / 480) * 480, sceneH = sceneW * 270 / 480;
  const scene = put(f, box(sceneW, Math.min(sceneH, height), DIM, "canvas: the fireside scene (landing/art, drawn in code, animated)"), phone ? 0 : (width - sceneW) / 2, phone ? 120 : height - sceneH);
  put(f, text("canvas: the fireside scene. Two cats on a log bench left of the fire, faces lit; logs; a glowing tent; smoke; pines, mountains, the milky way. Scaled by whole numbers, cropped at the sides, the sky colour continues above it.", 12, REG, GREY, phone ? width - 32 : 520), phone ? 16 : 24, phone ? 130 : height - 80);
  const head = col(8, "masthead"); head.appendChild(text("KittyChat Café", phone ? 24 : 32, BOLD, INK)); head.appendChild(text("All your Claude chats, in one cozy café.", 16, REG, INK));
  put(f, head, phone ? 16 : (width - 400) / 2, phone ? 32 : 90);
  const corner = row(8, "corner"); corner.appendChild(button("SOUND OFF")); corner.appendChild(button("STILL")); corner.appendChild(button("SKIP")); put(f, corner, width - (phone ? 240 : 270), 12);
  return { f, scene, phone };
}

// 1. Title screen: PRESS START blinking over the scene.
{ const { f } = title("1 Title screen");
  put(f, button("PRESS START"), 650, 560);
  put(f, note("PRESS START blinks on and off (530 ms each, no fade). Click, Enter or Space starts. The page can still be scrolled: the screens below are ordinary sections.", 420), 920, 560);
  put(f, note("Top right: SOUND OFF (off until she turns it on, remembered) and SKIP for someone who has seen the intro.", 320), 1080, 60); }

// 2. The dialogue: the two cats talk, a page at a time, typewriter.
{ const { f } = title("2 Dialogue");
  const d = card(760, 20, "dialogue box (night panel, 9-slice)", NIGHT2); const inner = row(20, "box"); inner.appendChild(box(68, 68, DIM, "portrait: the orange cat (from the lit sheet)"));
  const t = col(8); t.appendChild(text("BRIOCHE", 13, BOLD, PAPER)); t.appendChild(text("Oh! A visitor. Pull up a log, the fire's warm.▌", 16, REG, PAPER, 620)); inner.appendChild(t); d.appendChild(inner);
  const foot = row(0); foot.appendChild(text("▼", 12, BOLD, PAPER)); d.appendChild(foot);
  put(f, d, 340, 700);
  put(f, note("Typewriter, one character every 30 ms (33 a second) with a quiet tick (if sound is on). A press while it types shows the whole line; the next press turns the page. ▼ bobs 2 pixels at 2 Hz for five seconds. Four pages: Brioche, Pepper, Brioche, Pepper; the last asks where to go and becomes the menu.", 420), 1110, 700); }

// 3. The main menu, in the same box.
{ const { f } = title("3 Main menu");
  const d = card(760, 20, "menu box (night panel)", NIGHT2); const inner = row(20, "box"); inner.appendChild(box(68, 68, DIM, "portrait: the grey cat"));
  const t = col(6); t.appendChild(text("PEPPER", 13, BOLD, PAPER)); t.appendChild(text("Where would you like to go?", 16, REG, PAPER, 620));
  for (const [l, h, on] of [["NEW CAFÉ", "run your own, free", true], ["JOIN THE CAFÉ", "early access", false], ["HOW IT WORKS", "", false], ["SUPPORT THE WORK", "", false]]) { const r = menuItem(l, h, on); r.children.forEach((c) => { if ("fills" in c && c.type === "TEXT") c.fills = solid(PAPER); }); t.appendChild(r); }
  inner.appendChild(t); d.appendChild(inner); put(f, d, 340, 660);
  put(f, note("The pointer ▶ snaps to the item under the mouse or the arrow keys (no sliding). Enter or a click: a short confirm bleep, the screen wipes to black in three steps (240 ms), the page jumps to the section, the wipe lifts. NEW CAFÉ and JOIN THE CAFÉ land on their file slot and press it for a moment.", 420), 1110, 660); }

// 4. How it works: three cards.
{ const f = frame("4 How it works", 1440, 700);
  put(f, text("HOW IT WORKS", 24, BOLD), 200, 80);
  const three = row(24, "three cards");
  for (const [t, d] of [["Your chats become cats", "Work with Claude as you do. Each chat or coding session is a cat, and its project decides which room it lives in."], ["The café asks who's awake", "Each cat checks in at a small front desk with a short note: working, finished, or stuck and needs you. Busy cats play; finished cats sleep."], ["You answer from the page", "A cat that needs you meows. Point at it and it says what it wants. Click it, type a line or drop a file on it, and the queen handles the rest."]]) {
    const c = card(330, 20, "tan panel card"); c.appendChild(box(68, 68, DIM, "portrait")); c.appendChild(text(t, 16, BOLD)); c.appendChild(text(d, 14, REG, GREY, 290)); three.appendChild(c); }
  put(f, three, 200, 150);
  put(f, text("Your private chats stay in your own account. The café shows them; it never reads your code.", 13, REG, GREY, 900), 200, 480);
  put(f, note("Plain words, as the onboarding decided on 3 October: cats, rooms, the front desk, the queen. No MCP, API, gateway or LLM anywhere a sentence explains.", 420), 200, 540); }

// 5. Choose your file: the three ways to get the café as save slots.
{ const f = frame("5 Choose your file", 1440, 760);
  put(f, text("CHOOSE YOUR FILE", 24, BOLD), 200, 80);
  const slots = col(20, "slots");
  for (const [n, p, d, b, primary, hearts] of [
    ["FILE 1 · RUN YOUR OWN", "Free · open today", "The developers' door: clone it, deploy the front desk, install the plugin. Your art, your page. A terminal, this once.", "START A NEW CAFÉ", true, "♥♥♥"],
    ["FILE 2 · THE HOSTED CAFÉ", "[monthly] € a month · early access", "Your café on our address, nothing to install. Not open yet: join the list and be first through the door. Prices HT, TVA non applicable, art. 293 B du CGI.", "JOIN THE LIST", false, "♡♡♡"],
    ["FILE 3 · SET UP FOR YOU", "From 90 €, once", "An afternoon with Charlotte setting up your own café, from [setup-plus] €; or, from 90 €, the DIY course on customizing it and lifetime access to the hosted café when it opens.", "WRITE TO CHARLOTTE", false, "♥♥♥"]]) {
    const s = card(1040, 16, "file slot (night panel)", NIGHT2); const r = row(20); r.appendChild(text("▶", 14, BOLD, PAPER));
    const c = col(6); c.appendChild(text(n + "   " + hearts, 14, BOLD, PAPER)); c.appendChild(text(p, 16, REG, PAPER)); c.appendChild(text(d, 13, REG, DIM, 700)); r.appendChild(c); r.appendChild(button(b, primary)); s.appendChild(r); slots.appendChild(s); }
  put(f, slots, 200, 150);
  put(f, note("Zelda's file select: three slots, the pointer on the one under the mouse or focus. Hearts full = open today; outlined = not open yet (the hosted café is honest about being early access). Prices stay in brackets until she picks them. JOIN THE LIST is a mailto until the shop exists.", 480), 200, 640); }

// 6. Ask the queen (FAQ), Support, the legal footer.
{ const f = frame("6 FAQ, support, footer", 1440, 900);
  put(f, text("ASK THE QUEEN", 24, BOLD), 200, 60);
  const faq = col(0, "faq");
  for (const q of ["Do I need to know how to code?", "Does the café read my code?", "Is this Claude?", "Who sees my data?", "Can I stop?"]) { const r = row(12, "question"); r.appendChild(text("▶", 12, BOLD, GREY)); r.appendChild(text(q, 16, REG, INK, 900)); faq.appendChild(r); faq.appendChild(box(1040, 1, LINE, "rule")); }
  put(f, faq, 200, 110);
  put(f, note("Each question opens like a menu item (details/summary): the pointer on hover, the answer under it. The queen is the house's assistant in the product, so the FAQ is hers.", 420), 200, 330);
  put(f, text("SUPPORT THE WORK", 24, BOLD), 200, 420);
  const sup = row(20); sup.appendChild(box(68, 68, DIM, "portrait")); const sc = col(10); sc.appendChild(text("The café is open source, and I am one person building it between a stationery shop and a lot of cats. The subscription and the campaign fund the app, planned for December 2027. A coffee is thanks and a name in the credits; backing the app is a year of early access.", 14, REG, INK, 760)); sc.appendChild(text("Charlotte, who runs the café.", 12, REG, GREY));
  const sb = row(12); sb.appendChild(button("BUY ME A COFFEE")); sb.appendChild(button("BACK THE APP")); sc.appendChild(sb); sup.appendChild(sc); put(f, sup, 200, 470);
  const foot = col(10, "footer"); const links = row(20); for (const l of ["Mentions légales", "CGV", "Confidentialité", "Rétractation", "Contact"]) links.appendChild(text(l, 12, REG, GREY)); foot.appendChild(links);
  foot.appendChild(text("KittyChat Café · Charlotte Badot, EI. The fire, the cats, the tent and the night were drawn for this page. Type: Press Start 2P, Pixelify Sans and Nunito, under the SIL Open Font License.", 12, REG, GREY, 1000)); put(f, foot, 200, 760); }

// 7. The loading frame.
{ const f = frame("7 Loading frame", 1440, 900, NIGHT);
  const c = col(16, "now loading"); c.counterAxisAlignItems = "CENTER"; c.appendChild(text("NOW LOADING", 16, BOLD, PAPER)); c.appendChild(box(240, 16, DIM, "bar: fills as the pictures load")); const paws = row(12, "paws"); for (let i = 0; i < 3; i++) paws.appendChild(box(32, 32, DIM, "paw " + (i + 1))); c.appendChild(paws); put(f, c, 600, 400);
  put(f, note("Shown while the fifteen pictures load, never less than half a second so it never flashes, and it fades to the title in three steps. Three paws step in turn (1.2 s loop). Honest: it waits for something real.", 420), 510, 520); }

// 8. Every control and its states.
{ const f = frame("8 Controls and states", 1440, 900);
  put(f, text("Buttons", 18, BOLD), 80, 60);
  const states = row(20); for (const s of ["idle", "hover: white face, ▶ shows", "pressed: drops 4 px, shadow gone", "focus: gold ring", "disabled: faded"]) { const c = col(8); c.appendChild(button("START A NEW CAFÉ", true)); c.appendChild(text(s, 11, REG, GREY, 150)); states.appendChild(c); } put(f, states, 80, 100);
  put(f, text("Menu items and file slots", 18, BOLD), 80, 260);
  const m = row(40); for (const [l, s] of [["  NEW CAFÉ", "idle"], ["▶ NEW CAFÉ", "hover or focus: pointer, white text"], ["▶ NEW CAFÉ", "confirm: bleep, wipe, jump"]]) { const c = col(8); c.appendChild(text(l, 14, BOLD)); c.appendChild(text(s, 11, REG, GREY, 180)); m.appendChild(c); } put(f, m, 80, 300);
  put(f, text("Dialogue", 18, BOLD), 80, 420);
  const d = row(40); for (const [l, s] of [["Text▌", "typing, one character every 30 ms, cursor blinks"], ["▼", "page done: bobs 2 px at 2 Hz, a 44 px target"], ["(menu)", "last page: the menu replaces ▼"]]) { const c = col(8); c.appendChild(text(l, 14, BOLD)); c.appendChild(text(s, 11, REG, GREY, 180)); d.appendChild(c); } put(f, d, 80, 460);
  put(f, text("Corner", 18, BOLD), 80, 580);
  const k = row(20); for (const [l, s] of [["SOUND OFF", "default: no sound"], ["SOUND ON", "pressed look; bleeps on move, confirm, back, type"], ["STILL", "stops the scene; remembered; pressed under reduced motion"], ["SKIP", "straight to the menu"]]) { const c = col(8); c.appendChild(button(l, l === "SOUND ON")); c.appendChild(text(s, 11, REG, GREY, 160)); k.appendChild(c); } put(f, k, 80, 620);
  put(f, text("Pointer", 18, BOLD), 80, 740); put(f, text("A cat paw (16 × 16, our own), tip at the top left, on anything clickable. The arrow elsewhere.", 12, REG, GREY, 600), 80, 780);
  put(f, note("Sounds are four oscillator bleeps made in the page (no sound files): move 880 Hz 50 ms; confirm 660→990; back 440→330; a 15 ms tick every other letter. Off by default.", 420), 900, 60); }

// 9. The motion sheet: every animation, its timing, and what reduced motion does.
{ const f = frame("9 Motion sheet", 1440, 900);
  put(f, text("Every motion on the page", 18, BOLD), 80, 60);
  const rows = [["What", "Timing", "Reduced motion"],
    ["Loading frame", "≥ 500 ms, bar fills with real loads, fades out in 3 steps", "no minimum, no fade"],
    ["PRESS START", "blinks 530 ms on / 530 ms off, no fade; four blinks then it holds", "steady"],
    ["STILL", "the scene can be stopped at any time; remembered", "starts stopped"],
    ["Fire", "8 frames at 10 fps", "frame 1, still"],
    ["Firelight", "flicker between 3 baked levels every 90 ms, no blending", "level 2, still"],
    ["Smoke", "a particle every 380 ms, rises 26–40 px over 3–5 s, sine wobble, 3 opacity steps", "none"],
    ["Stars", "each twinkling star flips dim/bright on its own 0.4–3.5 s clock; a shooting star every 25–50 s", "still"],
    ["Tent glow", "3 opacity levels, one step every 800 ms", "middle level"],
    ["Cats", "breathe every 1.2 s; blink 180 ms every 2.5–7 s; an ear flick 260 ms; the tail 420 ms", "still"],
    ["Dialogue box", "grows open in 3 steps over 200 ms", "simply there"],
    ["Typewriter", "one character every 30 ms (Stardew's delay); a press completes the line", "the whole line at once"],
    ["Advance arrow ▼", "bobs 2 px at 2 Hz in 2 steps", "still"],
    ["Menu items", "appear one by one, 120 ms apart, no fade", "all at once"],
    ["Menu pointer", "snaps, no easing", "same"],
    ["Confirm", "the screen wipes to black in 3 steps over 240 ms, jumps, lifts in 3 steps", "a plain jump"],
    ["Buttons", "press drops 4 px, no transition", "same"],
    ["Sections", "none: no scroll reveals, no parallax", "same"]];
  const grid = col(6, "motion"); rows.forEach((r, i) => { const rr = row(0); r.forEach((cell, k) => rr.appendChild(text(cell, 12, i === 0 ? BOLD : REG, i === 0 ? GREY : INK, k === 0 ? 220 : k === 1 ? 640 : 300))); grid.appendChild(rr); }); put(f, grid, 80, 110); }

// 10 and 11. The phone: title and files at 390.
{ const { f } = title("10 Title (phone)", 390, 844); put(f, button("PRESS START"), 120, 420);
  put(f, note("On a phone the scene sits between the logo and the dialogue instead of under them: 480 wide cropped to 390, so the bench and the tent stay in view.", 358), 16, 500); }
{ const f = frame("11 Files (phone)", 390, 1100);
  put(f, text("CHOOSE YOUR FILE", 20, BOLD), 16, 40);
  const slots = col(16); for (const [n, p, b, primary] of [["FILE 1 · RUN YOUR OWN", "Free · open today", "START A NEW CAFÉ", true], ["FILE 2 · THE HOSTED CAFÉ", "[monthly] € a month · early access", "JOIN THE LIST", false], ["FILE 3 · SET UP FOR YOU", "From 90 €, once", "WRITE TO CHARLOTTE", false]]) {
    const s = card(358, 14, "file slot", NIGHT2); s.appendChild(text(n, 13, BOLD, PAPER)); s.appendChild(text(p, 15, REG, PAPER)); s.appendChild(button(b, primary)); slots.appendChild(s); } put(f, slots, 16, 90); }

return { createdNodeIds: ids };
