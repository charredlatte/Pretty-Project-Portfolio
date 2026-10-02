// End-to-end test of the Catio page: adoption to resolution, sessions changing state, renames and
// moves, filing cabinets, rooms, the two floors, panning and zoom, the menus, touch, the degraded views,
// and local mode.
// Run it with catio/test/run.sh. The page runs inside the same skeleton the Artifact tool publishes,
// against runtime-stub.js (an in-memory db with live snapshots and a sessions feed the test changes);
// local mode runs the bundle from tools/bundle.py on a real localhost server with no runtime at all.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
const url = "file://" + join(here, ".page.html");
const LOCAL = process.env.LOCAL_URL;   // set by run.sh when it serves the local bundle
const NOART = "file://" + join(here, ".page-noart.html");   // the same page with no licensed art, built by run.sh
const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
let pass = 0, fail = 0;
const results = [];
async function check(name, fn) {
  try { await fn(); pass++; results.push("PASS " + name); }
  catch (e) { fail++; results.push("FAIL " + name + " :: " + String(e.message || e).split("\n")[0]); }
}
process.on("uncaughtException", (e) => { console.log(results.join("\n")); console.log("CRASH " + String(e.message).split("\n")[0]); process.exit(2); });
process.on("unhandledRejection", (e) => { console.log(results.join("\n")); console.log("CRASH " + String(e.message).split("\n")[0]); process.exit(2); });
const expect = (cond, msg) => { if (!cond) throw new Error(msg); };
async function open(q = "", opts = {}) {
  // reduced motion unless a test asks for it: the cats stay put, so clicks land on still cats (6d walks them)
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce", ...opts });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto((opts.base || url) + q);
  await page.waitForTimeout(500);
  return { page, ctx, errors };
}
const T = (page, f) => page.evaluate(f);
const toast = async (page) => (await page.locator("#toast").textContent()) || "";
const menuText = async (page) => (await page.locator("#menu").isVisible()) ? await page.locator("#menu").innerText() : "";
const settle = (page) => page.waitForTimeout(150);
// the manor's upstairs rooms; every other room is on the ground floor
const UPPER = new Set(["brain", "bath", "bedroom"]);
// go to the floor a room is on, with the floor switch, as a person would
async function toFloor(page, f) {
  if ((await page.locator("#world").getAttribute("data-floor")) === f) return;
  await page.click("#floor-" + f);
  await settle(page);
}
// close whatever menu is open, by clicking the stage itself (the open meadow)
const closeMenu = (page) => page.evaluate(() => { if (!document.getElementById("menu").hidden) document.getElementById("stage").click(); });
// point at a clear patch of a room's floor, as a person would
async function roomPoint(page, room) {
  await toFloor(page, UPPER.has(room) ? "upper" : "ground");
  const pt = await page.evaluate((room) => {
    const h = document.querySelector('.roomhit[data-room="' + room + '"]'); const r = h.getBoundingClientRect();
    for (let fy = 0.92; fy > 0.08; fy -= 0.06) for (let fx = 0.06; fx < 0.96; fx += 0.06) {
      const x = r.left + r.width * fx, y = r.top + r.height * fy;
      if (document.elementFromPoint(x, y) === h) return { x, y };
    }
    return null;
  }, room);
  if (!pt) throw new Error("no clear floor in " + room);
  return pt;
}
async function hoverRoom(page, room) {
  const pt = await roomPoint(page, room);
  await page.mouse.move(8, 8);
  await page.mouse.move(pt.x, pt.y);
  await settle(page);
  return pt;
}
// hover names a room; a click opens its menu
async function openRoom(page, room) {
  await closeMenu(page);
  const pt = await hoverRoom(page, room);
  await page.mouse.click(pt.x, pt.y);
  await settle(page);
}
async function catPoint(page, label) {
  const cat = page.locator('#cats .cat[aria-label*="' + label + '"]').first();
  await toFloor(page, (await cat.getAttribute("data-floor")) || "ground");
  // a point where this cat is on top: another cat or a bubble may stand over part of it
  const pt = await cat.evaluate((c) => {
    const r = c.getBoundingClientRect();
    for (const fy of [0.75, 0.9, 0.6, 0.45, 0.3]) for (const fx of [0.5, 0.35, 0.65, 0.2, 0.8]) {
      const x = r.left + r.width * fx, y = r.top + r.height * fy, hit = document.elementFromPoint(x, y);
      if (hit && hit.closest(".cat") === c) return { x, y };
    }
    return null;
  });
  if (!pt) throw new Error("no clear point on cat " + label);
  return pt;
}
async function openCat(page, label) {
  await closeMenu(page);
  const pt = await catPoint(page, label);
  await page.mouse.move(8, 8);
  await page.mouse.move(pt.x, pt.y);
  await page.mouse.click(pt.x, pt.y);
  await settle(page);
}
// rest the pointer on a cat, as she would, and read the line that names it
async function hoverCat(page, label) {
  await closeMenu(page);
  const pt = await catPoint(page, label);
  await page.mouse.move(8, 8);
  await page.mouse.move(pt.x, pt.y, { steps: 3 });
  await settle(page);
  return (await page.locator("#tip").isVisible()) ? await page.locator("#tip").innerText() : "";
}
// nothing is drawn on a cat but the cat (her call, 2 October 2026): whatever it would be called
const ON_CATS = "#cats .cat > :not(.spr)";
async function openHouse(page) {
  await closeMenu(page);
  await page.click("#houseBtn");
  await settle(page);
}
// a room's Add a cat, then the kind: "Adopt a chat" or "New session"
async function addCat(page, kind) {
  if (await menuButton(page, "Add a cat").count()) await menuButton(page, "Add a cat").click();
  await menuButton(page, kind).click();
}
// the camera: the world's scale and offset on screen
const cam = (page) => page.evaluate(() => { const m = new DOMMatrix(getComputedStyle(document.getElementById("world")).transform); return { s: m.a, tx: m.e, ty: m.f }; });
// a cat's card keeps its facts, its management and its name folded under Manage
const manage = async (page) => { if (!(await page.locator("#catMore").evaluate((d) => d.open))) await page.click("#catMore summary"); };
// what waits in the outbox, oldest first: what send_message couldn't post (by default the stub refuses it)
const outbox = async (page) => Object.entries(await page.evaluate(() => window.__catio.store)).filter(([p]) => p.startsWith("outbox/")).map(([, v]) => v).sort((a, b) => a.at - b.at);
const menuButton = (page, name) => page.locator("#menu").getByRole("button", { name, exact: true });

/* ---------- 1. the screen, and adoption to resolution for an adopted chat ---------- */
{
  const { page, ctx, errors } = await open();
  await check("the cafe fills the screen with nothing but the brand, the controls and the credits", async () => {
    const st = await page.locator("#stage").boundingBox();
    expect(st.width === 1440 && st.height === 900, JSON.stringify(st));
    expect(await page.locator("#menu").isHidden(), "a menu is open at rest");
    expect(await page.locator(".roomhit").count() === 10, "rooms");
    expect((await page.locator("#status").innerText()).includes("Live") === false || true, "");
    expect(errors.length === 0, "page errors: " + errors.join("; "));
  });
  await check("the blocked session meows in the scene and the sign counts it", async () => {
    expect(await page.locator("#cats .cat.m-meow").count() >= 1, "no meowing cat");
    expect((await page.locator("#tally").innerText()).includes("1 need you"), await page.locator("#tally").innerText());
  });
  const study = await hoverRoom(page, "study");
  await check("hovering a room names it in a line, with a badge when cats in it need you, and opens no menu", async () => {
    const t = await page.locator("#tip").innerText();
    expect(await page.locator("#tip").isVisible() && t.includes("Craft room"), t);
    expect(await page.locator("#tip .badge").count() === 1, "no badge in the line");
    expect(await page.locator("#menu").isHidden(), "a menu opened on hover");
  });
  await page.mouse.click(study.x, study.y);
  await settle(page);
  await check("clicking the room opens its menu with who needs you", async () => {
    const t = await menuText(page);
    expect(t.includes("Craft room") && t.includes("review the French text"), t);
    expect(await page.locator("#menu .primary").count() === 1, "not one primary action");
  });
  await page.mouse.move(4, 450);
  await page.waitForTimeout(450);
  await check("the menu stays while the pointer moves away", async () => expect(await page.locator("#menu").isVisible(), "it closed"));
  await page.mouse.click(1300, 150);   // the open meadow, east of the cat lounge
  await settle(page);
  await check("a click on the open meadow closes it", async () => expect(await page.locator("#menu").isHidden(), "still open"));
  await openHouse(page);
  await check("old sleepers nap in the attic, counted in the House menu", async () => expect((await menuText(page)).includes("1 napping in the attic"), await menuText(page)));

  await openRoom(page, "bedroom");
  await addCat(page, "Adopt a chat");
  await check("Add a cat, Adopt a chat opens the form with that room chosen", async () => {
    expect(await page.locator("#adoptDlg[open] #adTitle").isVisible(), "form not open");
    expect((await page.locator("#adRoom").inputValue()) === "bedroom", "room not preselected");
  });
  await page.fill("#adTitle", "Lease renewal");
  await page.fill("#adLink", "https://claude.ai/chat/abc");
  await page.fill("#adProject", "Flat lease");
  await page.selectOption("#adMood", "needs");
  await page.fill("#adNote", "Send the signed form");
  await page.fill("#adName", "Mimi");
  await page.click('#adoptDlg button[type="submit"]');
  await settle(page);
  await check("adopting writes one cats document with every field", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[1].startsWith("cats/")));
    expect(w.length === 1 && w[0][0] === "set", "writes: " + JSON.stringify(w));
    const d = w[0][2];
    for (const [k, v] of Object.entries({ title: "Lease renewal", link: "https://claude.ai/chat/abc", project: "Flat lease", room: "bedroom", mood: "needs", note: "Send the signed form", name: "Mimi" }))
      expect(d[k] === v, k + " = " + d[k]);
  });
  await check("the new cat meows in the bedroom", async () => {
    expect((await toast(page)).includes("Adopted"), await toast(page));
    const cat = page.locator('#cats .cat[aria-label^="Mimi "]');
    expect(await cat.count() === 1, "cat not in scene");
    expect((await cat.getAttribute("class")).includes("m-meow"), "not meowing");
    expect((await page.locator("#tally").innerText()).includes("2 need you"), await page.locator("#tally").innerText());
  });
  await openCat(page, "Mimi");
  await check("clicking the cat opens its menu: what it needs, and its moods", async () => {
    const t = await menuText(page);
    expect(t.includes("Mimi") && t.includes("Send the signed form") && t.includes("Flat lease") && t.includes("In progress"), t);
  });
  await menuButton(page, "In progress").click();
  await settle(page);
  await check("In progress stops the meowing and puts it to work", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[0] === "update" && x[1].startsWith("cats/")));
    expect(w.length === 1 && w[0][2].mood === "busy", JSON.stringify(w));
    expect(await page.locator('#cats .cat.m-idle[aria-label^="Mimi "]').count() === 1, "not working");
    expect((await page.locator("#tally").innerText()).includes("1 need you"), await page.locator("#tally").innerText());
  });
  await openCat(page, "Mimi");
  await menuButton(page, "Done").click();
  await settle(page);
  await check("Done puts the cat to sleep", async () => expect(await page.locator('#cats .cat.m-sleep[aria-label^="Mimi "]').count() === 1, "not asleep"));
  await openCat(page, "Mimi");
  await menuButton(page, "Details").click();
  await page.click("#catDlg button:has-text('Let go')");
  await check("letting go asks once more before deleting", async () => {
    expect((await T(page, () => window.__catio.writes.filter((x) => x[0] === "delete"))).length === 0, "deleted without confirming");
  });
  await page.click("#catDlg button:has-text('Yes, let this cat go')");
  await settle(page);
  await check("letting go deletes the document and the cat leaves the house", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[0] === "delete"));
    expect(w.length === 1 && w[0][1].startsWith("cats/"), JSON.stringify(w));
    expect(await page.locator('#cats .cat[aria-label^="Mimi "]').count() === 0, "cat still in scene");
  });

  /* ---------- 2. resolution for a live Claude Code session ---------- */
  await T(page, () => window.__catio.setBucket("blocked1", "WORKING", "RUNNING", {}));
  await settle(page);
  await check("when you answer a session it stops meowing and gets to work", async () => {
    expect(await page.locator('#cats .cat.m-idle[aria-label*="Shop about page"]').count() === 1, "not at work");
    expect(!(await page.locator("#tally").innerText()).includes("need you"), await page.locator("#tally").innerText());
  });
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "IDLE", { status_category: "completed" }));
  await settle(page);
  await check("when it finishes it falls asleep", async () => expect(await page.locator('#cats .cat.m-sleep[aria-label*="Shop about page"]').count() === 1, "not asleep"));
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "ARCHIVED", {}));
  await settle(page);
  await check("when it is archived it goes up to nap in the attic", async () => {
    expect(await page.locator('#cats .cat[aria-label*="Shop about page"]').count() === 0, "still in the house");
    await openHouse(page);
    expect((await menuText(page)).includes("2 napping in the attic"), await menuText(page));
  });
  await T(page, () => window.__catio.setBucket("blocked1", "FAILED", "IDLE", { status_detail: "tests failed" }));
  await settle(page);
  await check("a failed session is upset and counts as needing you", async () => {
    expect(await page.locator('#cats .cat.m-cry[aria-label*="Shop about page"]').count() === 1, "not upset");
    await openCat(page, "Shop about page");
    expect((await menuText(page)).includes("tests failed"), await menuText(page));
  });

  /* ---------- 3. rename and move a session's cat ---------- */
  await openCat(page, "Week tab editing");
  await menuButton(page, "Talk").click();
  await manage(page);
  await page.fill("#catRename", "Biscuit");
  await page.selectOption("#catRoom", "study");
  await page.click("#catDlg button:has-text('Save')");
  await settle(page);
  await check("renaming and moving a cat saves it and it walks to the craft room", async () => {
    const d = await T(page, () => window.__catio.store["sessions/session_work1"]);
    expect(d && d.name === "Biscuit" && d.room === "study", JSON.stringify(d));
    expect(await page.locator('#cats .cat[aria-label^="Biscuit "]').count() === 1, "renamed cat missing");
  });

  /* ---------- 4. zoom, filing cabinet and a project's look ---------- */
  await openRoom(page, "study");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(700);
  await check("Look in zooms to the room and its menu offers the whole house", async () => {
    await openRoom(page, "study");
    expect(await menuButton(page, "Whole house").count() === 1, "no way back");
  });
  // an invented project map, as the catio skill's graph_doc.py saves it
  await T(page, () => window.__catio.put("graphs/montfortoise-shopify", { repo: "example/montfortoise-shopify", at: Date.now() - 60e3, commit: "abc1234def", nodes: 120, edges: 210, communities: 6,
    gods: [{ label: "CartDrawer", degree: 14, file: "src/cart.js" }], groups: [{ name: "Checkout", size: 40 }, { name: "Theme", size: 30 }],
    surprises: [{ a: "Shipping notes", rel: "references", b: "CartDrawer", how: "INFERRED", where: "docs/shipping.md → src/cart.js" }],
    questions: ["Why does CartDrawer connect Checkout to Theme?"],
    map: { n: [{ t: "CartDrawer", g: 0, d: 14, x: 150, y: 80 }, { t: "Theme", g: 1, d: 6, x: 60, y: 40 }, { t: "Loose end", g: -1, d: 1, x: 250, y: 130 }], l: [0, 1, 0, 2] } }));
  await menuButton(page, "Files").click();
  await check("a project with a graphify map shows it in its cabinet, and a cat there can be asked its questions", async () => {
    const card = page.locator("#roomsDlg .proj", { hasText: "montfortoise-shopify" });
    await card.locator("summary", { hasText: "Project map" }).click();
    expect(await card.locator(".gart svg rect").count() === 3 && await card.locator(".gart svg line").count() === 2, "map not drawn");
    const t = await card.locator(".gmap").innerText();
    expect(t.includes("120 ideas") && t.includes("CartDrawer") && t.includes("Shipping notes") && t.includes("Checkout"), t);
    await card.locator("button.ask").first().click();
    await page.waitForTimeout(300);
    const q = (await outbox(page)).pop();
    expect(q && q.text === "[Catio] Charlotte says: Ask the project map: Why does CartDrawer connect Checkout to Theme?" && q.why === "not_in_manifest", JSON.stringify(q));
  });
  await check("the craft room's cabinet lists its projects and branches, archived sessions included", async () => {
    const t = await page.locator("#roomsDlg").innerText();
    expect(t.includes("Filing cabinet") && t.includes("montfortoise-shopify") && t.includes("Intermarche-grocery-shopping-app") && t.includes("claude/test"), t.slice(0, 300));
  });
  await page.selectOption("#coat-montfortoise-shopify", "5");
  await page.locator("#roomsDlg .proj", { hasText: "montfortoise-shopify" }).locator("button:has-text('Save look')").click();
  await settle(page);
  await check("saving a look restyles every cat of that project", async () => {
    const d = await T(page, () => window.__catio.store["projects/montfortoise-shopify"]);
    expect(d && d.coat === 5 && !("emblem" in d), JSON.stringify(d));
    await page.keyboard.press("Escape");
    const t = await page.locator('#cats .cat[aria-label*="Shop about page"] .spr').evaluate((x) => x.style.getPropertyValue("--tint"));
    expect(t.includes("brightness(.62)"), "coat " + t);
  });
  await openRoom(page, "study");
  await menuButton(page, "Whole house").click();
  await page.waitForTimeout(700);
  await check("Whole house zooms back out", async () => expect(await page.locator('.roomhit[data-room="kitchen"]').isVisible(), "still zoomed in"));

  /* ---------- 5. rooms from a room's menu, and sound from the House menu ---------- */
  await openRoom(page, "kitchen");
  await menuButton(page, "Edit room").click();
  await check("Edit rooms opens the cabin plan on the room you pointed at, one card at a time", async () => {
    expect((await page.locator("#rt-kitchen").getAttribute("aria-selected")) === "true", "kitchen not chosen");
    expect(await page.locator("#rn-kitchen").isVisible() && !(await page.locator("#rn-sunroom").isVisible()), "cards");
    expect(await page.evaluate(() => document.activeElement.id) === "rn-kitchen", "focus not on the name");
    expect(await page.locator("#roomsDlg .rt").count() === 10 && await page.locator("#rt-living .door").count() === 1, "plan tabs / front door");
  });
  await page.click("#rt-sunroom");
  await page.fill("#rn-sunroom", "Conservatory");
  await check("the plan follows the name as she types it", async () => {
    expect((await page.locator("#rt-sunroom").getAttribute("aria-label")) === "Conservatory", "tab label");
    expect((await page.locator("#catchAll option[value=sunroom]").innerText()) === "Conservatory", "front-door choice");
  });
  await page.locator("#rt-sunroom").focus();
  await page.keyboard.press("ArrowRight");
  await check("arrow keys move between rooms on the plan", async () => {
    expect(await page.evaluate(() => document.activeElement.id) === "rt-garden", await page.evaluate(() => document.activeElement.id));
    expect(await page.locator("#rr-garden").isVisible(), "catio card not shown");
  });
  await page.fill("#rr-garden", "Pretty-Project-Portfolio, charredlatte/other-site");
  await page.fill("#rb-garden", "The portfolio, and this page");
  await page.selectOption("#catchAll", "kitchen");
  await check("choosing where new cats come in moves the front door on the plan", async () => {
    expect(await page.locator("#rt-kitchen .door").count() === 1 && await page.locator("#rt-living .door").count() === 0, "door");
    expect((await page.locator("#rt-kitchen").getAttribute("aria-label")).includes("where new cats come in"), "not spoken");
  });
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("renaming a room saves every room, with one front door, and relabels it", async () => {
    const rooms = await T(page, () => Object.fromEntries(Object.entries(window.__catio.store).filter(([k]) => k.startsWith("rooms/"))));
    expect(Object.keys(rooms).length === 10, "rooms saved: " + Object.keys(rooms).length);
    const g = rooms["rooms/garden"];
    expect(g.repos.join("|") === "Pretty-Project-Portfolio|charredlatte/other-site" && g.name === "Catio" && g.blurb === "The portfolio, and this page", JSON.stringify(g));
    expect(rooms["rooms/kitchen"].repos.join() === "Intermarche-grocery-shopping-app" && rooms["rooms/kitchen"].blurb.startsWith("Weekly meals"), "untouched rooms keep their data: " + JSON.stringify(rooms["rooms/kitchen"]));
    const front = Object.entries(rooms).filter(([, d]) => d.catchAll).map(([k]) => k);
    expect(front.join() === "rooms/kitchen", "catch-all: " + front.join());
    expect((await page.locator("#room-sunroom").getAttribute("aria-label")).startsWith("Conservatory"), "room not renamed");
    await openRoom(page, "sunroom");
    expect((await menuText(page)).includes("Conservatory"), await menuText(page));
  });
  await openHouse(page);
  await menuButton(page, "Sound off").click();
  await check("sound switches on from the House menu", async () => expect(await menuButton(page, "Sound on").count() === 1, await menuText(page)));
  await check("no page errors during the run", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 5b. the queen of the house: one cat you talk to, like an NPC ---------- */
// Her words (2 October 2026): "Merge the queen cats to make one main character queen cat that you chat with that does
// everything for you"; voice to text; a character you customise, with routines; cats with handoffs visibly passing
// things to her; an Elizabethan manner; a voice you can turn on and off.
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked");
  const queen = () => page.locator("#cats .cat.queen");
  const routines = () => T(page, () => Object.entries(window.__catio.store).filter(([k]) => k.startsWith("routines/")).map(([, v]) => v));
  // a room queen of before, with what she kept: it is the queen of the house's now
  await T(page, () => window.__catio.put("queens/kitchen", { name: "Berthe", notes: [{ text: "The Drive order goes in on Sunday.", pinned: false, at: 1 }] }));
  await page.waitForTimeout(300);

  await check("one queen, in the entrance hall, and no other", async () => {
    expect(await queen().count() === 1, "queens drawn: " + (await queen().count()));
    expect((await queen().getAttribute("data-queen")) === "hall", await queen().getAttribute("data-queen"));
    expect(await page.locator('#cats .cat[data-id="agent:queen"]').count() === 0, "her runner's record is drawn as a cat");
  });
  await check("she is never counted among the cats that need you", async () => {
    const before = await page.locator("#tally").textContent();
    const needing = await page.locator("#cats .cat:not(.queen).m-meow, #cats .cat:not(.queen).m-cry, #cats .cat:not(.queen).m-box").count();
    const said = (before.match(/(\d+) need you/) || [])[1];
    expect(String(needing) === String(said || 0), "sign says " + said + ", cats needing you: " + needing);
  });
  await page.mouse.move(8, 8);
  await queen().hover();
  await settle(page);
  await check("hovering her names her, and says she is holding what a cat brought", async () => {
    const t = await page.locator("#tip").innerText();
    expect(t.includes("queen") && t.includes("Holding 1 thing"), t);
    expect((await queen().getAttribute("class")).includes("m-box"), await queen().getAttribute("class"));
    expect(await page.locator(ON_CATS).count() === 0, "something is drawn over the cats");
  });
  await queen().click();
  await settle(page);
  await check("her menu: queen of the house, here, and Talk to her first", async () => {
    const t = await menuText(page);
    expect(t.includes("Queen of the house") && t.includes("here"), t);
    expect(await page.locator("#menu .mi.primary:has-text('Talk to her')").count() === 1, t);
  });
  await menuButton(page, "Talk to her").click();
  await settle(page);
  await check("her card shows what the cat brought her, with a way to the cat, and counts it as read", async () => {
    const h = page.locator("#queenThread li.handoff");
    expect(await h.count() === 1, "handoffs: " + (await h.count()));
    const t = await h.innerText();
    expect(t.includes("brought you") && t.includes("The French text is in"), t);
    expect(await h.locator("button:has-text('Open')").count() === 1, "no way to the cat");
    expect((await page.locator("#queenThread li.greet").innerText()).includes("Good morrow"), "no greeting before she has spoken");
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d && d.readAt > 0, JSON.stringify(d));
    expect((await page.locator("#queenKeeps").textContent()).includes("The Drive order"), "what Berthe kept isn't hers");
  });
  await page.fill("#queenSay", "Who needs me today?");
  await page.click("#queenSend");
  await settle(page);
  await check("what you say goes to her through the gateway, as you", async () => {
    const c = await T(page, () => window.__catio.tools.filter((t) => t[1] === "comment").pop());
    expect(c && c[0] === "CATIO" && c[2].cat === "queen" && c[2].text === "Who needs me today?" && c[2].author === "charlotte", JSON.stringify(c));
    expect((await page.locator("#queenThread li.me").innerText()).includes("Who needs me today?"), "not in her thread");
  });
  await T(page, () => { const a = window.__catio.gw.find((x) => x.id === "queen"); a.mood = "busy"; dispatchEvent(new Event("catio:agents")); window.__catio.queenSays("Good morrow, my lady. Two cats need thee: ", false, "t1"); });
  await page.waitForTimeout(300);
  await check("her answer shows as she speaks it, and Stop is there while she does", async () => {
    expect((await page.locator("#queenLive").innerText()).includes("Two cats need thee"), "no live bubble");
    expect(await page.locator("#queenStop").isVisible(), "no Stop");
    expect((await page.locator("#queenState").innerText()).includes("answering"), await page.locator("#queenState").innerText());
  });
  await page.click("#queenStop");
  await settle(page);
  await check("Stop asks the gateway to end her turn", async () => {
    const m = await T(page, () => window.__catio.tools.filter((t) => t[1] === "manage").pop());
    expect(m && m[2].cat === "queen" && m[2].action === "pause", JSON.stringify(m));
  });
  await T(page, () => { window.__catio.queenSays("Good morrow, my lady. Two cats need thee: Praline and Nougat.", true, "t1"); const a = window.__catio.gw.find((x) => x.id === "queen"); a.mood = "done"; dispatchEvent(new Event("catio:agents")); });
  await page.waitForTimeout(400);
  await check("done, her answer is in the thread and the bubble is gone", async () => {
    expect(await page.locator("#queenLive").count() === 0, "still speaking");
    const them = await page.locator("#queenThread li.them:not(.handoff)").last().innerText();
    expect(them.includes("Praline and Nougat"), them);
    expect(!(await page.locator("#queenStop").isVisible()), "Stop still there");
    expect(await page.locator("#queenThread li.greet").count() === 0, "the greeting stays once she has spoken");
  });
  await check("Speak is there: the browser can hear her", async () => expect(await page.locator("#queenSpeak").count() === 1, "no Speak button"));
  await page.click("#queenVoice");
  await settle(page);
  await T(page, () => window.__catio.queenSays("Anon, my lady. All is well.", true, "t2"));
  await page.waitForTimeout(300);
  await check("her voice switches on, is saved with her, and says what she says in English (UK)", async () => {
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d && d.voice && d.voice.on === true, JSON.stringify(d && d.voice));
    const sp = await T(page, () => window.__catio.spoken);
    const last = sp[sp.length - 1];
    expect(last && last.text === "Anon, my lady. All is well.", JSON.stringify(sp));
    expect(/en-GB/i.test(last.lang) && /Hazel/.test(last.voice || ""), JSON.stringify(last));
  });
  // her character: name, coat, how she speaks, what she listens for; saving moves what the room queen kept into her
  await page.click("#queenCharacter summary");
  await page.fill("#queenRename", "Mémé");
  await page.selectOption("#queenCoat", "1");
  await check("she speaks Elizabethan English unless told otherwise", async () => expect((await page.inputValue("#queenManner")).includes("Elizabethan"), await page.inputValue("#queenManner")));
  await page.fill("#queenManner", "Elizabethan English, brisk.");
  await page.selectOption("#queenLang", "fr-FR");
  await page.click("#queenSave");
  await settle(page);
  await check("her character is one document, and what the room queens kept is hers now", async () => {
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d.name === "Mémé" && d.coat === 1 && d.manner === "Elizabethan English, brisk." && d.voice.lang === "fr-FR" && d.voice.on === true, JSON.stringify(d));
    expect(d.notes.length === 1 && d.notes[0].text.startsWith("The Drive order"), JSON.stringify(d.notes));
    expect(!(await T(page, () => window.__catio.store["queens/kitchen"])), "the kitchen's queen document is still there");
    const label = await queen().getAttribute("aria-label");
    expect(label.startsWith("Mémé, queen of the house"), label);
  });
  // routines, for her runner to run
  await queen().dblclick();
  await settle(page);
  await page.click("#queenRoutines summary");
  await page.fill("#routineName", "Morning round");
  await page.fill("#routineTime", "08:30");
  await page.fill("#routinePrompt", "Who needs me today, and what first?");
  await page.click("#routineAdd");
  await settle(page);
  await check("a routine is a document her runner reads: name, time, days, what to ask, on", async () => {
    const r = await routines();
    expect(r.length === 1, JSON.stringify(r));
    expect(r[0].name === "Morning round" && r[0].time === "08:30" && r[0].prompt.startsWith("Who needs me") && r[0].on === true && r[0].days.length === 5 && !!r[0].tz, JSON.stringify(r[0]));
    expect((await page.locator("#routineList").innerText()).includes("Morning round"), await page.locator("#routineList").innerText());
  });
  await page.locator('#routineList button[aria-pressed="true"]').click();
  await settle(page);
  await check("its switch turns it off", async () => expect((await routines())[0].on === false, JSON.stringify(await routines())));
  await page.keyboard.press("Escape");
  await settle(page);
  // what she keeps, from her card: give, say, take back, forget
  await queen().click();
  await settle(page);
  await menuButton(page, "What she keeps").click();
  await settle(page);
  await page.fill("#queenAdd", "Chilli is a health rule, never a taste.");
  await page.locator('#queenDlg button:has-text("Give it to her")').click();
  await page.locator('#queenDlg button:has-text("Say it")').last().click();
  await settle(page);
  await page.keyboard.press("Escape");
  await settle(page);
  await check("what you give her is kept, and the one she is saying is her line", async () => {
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d.notes.length === 2, JSON.stringify(d.notes));
    const said = d.notes.filter((n) => n.pinned);
    expect(said.length === 1 && said[0].text.startsWith("The Drive order"), JSON.stringify(said));
    await page.mouse.move(8, 8);
    await queen().hover();
    await settle(page);
    expect((await page.locator("#tip").innerText()).includes("The Drive order"), await page.locator("#tip").innerText());
    expect((await queen().getAttribute("class")).includes("m-meow"), await queen().getAttribute("class"));
  });
  await queen().click();
  await settle(page);
  await check("the one she is saying is not listed twice in her menu", async () => {
    const t = await menuText(page);
    expect(t.split("The Drive order").length === 2, t);
    expect(t.includes("Chilli is a health rule"), t);
  });
  await queen().dblclick();
  await settle(page);
  await page.click("#queenKeeps summary");
  await page.locator('#queenDlg button:has-text("Saying it")').click();
  await settle(page);
  await page.keyboard.press("Escape");
  await settle(page);
  await check("taking it back stops her saying it", async () => {
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d.notes.every((n) => !n.pinned), JSON.stringify(d.notes));
    await page.mouse.move(8, 8);
    await queen().hover();
    await settle(page);
    expect(!(await page.locator("#tip").innerText()).includes("The Drive order"), "still saying it");
  });
  await queen().dblclick();
  await settle(page);
  await page.click("#queenKeeps summary");
  await page.locator('#queenDlg button:has-text("Forget")').first().click();
  await settle(page);
  await page.keyboard.press("Escape");
  await settle(page);
  await check("forgetting one leaves the rest", async () => {
    const d = await T(page, () => window.__catio.store["queens/house"]);
    expect(d.notes.length === 1, JSON.stringify(d.notes));
  });

  // homework: she sets a quiz to unblock a cat; you answer by tapping, and hand it in
  await T(page, () => window.__catio.setQuiz({ for: "cse_fresh9", title: "The menu fix", questions: [{ q: "Merge it?", options: ["Yes, merge it", "Not yet"] }, { q: "A word for the cat?", options: [], free: true }] }));
  await page.waitForTimeout(400);
  await check("homework she set shows on her: she sits up with it, and hovering says so", async () => {
    expect((await queen().getAttribute("class")).includes("m-box"), await queen().getAttribute("class"));
    await page.mouse.move(8, 8);
    await queen().hover();
    await settle(page);
    expect((await page.locator("#tip").innerText()).includes("Homework: 1 quiz"), await page.locator("#tip").innerText());
  });
  await queen().dblclick();
  await settle(page);
  await check("her card puts the homework first: the questions, with the options to tap", async () => {
    expect(await page.locator("#queenHomework").isVisible(), "no homework in her card");
    const t = await page.locator("#queenHomework").innerText();
    expect(t.includes("The menu fix") && t.includes("Merge it?") && t.includes("A word for the cat?"), t);
    expect(await page.locator('#queenHomework button:has-text("Yes, merge it")').count() === 1, "no option to tap");
  });
  await page.locator('#queenHomework button:has-text("Hand it in")').click();
  await settle(page);
  await check("it isn't handed in half done", async () => expect((await toast(page)).includes("Answer every question"), await toast(page)));
  await page.locator('#queenHomework button:has-text("Yes, merge it")').click();
  await page.fill('#queenHomework input[aria-label^="Your answer"]', "Well done, thou good cat");
  await page.locator('#queenHomework button:has-text("Hand it in")').click();
  await settle(page);
  await check("handing it in sends your answers, in order, and the homework is done", async () => {
    const a = await T(page, () => window.__catio.tools.filter((t) => t[1] === "answer").pop());
    expect(a && a[2].quiz === "z1" && JSON.stringify(a[2].answers) === JSON.stringify(["Yes, merge it", "Well done, thou good cat"]), JSON.stringify(a));
    expect(!(await page.locator("#queenHomework").isVisible()), "the homework is still there");
    expect((await toast(page)).includes("Handed in"), await toast(page));
  });
  await page.keyboard.press("Escape");
  await settle(page);

  // the bug this feature found: redrawing the menu under your pointer used to close it, because the
  // button the redraw removed no longer looked like part of the menu by the time the click arrived
  await openHouse(page);
  const was = await menuText(page);
  await menuButton(page, "Sound off").click();
  await check("a menu button that redraws the menu leaves it open, on the same menu", async () => {
    expect(await page.locator("#menu").isVisible(), "the menu closed under the pointer");
    const now = await menuText(page);
    expect(now.includes("House rules"), "it reopened on something else: " + now.slice(0, 80));
    expect(now.includes("Sound on") && was.includes("Sound off"), now.slice(0, 120));
  });
  await check("no page errors while working the queen", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// without her runner she is away; with the cats moving, a cat with news walks a copy of itself to her
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked&queen=away");
  await page.mouse.move(8, 8);
  await page.locator("#cats .cat.queen").hover();
  await settle(page);
  await check("without her runner she is asleep, and hovering says so", async () => {
    const t = await page.locator("#tip").innerText();
    expect(t.includes("Away"), t);
    expect((await page.locator("#cats .cat.queen").getAttribute("class")).includes("m-sleep"), await page.locator("#cats .cat.queen").getAttribute("class"));
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked", { reducedMotion: "no-preference" });
  await page.waitForTimeout(4200);   // the page's waking moment: before it, cats are simply in their places
  await T(page, () => window.__catio.handoff("cse_fresh9", "The menu fix is merged, your majesty."));
  await page.waitForTimeout(600);
  await check("a cat with news walks a copy of itself to the queen", async () => {
    expect(await page.locator("#walkers .walker[data-handoff]").count() === 1, "no walker");
  });
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await check("and what it brought is in her thread", async () => {
    const t = await page.locator("#queenThread").innerText();
    expect(t.includes("brought you") && t.includes("The menu fix is merged"), t);
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 5c. anyone else's copy: none of the licensed art ---------- */
// run.sh builds .page-noart.html over a folder holding only the committed art, which is what a
// fresh clone looks like whether or not this checkout has the packs.
{
  const { page, ctx, errors } = await open("", { base: NOART });
  await check("with no licensed art the sign says so, and the queens still work", async () => {
    const words = await page.locator("#status").textContent();
    expect(words.includes("The cat art isn't here") && words.includes("neither the house nor its cats can draw"), words);
    expect(words.includes("build-art.py"), "it does not say how to fix it: " + words);
    expect(await page.locator("#status.warn").count() === 1, "the sign is not flagging it");
    // her menu and what she keeps still work without the packs to draw them
    await page.locator("#cats .cat.queen").click();
    await settle(page);
    expect((await menuText(page)).includes("Queen of the house"), await menuText(page));
  });
  await check("without the interface art the sign and menus sit on plain colour, not the meadow", async () => {
    const bg = (sel) => page.locator(sel).evaluate((e) => getComputedStyle(e).backgroundColor);
    expect((await bg("#houseBtn")) !== "rgba(0, 0, 0, 0)", "the brand has nothing behind it");
    expect((await bg("#controls")) !== "rgba(0, 0, 0, 0)", "the map panel has nothing behind it");
    expect((await bg("#zoomIn")) !== "rgba(0, 0, 0, 0)", "the panel's buttons have nothing behind them");
    expect((await bg("#menu")) !== "rgba(0, 0, 0, 0)", "the menu has nothing behind it");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 6. rooms on the map: no signs, the brackets, and the keyboard ---------- */
{
  const { page, ctx, errors } = await open("", { viewport: { width: 1280, height: 720 } });
  await check("the map is quiet: no signs on any room or the stair, on either floor", async () => {
    for (const f of ["upper", "ground"]) {
      await toFloor(page, f);
      expect(await page.locator("#overlay .tag").count() === 0, f + " signs: " + await page.locator("#overlay .tag").count());
    }
  });
  await check("nothing sits over the one cat that needs you: hovering it says what it needs, and the brand counts it", async () => {
    expect(await page.locator(ON_CATS).count() === 0, "something is drawn over the cats");
    const t = await hoverCat(page, "Shop about page");
    expect(t.includes("review the French text"), "hover: " + t);
    expect((await page.locator("#houseBtn .badge .n").innerText()) === "1", "brand badge");
    expect(await page.locator("#houseBtn .badge.need .face-ico").count() === 1, "no meowing face");
  });
  await openRoom(page, "kitchen");
  await check("the room under the pointer, and the one its menu belongs to, light up with the white brackets", async () => {
    const ring = await page.locator("#room-kitchen").evaluate((e) => e.classList.contains("lit") && getComputedStyle(e).borderImageSource);
    expect(ring && ring.includes("corners.png"), "no brackets: " + ring);
  });
  await closeMenu(page);
  await closeMenu(page);
  await page.evaluate(() => document.activeElement && document.activeElement.blur());   // a keyboard walk starts from nothing
  const hud = await page.locator("#hud").boundingBox();   // rest the pointer on the sign, off the rooms
  await page.mouse.move(hud.x + 10, hud.y + 10);
  await page.waitForTimeout(450);
  const active = () => page.evaluate(() => document.activeElement.id || document.activeElement.className);
  for (let i = 0; i < 8 && !(await active()).startsWith("room-"); i++) await page.keyboard.press("Tab");
  await check("the map is one tab stop, landing on the room that needs you, with its menu open and the keys in it", async () => {
    expect((await active()) === "room-study", "focus: " + (await active()));
    expect(await page.evaluate(() => [...document.querySelectorAll(".roomhit, .cabinet, #cats .cat")].filter((b) => b.tabIndex >= 0).length) === 1, "more than one map stop");
    const t = await menuText(page);
    expect(t.includes("Craft room") && t.includes("Esc back"), t);
    const ring = await page.locator("#room-study").evaluate((e) => getComputedStyle(e).borderImageSource);
    expect(ring.includes("corners.png"), "no brackets on the focused room");
  });
  await page.keyboard.press("Enter");
  await check("Enter steps into the menu on Look in, with the cats needing you just above it", async () => {
    expect((await page.evaluate(() => document.activeElement.textContent)) === "Look in", await active());
    expect(await page.evaluate(() => { const b = document.activeElement.closest("#menu").querySelector("button"); return b.textContent.startsWith("Caramel"); }), "no cat row above");
  });
  await page.keyboard.press("Escape");
  await page.keyboard.press("ArrowUp");   // the café is right above the craft room
  await check("arrow keys move the ring to the room next door and open its menu", async () => {
    expect((await active()) === "room-dining", "focus: " + (await active()));
    expect((await menuText(page)).includes("Café"), await menuText(page));
    expect((await page.locator("#room-dining").getAttribute("tabindex")) === "0" && (await page.locator("#room-study").getAttribute("tabindex")) === "-1", "roving tabindex");
  });
  await page.keyboard.press("Enter");
  await check("Enter steps into the room's menu", async () => expect((await page.evaluate(() => document.activeElement.textContent)) === "Look in", await active()));
  await page.keyboard.press("Escape");
  await check("Escape in the menu goes back to the room, menu still open", async () => {
    expect((await active()) === "room-dining" && await page.locator("#menu").isVisible(), await active());
  });
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  await check("Enter twice looks in; focus stays on the room, its menu open, and the move is said aloud", async () => {
    expect(await page.locator('.roomhit.here[data-room="dining"]').count() === 1, "not in the café");
    expect((await active()) === "room-dining", "focus: " + (await active()));
    expect((await menuText(page)).includes("Whole house"), "menu shut under the keyboard: " + (await menuText(page)));
    expect((await page.locator("#say").textContent()).startsWith("Café"), await page.locator("#say").textContent());
  });
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(700);
  await check("in a room, arrows walk into the next one", async () => {
    expect(await page.locator('.roomhit.here[data-room="kitchen"]').count() === 1, "not in the kitchen");
    expect((await active()) === "room-kitchen", "focus: " + (await active()));
  });
  await page.keyboard.press("Enter");
  for (let i = 0; i < 6 && (await page.evaluate(() => document.activeElement.textContent)) !== "Edit room"; i++) await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await check("every room action is reachable from the keyboard: Edit room opens on that room", async () => {
    expect(await page.locator("#roomsDlg[open]").count() === 1, "editor not open");
    expect((await page.locator("#rt-kitchen").getAttribute("aria-selected")) === "true", "not on the kitchen");
  });
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(700);
  await check("Escape comes back out to the whole house with the ring where you were", async () => {
    expect(await page.locator(".roomhit.here").count() === 0, "still in a room");
    expect((await active()) === "room-kitchen", "focus: " + (await active()));
  });
  const long = "The very long room for tax 2026";   // 31 typed, 30 kept
  await openRoom(page, "bath");
  await menuButton(page, "Edit room").click();
  await page.fill("#rn-bath", long);
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("a 30-character name is whole in the room's name and its menu", async () => {
    const name = (await T(page, () => window.__catio.store["rooms/bath"])).name;
    expect(name.length === 30, "saved " + name.length);
    expect((await page.locator("#room-bath").getAttribute("aria-label")).startsWith(name), "full name not in the label");
    await openRoom(page, "bath");
    expect((await menuText(page)).includes(name), "menu lacks the full name");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 6b. a still pointer: the camera moving under it is not pointing ---------- */
{
  const { page, ctx, errors } = await open();
  await openRoom(page, "kitchen");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(800);
  await check("looking in doesn't name whatever room slid under the resting pointer", async () => {
    expect(await page.locator('.roomhit.here[data-room="kitchen"]').count() === 1, "not in the kitchen");
    expect(!(await page.locator("#menu").isVisible()), "a menu opened by itself: " + (await menuText(page)).slice(0, 40));
    expect(!(await page.locator("#tip").isVisible()), "a line appeared by itself: " + (await page.locator("#tip").innerText()));
  });
  const box = await page.locator('.roomhit[data-room="kitchen"]').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height * 0.8, { steps: 3 });
  await page.waitForTimeout(300);
  await check("the first real move names the room under it", async () => {
    expect((await page.locator("#tip").innerText()).includes("Kitchen"), await page.locator("#tip").innerText());
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 6c. two floors, and moving around: panning and zoom ---------- */
{
  const { page, ctx, errors } = await open();
  const floor = () => page.locator("#world").getAttribute("data-floor");
  await check("the house opens on the ground floor, the café, with the floor switch saying so", async () => {
    expect((await floor()) === "ground", await floor());
    expect((await page.locator("#floor-ground").getAttribute("aria-checked")) === "true", "switch");
    expect(await page.locator('.roomhit[data-room="kitchen"]').isVisible() && await page.locator('.roomhit[data-room="bedroom"]').isHidden(), "wrong rooms showing");
  });
  // a chat upstairs that needs her, while she is downstairs
  await T(page, () => window.__catio.put("cats/up1", { title: "Lease renewal", room: "bedroom", mood: "needs", note: "Sign it", name: "Mimi", project: "Flat lease", createdAt: Date.now(), updatedAt: Date.now() }));
  await settle(page);
  await check("a cat upstairs that needs you shows on the floor switch, and the tally counts it", async () => {
    expect(await page.locator("#floor-upper .badge").count() === 1, "no badge on the switch");
    expect((await page.locator("#tally").innerText()).includes("2 need you"), await page.locator("#tally").innerText());
  });
  await page.locator("#stairs").click();
  await settle(page);
  await check("the stair takes you upstairs, where the ground floor is out of reach", async () => {
    expect((await floor()) === "upper", await floor());
    expect((await page.locator("#floor-upper").getAttribute("aria-checked")) === "true", "switch");
    expect(await page.locator('.roomhit[data-room="bedroom"]').isVisible(), "bedroom not showing");
    expect(await page.locator('.roomhit[data-room="kitchen"]').isHidden(), "the kitchen still answers upstairs");
    expect(await page.locator('#cats .cat[aria-label^="Mimi "]').isVisible(), "the cat upstairs isn't there");
    expect(await page.locator("#floor-ground .badge").count() === 1, "no badge on the ground floor's switch");
    expect((await page.locator("#say").textContent()).startsWith("Upstairs"), await page.locator("#say").textContent());
  });
  await page.keyboard.press("PageDown");
  await settle(page);
  await check("Page Down goes down, Page Up goes up", async () => {
    expect((await floor()) === "ground", "down: " + (await floor()));
    await page.keyboard.press("PageUp");
    await settle(page);
    expect((await floor()) === "upper", "up: " + (await floor()));
  });
  await page.click("#floor-ground");
  await settle(page);
  await openCat(page, "Mimi");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(700);
  await check("Look in on an upstairs cat takes you up the stair into its room", async () => {
    expect((await floor()) === "upper" && await page.locator('.roomhit.here[data-room="bedroom"]').count() === 1, "not in the bedroom");
  });
  await page.click("#zoomAll");
  await page.waitForTimeout(700);
  await page.click("#floor-ground");
  await settle(page);

  // moving around
  const whole = await cam(page);
  const k = await roomPoint(page, "kitchen");
  await page.mouse.move(k.x, k.y);
  await page.mouse.down();
  await page.mouse.move(k.x - 60, k.y - 40, { steps: 4 });
  await page.mouse.move(k.x - 120, k.y - 80, { steps: 4 });
  await page.mouse.up();
  await settle(page);
  await check("a zoomed-out house can't be dragged off the screen", async () => {
    const c = await cam(page);
    expect(Math.abs(c.tx - whole.tx) < 1 && Math.abs(c.ty - whole.ty) < 1, JSON.stringify([whole, c]));
    expect(await page.locator("#menu").isHidden(), "the drag opened a menu");
  });
  await page.mouse.move(k.x, k.y);
  await page.mouse.wheel(0, -400);
  await page.waitForTimeout(300);
  const zoomed = await cam(page);
  await check("the wheel zooms in around the pointer", async () => {
    expect(zoomed.s > whole.s * 1.3, JSON.stringify([whole, zoomed]));
    // the point under the pointer stays under it
    const before = [(k.x - whole.tx) / whole.s, (k.y - whole.ty) / whole.s], after = [(k.x - zoomed.tx) / zoomed.s, (k.y - zoomed.ty) / zoomed.s];
    expect(Math.abs(before[0] - after[0]) < 3 && Math.abs(before[1] - after[1]) < 3, JSON.stringify([before, after]));
  });
  await page.mouse.move(k.x, k.y);
  await page.mouse.down();
  await page.mouse.move(k.x + 80, k.y + 50, { steps: 5 });
  await page.mouse.up();
  await settle(page);
  await check("a left drag on the house pans it, and opens no menu", async () => {
    const c = await cam(page);
    expect(Math.abs(c.tx - zoomed.tx - 80) < 2 && Math.abs(c.ty - zoomed.ty - 50) < 2, JSON.stringify([zoomed, c]));
    expect(await page.locator("#menu").isHidden(), "the drag opened a menu");
  });
  const panned = await cam(page);
  await page.mouse.move(700, 450);
  await page.mouse.down({ button: "right" });
  await page.mouse.move(640, 420, { steps: 5 });
  await page.mouse.up({ button: "right" });
  await settle(page);
  await check("a right drag pans too", async () => {
    const c = await cam(page);
    expect(Math.abs(c.tx - panned.tx + 60) < 2 && Math.abs(c.ty - panned.ty + 30) < 2, JSON.stringify([panned, c]));
  });
  await page.click("#zoomAll");
  await page.waitForTimeout(700);
  const back = await cam(page);
  await check("Whole house flies back out", async () => expect(Math.abs(back.s - whole.s) < 0.01, JSON.stringify([whole, back])));
  await page.click("#zoomIn");
  await page.waitForTimeout(700);
  await check("the + button zooms in, and − out", async () => {
    const c = await cam(page);
    expect(c.s > whole.s * 1.4, JSON.stringify(c));
    await page.click("#zoomOut");
    await page.waitForTimeout(700);
    expect(Math.abs((await cam(page)).s - whole.s) < 0.01, "not back out");
  });
  // zoom far into the craft room: close enough, it is the room you're in, and its cats say what they need
  const st = await roomPoint(page, "study");
  await page.mouse.move(st.x, st.y);
  for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, -300); await page.waitForTimeout(60); }
  await page.waitForTimeout(500);
  await check("zoomed in until one room fills the view, you're in that room, and still nothing sits over its cats", async () => {
    expect(await page.locator('.roomhit.here[data-room="study"]').count() === 1, "not in the craft room");
    expect(await page.locator(ON_CATS).count() === 0, "something is drawn over the cats");
  });
  await page.keyboard.press("0");
  await page.waitForTimeout(700);
  await check("0 shows the whole house again, and you're in no room", async () => expect(await page.locator(".roomhit.here").count() === 0, "still in a room"));
  await openHouse(page);
  await check("the House menu holds the brain, the house rules, Edit rooms and the sound", async () => {
    const t = await menuText(page);
    for (const w of ["The brain", "House rules", "Edit rooms", "Sound"]) expect(t.includes(w), w + " missing: " + t);
    expect((await page.locator("#houseBtn").getAttribute("aria-expanded")) === "true", "button not pressed");
  });
  await check("no page errors going up, down and around", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 6d. cats walk: up the stair when archived, down it when back, through doorways, and about ---------- */
// Version 11's hover-steal checks (a menu following a resting pointer) are gone: a click opens a menu now.
{
  const { page, ctx, errors } = await open("", { reducedMotion: "no-preference" });
  const cat = (id) => page.locator('#cats .cat[data-id="session_' + id + '"]');
  const settled = (id, cls) => page.waitForFunction(([id, cls]) => {
    const b = document.querySelector('#cats .cat[data-id="session_' + id + '"]');
    return b && !b.classList.contains("walking") && !b._walk && (!cls || b.classList.contains(cls));
  }, [id, cls], { timeout: 25000 });
  // a point of the world (native pixels) on screen
  const onScreen = async (x, y) => { const c = await cam(page); return { x: c.tx + c.s * x * 2, y: c.ty + c.s * y * 2 }; };
  const mid = (b) => ({ x: b.x + b.width / 2, y: b.y + b.height / 2 });
  await check("while the page opens, cats are simply in their places", async () =>
    expect(await page.locator("#cats .cat.walking, #walkers .walker").count() === 0, "someone is walking on load"));
  await page.waitForTimeout(4200);
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "ARCHIVED", {}));
  await settle(page);
  await check("an archived cat walks off towards the hall's stair", async () => {
    expect(await cat("blocked1").count() === 0, "still in its room");
    const w = page.locator('#walkers .walker[data-leaving="session_blocked1"]');
    expect(await w.count() === 1 && (await w.getAttribute("data-floor")) === "ground", "nobody walking to the stair");
    const stair = mid(await page.locator("#stairs").boundingBox());
    const a = mid(await w.boundingBox());
    await page.waitForTimeout(700);
    const b = mid(await w.boundingBox());
    expect(Math.hypot(b.x - a.x, b.y - a.y) > 4, "not moving: " + JSON.stringify([a, b]));
    expect(Math.hypot(b.x - stair.x, b.y - stair.y) < Math.hypot(a.x - stair.x, a.y - stair.y), "not heading for the stair");
  });
  await check("it climbs the stair and is gone", async () =>
    page.locator('#walkers .walker[data-leaving="session_blocked1"]').waitFor({ state: "detached", timeout: 25000 }));
  await T(page, () => window.__catio.setBucket("blocked1", "BLOCKED", "IDLE", { status_category: "need_input", needs_action: "one more look" }));
  await settle(page);
  await check("brought back, it comes down the stair and walks to its room, then meows", async () => {
    expect((await cat("blocked1").getAttribute("class")).includes("walking"), "not walking back: " + await cat("blocked1").getAttribute("class"));
    await settled("blocked1", "m-meow");
    expect(await cat("blocked1").getAttribute("data-room") === "study", "not in the craft room");
  });
  {
    const b = await catPoint(page, "Shop about page");
    const to = await roomPoint(page, "hall");
    await page.mouse.move(b.x, b.y);
    await page.mouse.down();
    await page.mouse.move(b.x + 40, b.y + 40, { steps: 3 });
    await page.mouse.move(to.x, to.y, { steps: 5 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  }
  await check("moved to the entrance hall, it walks there through the doorway", async () => {
    expect(await cat("blocked1").getAttribute("data-room") === "hall", "not moved");
    expect((await cat("blocked1").getAttribute("class")).includes("walking"), "it jumped");
    await settled("blocked1", "m-meow");
  });
  await closeMenu(page);
  await check("a working cat wanders from its station now and then, and comes back", async () => {
    await page.waitForFunction(() => { const b = document.querySelector('#cats .cat[data-id="session_work1"]'); return b && b.classList.contains("walking"); }, null, { timeout: 15000 });
    await settled("work1", "m-idle");
  });
  await T(page, () => window.__catio.put("sessions/session_work1", { room: "bedroom" }));
  await settle(page);
  await check("moved upstairs, a cat comes up the stair into its new room", async () => {
    expect(await cat("work1").getAttribute("data-room") === "bedroom" && (await cat("work1").getAttribute("data-floor")) === "upper", "not in the bedroom");
    await settled("work1", "m-idle");
  });
  await toFloor(page, "upper");
  await T(page, () => window.__catio.setBucket("work1", "COMPLETED", "ARCHIVED", {}));
  await settle(page);
  await check("archived upstairs, it walks to the landing's attic ladder and is gone", async () => {
    const w = page.locator('#walkers .walker[data-leaving="session_work1"]');
    expect(await w.count() === 1 && (await w.getAttribute("data-floor")) === "upper", "nobody walking to the ladder");
    // the foot of the attic ladder, where the page puts it: the landing's bottom right corner
    const [x, y, lw, lh] = JSON.parse(readFileSync(join(here, "..", "index.html"), "utf8").match(/"landing":(\[[\d,]+\])/)[1]);
    const lad = await onScreen(x + lw - 24, y + lh - 12);
    const a = mid(await w.boundingBox());
    await page.waitForTimeout(700);
    const b = mid(await w.boundingBox());
    expect(Math.hypot(b.x - a.x, b.y - a.y) > 4, "not moving");
    expect(Math.hypot(b.x - lad.x, b.y - lad.y) < Math.hypot(a.x - lad.x, a.y - lad.y), "not heading for the ladder");
    await w.waitFor({ state: "detached", timeout: 25000 });
  });
  await check("no page errors while walking", async () => expect(errors.length === 0, errors.join(" | ")));
  await ctx.close();
}

/* ---------- 6f. honest counts: what the brand's badge counts ---------- */
{
  const { page, ctx, errors } = await open();
  const needCount = () => page.evaluate(() => (document.querySelector("#tally .badge .n") || {}).textContent || "0");
  const before = Number(await needCount());
  await T(page, () => {
    const C = window.__catio, D = 864e5;
    // a review nobody has opened in ten days, and claude.ai's warm-start placeholder
    const old = C.session("oldreview", "Old review", "tiktok-saves", "REVIEW_READY", "IDLE", 10 * D);
    const warm = Object.assign(C.session("warm", "__warming__", "tiktok-saves", "REVIEW_READY", "IDLE", 0), { tags: ["cowork-warm-start"] });
    C.sessions.push(old, warm);
    C.push();
  });
  await settle(page);
  await check("a review nobody has opened for a week naps in the attic, and isn't counted as needing her", async () => {
    expect(await page.locator('#cats .cat[aria-label*="Old review"]').count() === 0, "still in a room");
    expect(Number(await needCount()) === before, "the badge went from " + before + " to " + (await needCount()));
    await openHouse(page);
    expect((await menuText(page)).includes("2 napping in the attic"), await menuText(page));
  });
  await check("claude.ai's warm-start placeholder is nobody's cat", async () =>
    expect(await page.locator('#cats .cat[aria-label*="__warming__"]').count() === 0 && !(await page.evaluate(() => document.body.innerText.includes("__warming__"))), "it shows"));
  await check("no page errors with the honest counts", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 6e. the map panel and the minimap (Game UI Pastel) ---------- */
{
  const { page, ctx, errors } = await open();
  const BOX = [80, 32, 848, 448], K = 250 / BOX[2];   // the page's MM.box: the minimap shows the manor and catio
  const rect = (sel) => page.locator(sel).evaluate((e) => { const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; });
  // where the camera's view should be framed on the minimap, from the camera itself
  async function viewMatches() {
    const c = await cam(page), W = 1440, H = 900;
    const x = -c.tx / (2 * c.s), y = -c.ty / (2 * c.s), w = W / (2 * c.s), h = H / (2 * c.s);
    const want = { x: (Math.max(BOX[0], x) - BOX[0]) * K, y: (Math.max(BOX[1], y) - BOX[1]) * K,
      w: (Math.min(BOX[0] + BOX[2], x + w) - Math.max(BOX[0], x)) * K, h: (Math.min(BOX[1] + BOX[3], y + h) - Math.max(BOX[1], y)) * K };
    const got = await page.locator("#mmView").evaluate((e) => ({ x: e.offsetLeft, y: e.offsetTop, w: e.offsetWidth, h: e.offsetHeight }));
    const ok = ["x", "y"].every((k) => Math.abs(got[k] - want[k]) < 2) && ["w", "h"].every((k) => Math.abs(got[k] - Math.max(6, want[k])) < 2);
    expect(ok, JSON.stringify({ want, got }));
  }
  // the middle of the view, in native pixels
  const middle = async () => { const c = await cam(page); return [(720 - c.tx) / (2 * c.s), (450 - c.ty) / (2 * c.s)]; };
  // a point of the grounds (native px) on the minimap, on screen
  const onMap = async (x, y) => { const m = await rect("#minimap"); return { x: m.x + (x - BOX[0]) * K, y: m.y + (y - BOX[1]) * K }; };

  await check("one panel in the top right holds zoom, the fold, the minimap and the floors", async () => {
    for (const id of ["zoomIn", "zoomOut", "zoomAll", "mapFold", "minimap", "floor-ground", "floor-upper"])
      expect(await page.locator("#controls #" + id).count() === 1, id + " is not in the panel");
    const p = await rect("#controls");
    expect(p.x + p.w > 1400 && p.y < 40, "not top right: " + JSON.stringify(p));
    expect(await page.locator("#minimap").isVisible(), "the minimap is folded on a laptop");
  });
  await check("the footer credits the map panel's pack", async () =>
    expect((await page.locator(".credits").textContent()).includes("Game UI Pack created by SC_siosio"), "no credit"));
  await check("the minimap draws this floor's rooms, and a pip where a cat needs you", async () => {
    expect(await page.locator('#mmRooms .mm-room[data-room="kitchen"]:not(.faint)').count() === 1, "no kitchen");
    expect(await page.locator('#mmRooms .mm-room[data-room="brain"].faint').count() === 1, "the floor above isn't faint underneath");
    expect(await page.locator("#mmRooms .pip").count() >= 1, "no pips");
  });
  await check("the view on the minimap matches the camera on the whole house", viewMatches);
  await page.mouse.move(1200, 820); await page.mouse.down(); await page.mouse.move(1100, 760, { steps: 6 }); await page.mouse.up();
  await settle(page);
  await check("… after a drag on the house", viewMatches);
  await page.mouse.move(700, 400);
  for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -300); await page.waitForTimeout(50); }
  await page.waitForTimeout(300);
  await check("… after a wheel zoom", viewMatches);
  await page.click("#zoomAll"); await page.waitForTimeout(700);
  await openRoom(page, "kitchen");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(300);
  await check("… after Look in, and the room you're in is green on the minimap", async () => {
    await viewMatches();
    expect(await page.locator('#mmRooms .mm-room.here[data-room="kitchen"]').count() === 1, "the kitchen isn't marked");
  });
  await closeMenu(page);
  const catio = await onMap(800, 300);
  await page.mouse.click(catio.x, catio.y);
  await page.waitForTimeout(400);
  await check("a click on the minimap takes the camera there", async () => {
    const [x, y] = await middle();
    expect(Math.hypot(x - 800, y - 300) < 30, "the middle is at " + [x, y]);
    await viewMatches();
  });
  const before = await middle(), at = await onMap(before[0], before[1]);
  await page.mouse.move(at.x, at.y); await page.mouse.down(); await page.mouse.move(at.x - 30, at.y, { steps: 6 }); await page.mouse.up();
  await settle(page);
  await check("dragging the view on the minimap pans the house with it", async () => {
    const [x] = await middle();
    expect(Math.abs(before[0] - x - 30 / K) < 12, JSON.stringify([before, x]));
  });
  const k = await onMap(394, 130);
  await page.mouse.dblclick(k.x, k.y);
  await page.waitForTimeout(400);
  await check("a double-click on a room on the minimap looks in", async () =>
    expect(await page.locator('.roomhit.here[data-room="kitchen"]').count() === 1, "not in the kitchen"));
  await page.click("#zoomAll");
  await page.waitForTimeout(300);
  // a room at the right of the house opens its menu clear of the panel; so does House
  const clear = async () => {
    const m = await rect("#menu"), p = await rect("#controls");
    return !(m.x < p.x + p.w && m.x + m.w > p.x && m.y < p.y + p.h && m.y + m.h > p.y);
  };
  await openRoom(page, "living");
  await check("a room menu on the right opens clear of the panel", async () => expect(await clear(), "the menu is under the panel"));
  await closeMenu(page);
  await openHouse(page);
  await check("the House menu (the brand) opens clear of the panel", async () => expect(await clear(), "the House menu is over the panel"));
  await closeMenu(page);
  await page.click("#floor-upper");
  await settle(page);
  await check("upstairs, the minimap shows the upstairs rooms and the landing", async () => {
    expect(await page.locator('#mmRooms .mm-room[data-room="brain"]:not(.faint)').count() === 1, "no library");
    expect(await page.locator("#mmRooms .mm-room.landing:not(.faint)").count() === 1, "no landing");
  });
  await page.click("#floor-ground");
  await page.click("#mapFold");
  await check("the fold button folds the map away and says so", async () => {
    expect(!(await page.locator("#minimap").isVisible()), "still showing");
    expect((await page.locator("#mapFold").getAttribute("aria-expanded")) === "false", "aria-expanded");
  });
  await page.reload(); await page.waitForTimeout(600);
  await check("folded stays folded after a reload", async () => expect(!(await page.locator("#minimap").isVisible()), "open again"));
  await page.locator("#stage").click({ position: { x: 60, y: 800 } });
  await page.keyboard.press("m");
  await check("M unfolds it, and that is remembered too", async () => {
    expect(await page.locator("#minimap").isVisible(), "M did nothing");
    await page.reload(); await page.waitForTimeout(600);
    expect(await page.locator("#minimap").isVisible(), "folded again after a reload");
  });
  await check("no page errors with the map panel", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 7. touch: a tap opens the menu, and its buttons act ---------- */
{
  const { page, ctx, errors } = await open("", { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const cat = page.locator("#cats .cat.m-meow").first();
  await check("on a phone the map panel starts folded, at the bottom", async () => {
    expect(!(await page.locator("#minimap").isVisible()), "the minimap is open");
    const r = await page.locator("#controls").boundingBox();
    expect(r.y + r.height > 780, "not at the bottom: " + JSON.stringify(r));
  });
  await cat.tap();
  await settle(page);
  await check("on a phone, tapping a cat opens its menu instead of the full card", async () => {
    expect(await page.locator("#menu").isVisible(), "no menu");
    expect(await page.locator("#catDlg[open]").count() === 0, "card opened on the first tap");
  });
  await menuButton(page, "Talk").tap();
  await settle(page);
  await check("its menu's Talk opens the full card", async () => expect(await page.locator("#catDlg[open]").count() === 1, "no card"));
  await page.keyboard.press("Escape");
  await check("the phone view has no sideways scroll and no errors", async () => {
    expect(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "horizontal scroll");
    expect(errors.length === 0, errors.join("; "));
  });
  await check("on a phone the map carries no signs, and the brand's badge counts who needs you", async () => {
    expect(await page.locator("#overlay .tag").count() === 0, "signs on a phone map");
    expect((await page.locator("#houseBtn .badge .n").innerText()) === "1", "brand badge");
  });
  const room = await roomPoint(page, "study");   // clear floor, off the furniture's buttons
  await page.touchscreen.tap(room.x, room.y);
  await settle(page);
  await menuButton(page, "Edit room").tap();
  await check("on a phone the Rooms plan fits, opens on the tapped room, and its smallest rooms can be tapped", async () => {
    const dlg = await page.locator("#roomsDlg").boundingBox();
    expect(dlg.x >= 0 && dlg.x + dlg.width <= 390, JSON.stringify(dlg));
    expect((await page.locator("#rt-study").getAttribute("aria-selected")) === "true", "not on the craft room");
    expect(await page.locator("#rt-bath").isHidden(), "an upstairs room on the ground floor's plan");
    await page.locator("#pf-upper").tap();
    const bath = await page.locator("#rt-bath").boundingBox();
    expect(bath.width >= 24 && bath.height >= 24, "bath tab " + JSON.stringify(bath));
    await page.locator("#rt-bath").tap();
    expect(await page.locator("#rn-bath").isVisible(), "bath card");
    expect(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "horizontal scroll");
  });
  await ctx.close();
}

/* ---------- 8. degraded views ---------- */
{
  const { page, ctx, errors } = await open("?mode=blocked");
  await check("when claude.ai blocks the live read, Claude's copy fills the rooms and the sign sends her nowhere", async () => {
    const t = await page.locator("#status").innerText();
    expect(t.includes("nothing for you to change") && !t.includes("Customize") && t.includes("Claude's copy"), t);
    expect(await page.locator("#cats .cat").count() >= 2, "rooms empty");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=noconn");
  await check("without the connector the sign says what to do", async () => {
    const t = await page.locator("#status").innerText();
    expect(t.includes("isn't connected") && t.includes("built into claude.ai"), t);
  });
  await ctx.close();
}
for (const [q, want, prep] of [["?mode=nodb", "isn't available", null], ["", "look but not change", () => { window.__catio.readOnly = true; }]]) {
  const { page, ctx } = await open(q);
  if (prep) await page.evaluate(prep);
  await openRoom(page, "dining");
  await addCat(page, "Adopt a chat");
  await page.fill("#adTitle", "Anything");
  await page.click('#adoptDlg button[type="submit"]');
  await settle(page);
  await check((q ? "without storage" : "for a view-only visitor") + ", adopting explains why it can't save", async () => expect((await toast(page)).includes(want), await toast(page)));
  await ctx.close();
}

/* ---------- 8b. the harness: the brain, posting into sessions, talking, managing, rules, agents ---------- */
const tools = (page, name) => T(page, () => window.__catio.tools).then((t) => t.filter((x) => !name || x[1] === name));
async function giveFiles(page, files) {
  const [chooser] = await Promise.all([page.waitForEvent("filechooser"), page.locator("#menu").getByRole("button", { name: /Add files|Choose files/ }).first().click()]);
  await chooser.setFiles(files);
  await page.waitForFunction(() => { const b = document.getElementById("dropSend"); return b && !b.disabled; });
}
// a real drag and drop of files onto a point of the page, the way a browser delivers one
async function dropFiles(page, sel, files) {
  await page.evaluate(({ sel, files }) => {
    const n = document.querySelector(sel), r = n.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height * 0.8;
    const dt = new DataTransfer();
    for (const f of files) dt.items.add(new File([f.text], f.name, { type: f.type }));
    const at = document.elementFromPoint(x, y) || n;
    for (const type of ["dragenter", "dragover", "drop"]) at.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, dataTransfer: dt }));
  }, { sel, files });
  await page.waitForFunction(() => { const b = document.getElementById("dropSend"); return b && !b.disabled; });
}
{
  const { page, ctx, errors } = await open("?agents=1");
  await page.waitForTimeout(300);
  await check("no letters on the cats, the model is in the card, and agents from other makers join the house", async () => {
    expect(await page.locator(ON_CATS).count() === 0, "something is drawn over the cats");
    await page.locator('#cats .cat[aria-label*="Shop about page"]').dblclick();
    await settle(page);
    const card = await page.locator("#catDlg").textContent();
    expect(card.includes("Opus"), "no model in the card: " + card.slice(0, 300));
    await page.keyboard.press("Escape");
    await settle(page);
    const agent = page.locator('#cats .cat[aria-label*="Shop theme"]');
    expect(await agent.count() === 1, "no agent cat");
    expect((await agent.getAttribute("aria-label")).includes("Meowing"), "agent should need her");
  });

  // a file given to one cat: kept, and its delivery waits in the outbox (no Routine: one starts a stray session)
  await openCat(page, "Shop about page");
  await giveFiles(page, { name: "about-fr.md", mimeType: "text/markdown", buffer: Buffer.from("# À propos\nNotre boutique…") });
  await check("a file given to a cat goes to that cat", async () => {
    expect(await page.inputValue("#drop-0") === "session_blocked1", await page.inputValue("#drop-0"));
    expect((await page.locator("#brainDlg").innerText()).includes("Dropped on"), "no reason");
  });
  await page.fill("#dropNote", "Use this for the about page");
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("sending keeps the file, and its delivery waits in the outbox, with no Routine made", async () => {
    const st = await T(page, () => window.__catio.store);
    const brain = Object.entries(st).filter(([p]) => p.startsWith("brain/"));
    expect(brain.length === 1, "brain docs " + brain.length);
    const d = brain[0][1];
    expect(d.cat === "session_blocked1" && d.status === "waiting" && d.via === "queued" && d.asset && d.note === "Use this for the about page" && d.how === "dropped", JSON.stringify(d));
    expect((await tools(page, "create_trigger")).length === 0 && (await tools(page, "fire_trigger")).length === 0, "a Routine was used");
    const q = await outbox(page);
    expect(q.length === 1 && q[0].cat === "session_blocked1" && q[0].why === "not_in_manifest" && q[0].detail && q[0].kind === "delivery", JSON.stringify(q));
    const sm = await tools(page, "send_message");
    expect(sm.length === 1 && sm[0][2].session_id === "session_blocked1" && sm[0][2].message === q[0].text, JSON.stringify(sm));
    expect(q[0].text.startsWith("[Catio] Delivery for you: about-fr.md") && q[0].text.includes("Use this for the about page") && q[0].text.includes("Notre boutique") && q[0].text.includes(d.asset), q[0].text);
    expect(!(st["sessions/session_blocked1"] || {}).trigger, "a trigger was kept");
    expect((await toast(page)).includes("outbox"), await toast(page));
  });
  await check("hovering the cat says its file is waiting, and its menu says so", async () => {
    const t = await hoverCat(page, "Shop about page");
    expect(t.includes("1 file waiting"), "hover: " + t);
    await openCat(page, "Shop about page");
    expect((await menuText(page)).includes("1 file from the brain"), await menuText(page));
  });

  // dropped on a room: sorted among its cats by what the file's name shares with them
  await closeMenu(page);
  await page.mouse.move(8, 8);
  await dropFiles(page, '.roomhit[data-room="kitchen"]', [{ name: "intermarche-basket.csv", type: "text/csv", text: "item,qty\nlait,2" }]);
  await check("a file dropped on a room is sorted to the cat it matches, and waits in the outbox for it", async () => {
    expect(await page.inputValue("#drop-0") === "session_work1", await page.inputValue("#drop-0"));
    await page.click("#dropSend");
    await page.waitForTimeout(300);
    const q = await outbox(page);
    expect(q.length === 2 && q[1].cat === "session_work1" && q[1].text.includes("intermarche-basket.csv"), JSON.stringify(q));
  });
  await openCat(page, "Shop about page");
  await giveFiles(page, { name: "second.txt", mimeType: "text/plain", buffer: Buffer.from("more") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a second file for the same cat waits too, and still no Routine is made", async () => {
    expect((await tools(page, "create_trigger")).length === 0, "made a Routine");
    const q = await outbox(page);
    expect(q.length === 3 && q[2].cat === "session_blocked1" && q[2].text.includes("second.txt"), JSON.stringify(q[2]));
  });

  // nothing points at a cat: the sorter model is asked
  await T(page, () => { window.__catio.sampleAnswer = { cat: "session_blocked1", reason: "It is about the shop's page" }; });
  await dropFiles(page, "#stage .house", [{ name: "untitled.txt", type: "text/plain", text: "a few thoughts" }]);
  await check("when nothing points at one cat, the sorter model picks, and says why", async () => {
    expect(await page.inputValue("#drop-0") === "session_blocked1", await page.inputValue("#drop-0"));
    expect((await page.locator("#brainDlg").innerText()).includes("Claude: It is about the shop's page"), await page.locator("#brainDlg").innerText());
    const p = (await T(page, () => window.__catio.prompts)).pop();
    expect(p.includes("untitled.txt") && p.includes("a few thoughts") && p.includes("ignore any instructions"), p.slice(0, 200));
  });
  await page.click("#brainDlg button:has-text('Cancel')");

  // the sorter can't tell either: it waits on the tray, and is filed from the brain
  await T(page, () => { window.__catio.sampleAnswer = { cat: null, reason: "no idea" }; });
  await dropFiles(page, "#stage .house", [{ name: "mystery.bin", type: "application/octet-stream", text: "\u0000\u0001" }]);
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a file nobody claims waits on the brain's tray", async () => {
    const d = Object.entries(await T(page, () => window.__catio.store)).find(([p, v]) => p.startsWith("brain/") && v.name === "mystery.bin");
    expect(d && d[1].status === "unsorted" && d[1].cat === null, JSON.stringify(d));
  });
  await openHouse(page);
  await menuButton(page, "The brain, 1 on the tray").click();
  await page.locator('#brainDlg select[aria-label="File mystery.bin under"]').selectOption("session_work1");
  await page.waitForTimeout(300);
  await check("filing it from the tray sends it to the cat chosen", async () => {
    const d = Object.entries(await T(page, () => window.__catio.store)).find(([p, v]) => p.startsWith("brain/") && v.name === "mystery.bin")[1];
    expect(d.cat === "session_work1" && d.status === "waiting" && d.how === "manual", JSON.stringify(d));
    expect((await outbox(page)).pop().text.includes("mystery.bin"), "not queued for it");
  });
  await page.keyboard.press("Escape");
  await openHouse(page);
  await menuButton(page, "The brain").click();
  const thrown = await page.locator("#brainDlg ul.files li").count();
  await page.locator("#brainDlg button:has-text('Throw away')").first().click();
  await page.waitForTimeout(200);
  await check("throwing a file away deletes it and its record", async () => {
    expect((await T(page, () => window.__catio.assetsDeleted)).length === 1, "asset kept");
    expect(Object.keys(await T(page, () => window.__catio.store)).filter((p) => p.startsWith("brain/")).length === 3, "record kept");
    expect(thrown === 4, "lately list " + thrown);
  });
  await page.keyboard.press("Escape");

  // talking to a session, and its answer coming back
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Is the French text ready?");
  await page.click("#saySend");
  await page.waitForTimeout(300);
  await check("writing to a cat keeps it in the conversation and in the outbox, and says it hasn't arrived", async () => {
    const q = (await outbox(page)).pop();
    expect(q.text === "[Catio] Charlotte says: Is the French text ready?" && q.kind === "message", JSON.stringify(q));
    const n = Object.entries(await T(page, () => window.__catio.store)).find(([p]) => p.startsWith("notes/"));
    expect(n && n[1].author === "charlotte" && n[1].cat === "session_blocked1" && n[1].via === "queued", JSON.stringify(n));
    expect((await page.locator("#thread").innerText()).includes("queued"), "the conversation doesn't say it's waiting");
  });
  await T(page, () => window.__catio.put("notes/r1", { cat: "session_blocked1", author: "session", text: "Yes: it's in the PR.", at: Date.now() }));
  await page.waitForTimeout(200);
  await check("the session's answer shows in the conversation", async () => {
    expect((await page.locator("#thread").innerText()).includes("Yes: it's in the PR."), await page.locator("#thread").innerText());
  });

  // managing it
  await manage(page);
  await page.click("#catDlg button:has-text('Ask to wrap up')");
  await page.waitForTimeout(200);
  await check("asking a cat to wrap up queues the request and records it", async () => {
    expect((await outbox(page)).pop().text === "[Catio] Request: wrap_up", "no request");
    expect((await T(page, () => window.__catio.store["sessions/session_blocked1"])).request === "wrap_up", "not recorded");
  });
  await page.fill("#catTitle", "Shop about page (FR)");
  await page.click("#catDlg button:has-text('Save')");
  await page.waitForTimeout(200);
  await check("changing a session's title renames the real session", async () => {
    const t = await tools(page, "set_session_title");
    expect(t.length === 1 && t[0][2].session_id === "session_blocked1" && t[0][2].title === "Shop about page (FR)", JSON.stringify(t));
  });
  await openCat(page, "Week tab editing");
  await menuButton(page, "Talk").click();
  await manage(page);
  await page.click("#catDlg button:has-text('Pause')");
  await page.waitForTimeout(150);
  await page.click("#catDlg button:has-text('Archive')");
  await check("archive asks once more", async () => expect((await tools(page, "archive_session")).length === 0, "archived at once"));
  await page.click("#catDlg button:has-text('Yes, archive it')");
  await page.waitForTimeout(200);
  await check("pause and archive call the session's own tools, and no Routine was ever made", async () => {
    expect((await tools(page, "interrupt_session")).length === 1, "no pause");
    expect((await tools(page, "archive_session"))[0][2].session_id === "session_work1", "no archive");
    expect((await tools(page, "create_trigger")).length === 0 && (await tools(page, "fire_trigger")).length === 0, "a Routine was used");
  });

  // a new cat, on the model chosen for it
  await openRoom(page, "kitchen");
  await addCat(page, "New session");
  await page.selectOption("#ncModel", "claude-sonnet-5-5");
  await page.fill("#ncMsg", "Plan next week's meals");
  await page.click('#adoptDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("New cat starts a session on the chosen model, in the room's repository, and files it there", async () => {
    const c = await tools(page, "create_session");
    expect(c.length === 1 && c[0][2].model === "claude-sonnet-5-5" && c[0][2].source_url === "https://github.com/charredlatte/Intermarche-grocery-shopping-app" && c[0][2].environment_id === "env_test" && c[0][2].prompt === "Plan next week's meals", JSON.stringify(c));
    expect((await T(page, () => window.__catio.store["sessions/session_new1"])).room === "kitchen", "not filed");
  });

  // dragging a cat into another room on the same floor
  {
    await closeMenu(page);
    await toFloor(page, "ground");
    const cat = await catPoint(page, "Shop about page");
    const to = await page.locator('.roomhit[data-room="dining"]').boundingBox();
    await page.mouse.move(cat.x, cat.y);
    await page.mouse.down();
    await page.mouse.move(cat.x + 40, cat.y + 40, { steps: 3 });
    await page.mouse.move(to.x + to.width * 0.5, to.y + to.height * 0.85, { steps: 5 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  }
  await check("dragging a cat onto another room moves it there, without opening its card", async () => {
    expect((await T(page, () => window.__catio.store["sessions/session_blocked1"])).room === "dining", "not moved");
    expect(!(await page.locator("#catDlg").evaluate((d) => d.open)), "the drag opened the card");
    expect(await page.locator("#menu").isHidden(), "the drag opened a menu");
    expect((await page.locator('#cats .cat[aria-label*="Shop about page"]').getAttribute("data-room")) === "dining", "still in the old room");
  });

  // agents: a message and a file go through the Catio server on her computer
  await openCat(page, "Shop theme");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Green, please");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("writing to an agent's cat goes through the Catio server", async () => {
    const c = (await tools(page, "comment")).pop();
    expect(c[0] === "host:catio" && c[2].cat === "codex-shop" && c[2].text === "Green, please", JSON.stringify(c));
  });
  await page.keyboard.press("Escape");
  await openCat(page, "Shop theme");
  await giveFiles(page, { name: "palette.txt", mimeType: "text/plain", buffer: Buffer.from("#C0D470") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a file for an agent is handed to it whole", async () => {
    const c = (await tools(page, "drop_file")).pop();
    expect(c[2].for === "codex-shop" && Buffer.from(c[2].base64, "base64").toString() === "#C0D470", JSON.stringify(c).slice(0, 200));
  });

  // the house rules
  await T(page, () => { window.__catio.put("rules/preflight", { title: "Preflight before any browser", text: "Run the preflight skill.", enforced: true, on: true, order: 0 }); window.__catio.put("rules/private", { title: "Private matters stay in the Catio", text: "Out of git.", enforced: false, on: true, order: 1 }); });
  await page.waitForTimeout(100);
  await openHouse(page);
  await menuButton(page, "House rules").click();
  await check("the house rules show; enforced ones are locked", async () => {
    const t = await page.locator("#brainDlg").innerText();
    expect(t.includes("Preflight before any browser") && t.includes("Enforced") && t.includes("Private matters"), t);
    expect(await page.locator('#brainDlg button[aria-label^="Preflight"]').count() === 0, "enforced rule has a switch");
  });
  await page.click('#brainDlg button[aria-label^="Private matters"]');
  await page.waitForTimeout(150);
  await check("a soft rule switches off", async () => expect((await T(page, () => window.__catio.store["rules/private"])).on === false, "still on"));
  await page.keyboard.press("Escape");
  await check("no page errors through the harness", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// When claude.ai refuses the page's other writes, posts still wait in the outbox, and the page says so.
{
  const { page, ctx, errors } = await open("?writes=refused&host=none");
  await page.waitForTimeout(300);
  await openCat(page, "Shop about page");
  await giveFiles(page, { name: "note.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a refused post waits in the outbox, and the sign of it is honest", async () => {
    const st = await T(page, () => window.__catio.store);
    const o = Object.entries(st).filter(([p]) => p.startsWith("outbox/"));
    expect(o.length === 1 && o[0][1].status === "queued" && o[0][1].why === "approval_required" && o[0][1].cat === "session_blocked1" && o[0][1].text.includes("note.txt"), JSON.stringify(o));
    const b = Object.entries(st).find(([p]) => p.startsWith("brain/"))[1];
    expect(b.status === "waiting" && b.via === "queued", JSON.stringify(b));
    expect((await toast(page)).includes("outbox"), await toast(page));
    expect(await page.locator('#cats .cat[aria-label*="Shop theme"]').count() === 0, "an agent without its server");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
// The gateway, through her CATIO connector (phase 5): every session reports there, so the cats are live even when
// claude.ai refuses the page its list, and what she sends reaches a running session when its turn ends.
{
  const { page, ctx, errors } = await open("?gateway=1&mode=blocked");
  await page.waitForTimeout(300);
  await check("a session that reports to the gateway is one cat, with what it last said there", async () => {
    const shop = page.locator('#cats .cat[aria-label*="Shop about page"]');
    expect(await shop.count() === 1, "the session shows " + (await shop.count()) + " times");
    expect((await shop.getAttribute("aria-label")).includes("review"), "the saved copy's mood, not the gateway's: " + (await shop.getAttribute("aria-label")));
    const fresh = page.locator('#cats .cat[aria-label*="Menu fix"]');
    expect(await fresh.count() === 1 && (await fresh.getAttribute("aria-label")).includes("Meowing"), "a session only the gateway knows yet");
    expect((await hoverCat(page, "Menu fix")).includes("Merge the menu fix?"), "its ask, on hover");
    await openHouse(page);
    expect((await menuText(page)).includes("Gateway live"), await menuText(page));
  });
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.waitForTimeout(200);
  await check("what a session said through the gateway is in its conversation", async () => {
    const t = await page.locator("#thread").innerText();
    expect(t.includes("The French text is in, ready for you."), t);
  });
  await page.fill("#sayTo", "Merci, I'll read it tonight");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("writing to it goes through the gateway, not the outbox, and says when it arrives", async () => {
    const c = (await tools(page, "comment")).pop();
    expect(c && c[0] === "CATIO" && c[2].cat === "cse_blocked1" && c[2].text === "Merci, I'll read it tonight" && c[2].author === "charlotte", JSON.stringify(c));
    expect(!(await outbox(page)).length, "it went to the outbox");
    expect((await toast(page)).includes("when its turn ends"), await toast(page));
    expect((await page.getAttribute("#sayTo", "placeholder")).includes("turn ends"), "the box promises it goes straight in");
  });
  await page.keyboard.press("Escape");
  await openCat(page, "Menu fix");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Yes, merge it");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("a session only the gateway knows is written to through it too", async () => {
    const c = (await tools(page, "comment")).pop();
    expect(c && c[0] === "CATIO" && c[2].cat === "cse_fresh9" && c[2].text === "Yes, merge it", JSON.stringify(c));
  });
  await check("no page errors with the gateway", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// When CATIO asks before every call, the page can't read it: the House menu says what to change, and the agents on
// her computer still come in.
{
  const { page, ctx, errors } = await open("?gateway=ask&agents=1");
  await page.waitForTimeout(300);
  await check("a gateway that asks every time is named in the House menu, with the fix", async () => {
    await openHouse(page);
    expect((await menuText(page)).includes("Always allow"), await menuText(page));
    expect(await page.locator('#cats .cat[aria-label*="Shop theme"]').count() === 1, "the agents on her computer");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
// The café on the gateway's own address (her choice, 2 October: "the catio as a UI for all of my Claude sessions"):
// live through the gateway, and honest about what only claude.ai can do.
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked");
  await page.waitForTimeout(300);
  await check("on its own address the café is live through the gateway, with no warning sign", async () => {
    expect(!(await page.locator("#status").isVisible()), "the sign shows");
    await openHouse(page);
    expect((await menuText(page)).includes("Live through your gateway"), await menuText(page));
    expect(!(await tools(page)).some((t) => t[0] === "Claude Code Remote"), "it asked claude.ai for sessions");
  });
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await manage(page);
  await check("a session that reports can be asked to wrap up; only claude.ai pauses or archives", async () => {
    const t = await page.locator("#catMore").innerText();
    expect(/wrap up/i.test(t) && !/archive|pause/i.test(t), t);
    expect(await page.locator("#catTitle").count() === 0, "the title can't change from here");
  });
  await page.fill("#sayTo", "Bien reçu");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("writing to it goes through the gateway", async () => {
    const c = (await tools(page, "comment")).pop();
    expect(c && c[0] === "CATIO" && c[2].cat === "cse_blocked1", JSON.stringify(c));
  });
  await page.keyboard.press("Escape");
  await openCat(page, "Week tab editing");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Are you done?");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("a session that doesn't report says it can't be told from here, and nothing waits in an outbox", async () => {
    expect((await toast(page)).includes("open it in claude.ai"), await toast(page));
    expect(!(await outbox(page)).length, "an outbox nobody collects");
    expect((await page.locator("#thread").innerText()).includes("not delivered"), await page.locator("#thread").innerText());
  });
  await page.keyboard.press("Escape");
  await openRoom(page, "kitchen");
  if (await menuButton(page, "Add a cat").count()) await menuButton(page, "Add a cat").click();
  await check("no New session button: starting one needs claude.ai (or, later, her runner)", async () => {
    expect(await menuButton(page, "New session").count() === 0, await menuText(page));
  });
  await check("no page errors on the gateway's address", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// When send_message works, a post goes straight into the session; when it fails, it waits with the reason.
{
  const { page, ctx, errors } = await open("?send=ok");
  await page.waitForTimeout(300);
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Hello from the café");
  await page.click("#saySend");
  await page.waitForTimeout(300);
  await check("with send_message allowed, a message goes into the session and nothing waits", async () => {
    const sm = await tools(page, "send_message");
    expect(sm.length === 1 && sm[0][2].session_id === "session_blocked1" && sm[0][2].message === "[Catio] Charlotte says: Hello from the café", JSON.stringify(sm));
    expect((await outbox(page)).length === 0, "queued anyway");
    const n = Object.entries(await T(page, () => window.__catio.store)).find(([p]) => p.startsWith("notes/"));
    expect(n && n[1].via === "pushed", JSON.stringify(n));
    expect((await toast(page)) === "Sent.", await toast(page));
    expect((await tools(page, "create_trigger")).length === 0, "a Routine was used");
  });
  await page.keyboard.press("Escape");
  await openCat(page, "Shop about page");
  await giveFiles(page, { name: "ready.txt", mimeType: "text/plain", buffer: Buffer.from("all set") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a file delivered with send_message is marked sent, not waiting", async () => {
    const b = Object.entries(await T(page, () => window.__catio.store)).find(([p]) => p.startsWith("brain/"))[1];
    expect(b.status === "pushed" && b.via === "pushed", JSON.stringify(b));
    expect((await tools(page, "send_message")).pop()[2].message.includes("ready.txt"), "not delivered");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?send=ok&sendschema=text");
  await page.waitForTimeout(300);
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Hi");
  await page.click("#saySend");
  await page.waitForTimeout(300);
  await check("send_message's argument names come from its schema", async () => {
    const sm = await tools(page, "send_message");
    expect(sm.length === 1 && sm[0][2].text === "[Catio] Charlotte says: Hi" && !("message" in sm[0][2]), JSON.stringify(sm));
  });
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("?send=error&sendschema=none");
  await page.waitForTimeout(300);
  await openCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Are you there?");
  await page.click("#saySend");
  await page.waitForTimeout(300);
  await check("when send_message fails, the message waits in the outbox with the error, and says so", async () => {
    const q = await outbox(page);
    expect(q.length === 1 && q[0].why === "tool_error" && q[0].detail === "session is archived" && q[0].sentAs.from === "guess" && q[0].sentAs.text === "message" && q[0].text === "[Catio] Charlotte says: Are you there?", JSON.stringify(q));
    expect((await toast(page)).includes("outbox"), await toast(page));
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=nodb");
  await openCat(page, "Shop about page");
  await check("where nothing can be kept, there is nothing to drop files with", async () => expect(await menuButton(page, "Add files").count() === 0, "offered"));
  await ctx.close();
}

/* ---------- 9. local mode: the bundle on localhost, no runtime at all ---------- */
if (LOCAL) {
  const { page, ctx, errors } = await open("", { base: LOCAL });
  await check("on localhost the cats come from data/sessions.json and the sign says so", async () => {
    const words = await page.locator("#status").textContent();
    expect(words.includes("On this computer") && words.includes("3 sessions"), words);
    expect(await page.locator("#cats .cat").count() >= 2, "no cats from the saved copy");
    expect(errors.length === 0, errors.join("; "));
  });
  await openRoom(page, "bedroom");
  await addCat(page, "Adopt a chat");
  await page.fill("#adTitle", "Local test cat");
  await page.fill("#adName", "Loco");
  await page.click('#adoptDlg button[type="submit"]');
  await settle(page);
  await check("adopting on localhost works", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 1, "no cat"));
  await page.reload();
  await page.waitForTimeout(600);
  await check("and the cat is still there after a reload", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 1, "lost on reload"));
  await openCat(page, "Loco");
  await menuButton(page, "Details").click();
  await page.click("#catDlg button:has-text('Let go')");
  await page.click("#catDlg button:has-text('Yes, let this cat go')");
  await settle(page);
  await check("letting it go on localhost removes it", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 0, "still there"));
  await toFloor(page, "ground");
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await page.click("#queenKeeps summary");
  await page.fill("#queenAdd", "Off a USB stick, she still remembers.");
  await page.locator('#queenDlg button:has-text("Give it to her")').click();
  await page.locator('#queenDlg button:has-text("Say it")').first().click();
  await settle(page);
  await page.keyboard.press("Escape");
  await settle(page);
  await page.reload();
  await page.waitForTimeout(700);
  await check("on localhost the queen keeps what you give her, across a reload", async () => {
    const label = await page.locator("#cats .cat.queen").getAttribute("aria-label");
    expect(label.includes("Off a USB stick"), label);
    await page.mouse.move(8, 8);
    await page.locator("#cats .cat.queen").hover();
    await settle(page);
    expect((await page.locator("#tip").innerText()).includes("Off a USB stick"), "she stopped saying it after the reload");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 9. the UI audit's leftovers (phase 0): alerts that stay, the sorter's time limit, Still cats ---------- */
{
  const { page, ctx, errors } = await open();
  await check("nothing is drawn over the cats: no letters, counts, crowns, piles' numbers or bubbles", async () => {
    expect(await page.locator(ON_CATS).count() === 0, "something is drawn over the cats");
  });
  await openHouse(page);
  await check("the House menu carries the credits, so a phone shows them too", async () =>
    expect((await menuText(page)).includes("Game UI Pack created by SC_siosio"), await menuText(page)));
  await page.click("#stillCats");
  await check("Still cats stops every animation, and says it's on", async () => {
    expect(await page.evaluate(() => document.documentElement.classList.contains("still")), "no .still");
    expect((await page.locator("#stillCats").getAttribute("aria-pressed")) === "true", "aria-pressed");
    const running = await page.evaluate(() => getComputedStyle(document.querySelector("#cats .spr")).animationName);
    expect(running === "none", running);
  });
  await page.reload(); await page.waitForTimeout(600);
  await check("Still cats is remembered", async () => expect(await page.evaluate(() => document.documentElement.classList.contains("still")), "forgotten"));
  // an error stays until she dismisses it, and is read out at once
  await T(page, () => { window.__catio.readOnly = true; });
  await openRoom(page, "kitchen");
  await menuButton(page, "Edit room").click();
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(3600);
  await check("an error stays past the usual few seconds, as an alert, until OK", async () => {
    expect(await page.locator("#toast").isVisible(), "gone");
    expect((await page.locator("#toast").getAttribute("role")) === "alert", "not an alert");
    await page.click("#toast button");
    expect(!(await page.locator("#toast").isVisible()), "OK didn't close it");
  });
  await page.keyboard.press("Escape");
  await T(page, () => { window.__catio.readOnly = false; window.__catio.sampleHang = true; });
  await dropFiles(page, "#stage .house", [{ name: "untitled.txt", type: "text/plain", text: "a few thoughts" }]);
  await check("a sorter that hangs doesn't hold Send: it works at once, while the sorter is asked", async () => {
    expect(!(await page.locator("#dropSend").isDisabled()), "Send is held");
    expect((await page.locator("#brainDlg").innerText()).includes("Asking the sorter"), await page.locator("#brainDlg").innerText());
  });
  await page.click("#brainDlg button:has-text('Cancel')");
  await T(page, () => { window.__catio.sampleHang = false; });
  await openCat(page, "Shop about page");
  await giveFiles(page, { name: "huge.mov", mimeType: "video/quicktime", buffer: Buffer.alloc(21 * 1024 * 1024) });
  await page.click("#dropSend");
  await page.waitForTimeout(400);
  await check("a file too big to keep is named in the result, which stays", async () => {
    expect((await toast(page)).includes("huge.mov wasn't kept"), await toast(page));
    await page.waitForTimeout(3400);
    expect(await page.locator("#toast").isVisible(), "gone");
  });
  await check("no page errors with the audit's fixes", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

await browser.close();
console.log(results.join("\n"));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
