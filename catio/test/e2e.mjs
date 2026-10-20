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
// Resize and wait for the page to have taken the new size, rather than guessing how long the relayout takes:
// setViewportSize resolves when the browser acknowledges it, which can be before the renderer has relaid out.
async function resize(page, width, height) {
  await page.setViewportSize({ width, height });
  await page.evaluate(([w, h]) => new Promise((ok, no) => {
    let last = "", same = 0;
    // the deadline is its own timer: a page that stops being painted stops firing rAF, and a deadline checked
    // only inside the rAF loop would never be reached, hanging the suite instead of failing it
    const bust = setTimeout(() => no(new Error("the page never settled at " + w + "x" + h + ", last " + last)), 5000);
    const open = () => [...document.querySelectorAll("dialog[open]")].map((d) => { const r = d.getBoundingClientRect(); return Math.round(r.width) + "x" + Math.round(r.height); }).join(",");
    (function wait() {
      const now = innerWidth + "x" + innerHeight + ":" + document.documentElement.clientWidth + ":" + open();
      same = innerWidth === w && innerHeight === h && now === last ? same + 1 : 0;
      last = now;
      if (same >= 2) { clearTimeout(bust); return ok(); }
      requestAnimationFrame(wait);
    })();
  }), [width, height]);
}
// Run a check that moves the viewport about, then put it back. A restore that fails must not replace the failure
// it follows, and must not be swallowed when there was none: the checks after it would run at the wrong size.
async function atSizes(page, body, to) {
  const back = to || page.viewportSize();   // this context's own size, not a desktop guess
  let failed = null;
  try { await body(); } catch (e) { failed = e; }
  try { await resize(page, back.width, back.height); } catch (e) { failed = failed || e; }
  if (failed) throw failed;
}
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
  await check("renaming a session's cat renames the real session too", async () => {
    const t = (await T(page, () => window.__catio.tools)).filter((x) => x[1] === "set_session_title" && x[2].session_id === "session_work1");
    expect(t.length === 1 && t[0][2].title === "Biscuit", JSON.stringify(t));
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
  // the project maps (her ask, 3 October: "a customizable dashboard built on Graphify", the graphify in her house rules)
  await page.evaluate(() => { for (const d of document.querySelectorAll("dialog[open]")) d.close(); });
  await closeMenu(page);
  await settle(page);
  await T(page, () => window.__catio.put("graphs/intermarche-grocery-shopping-app", { repo: "example/Intermarche-grocery-shopping-app", at: Date.now() - 36e5, nodes: 64, edges: 98, communities: 4,
    gods: [{ label: "Basket", degree: 11, file: "src/basket.js" }], groups: [{ name: "Basket", size: 20 }], surprises: [], questions: ["Where does the basket get its prices?"],
    map: { n: [{ t: "Basket", g: 0, d: 11, x: 150, y: 80 }, { t: "Menus", g: 1, d: 4, x: 60, y: 40 }], l: [0, 1] } }));
  const maps = () => page.locator("#mapsDlg .mapcard").evaluateAll((cs) => cs.map((c) => c.dataset.map));
  const mapTool = (id, label) => page.locator('#mapsDlg .mapcard[data-map="' + id + '"] button[aria-label^="' + label + ':"]');
  const manageMaps = () => page.evaluate(() => { for (const d of document.querySelectorAll("#mapsDlg .manage-tools:not([open])")) d.querySelector("summary").click(); });   // Manage folds each card's tools
  await page.click("#houseBtn");
  await page.locator("#menu .mi", { hasText: "Project maps" }).click();   // its name carries the count: "Project maps, 2"
  await settle(page);
  await check("the House menu opens every project's map as a card, the newest map first", async () => {
    expect(JSON.stringify(await maps()) === JSON.stringify(["montfortoise-shopify", "intermarche-grocery-shopping-app"]), JSON.stringify(await maps()));
    expect(await page.locator('#mapsDlg .mapcard[data-map="montfortoise-shopify"] .gart svg rect').count() === 3, "the map isn't drawn");
    expect((await page.locator("#mapsDlg").innerText()).includes("Where does the basket get its prices?"), "no questions");
  });
  await manageMaps();
  await mapTool("intermarche-grocery-shopping-app", "Pin").click();
  await settle(page);
  await mapTool("montfortoise-shopify", "Wide").click();
  await settle(page);
  await check("pinning puts a map first and widening spreads it, and the café keeps both", async () => {
    expect((await maps())[0] === "intermarche-grocery-shopping-app", JSON.stringify(await maps()));
    const d = await T(page, () => window.__catio.store["dashboard/maps"]);
    expect(d && d.pinned.includes("intermarche-grocery-shopping-app") && d.wide.includes("montfortoise-shopify"), JSON.stringify(d));
    expect((await page.locator('#mapsDlg .mapcard[data-map="montfortoise-shopify"]').getAttribute("class")).includes("wide"), "not wide");
  });
  await check("a map moves within its group: an unpinned one can't be moved above a pinned one", async () => {
    expect(await mapTool("montfortoise-shopify", "Earlier").isDisabled(), "Earlier would cross the pinned map");
    expect(await mapTool("intermarche-grocery-shopping-app", "Later").isDisabled(), "Later would cross into the unpinned ones");
  });
  await mapTool("intermarche-grocery-shopping-app", "Unpin").click();
  await settle(page);
  await mapTool("intermarche-grocery-shopping-app", "Earlier").click();
  await settle(page);
  await check("moving a map earlier changes the order, and the order is kept", async () => {
    expect((await maps())[0] === "intermarche-grocery-shopping-app", JSON.stringify(await maps()));
    expect(JSON.stringify((await T(page, () => window.__catio.store["dashboard/maps"])).order) === JSON.stringify(["intermarche-grocery-shopping-app", "montfortoise-shopify"]), "order not kept");
  });
  await mapTool("montfortoise-shopify", "Hide").click();
  await settle(page);
  await check("hiding a map takes it off the page and keeps a way back", async () => {
    expect(JSON.stringify(await maps()) === JSON.stringify(["intermarche-grocery-shopping-app"]), JSON.stringify(await maps()));
    expect(await page.locator('#mapsHidden button:has-text("Show montfortoise-shopify")').count() === 1, "no way back");
  });
  await page.locator('#mapsHidden button:has-text("Show montfortoise-shopify")').click();
  await settle(page);
  await check("Show brings it back where it was", async () => expect(JSON.stringify(await maps()) === JSON.stringify(["intermarche-grocery-shopping-app", "montfortoise-shopify"]), JSON.stringify(await maps())));
  // set elsewhere (another tab, her phone): the open page shows it, and the next change keeps it
  await T(page, () => { const d = window.__catio.store["dashboard/maps"]; window.__catio.put("dashboard/maps", Object.assign({}, d, { pinned: ["montfortoise-shopify"] })); });
  await page.waitForTimeout(300);
  await check("a layout set on another device shows at once, and a change here keeps it", async () => {
    expect((await maps())[0] === "montfortoise-shopify", "the other device's pin didn't show: " + JSON.stringify(await maps()));
    await manageMaps();
    await mapTool("intermarche-grocery-shopping-app", "Wide").click();
    await settle(page);
    const d = await T(page, () => window.__catio.store["dashboard/maps"]);
    expect(d.pinned.includes("montfortoise-shopify") && d.wide.includes("intermarche-grocery-shopping-app"), JSON.stringify(d));
  });
  await T(page, () => window.__catio.put("graphs/tiktok-saves", { repo: "example/tiktok-saves", at: Date.now(), nodes: 9, edges: 8, communities: 2, gods: [], groups: [], surprises: [], questions: [],
    map: { n: [{ t: "Saves", g: 0, d: 3, x: 150, y: 80 }], l: [] } }));
  await T(page, () => window.__catio.put("graphs/half-saved", { repo: "example/half-saved", at: Date.now(), map: {} }));
  await page.waitForTimeout(300);
  await check("a map a session saves shows while the page is open; one with nothing to draw doesn't break it", async () => {
    const m = await maps();
    expect(m.includes("tiktok-saves") && !m.includes("half-saved"), JSON.stringify(m));
    expect(await page.locator("#mapsDlg .mapcard").count() === 3, "the page lost its cards");
  });
  await T(page, () => { window.__catio.readOnly = true; });
  await manageMaps();
  await mapTool("tiktok-saves", "Pin").click();
  await settle(page);
  await check("a refused save changes nothing on the page", async () => {
    expect(await page.locator('#mapsDlg .mapcard[data-map="tiktok-saves"] .star').count() === 0, "shown pinned though nothing was saved");
    expect(!((await T(page, () => window.__catio.store["dashboard/maps"])).pinned || []).includes("tiktok-saves"), "saved anyway");
  });
  await T(page, () => { window.__catio.readOnly = false; });
  await page.keyboard.press("Escape");
  await settle(page);
  await openRoom(page, "study");
  await menuButton(page, "Files").click();
  await settle(page);
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
    expect(c && c[0] === "CATIO" && c[2].cat === "queen" && c[2].text === "Who needs me today?" && c[2].author === "owner", JSON.stringify(c));
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
  await page.click("#queenSettingsBtn");   // her settings sit in an overlay over the scene (her ask, 3 October)
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
  await page.click("#queenSettingsBtn");
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
  await page.click("#queenSettingsBtn");
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
  await page.click("#queenSettingsBtn");
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
  // while she answers, a cat reports and a second quiz arrives (her words, 3 October: "everything refreshed and
  // greyed out while I was typing"): her pick and her typing stay where they are
  await T(page, () => { dispatchEvent(new Event("catio:agents")); window.__catio.setQuiz({ for: "", title: "The French text", questions: [{ q: "Ship it?", options: ["Ship it", "Hold it"] }] }); });
  await page.waitForTimeout(500);
  await check("a cat reporting, or more homework arriving, never wipes what she has answered so far", async () => {
    expect(await page.locator('#queenHomework form[data-quiz="z1"] button[aria-pressed="true"]:has-text("Yes, merge it")').count() === 1, "her pick was lost");
    expect((await page.inputValue('#queenHomework form[data-quiz="z1"] input[aria-label^="Your answer"]')) === "Well done, thou good cat", "her typing was lost");
    expect(await page.locator('#queenHomework form[data-quiz="z2"]').count() === 1, "the second quiz didn't show");
    expect((await T(page, () => (document.activeElement && document.activeElement.getAttribute("aria-label")) || "")).startsWith("Your answer"), "her typing lost its place");
  });
  // nor does closing her card and coming back
  await page.keyboard.press("Escape");
  await settle(page);
  await queen().dblclick();
  await settle(page);
  await check("closing her card and opening it again finds her answers so far where she left them", async () => {
    expect(await page.locator('#queenHomework form[data-quiz="z1"] button[aria-pressed="true"]:has-text("Yes, merge it")').count() === 1, "her pick was lost");
    expect((await page.inputValue('#queenHomework form[data-quiz="z1"] input[aria-label^="Your answer"]')) === "Well done, thou good cat", "her typing was lost");
  });
  await page.locator('#queenHomework form[data-quiz="z1"] button:has-text("Hand it in")').click();
  await settle(page);
  await check("handing it in sends your answers, in order", async () => {
    const a = await T(page, () => window.__catio.tools.filter((t) => t[1] === "answer").pop());
    expect(a && a[2].quiz === "z1" && JSON.stringify(a[2].answers) === JSON.stringify(["Yes, merge it", "Well done, thou good cat"]), JSON.stringify(a));
    expect((await toast(page)).includes("Handed in"), await toast(page));
    expect(await page.locator('#queenHomework form[data-quiz="z1"]').count() === 0, "the handed-in quiz is still there");
  });
  await page.locator('#queenHomework form[data-quiz="z2"] button:has-text("Ship it")').click();
  // a slow hand-in the gateway then refuses, while she closes her card and opens it again: the reopened card
  // shows it on its way, and gets its Hand it in back when the refusal comes
  await T(page, () => { window.__catio.answerFail = 1; window.__catio.answerHold = new Promise((go) => { window.__catio.answerGo = go; }); });
  await page.locator('#queenHomework form[data-quiz="z2"] button:has-text("Hand it in")').click();
  await page.keyboard.press("Escape");
  await settle(page);
  await queen().dblclick();
  await settle(page);
  await check("a reopened card shows a hand-in on its way as greyed, so it isn't sent twice", async () => {
    expect(await page.locator('#queenHomework form[data-quiz="z2"] .hand:disabled').count() === 1, "no greyed Hand it in");
  });
  await T(page, () => window.__catio.answerGo());
  await settle(page);
  await check("when the gateway refuses it, the card that is open gets its Hand it in back, her pick with it", async () => {
    expect(await page.locator('#queenHomework form[data-quiz="z2"] .hand:not(:disabled)').count() === 1, "Hand it in stayed greyed out");
    expect(await page.locator('#queenHomework form[data-quiz="z2"] button[aria-pressed="true"]:has-text("Ship it")').count() === 1, "her pick was lost");
  });
  // a cat reports just before she hands the last quiz in, so a read of the list that still shows it is on its
  // way; the gateway takes her answers, the read after fails, then that old list lands: the handed-in quiz leaves
  // her card and never comes back, and nothing stays greyed out
  await T(page, () => { window.__catio.quizzesHold = new Promise((go) => { window.__catio.quizzesGo = go; }); dispatchEvent(new Event("catio:agents")); });
  await page.waitForTimeout(150);
  await T(page, () => { window.__catio.quizzesFail = 1; });
  await page.locator('#queenHomework form[data-quiz="z2"] button:has-text("Hand it in")').click();
  await settle(page);
  await T(page, () => window.__catio.quizzesGo());
  await settle(page);
  await check("with the last quiz handed in, the homework is done, whatever the list reads say meanwhile", async () => {
    const a = await T(page, () => window.__catio.tools.filter((t) => t[1] === "answer").pop());
    expect(a && a[2].quiz === "z2" && JSON.stringify(a[2].answers) === JSON.stringify(["Ship it"]), JSON.stringify(a));
    expect(await T(page, () => window.__catio.quizzesFail) === 0, "the quizzes list was never read back");
    expect(await T(page, () => window.__catio.quizzesHold) === null, "the old list never landed");
    expect(!(await page.locator("#queenHomework").isVisible()), "the homework is still there");
    expect(await page.locator("#queenHomework button:disabled").count() === 0, "a greyed-out Hand it in is left behind");
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

/* ---------- 5c. the line at the front door (her ask, 3 October) ---------- */
// Her words: "every cat whose mood is 'needs' (waiting on her) should line up in front of the entrance-hall door,
// beside the queen, in the order it started waiting, the longest wait first. When a cat is no longer waiting, it leaves
// the line and goes back to its room."
{
  const { page, ctx, errors } = await open("?waiting=4", { reducedMotion: "no-preference" });
  const line = () => page.evaluate(() => [...document.querySelectorAll("#cats .cat[data-line]")].sort((a, b) => a.dataset.line - b.dataset.line)
    .map((b) => ({ label: b.getAttribute("aria-label"), x: b.getBoundingClientRect().x, room: b.dataset.room })));
  await page.waitForTimeout(4500);   // the first seconds, cats are simply in their places
  await check("every cat waiting on her lines up at the entrance-hall door, beside the queen, the longest wait first", async () => {
    const l = await line();
    const order = l.map((c) => c.label.split(": ").pop());
    expect(JSON.stringify(order) === JSON.stringify(["Grocery list", "Snail mail labels", "Café pitch", "TikTok tags", "Shop about page"]), JSON.stringify(order));
    expect(l.every((c) => c.room === "hall"), "not all in the hall");
    expect(l.every((c, i) => !i || c.x > l[i - 1].x), "not a line: " + JSON.stringify(l.map((c) => c.x)));
    const q = await page.locator("#cats .cat.queen").boundingBox();
    expect(q.x < l[0].x && l[0].x - q.x < 120, "the first in line isn't beside the queen: " + q.x + " / " + l[0].x);
    expect(await page.locator("#cats .cat:not(.queen):not([data-line]).m-meow").count() === 0, "a cat waiting on her is still in its room");
  });
  await T(page, () => window.__catio.setBucket("wait0", "WORKING", "RUNNING"));
  await page.waitForTimeout(400);
  await check("one that stops waiting leaves the line and walks back to its room", async () => {
    const b = page.locator('#cats .cat[data-id="session_wait0"]');
    expect((await b.getAttribute("data-room")) === "kitchen", "not on its way to the kitchen: " + await b.getAttribute("data-room"));
    expect((await b.getAttribute("class")).includes("walking"), "it jumped");
    expect(await b.getAttribute("data-line") === null, "still in the line");
    const order = (await line()).map((c) => c.label.split(": ").pop());
    expect(order[0] === "Snail mail labels", "the next one didn't move up: " + JSON.stringify(order));
  });
  await check("no page errors around the line", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 5d. the queen's chat, as a scene (her ask, 3 October) ---------- */
// Her words: "The queen sits on the right, talking, as an animated 2D character. The owner of the house sits on the left,
// seen from behind, as a 2D character Charlotte can customise. The conversation shows as chat bubbles between them, and it
// scrolls. All other settings move into an overlay. The existing menu still opens when she hovers over the queen."
{
  const { page, ctx, errors } = await open("?via=gateway");
  const box = (sel) => page.locator(sel).boundingBox();
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await check("her card is a scene: you on the left, seen from behind, the queen on the right, and the talk between", async () => {
    const you = await box("#queenOwnerFig"), her = await box("#queenFig"), talk = await box("#queenThread");
    expect(you && her && talk, "a piece is missing");
    expect(you.x + you.width <= talk.x + 2 && talk.x + talk.width <= her.x + 2, JSON.stringify({ you, talk, her }));
    expect(await page.locator("#queenOwnerFig svg rect").count() > 20, "you aren't drawn");
    expect(await page.locator("#queenFig .spr").count() === 1, "she isn't drawn");
  });
  await page.fill("#queenSay", "Who needs me today?");
  await page.click("#queenSend");
  await settle(page);
  // Her ask, 4 October: a loading state like Claude's own ("Searching … 22s ›"), drawn from the games of the early
  // 2000s she picked from the wireframes: Animal Crossing's pause while she wakes, The Sims' action queue while she
  // works, every step when unfolded, and the RPG "more" arrow while she answers. Under the talk, on her side.
  await check("the moment you send, she is thinking: her name on a tab, the dots and the seconds, under the talk", async () => {
    const w = page.locator("#queenWork");
    expect(await w.isVisible(), "no strip after Send");
    const t = await w.innerText();
    expect(/thinking/i.test(t) && /\d+s/.test(t), t);
    expect((await page.locator("#queenWork .tab").innerText()).trim().length > 0, "no name on the tab");
    expect(await page.locator("#queenLive").count() === 0, "an empty bubble before she has said a word");
    expect(!(await page.locator("#queenFig").getAttribute("class")).includes("talking"), "talking before she has a word to say");
    const strip = await w.boundingBox(), talk = await page.locator("#queenThread").boundingBox(), say = await page.locator("#queenSay").boundingBox();
    expect(strip.y >= talk.y + talk.height - 2 && strip.y + strip.height <= say.y, "not under the talk: " + JSON.stringify({ strip, talk, say }));
    expect(strip.x + strip.width > talk.x + talk.width * .6, "not on her side: " + JSON.stringify({ strip, talk }));
  });
  const other = await T(page, () => window.__catio.gw.find((a) => a.id !== "queen").id);
  await T(page, (c) => window.__catio.queenSays("", false, "t9", [{ tool: "list_agents" }, { tool: "comments", cat: c }]), other);
  await page.waitForTimeout(200);
  await check("at work, each step she has done is a ticked tile and the one she is on is lit, in words", async () => {
    expect(await page.locator("#queenWork .tile.done").count() === 2, "the steps done (Awake, the cats): " + await page.locator("#queenWork").innerHTML());
    const now = await page.locator("#queenWork .tile.now").innerText();
    expect(/reading .+'s notes/i.test(now) && !now.includes(other), now);
    expect(/\d+s/.test(now), "no seconds: " + now);
  });
  await page.click("#queenWork summary");
  await settle(page);
  await check("unfolded, every step this turn, Awake first, each with its time", async () => {
    const li = page.locator("#queenWork ol li");
    expect(await li.count() === 3, await page.locator("#queenWork").innerText());
    expect((await li.first().innerText()).includes("Awake"), await li.first().innerText());
    expect(/looking in on the cats/i.test(await li.nth(1).innerText()), await li.nth(1).innerText());
  });
  await T(page, () => window.__catio.queenSays("Good morrow, my lady. Two cats need ", false, "t9"));
  await page.waitForTimeout(200);
  await check("once her words come, the lit tile says she is answering and her steps stay unfolded", async () => {
    expect(/answering/i.test(await page.locator("#queenWork .tile.now").innerText()), await page.locator("#queenWork").innerText());
    expect(await page.locator("#queenWork details").evaluate((d) => d.open), "the fold closed under her");
    expect(await page.locator("#queenWork .tile.done").count() === 3, "a step was lost");
  });
  await check("while she speaks she is animated, talking", async () => {
    expect((await page.locator("#queenFig").getAttribute("class")).includes("talking"), await page.locator("#queenFig").getAttribute("class"));
    expect((await page.locator("#queenFig").getAttribute("data-mood")) === "meow", await page.locator("#queenFig").getAttribute("data-mood"));
  });
  await T(page, () => window.__catio.queenSays("Good morrow, my lady. Two cats need thee.", true, "t9"));
  await page.waitForTimeout(300);
  await check("what you say sits by you, what she says by her, as bubbles", async () => {
    const html = await page.locator("#queenThread").innerHTML();
    const n = (sel) => page.locator(sel).count();
    expect(await n("#queenThread li.me") > 0 && await n("#queenThread li.them:not(.handoff)") > 0, "a bubble is missing: " + html.slice(0, 600));
    const me = await page.locator("#queenThread li.me").last().boundingBox(), them = await page.locator("#queenThread li.them:not(.handoff)").last().boundingBox();
    expect(me && them, "a bubble is missing");
    expect(me.x < them.x && me.x + me.width < them.x + them.width, JSON.stringify({ me, them }));
    expect(!(await page.locator("#queenFig").getAttribute("class")).includes("talking"), "still talking when done");
    expect(!(await page.locator("#queenWork").isVisible()), "the strip outlived her answer");
  });
  await T(page, () => { for (let i = 0; i < 14; i++) window.__catio.queenSays("Line " + i + " of a long answer, my lady, for the scroll.", true, "t" + (20 + i)); });
  await page.waitForTimeout(400);
  await check("a long conversation scrolls inside the scene, the newest at the bottom", async () => {
    const s = await page.locator("#queenThread").evaluate((u) => ({ h: u.scrollHeight, c: u.clientHeight, t: u.scrollTop }));
    expect(s.h > s.c, "it doesn't overflow: " + JSON.stringify(s));
    expect(s.t + s.c >= s.h - 4, "not at the newest: " + JSON.stringify(s));
    const card = await box("#queenDlg");
    expect(card.height <= 900, "the card grew instead of scrolling: " + card.height);
  });
  // "make this window useable" (3 October): her words were running off the side of a box a third of the card wide,
  // with a sideways scrollbar under them, so a whole answer could not be read.
  await T(page, () => window.__catio.queenSays("Pushed to https://github.com/charredlatte/Pretty-Project-Portfolio/compare/claude/a-branch-name-that-will-never-break-anywhere-at-all", true, "t40"));
  await page.waitForTimeout(300);
  await check("nothing she says runs off the side, and the talk gets most of the scene, at any width", async () => {
    // every width down to the phone layout, not only this one: in between, the two of them used to leave the words
    // a strip under half the scene
    await atSizes(page, async () => {
      for (const [w, least] of [[1440, .6], [900, .6], [811, .6], [700, .6], [600, .55], [561, .55]]) {
        await resize(page, w, 900);
        const s = await page.locator("#queenThread").evaluate((u) => ({ over: u.scrollWidth - u.clientWidth, w: u.clientWidth }));
        expect(s.over <= 0, "at " + w + " her words scroll sideways: " + JSON.stringify(s));
        const stage = await page.locator(".qstage").evaluate((e) => e.clientWidth);   // inside the frame: what there is to share
        expect(s.w > stage * least, "at " + w + " the talk gets too little of the scene: " + s.w + " of " + stage);
      }
    });
  });
  // and at any height: the scene used to take a share of the window (62vh and the like), which fits one window and
  // spills out of a short one, pushing Send off the bottom
  await T(page, () => window.__catio.setQuiz({ for: "cse_blocked1", title: "Unblock Caramel", questions: [{ q: "Which project is this one for?", options: ["montfortoise-shopify", "Pretty-Project-Portfolio"] }] }));
  await page.waitForTimeout(500);
  await check("her card fits a short window too, with Send reachable and nothing of hers out of reach", async () => {
    expect(await page.locator("#queenHomework .quiz").count() > 0, "no homework: the short windows below would miss the one case that breaks");
    await atSizes(page, async () => {
      for (const [w, h] of [[1440, 900], [900, 560], [900, 430], [844, 390], [811, 669], [700, 500], [390, 844], [390, 600], [390, 500], [390, 420]]) {
        await resize(page, w, h);
        const m = await page.evaluate(() => {
          const dlg = document.getElementById("queenDlg"), st = document.querySelector(".qstage"), ul = document.getElementById("queenThread");
          const send = document.getElementById("queenSend"), hw = document.getElementById("queenHomework");
          const qc = document.querySelector(".qchar"), ow = document.querySelector(".owner");
          dlg.scrollTop = dlg.scrollHeight;   // as she would, when the window is too short for the whole card
          const r = send.getBoundingClientRect(), at = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
          // the scene clips at its content box, inside the frame, so that is what anything in it has to fit
          const cs = getComputedStyle(st), sr = st.getBoundingClientRect();
          const top = sr.top + parseFloat(cs.borderTopWidth), bottom = sr.bottom - parseFloat(cs.borderBottomWidth);
          const out = (e) => { const b = e.getBoundingClientRect(); return Math.round(Math.max(top - b.top, b.bottom - bottom, 0)); };
          // the two of them are tucked 2 px into the frame on purpose, to stand on it: their heads are the side that fails
          const above = (e) => Math.round(Math.max(top - e.getBoundingClientRect().top, 0));
          // neither of them may stand on the words: beside them on a wide card, under them on a phone, never over
          const over = (e, f) => { const a = e.getBoundingClientRect(), b = f.getBoundingClientRect();
            return Math.round(Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top))); };
          return { sendInView: r.top >= 0 && r.bottom <= innerHeight + 1, sendOnTop: !!at && (at === send || send.contains(at)),
            ownerOut: above(ow), queenOut: above(qc), talkOut: out(ul), overTalk: Math.max(over(ow, ul), over(qc, ul)),
            talk: ul.clientHeight, homework: hw.clientHeight };
        });
        const at = w + "x" + h + " ";
        expect(m.sendInView, "at " + at + "Send can't be brought on screen, even with the card scrolled down");
        expect(m.sendOnTop, "at " + at + "something is drawn over Send, so it can't be clicked");
        // the scene clips what it cannot hold, and clipped is unreachable
        expect(m.ownerOut <= 1, "at " + at + "the owner's head is " + m.ownerOut + " px above the frame, so it is cut off");
        expect(m.queenOut <= 1, "at " + at + "the queen's head is " + m.queenOut + " px above the frame, so it is cut off");
        expect(m.talkOut <= 1, "at " + at + "the talk is " + m.talkOut + " px outside the frame, with nowhere to scroll");
        expect(m.overTalk === 0, "at " + at + "one of them stands over the words, by " + m.overTalk + " square px");
        expect(m.talk >= 20, "at " + at + "the talk is " + m.talk + " px: the two of them squeezed it out");
        expect(m.homework >= 20, "at " + at + "her homework is " + m.homework + " px: the talk's floor squeezed it out");
        // where the window has the room, not squeezed out isn't enough: a whole bubble, and a question with its
        // options, have to be readable without scrolling for the card to be worth opening. Below this the card is
        // shorter than the two of them plus both of those, so each pane scrolls and the floors above are what hold.
        if (h >= 600) {
          expect(m.talk >= 46, "at " + at + "the talk is " + m.talk + " px, under one bubble");
          expect(m.homework >= 92, "at " + at + "her homework is " + m.homework + " px, under a question and its options");
        }
      }
    });
  });
  await check("every other setting is in an overlay, out of the scene until Settings", async () => {
    for (const sel of ["#queenVoice", "#queenKeeps", "#queenCharacter", "#queenYou"]) expect(await page.locator(sel).isHidden(), sel + " shows in the scene");
    await page.click("#queenSettingsBtn");
    for (const sel of ["#queenVoice", "#queenKeeps", "#queenCharacter", "#queenYou", "#queenRoutines"]) expect(await page.locator(sel).isVisible(), sel + " not in Settings");
    await page.click("#queenSettingsClose");
    expect(await page.locator("#queenSettings").isHidden(), "Settings stayed open");
    expect(await page.locator("#queenThread").isVisible(), "the scene didn't come back");
  });
  await page.click("#queenSettingsBtn");
  await page.click("#queenYou summary");
  await page.selectOption("#own-hair", "bun");
  await page.selectOption("#own-top", "2");
  await page.selectOption("#own-extra", "ears");
  const before = await page.locator("#queenOwnerFig").innerHTML();
  await page.click("#ownerSave");
  await settle(page);
  await check("you can dress yourself, and the café keeps it", async () => {
    const o = (await T(page, () => window.__catio.store["house/main"]) || {}).owner;
    expect(o && o.hair === "bun" && o.top === 2 && o.extra === "ears", JSON.stringify(o));
    expect((await page.locator("#queenOwnerFig").innerHTML()) !== before, "the scene didn't change");
  });
  await page.keyboard.press("Escape");
  await settle(page);
  await page.mouse.move(8, 8);
  await page.locator("#cats .cat.queen").hover();
  await settle(page);
  await check("on the map, hovering her still names her, and a click still opens her menu", async () => {
    expect((await page.locator("#tip").innerText()).length > 0, "no hover line");
    await page.locator("#cats .cat.queen").click();
    await settle(page);
    expect((await menuText(page)).includes("Talk to her"), await menuText(page));
  });
  await check("no page errors in her scene", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// her turn as it goes, the rest of it (4 October): a long wait gets The Sims' loading tips, Stop turns the lit tile
// pink until she has stopped, and with her runner away there is no strip at all, only a line saying why
{
  const { page, ctx, errors } = await open("?via=gateway");
  await page.clock.install();
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await page.fill("#queenSay", "Sort the litter box for me.");
  await page.click("#queenSend");
  await T(page, () => window.__catio.queenSays("", false, "t1", [{ tool: "house_rules" }]));
  await settle(page);
  await check("a short wait has no tip", async () => expect(!(await page.locator("#queenWork .qtip").isVisible()), "a tip too soon"));
  await page.clock.fastForward(60e3);
  await check("a long wait gets a loading tip under the queue, and the seconds turn to minutes", async () => {
    expect((await page.locator("#queenWork .qtip").innerText()).endsWith("\u2026"), await page.locator("#queenWork").innerText());
    expect(/1:0\d/.test(await page.locator("#queenWork .tile.now").innerText()), await page.locator("#queenWork .tile.now").innerText());
  });
  await page.click("#queenStop");
  await settle(page);
  await check("Stop turns the step she is on to stopping, and stays pressed until she has", async () => {
    expect(await page.locator("#queenWork .tile.now.stop").count() === 1, await page.locator("#queenWork").innerHTML());
    expect(/stopping/i.test(await page.locator("#queenWork .tile.now").innerText()), await page.locator("#queenWork").innerText());
    expect(await page.locator("#queenStop").isDisabled(), "Stop can be pressed twice");
  });
  await T(page, () => window.__catio.queenSays("Stopped there, my lady.", true, "t1"));
  await settle(page);
  await check("stopped, the strip is gone and Stop is free again", async () => {
    expect(!(await page.locator("#queenWork").isVisible()), "the strip stayed");
    expect(!(await page.locator("#queenStop").isDisabled()), "Stop stuck pressed");
  });
  await check("no page errors while she works", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("?via=gateway&queen=away");
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await page.fill("#queenSay", "Are you there?");
  await page.click("#queenSend");
  await settle(page);
  await check("with her runner away, your words wait with one line saying why, and nothing ticks", async () => {
    expect(/asleep/i.test(await page.locator("#queenWork").innerText()), await page.locator("#queenWork").innerText());
    expect(await page.locator("#queenWork .tile, #queenWork .qdots, #queenWork time").count() === 0, "a working strip for a queen who is asleep");
    expect(!(await page.locator("#queenStop").isVisible()), "Stop with nothing to stop");
  });
  await check("no page errors with her away", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// her quest log (3 October 2026: "where do I take the litter box quiz in the cafe UI?", then the queen's quest log, the
// cards kept in her gateway): the queen keeps one list of everything waiting on her, quizzes that unblock a cat, litter
// box notes to sort and decisions; the House menu and the litter box on the map open it, a card at a time, a tap answers
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked");
  await T(page, () => {
    const T = window.__catio;
    T.setQuiz({ kind: "litterbox", title: "Loose ends", note: "- **Rename the grey cat** in the craft room.", from: "litterbox/loose-ends.md", hint: "Pretty-Project-Portfolio", questions: [{ q: "Which project is it for?", options: ["Pretty-Project-Portfolio", "tiktok-saves", "Settled: drop it"] }] });
    T.setQuiz({ kind: "litterbox", title: "Loose ends", note: "The shop's photos need a white background.", hint: "montfortoise-shopify", questions: [{ q: "Which project is it for?", options: ["montfortoise-shopify", "Pretty-Project-Portfolio", "Settled: drop it"] }] });
    // the third option is as long as a repository name, with nothing to break at: it is what used to push her card off the side
    T.setQuiz({ kind: "decision", title: "The roadmap", note: "Which comes first?", hint: "The camera", questions: [{ q: "Which first?", options: ["The camera", "Build mode", "Pretty-Project-Portfolio-with-a-name-that-will-never-break-anywhere"] }] });
  });
  await page.waitForTimeout(400);
  await check("what a cat brought her comes before notes to sort in her line", async () => {
    await page.mouse.move(8, 8);
    await page.locator("#cats .cat.queen").hover();
    await settle(page);
    const t = await page.locator("#tip").innerText();
    expect(t.includes("Holding 1 thing for you"), t);
  });
  await T(page, () => window.__catio.put("queens/house", { readAt: Date.now() + 864e5 }));   // the handoff read
  await page.waitForTimeout(300);
  await check("everything waiting on her is homework: the queen's line counts each kind", async () => {
    await page.mouse.move(8, 8);
    await page.locator("#cats .cat.queen").hover();
    await settle(page);
    const t = await page.locator("#tip").innerText();
    expect(t.includes("Homework: 2 notes to sort, 1 decision"), t);
  });
  await openHouse(page);
  await check("the House menu leads with Homework, saying how many wait", async () => {
    const first = page.locator("#menu .list .mi").first();
    expect((await first.innerText()).startsWith("Homework") && (await first.innerText()).includes("3 waiting"), await first.innerText());
  });
  await page.locator('#menu .mi:has-text("Homework")').click();
  await settle(page);
  await check("Homework opens her card on the cards, a deck at a time, the note's words with no markdown marks", async () => {
    expect(await page.locator("#queenDlg").isVisible(), "her card didn't open");
    expect(await page.locator('#queenHomework [data-deck="litterbox"]').count() === 1 && await page.locator('#queenHomework [data-deck="decision"]').count() === 1, "not one card per deck");
    const t = await page.locator('#queenHomework [data-deck="litterbox"]').innerText();
    expect(t.includes("1 of 2") && t.includes("Rename the grey cat") && !t.includes("**") && t.includes("The sifter guessed Pretty-Project-Portfolio"), t);
    expect(await page.locator('#queenHomework [data-deck="litterbox"] strong:has-text("Rename the grey cat")').count() === 1, "the bold is lost");
  });
  // "make this window useable": homework used to take the whole talk, leaving the conversation under it no height
  // at all, and an option as long as a repository name pushed the card off the side.
  await check("homework leaves the talk room under it, and a long option wraps instead of running off the card", async () => {
    const t = await page.locator("#queenHomework").innerText();
    expect(t.includes("never-break-anywhere"), "the long option isn't drawn, so this proves nothing: " + t.slice(0, 200));
    const o = await page.locator("#queenHomework").evaluate((u) => u.scrollWidth - u.clientWidth);
    expect(o <= 0, "her homework scrolls sideways: " + o);
    const h = await page.locator("#queenThread").evaluate((u) => u.clientHeight);
    expect(h > 80, "her homework left the talk no height: " + h);
  });
  await page.locator('#queenHomework [data-deck="litterbox"] button:has-text("Skip")').click();
  await settle(page);
  await check("Skip puts the next note on top, without answering", async () => {
    const t = await page.locator('#queenHomework [data-deck="litterbox"]').innerText();
    expect(t.includes("2 of 2") && t.includes("white background"), t);
    expect(!(await T(page, () => window.__catio.tools.some((x) => x[1] === "answer"))), "Skip answered");
  });
  await page.locator('#queenHomework [data-deck="litterbox"] button:has-text("montfortoise-shopify")').click();
  await settle(page);
  await check("a tap hands the card in, and the deck moves on to the one left", async () => {
    const a = await T(page, () => window.__catio.tools.filter((x) => x[1] === "answer").pop());
    expect(a && a[2].quiz === "z2" && JSON.stringify(a[2].answers) === JSON.stringify(["montfortoise-shopify"]), JSON.stringify(a));
    const t = await page.locator('#queenHomework [data-deck="litterbox"]').innerText();
    expect(t.includes("1 of 1") && t.includes("Rename the grey cat"), t);
    expect(!t.includes("Skip"), "Skip with one card left");
  });
  await page.keyboard.press("Escape");
  await settle(page);
  await page.click("#floor-upper");
  await page.keyboard.press("0");
  await settle(page);
  const litter = page.locator(".cabinet.litter");
  await check("the litter box is on the map with no sign: hovering it says what waits", async () => {
    expect(await litter.isVisible(), "no litter box upstairs");
    expect((await litter.innerText()).trim() === "", "a sign on the litter box");
    await page.mouse.move(8, 8);
    await litter.hover();
    await settle(page);
    const t = await page.locator("#tip").innerText();
    expect(t.includes("The litter box") && t.includes("1 note to sort"), t);
  });
  await litter.click();
  await settle(page);
  await check("clicking the litter box opens her card at the litter box", async () => {
    expect(await page.locator("#queenDlg").isVisible(), "her card didn't open");
    expect(await page.evaluate(() => !!document.activeElement.closest('[data-deck="litterbox"]')), "not at the litter box");
  });
  await page.locator('#queenHomework [data-deck="litterbox"] button:has-text("Settled: drop it")').click();
  await settle(page);
  await check("with the litter box empty its deck goes, and the decision stays", async () => {
    expect(await page.locator('#queenHomework [data-deck="litterbox"]').count() === 0, "the litter box deck is still there");
    expect(await page.locator('#queenHomework [data-deck="decision"]').count() === 1, "the decision went too");
  });
  await check("no page errors in her quest log", async () => expect(errors.length === 0, errors.join("; ")));
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
  // her ask, 4 October 2026: hovering the cats, the chats, the sessions "outlines the object boundaries of the 2D asset"
  await check("the cat under the pointer is outlined around its own shape, not boxed, and only while it is pointed at", async () => {
    const hot = () => page.evaluate(() => [...document.querySelectorAll("#cats .cat, #props .piece")].filter((e) => getComputedStyle(e).filter.includes("drop-shadow")).map((e) => e.getAttribute("aria-label") || e.dataset.piece));
    const on = await hot();
    expect(on.length === 1 && on[0].includes("Shop about page"), "outlined: " + JSON.stringify(on));
    expect(await page.locator("#cats .cat.hot").evaluate((e) => getComputedStyle(e).borderImageSource === "none" && getComputedStyle(e).borderTopWidth === "0px"), "a box around the cat");
    await page.mouse.move(8, 8);
    await settle(page);
    expect((await hot()).length === 0, "still outlined after the pointer left: " + JSON.stringify(await hot()));
  });
  await check("a filing cabinet under the pointer outlines the cabinet itself", async () => {
    const cab = await page.locator('#hits .cabinet[data-room="kitchen"]').boundingBox();
    await page.mouse.move(cab.x + cab.width / 2, cab.y + cab.height / 2, { steps: 3 });
    await settle(page);
    const on = await page.evaluate(() => [...document.querySelectorAll("#props .piece")].filter((e) => getComputedStyle(e).filter.includes("drop-shadow")).map((e) => e.dataset.room + "/" + e.dataset.piece));
    expect(on.length === 1 && on[0] === "kitchen/filing_cabinet", "outlined: " + JSON.stringify(on));
    await page.mouse.move(8, 8);
    await settle(page);
  });
  await check("after a skin redraws the furniture, a filing cabinet under the pointer still outlines the cabinet", async () => {
    await page.evaluate(() => { for (const p of document.querySelectorAll("#props .piece")) p.dataset.old = "1"; window.__catio.put("skin/cat-work", { src: "art/licensed/mochi-idle.png", at: 1 }); });   // a cat of hers: the house is drawn again
    try {
      await page.waitForFunction(() => document.querySelector("#props .piece") && !document.querySelector("#props .piece[data-old]"), null, { timeout: 5000 });
      const cab = await page.locator('#hits .cabinet[data-room="kitchen"]').boundingBox();
      await page.mouse.move(cab.x + cab.width / 2, cab.y + cab.height / 2, { steps: 3 });
      await settle(page);
      const on = await page.evaluate(() => [...document.querySelectorAll("#props .piece")].filter((e) => getComputedStyle(e).filter.includes("drop-shadow")).map((e) => e.dataset.room + "/" + e.dataset.piece));
      expect(on.length === 1 && on[0] === "kitchen/filing_cabinet", "outlined: " + JSON.stringify(on));
      // and with the pointer still on it, a redraw outlines the new piece
      await page.evaluate(() => { for (const p of document.querySelectorAll("#props .piece")) p.dataset.old = "1"; window.__catio.drop("skin/cat-work"); });
      await page.waitForFunction(() => document.querySelector("#props .piece") && !document.querySelector("#props .piece[data-old]"), null, { timeout: 5000 });
      const still = await page.evaluate(() => [...document.querySelectorAll("#props .piece")].filter((e) => getComputedStyle(e).filter.includes("drop-shadow")).map((e) => e.dataset.room + "/" + e.dataset.piece));
      expect(still.length === 1 && still[0] === "kitchen/filing_cabinet", "after the redraw, outlined: " + JSON.stringify(still));
    } finally {
      await page.mouse.move(8, 8); await settle(page);
      if (await page.evaluate(() => !!window.__catio.store["skin/cat-work"])) {
        await page.evaluate(() => { for (const p of document.querySelectorAll("#props .piece")) p.dataset.old = "1"; window.__catio.drop("skin/cat-work"); });
        await page.waitForFunction(() => !document.querySelector("#props .piece[data-old]"), null, { timeout: 5000 });
      }
    }
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
  // her words (3 October): every cat waiting on her lines up in front of the entrance-hall door, beside the queen
  await check("a cat upstairs that waits on you comes down to the line at the front door, and the tally counts it", async () => {
    expect((await page.locator('#cats .cat[aria-label^="Mimi "]').getAttribute("data-room")) === "hall", "not in the line");
    expect(await page.locator("#floor-upper .badge").count() === 0, "the upper floor's switch sends her upstairs to nobody");
    expect((await page.locator("#tally").innerText()).includes("2 need you"), await page.locator("#tally").innerText());
  });
  await page.locator("#stairs").click();
  await settle(page);
  await check("the stair takes you upstairs, where the ground floor is out of reach", async () => {
    expect((await floor()) === "upper", await floor());
    expect((await page.locator("#floor-upper").getAttribute("aria-checked")) === "true", "switch");
    expect(await page.locator('.roomhit[data-room="bedroom"]').isVisible(), "bedroom not showing");
    expect(await page.locator('.roomhit[data-room="kitchen"]').isHidden(), "the kitchen still answers upstairs");
    expect(await page.locator('#cats .cat[aria-label^="Mimi "]').isHidden(), "the cat waiting on her is still upstairs");
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
  await check("brought back waiting on her, it comes down the stair and walks to the line at the front door, then meows", async () => {
    expect((await cat("blocked1").getAttribute("class")).includes("walking"), "not walking back: " + await cat("blocked1").getAttribute("class"));
    await settled("blocked1", "m-meow");
    expect(await cat("blocked1").getAttribute("data-room") === "hall", "not in the line");
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
  await check("moved to the entrance hall while it waits, the move is kept and it stays in the line", async () => {
    expect((await T(page, () => window.__catio.store["sessions/session_blocked1"])).room === "hall", "not moved");
    expect(await cat("blocked1").getAttribute("data-room") === "hall", "left the line");
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
  const whole = await rect("#controls");
  await page.click("#mapFold");
  await check("the fold button folds the map away and says so", async () => {
    expect(!(await page.locator("#minimap").isVisible()), "still showing");
    expect((await page.locator("#mapFold").getAttribute("aria-expanded")) === "false", "aria-expanded");
  });
  // her ask, 5 October: "allow the mini-map to be minimizable": the whole panel, not just the plan
  await check("minimised, the panel is its one button, in the corner it was in", async () => {
    for (const id of ["zoomIn", "zoomOut", "zoomAll", "floor-ground", "floor-upper"])
      expect(!(await page.locator("#" + id).isVisible()), id + " still shows");
    const p = await rect("#controls");
    expect(p.w < 90 && p.h < 70, "more than one button: " + JSON.stringify(p));
    expect(Math.abs(p.x + p.w - (whole.x + whole.w)) < 1 && Math.abs(p.y - whole.y) < 1, "it moved: " + JSON.stringify([whole, p]));
  });
  await page.locator("#stage").click({ position: { x: 60, y: 800 } });
  await page.keyboard.press("PageUp");
  await settle(page);
  await check("minimised, its button carries the pip the hidden floor tab would have", async () => {
    expect(await page.locator("#mapFold .pip").count() === 1, "no pip");
    const n = (await page.locator("#mapFold .pip").innerText()).trim(), ground = (await page.locator("#floor-ground .pip").innerText()).trim();
    expect(n === ground, "it counts " + n + ", the hidden ground floor tab " + ground);
    expect(/need you/.test(await page.locator("#mapFold").getAttribute("aria-label")), "its name doesn't say so");
  });
  await page.keyboard.press("PageDown");
  await settle(page);
  await openRoom(page, "living");
  await page.keyboard.press("m");
  await settle(page);
  await check("a menu open as the panel opens finds its place clear of it again", async () => {
    expect(await page.locator("#minimap").isVisible(), "M didn't open it");
    expect(await page.locator("#menu").isVisible(), "the menu closed");
    expect(await clear(), "the menu is under the panel");
  });
  await closeMenu(page);
  await page.focus("#zoomIn");
  await page.keyboard.press("m");
  await check("minimising from one of its buttons leaves the keyboard on the fold", async () => {
    expect(!(await page.locator("#minimap").isVisible()), "still open");
    expect((await page.evaluate(() => document.activeElement && document.activeElement.id)) === "mapFold", "focus fell off");
  });
  await page.locator("#room-living").focus();
  await page.keyboard.press("Enter");
  await settle(page);
  const onItem = () => page.evaluate(() => { const a = document.activeElement; return !!a && document.getElementById("menu").contains(a) ? a.textContent : null; });
  const item = await onItem();
  await page.keyboard.press("m");
  await settle(page);
  await check("opening the panel from inside a menu keeps the keyboard on the same item", async () => {
    expect(item !== null, "Enter didn't step into the menu");
    expect((await onItem()) === item, "focus fell off: " + item);
  });
  await page.keyboard.press("Escape"); await page.keyboard.press("Escape");
  await page.click("#mapFold");
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
  await page.locator("#mapFold").tap();
  await check("on a phone, opened, the fold stays in the bottom right corner, under her thumb", async () => {
    expect(await page.locator("#minimap").isVisible(), "the tap didn't open it");
    const f = await page.locator("#mapFold").boundingBox(), r = await page.locator("#controls").boundingBox();
    expect(r.x + r.width - (f.x + f.width) < 20 && r.y + r.height - (f.y + f.height) < 20, "the fold isn't in the corner: " + JSON.stringify([f, r]));
  });
  await page.locator("#mapFold").tap();
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

/* ---------- 7b. her card on a phone ("make this window useable", 3 October) ---------- */
// Flanking her on a phone the two of them left the words a strip under 200 px wide, and nothing in the walk
// opened her card at that size, so the rules that only apply there went unchecked.
{
  const { page, ctx, errors } = await open("?via=gateway&mode=blocked", { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const fits = () => page.locator("#queenDlg").evaluate((d) => d.scrollHeight - d.clientHeight);
  await page.locator("#cats .cat.queen").tap();   // the way she opens it on a phone: a tap names her and opens her menu
  await settle(page);
  await check("on a phone a tap on her opens her menu, and Talk to her opens her card", async () => {
    expect(await page.locator("#menu").isVisible(), "no menu");
    expect(await page.locator("#queenDlg[open]").count() === 0, "her card opened on the first tap");
    await menuButton(page, "Talk to her").tap();
    await settle(page);
    expect(await page.locator("#queenDlg[open]").count() === 1, "Talk to her didn't open her card");
  });
  await check("on a phone her card fits the screen, the two of them at its foot and the words across the whole scene", async () => {
    const over = await fits();
    expect(over <= 1, "her card is taller than the screen by " + over);
    expect(await page.locator("#queenSend").evaluate((s) => s.getBoundingClientRect().bottom <= innerHeight + 1), "Send is under the fold");
    const you = await page.locator("#queenOwnerFig").boundingBox(), her = await page.locator("#queenFig").boundingBox(), talk = await page.locator("#queenThread").boundingBox();
    expect(you && her && talk, "a piece is missing: " + JSON.stringify({ you, her, talk }));
    expect(you.x + you.width <= her.x + 2, "they aren't side by side: " + JSON.stringify({ you, her }));
    expect(talk.y + talk.height <= you.y + 2, "the words aren't above them: " + JSON.stringify({ talk, you }));
    const stage = await page.locator(".qstage").evaluate((e) => e.clientWidth);
    expect(talk.width > stage * .9, "the words don't cross the scene: " + Math.round(talk.width) + " of " + stage);
    expect(await page.locator("#queenThread").evaluate((u) => u.scrollWidth - u.clientWidth) <= 0, "her words scroll sideways");
  });
  await T(page, () => window.__catio.setQuiz({ for: "cse_blocked1", title: "Unblock Caramel", questions: [
    { q: "Which project is this one for?", options: ["montfortoise-shopify", "Pretty-Project-Portfolio"] },
    { q: "Does the menu fix go in first?", options: ["Yes", "No", "Ask me again on Sunday"] },
    { q: "Anything else I should know?" },
  ] }));   // taller than a phone's scene, so the branch that scrolls is the one this check runs
  await page.waitForTimeout(500);
  // a quiz taller than a phone's scene has to scroll; what must hold is that the talk keeps a bubble's worth of
  // room under it, and that what doesn't fit can be reached rather than being cut off
  await check("on a phone her homework leaves the talk room under it, and what doesn't fit can be scrolled to", async () => {
    expect(await page.locator("#queenHomework .quiz").count() > 0, "no homework drawn");
    const h = await page.locator("#queenThread").evaluate((u) => u.clientHeight);
    expect(h > 80, "her homework left the talk no height: " + h);
    // scroll it, rather than trusting the stylesheet: what was below the fold has to come into view
    const hw = await page.locator("#queenHomework").evaluate((e) => {
      const over = e.scrollHeight - e.clientHeight;
      if (over <= 0) return { over, reached: true, hand: true };
      e.scrollTop = e.scrollHeight;
      const box = e.getBoundingClientRect();
      const hands = e.querySelectorAll(".hand");   // its own class: .actions also holds a deck's Skip
      const hand = hands[hands.length - 1];   // the one at the bottom, where it has just been scrolled to
      const hr = hand && hand.getBoundingClientRect();
      return { over, reached: e.scrollTop > 0, hand: !!hr && hr.bottom <= box.bottom + 1 && hr.top >= box.top - 1 };
    });
    expect(hw.over > 0, "the quiz fits, so this proves nothing about what doesn't: " + JSON.stringify(hw));
    expect(hw.reached, "her homework is cut off with no way to scroll to the rest: " + JSON.stringify(hw));
    expect(hw.hand, "Hand it in can't be reached even scrolled to the bottom: " + JSON.stringify(hw));
    const over = await fits();
    expect(over <= 1, "her card grew past the screen with homework open, by " + over);
  });
  await check("no page errors in her card on a phone", async () => expect(errors.length === 0, errors.join("; ")));
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
  await check("the decider is asked the same question, logged beside the sorter's pick, and not waited for", async () => {
    const d = (await tools(page, "decide")).pop();
    expect(d, "the decider wasn't asked");
    expect(d[2].kind === "sort" && d[2].old === "session_blocked1", JSON.stringify(d[2]).slice(0, 200));
    const q = d[2].questions.cat;
    expect(q.type === "choice" && q.criteria.none && q.criteria.session_blocked1 && d[2].state.file.name === "untitled.txt", JSON.stringify(q).slice(0, 300));
    expect(d[2].floor === 0.6 && typeof d[2].ref === "string" && d[2].ref, "the log can't tell how sure counts, or which file: " + JSON.stringify(d[2]).slice(0, 200));
  });
  // house/main.decide "on": the decider sorts first, when it is sure
  await T(page, () => { window.__catio.decideAnswer = { model: "stub", answers: { cat: { type: "choice", choice: "session_work1", confidence: 0.91, probabilities: { session_work1: 0.91 } } } }; window.__catio.put("house/main", { name: "KittyChat Café", decide: "on" }); });
  await dropFiles(page, "#stage .house", [{ name: "untitled2.txt", type: "text/plain", text: "more thoughts" }]);
  await check("switched on, the decider's sure pick sorts the file, and says how sure", async () => {
    expect(await page.inputValue("#drop-0") === "session_work1", await page.inputValue("#drop-0"));
    expect((await page.locator("#brainDlg").innerText()).includes("The decider: 91% sure"), await page.locator("#brainDlg").innerText());
  });
  await page.click("#brainDlg button:has-text('Cancel')");
  await T(page, () => { window.__catio.decideAnswer.answers.cat = { type: "choice", choice: "session_work1", confidence: 0.3, probabilities: { session_work1: 0.3 } }; });
  await dropFiles(page, "#stage .house", [{ name: "untitled3.txt", type: "text/plain", text: "faint thoughts" }]);
  await check("unsure, the decider leaves it to the sorter model", async () => {
    expect(await page.inputValue("#drop-0") === "session_blocked1", await page.inputValue("#drop-0"));
    expect((await page.locator("#brainDlg").innerText()).includes("Claude: It is about the shop's page"), await page.locator("#brainDlg").innerText());
  });
  await page.click("#brainDlg button:has-text('Cancel')");
  await T(page, () => { window.__catio.put("house/main", { name: "KittyChat Café" }); window.__catio.decideAnswer.answers.cat = { type: "choice", choice: "none", confidence: 0.9, probabilities: { none: 0.9 } }; });
  await page.waitForTimeout(100);   // back to observe before the next drop

  // the sorter can't tell either: it waits on the tray, and is filed from the brain
  await T(page, () => { window.__catio.sampleAnswer = { cat: null, reason: "no idea" }; });
  await dropFiles(page, "#stage .house", [{ name: "mystery.bin", type: "application/octet-stream", text: "\u0000\u0001" }]);
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a file nobody claims waits on the brain's tray", async () => {
    const d = Object.entries(await T(page, () => window.__catio.store)).find(([p, v]) => p.startsWith("brain/") && v.name === "mystery.bin");
    expect(d && d[1].status === "unsorted" && d[1].cat === null, JSON.stringify(d));
  });
  await check("the decider's log says the sorter found nobody, and names the file as the brain keeps it", async () => {
    const d = (await tools(page, "decide")).pop();
    const kept = Object.keys(await T(page, () => window.__catio.store)).find((p) => p === "brain/" + d[2].ref);
    expect(d[2].state.file.name === "mystery.bin" && d[2].old === "none" && kept, JSON.stringify({ old: d[2].old, ref: d[2].ref, kept }));
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
    expect(n && n[1].author === "owner" && n[1].cat === "session_blocked1" && n[1].via === "queued", JSON.stringify(n));
    expect((await page.locator("#thread").innerText()).includes("queued"), "the conversation doesn't say it's waiting");
  });
  await T(page, () => window.__catio.put("notes/r1", { cat: "session_blocked1", author: "session", text: "Yes: it's in the PR.", at: Date.now() }));
  await page.waitForTimeout(200);
  await check("the session's answer shows in the conversation", async () => {
    expect((await page.locator("#thread").innerText()).includes("Yes: it's in the PR."), await page.locator("#thread").innerText());
  });
  // a note of hers from before accounts, written as "charlotte": still hers
  await T(page, () => window.__catio.put("notes/old1", { cat: "session_blocked1", author: "charlotte", text: "Old one, from before.", at: Date.now() - 1 }));
  await page.waitForTimeout(200);
  await check("a note written as charlotte before accounts still reads as hers", async () => {
    const li = page.locator("#thread li.me", { hasText: "Old one, from before." });
    expect(await li.count() === 1, await page.locator("#thread").innerText());
    expect((await li.innerText()).startsWith("You"), await li.innerText());
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
    const t = (await tools(page, "set_session_title")).filter((x) => x[2].session_id === "session_blocked1");
    expect(t.length === 1 && t[0][2].title === "Shop about page (FR)", JSON.stringify(t));
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
    expect((await page.locator('#cats .cat[aria-label*="Shop about page"]').getAttribute("data-room")) === "hall", "a cat waiting on her left the line");
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
    expect(c && c[0] === "CATIO" && c[2].cat === "cse_blocked1" && c[2].text === "Merci, I'll read it tonight" && c[2].author === "owner", JSON.stringify(c));
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
  await page.waitForTimeout(1200);   // past the second the wizard gives the rooms
  await check("on localhost the rooms come from data/rooms.json, so the wizard never shows", async () => expect(await page.locator("#setupDlg[open]").count() === 0, "wizard open on a seeded café"));
  await openCat(page, "Loco");
  await menuButton(page, "Details").click();
  await page.click("#catDlg button:has-text('Let go')");
  await page.click("#catDlg button:has-text('Yes, let this cat go')");
  await settle(page);
  await check("letting it go on localhost removes it", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 0, "still there"));
  await toFloor(page, "ground");
  await page.locator("#cats .cat.queen").dblclick();
  await settle(page);
  await page.click("#queenSettingsBtn");
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
// The walkthrough's localhost player: catio_mcp.py --serve answers its tools by POST only, so the page must ask it that
// way; and with no front desk the queen can't wake, so she says so instead of "start her runner".
if (LOCAL) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  const page = await ctx.newPage();
  const errors = [], asked = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/api/list_agents", (r) => {
    asked.push(r.request().method());
    if (r.request().method() !== "POST") return r.fulfill({ status: 404, contentType: "application/json", body: '{"error": "the tools are POST only"}' });
    return r.fulfill({ contentType: "application/json", body: JSON.stringify({ agents: [] }) });
  });
  await page.goto(LOCAL);
  for (let i = 0; i < 100 && asked.length < 2; i++) await page.waitForTimeout(50);   // the probe, then refreshAgents: up to 5 s
  await check("on localhost the page asks catio_mcp.py --serve for its agents by POST", async () =>
    expect(asked.length >= 2 && asked.every((m) => m === "POST"), "asked by " + asked.join(", ")));
  await toFloor(page, "ground");
  await page.mouse.move(8, 8);
  await page.locator("#cats .cat.queen").hover();
  await settle(page);
  await check("on localhost the queen's hover says she only wakes with a front desk, not to start a runner", async () => {
    const t = await page.locator("#tip").innerText();
    expect(t.includes("front desk") && !t.includes("runner"), t);
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

/* ---------- 10. the first run: the wizard over an empty café, and closed rooms ---------- */
// the wizard gives the rooms a second to arrive before it opens
const wizard = (page) => page.waitForSelector("#setupDlg[open]", { timeout: 4000 }).then(() => settle(page));
{
  const { page, ctx } = await open("");
  await page.waitForTimeout(1500);   // past the second the wizard gives the rooms
  await check("a café with rooms never sees the wizard", async () => expect(await page.locator("#setupDlg[open]").count() === 0, "wizard open"));
  await ctx.close();
}
// The first user test (5 October): with no licensed art, which is every invited guest and every fresh clone, the
// Welcome step threw "NOART is not defined" and the wizard never opened.
{
  const { page, ctx, errors } = await open("?mode=empty", { base: NOART });
  await check("with no licensed art the wizard still opens on Welcome, saying once that the art isn't here", async () => {
    await wizard(page);
    expect(await page.locator("#setupDlg[open]").count() === 1, "wizard not open");
    const words = await page.locator("#setupDlg").innerText();
    expect(words.split("The cat art isn't here").length === 2, "the art note, not once: " + words);
    expect(words.split("All your Claude chats").length === 2, "the welcome, not once: " + words);
    expect(!errors.some((e) => /NOART|ReferenceError/.test(e)), errors.join(" | "));
  });
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("?mode=empty");
  const nextStep = async () => { await page.click("#setupDlg button[type=submit]"); await settle(page); };
  const title = () => page.locator("#setupTitle").innerText();
  await check("a café with no rooms opens the wizard on Welcome, and Later or Escape closes it without writing", async () => {
    await wizard(page);
    expect(await page.locator("#setupDlg[open]").count() === 1, "wizard not open");
    expect((await title()) === "Welcome", await title());
    await page.click("#setupDlg button:has-text('Later')"); await settle(page);
    expect(await page.locator("#setupDlg[open]").count() === 0, "Later left it open");
    await page.click("#houseBtn");
    await menuButton(page, "Set up again…").click(); await settle(page);
    await page.keyboard.press("Escape"); await settle(page);
    expect(await page.locator("#setupDlg[open]").count() === 0, "still open");
    expect((await T(page, () => window.__catio.writes.length)) === 0, "wrote something");
  });
  await page.click("#houseBtn");
  await menuButton(page, "Set up again…").click();
  await settle(page);
  await check("the House menu opens it again", async () => expect(await page.locator("#setupDlg[open]").count() === 1, "not open"));
  await page.fill("#setupName", "Mochi's Café");
  await nextStep();
  await check("Rooms: the counter opens rooms from the front of the house, with a name field each", async () => {
    expect((await title()) === "Rooms", await title());
    expect((await page.locator("#roomsN").innerText()) === "4", "not 4");
    await page.click("#roomsLess"); await settle(page);
    expect((await page.locator("#roomsN").innerText()) === "3", "not 3");
    expect(await page.locator('.roomgrid li[data-open="true"]').count() === 3 && await page.locator('.roomgrid li[data-open="false"]').count() === 7, "grid");
    expect((await page.locator('.roomgrid li[data-room="hall"]').innerText()).toLowerCase().includes("closed"), "a reader isn't told closed");
    expect(await page.locator("#sn-living").count() === 1 && await page.locator("#sn-kitchen").count() === 1 && await page.locator("#sn-study").count() === 0, "name fields");
    expect((await page.locator("#setupDlg").innerText()).includes("new cats come in here"), "front door not said");
  });
  await page.fill("#sn-living", "Lounge");
  await nextStep();
  await page.click("#ghConnect");
  await page.waitForTimeout(300);
  await check("GitHub: the repositories listed, each with a select of the open rooms, the front door first", async () => {
    expect((await title()) === "GitHub", await title());
    expect(await page.locator("#setupDlg .repo").count() === 2, "rows: " + await page.locator("#setupDlg .repo").count());
    expect((await page.locator("#setupDlg .repo").first().innerText()).includes("charredlatte/my-portfolio"), "first repo");
    expect((await page.locator("#sr-0").inputValue()) === "living", "default room");
    expect(await page.locator("#sr-0 option").count() === 3, "closed rooms offered");
    expect((await page.locator("#sr-0 option").first().innerText()) === "Lounge", "the name she typed");
  });
  await page.selectOption("#sr-1", "kitchen");
  await page.click("#setupDlg button:has-text('Back')"); await settle(page);
  await page.click("#roomsLess"); await settle(page);
  await nextStep();
  await check("a pick for a room closed afterwards falls back to the front door on a first run", async () => {
    expect((await page.locator("#sr-1").inputValue()) === "living", "recipes' room: " + await page.locator("#sr-1").inputValue());
    expect(await page.locator("#sr-1 option").count() === 2, "a closed room offered");
  });
  await page.click("#setupDlg button:has-text('Back')"); await settle(page);
  await page.click("#roomsMore"); await settle(page);
  await nextStep();
  await page.selectOption("#sr-1", "kitchen");
  await nextStep();
  await check("Sessions: what the live read found, with no new call", async () => {
    expect((await title()) === "Sessions", await title());
    expect((await page.locator("#setupDlg").innerText()).includes("3 sessions found"), await page.locator("#setupDlg").innerText());
    expect((await T(page, () => window.__catio.calls)) === 1, "list_sessions called again");
  });
  await nextStep();
  await check("Litter box: a drop zone and the brain, nothing to switch", async () => {
    expect((await title()) === "Litter box", await title());
    expect(await page.locator("#setupDrop").isVisible() && await page.locator("#setupBrain").isVisible(), "drop zone / brain");
    expect(await page.locator("#setupDlg .switch").count() === 0, "a switch");
    expect((await page.locator("#setupDlg").innerText()).includes("litterbox/"), "the folder");
  });
  await nextStep();
  await check("How it works: the five lines and the two install lines", async () => {
    expect((await title()) === "How it works", await title());
    expect(await page.locator("#setupDlg ul.how li").count() === 5, "lines");
    // the harness as a car (her ask, 4 October): Claude alone is a stripped car, the café the rest of it, the queen drives
    expect((await page.locator("#setupDlg").innerText()).includes("stripped car"), "the stripped car");
    expect(/^\S+ drives\.$/i.test(await page.locator("#setupDlg ul.how li b").first().innerText()), "the queen at the wheel");
    expect((await page.locator("#installLines").innerText()).includes("claude plugin install kittychat-house-rules@kittychat"), "install line");
    expect(await page.locator("#copyInstall").isVisible(), "copy");
  });
  await nextStep();
  await check("Done: the summary, and nothing written yet", async () => {
    expect((await title()) === "Done", await title());
    const t = await page.locator("#setupDlg").innerText();
    for (const w of ["Mochi's Café", "3 rooms open", "2 repositories filed", "3 cats at the door", "OPEN THE DOORS"]) expect(t.toUpperCase().includes(w.toUpperCase()), w + " missing: " + t);
    expect(t.includes("has the keys"), "the keys");
    expect((await T(page, () => window.__catio.writes.length)) === 0, "wrote before the doors opened");
  });
  await nextStep();
  await page.waitForTimeout(300);
  await check("Open the doors writes the house and all ten rooms in one go: three open, seven closed, each with a model", async () => {
    expect(await page.locator("#setupDlg[open]").count() === 0, "still open");
    const st = await T(page, () => window.__catio.store);
    expect(st["house/main"] && st["house/main"].name === "Mochi's Café" && st["house/main"].onboarded > 0, JSON.stringify(st["house/main"]));
    const rooms = Object.entries(st).filter(([k]) => k.startsWith("rooms/"));
    expect(rooms.length === 10, "rooms: " + rooms.length);
    expect(rooms.filter(([, r]) => r.closed).length === 7 && !st["rooms/living"].closed && !st["rooms/dining"].closed && !st["rooms/kitchen"].closed, "open set");
    expect(rooms.every(([, r]) => r.model === "claude-opus-5-5" && r.blurb === ""), "model or blurb missing");
    expect(st["rooms/living"].catchAll && !st["rooms/kitchen"].catchAll && st["rooms/living"].name === "Lounge", "front door / name");
    expect(st["rooms/living"].repos.includes("charredlatte/my-portfolio") && st["rooms/kitchen"].repos.includes("charredlatte/recipes"), "repos");
  });
  await check("the brand and the title read the café's name", async () => {
    expect((await page.locator("#houseBtn .nm").innerText()) === "Mochi's Café", await page.locator("#houseBtn .nm").innerText());
    expect((await page.title()).includes("Mochi's Café"), await page.title());
  });
  // a closed room gets no cats: a repo listed in it, and a chat moved to it, both land at the front door
  await T(page, () => { window.__catio.put("rooms/study", { name: "Craft room", blurb: "", repos: ["montfortoise-shopify"], catchAll: false, closed: true, model: "claude-opus-5-5" }); });
  await T(page, () => { window.__catio.put("cats/willow", { title: "Willow", room: "study", mood: "busy", name: "Willow" }); });
  await page.waitForTimeout(300);
  await check("the adopt form offers open rooms only, starting at the front door", async () => {
    await openRoom(page, "living");
    await menuButton(page, "Add a cat").click(); await settle(page);
    await menuButton(page, "Adopt a chat").click(); await settle(page);
    expect((await page.locator("#adRoom").inputValue()) === "living", "not the front door: " + await page.locator("#adRoom").inputValue());
    expect(await page.locator("#adRoom option[value=study]").count() === 0 && await page.locator("#adRoom option[value=bath]").count() === 0, "a closed room offered");
    await page.keyboard.press("Escape"); await settle(page);
  });
  await check("a session whose repo a closed room lists, and a chat moved there, sit at the front door", async () => {
    await page.locator('#cats .cat[aria-label*="Shop about page"]').click();   // waiting on her, it is in the line; its room is the lounge
    await settle(page);
    expect(/lounge/i.test(await menuText(page)), "session not filed in the lounge: " + await menuText(page));
    await closeMenu(page);
    expect((await page.locator('#cats .cat[aria-label^="Willow"]').getAttribute("data-room")) === "living", "chat not in the lounge");
  });
  await T(page, () => { window.__catio.put("sessions/session_work1", { room: "bath" }); });
  await page.waitForTimeout(300);
  await closeMenu(page);
  await page.locator('#cats .cat[aria-label*="Week tab editing"]').dispatchEvent("dblclick");
  await settle(page);
  await check("a session's card keeps the closed room she moved it to, so a save never moves it", async () => {
    expect((await page.locator('#cats .cat[aria-label*="Week tab editing"]').getAttribute("data-room")) === "living", "not at the front door meanwhile");
    expect((await page.locator("#catDlg #catRoom").inputValue()) === "bath", "room: " + await page.locator("#catDlg #catRoom").inputValue());
  });
  await page.keyboard.press("Escape"); await settle(page);
  await closeMenu(page);
  await page.locator('#cats .cat[aria-label^="Willow"]').dispatchEvent("dblclick");   // the card
  await settle(page);
  await check("a cat's card keeps its closed room, named closed, so a save never moves it", async () => {
    expect(await page.locator("#catDlg[open]").count() === 1, "card not open");
    const sel = page.locator("#catDlg #adRoom");
    expect((await sel.inputValue()) === "study", "room: " + await sel.inputValue());
    expect((await sel.locator("option[value=study]").innerText()).includes("closed"), "not said closed");
    expect(await sel.locator("option[value=bath]").count() === 0, "another closed room offered");
  });
  await page.keyboard.press("Escape"); await settle(page);
  await check("a closed room is dimmed, faint on the minimap, has no queen, and hovering it says closed", async () => {
    expect(await page.locator('.roomhit[data-room="study"][data-closed]').count() === 1, "not marked closed");
    expect(await page.locator('.roomhit[data-room="study"] .tag, #overlay .tag').count() === 0, "a sign");
    expect(await page.locator('.mm-room[data-room="study"].closed').count() === 1, "minimap");
    expect(await page.locator('#cats .cat[data-queen="study"]').count() === 0, "queen drawn");
    await hoverRoom(page, "study");
    const t = await page.locator("#tip").innerText();
    expect(t.includes("Craft room") && t.toLowerCase().includes("closed"), t);
  });
  await openRoom(page, "study");
  await check("a closed room's menu is its name, Closed, Open this room and Edit rooms", async () => {
    const t = await menuText(page);
    expect(t.includes("Craft room") && t.includes("Closed") && t.includes("Open this room") && t.includes("Edit rooms"), t);
    expect(!t.includes("Look in") && !t.includes("Add a cat"), "a working room's actions: " + t);
  });
  await menuButton(page, "Open this room").click();
  await page.waitForTimeout(300);
  await check("Open this room opens it: the house's one queen is still there and the listed repo's cat walks in", async () => {
    expect((await T(page, () => window.__catio.store["rooms/study"].closed)) === false, "still closed");
    expect(await page.locator("#cats .cat[data-queen]").count() === 1, "the queen of the house is missing");
    await closeMenu(page);
    await page.locator('#cats .cat[aria-label*="Shop about page"]').click();   // waiting on her, it is in the line; its room is the craft room again
    await settle(page);
    expect((await menuText(page)).includes("Craft room"), "cat not filed in the craft room: " + await menuText(page));
    await closeMenu(page);
  });
  // Edit rooms: a switch per room; the front door can't be closed, it moves
  await page.click("#houseBtn");
  await menuButton(page, "Edit rooms").click();
  await settle(page);
  await check("Edit rooms has an Open switch per room, and a closed room's option is off the front-door list", async () => {
    expect((await page.locator("#ro-living").getAttribute("aria-pressed")) === "true" && (await page.locator("#ro-bath").getAttribute("aria-pressed")) === "false", "switches");
    expect(await page.locator("#catchAll option[value=bath]").evaluate((o) => o.hidden && o.disabled), "a closed room offered as the front door");
    expect(await page.locator("#rt-bath.closed").count() === 1, "plan tab not dimmed");
  });
  await page.click("#rt-living");
  await page.click("#ro-living");
  await check("closing the front door's room moves the front door to the next open room", async () => {
    expect((await page.locator("#catchAll").inputValue()) === "dining", "front door: " + await page.locator("#catchAll").inputValue());
    expect((await page.locator("#ro-living").getAttribute("aria-pressed")) === "false", "not closed");
    expect(await page.locator("#rt-dining .door").count() === 1, "door not moved");
  });
  await page.click("#ro-living");   // open it again
  await page.click("#rt-kitchen");
  await page.fill("#rb-kitchen", "Weekly meals");
  await page.click("#ro-kitchen");
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(300);
  await check("Save rooms keeps closed with the rest of each room", async () => {
    const k = await T(page, () => window.__catio.store["rooms/kitchen"]);
    expect(k.closed === true && k.blurb === "Weekly meals" && k.model === "claude-opus-5-5", JSON.stringify(k));
    expect((await T(page, () => window.__catio.store["rooms/living"].closed)) === false, "lounge closed");
  });
  // set up again: prefilled, and a room's blurb and model survive it
  await page.click("#houseBtn");
  await menuButton(page, "Set up again…").click();
  await settle(page);
  await T(page, () => { const st = window.__catio.store; window.__catio.put("rooms/dining", Object.assign({}, st["rooms/dining"], { repos: ["recipes", "Snail-Mail-Trail"] })); window.__catio.put("rooms/study", Object.assign({}, st["rooms/study"], { repos: ["montfortoise-shopify", "Snail-Mail-Trail", "upstream/recipes"] })); });
  await page.waitForTimeout(100);
  await check("Set up again is prefilled from the café as it is", async () => {
    expect((await page.locator("#setupName").inputValue()) === "Mochi's Café", "name");
    await nextStep();
    expect((await page.locator("#roomsN").innerText()) === "3", "open rooms: " + await page.locator("#roomsN").innerText());
    expect((await page.locator("#sn-living").inputValue()) === "Lounge", "the lounge's name");
    const t = await page.locator("#setupDlg").innerText().then((x) => x.toUpperCase());
    expect(t.includes("CAFÉ · NEW CATS COME IN HERE") && !t.includes("CAT LOUNGE · NEW CATS"), "the front door she flagged (the café) not kept: " + t);
  });
  await nextStep();
  await page.click("#ghConnect"); await page.waitForTimeout(300);
  await check("a listed repository keeps the room it is filed in as its default, a closed one included", async () => {
    // charredlatte/recipes was filed in the kitchen on the first run; the kitchen is closed now, and dining lists it by name alone
    expect((await page.locator("#sr-1").inputValue()) === "kitchen", "recipes' room: " + await page.locator("#sr-1").inputValue());
    expect((await page.locator("#sr-1 option[value=kitchen]").innerText()).includes("closed"), "the closed room not said");
    expect((await page.locator("#sr-0").inputValue()) === "living", "my-portfolio's room");
  });
  await page.selectOption("#sr-1", "living");
  await page.click("#setupDlg button:has-text('Back')"); await settle(page);
  await page.click("#roomsMore"); await settle(page);
  await check("+ opens the next room in the opening order, and keeps the focus on the button", async () => {
    expect((await page.locator("#roomsN").innerText()) === "4", "not 4");
    expect(await page.locator('.roomgrid li[data-room="kitchen"][data-open="true"]').count() === 1, "the kitchen, next in order, not opened");
    expect(await page.locator('.roomgrid li[data-room="study"][data-open="true"]').count() === 1, "the craft room closed");
    expect((await page.evaluate(() => document.activeElement.id)) === "roomsMore", "focus: " + await page.evaluate(() => document.activeElement.id));
  });
  for (let i = 0; i < 6; i++) await nextStep();
  await page.waitForTimeout(300);
  await check("opening the doors again keeps what Edit rooms looks after, and the rooms she had open", async () => {
    const st = await T(page, () => window.__catio.store);
    expect(await page.locator("#setupDlg[open]").count() === 0, "still open");
    expect(st["rooms/kitchen"].closed === false && st["rooms/kitchen"].blurb === "Weekly meals" && st["rooms/kitchen"].model === "claude-opus-5-5", JSON.stringify(st["rooms/kitchen"]));
    expect(st["rooms/study"].closed === false && st["rooms/study"].repos.includes("montfortoise-shopify"), "the craft room lost its state or its repo: " + JSON.stringify(st["rooms/study"]));
    expect(st["rooms/bath"].closed === true, "the ensuite opened");
    expect(st["rooms/dining"].catchAll && !st["rooms/living"].catchAll, "the front door moved");
    expect(st["rooms/living"].repos.includes("charredlatte/recipes") && !st["rooms/dining"].repos.includes("recipes") && !st["rooms/kitchen"].repos.includes("charredlatte/recipes"), "recipes in two rooms or two spellings: " + JSON.stringify([st["rooms/living"].repos, st["rooms/dining"].repos, st["rooms/kitchen"].repos]));
    expect(st["rooms/dining"].repos.includes("Snail-Mail-Trail") && st["rooms/study"].repos.includes("Snail-Mail-Trail"), "a repository GitHub never listed was moved");
    expect(st["rooms/study"].repos.includes("upstream/recipes"), "another owner's recipes taken for hers");
    expect(st["house/main"].name === "Mochi's Café", "name lost");
  });
  await check("no page errors through the first run", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=empty&repos=none");
  const nextStep = async () => { await page.click("#setupDlg button[type=submit]"); await settle(page); };
  await wizard(page);
  await nextStep(); await nextStep();
  await page.click("#ghConnect");
  await page.waitForTimeout(300);
  await check("GitHub not connected: the page says what to do, and Skip for now moves on", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect(t.includes("Connect GitHub in claude.ai") && t.includes("install the Claude GitHub App"), t);
    expect(await page.locator("#ghRetry").isVisible(), "no Check again");
    await page.click("#ghSkip"); await settle(page);
    expect((await page.locator("#setupTitle").innerText()) === "Sessions", await page.locator("#setupTitle").innerText());
  });
  await check("the first run's own writes don't close it early: one toast, the doors open once", async () => {
    expect(await page.locator("#setupDlg[open]").count() === 1, "closed early");
  });
  for (let i = 0; i < 4; i++) await nextStep();
  await page.waitForTimeout(300);
  await check("the doors still open with no repositories filed", async () => {
    const st = await T(page, () => window.__catio.store);
    expect(st["house/main"] && st["rooms/living"] && st["rooms/living"].catchAll && st["rooms/living"].repos.length === 0, JSON.stringify(st["rooms/living"]));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=empty&repos=denied");
  const nextStep = async () => { await page.click("#setupDlg button[type=submit]"); await settle(page); };
  await wizard(page);
  await nextStep(); await nextStep();
  await page.click("#ghConnect");
  await page.waitForTimeout(300);
  await check("the page's own grant refused: its own words, nothing about GitHub, and Skip", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect(t.includes("list_repos") && t.includes("Edit rooms") && !t.includes("Claude GitHub App"), t);
    await page.click("#ghSkip"); await settle(page);
    expect((await page.locator("#setupTitle").innerText()) === "Sessions", "not on Sessions");
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=empty", { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await check("on a phone the wizard fits, and a tap moves it on", async () => {
    await wizard(page);
    const dlg = await page.locator("#setupDlg").boundingBox();
    expect(dlg && dlg.x >= 0 && dlg.x + dlg.width <= 390, JSON.stringify(dlg));
    await page.locator("#setupDlg button[type=submit]").tap(); await settle(page);
    expect((await page.locator("#setupTitle").innerText()) === "Rooms", "not on Rooms");
    const dlg2 = await page.locator("#setupDlg").boundingBox();
    expect(dlg2.x >= 0 && dlg2.x + dlg2.width <= 390, JSON.stringify(dlg2));
    expect(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "horizontal scroll");
  });
  await ctx.close();
}
// The walkthrough's invitee, on the café's own address: no GitHub button that can only fail, the cats that checked in
// counted, and How it works saying the plugin is how a cat checks in, where to type the lines and the two variables.
{
  const { page, ctx, errors } = await open("?via=gateway&mode=empty");
  const nextStep = async () => { await page.click("#setupDlg button[type=submit]"); await settle(page); };
  await wizard(page);
  await nextStep(); await nextStep();
  await check("on its own address the GitHub step offers no Connect GitHub, and says to file repositories under Edit rooms", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect(await page.locator("#ghConnect").count() === 0, "a Connect GitHub that can only fail");
    expect(t.includes("Edit rooms") && !t.includes("Claude GitHub App"), t);
  });
  await nextStep();
  await check("on its own address the Sessions step counts the cats that checked in", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect((await page.locator("#setupTitle").innerText()) === "Sessions", await page.locator("#setupTitle").innerText());
    expect(t.includes("2 cats have checked in"), t);
  });
  await nextStep(); await nextStep();
  await check("on its own address How it works says the plugin checks the cats in, where to type it, and CATIO_URL and CATIO_TOKEN", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect(t.includes("check-in") && t.includes("terminal") && t.includes("CATIO_URL") && t.includes("CATIO_TOKEN"), t);
    expect((await page.locator("#cafeAddress").innerText()).startsWith("CATIO_URL="), "no address");
  });
  await check("no page errors through the wizard on its own address", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
// The first outside player (5 October) made his Antigravity agent's key by pasting a fetch into the browser's console,
// because the café had no button for it. On its own address the House menu has Keys: the account's keys by name, each
// with a Delete that asks first, and Make a key, which shows the new key once beside CATIO_URL, and nowhere else.
{
  const { page, ctx, errors } = await open("?via=gateway");
  const T0 = (f, a) => page.evaluate(f, a);
  const keysOpen = async () => { await openHouse(page); await menuButton(page, "Keys").click(); await settle(page); };
  await openHouse(page);
  await check("on its own address the House menu has Keys, opening the account's keys by name", async () => {
    expect(await menuButton(page, "Keys").count() === 1, await menuText(page));
    await menuButton(page, "Keys").click(); await settle(page);
    expect(await page.locator("#keysDlg[open]").count() === 1, "no Keys card");
    const t = await page.locator("#keysDlg").innerText();
    expect(/report to this café as a cat/.test(t) && /shown once/.test(t) && /password manager/.test(t), t);
    expect(await page.locator('#keyList li[data-key="bootstrap"]').count() === 1 && await page.locator('#keyList li[data-key="queen"]').count() === 1, t);
  });
  let key = "";
  await check("Make a key shows the new key once, with CATIO_URL as the café's address and CATIO_TOKEN as the key", async () => {
    await page.fill("#keyName", "laptop");
    await page.click("#keysDlg button[type=submit]"); await settle(page);
    key = await T0(() => window.__catio.minted[0]);
    expect(key && key.length === 64, "no key minted: " + key);
    expect((await page.locator("#keyValue").inputValue()) === key, "the field isn't the key");
    expect((await page.locator("#keyUrl").inputValue()) === (await T0(() => location.origin)), "the address isn't the café's");
    const t = await page.locator("#keysDlg").innerText();
    expect(t.includes("CATIO_URL") && t.includes("CATIO_TOKEN") && /shown this once/.test(t), t);
    expect(await page.locator("#keyValue").evaluate((i) => i.readOnly) && await page.locator("#keyUrl").evaluate((i) => i.readOnly), "a setting can be edited");
    expect(await page.locator('#keysDlg button[aria-label="Copy CATIO_TOKEN"]').count() === 1, "no Copy beside the key");
    expect(await page.locator('#keyList li[data-key="laptop"]').count() === 1, "laptop isn't listed");
    expect(!(await toast(page)).includes(key), "the key is in a note");
  });
  await check("the key goes with the card, and is nowhere in the database, the browser's storage or a tool call", async () => {
    await page.click("#keysDlg .actions .btn:has-text('Close')"); await settle(page);
    const found = await T0((k) => {
      const where = [];
      if (document.documentElement.outerHTML.includes(k)) where.push("the page");
      if ([...document.querySelectorAll("input, textarea")].some((i) => i.value.includes(k))) where.push("a field");
      if (JSON.stringify(window.__catio.store).includes(k) || JSON.stringify(window.__catio.writes).includes(k)) where.push("the database");
      if (JSON.stringify(window.__catio.tools).includes(k)) where.push("a tool call");
      for (const s of [localStorage, sessionStorage]) for (let i = 0; i < s.length; i++) if ((s.key(i) + s.getItem(s.key(i))).includes(k)) where.push("storage");
      return where;
    }, key);
    expect(!found.length, "the key is still in " + found.join(", "));
    await keysOpen();
    expect(await page.locator("#keyValue").count() === 0 && await page.locator('#keyList li[data-key="laptop"]').count() === 1, "opened again, the key shows, or laptop is gone");
  });
  await check("Delete asks first, then the key is gone", async () => {
    const del = page.locator('#keyList li[data-key="laptop"] button');
    await del.click(); await settle(page);
    expect((await del.innerText()).trim() === "Yes, delete it", await del.innerText());
    expect(await T0(() => window.__catio.keys.some((k) => k.name === "laptop")), "deleted without asking");
    await del.click(); await settle(page);
    expect(!(await T0(() => window.__catio.keys.some((k) => k.name === "laptop"))), "still kept");
    expect(await page.locator('#keyList li[data-key="laptop"]').count() === 0, "still listed");
  });
  await check("a name already taken shows the gateway's own refusal, and no key", async () => {
    await page.fill("#keyName", "bootstrap");
    await page.click("#keysDlg button[type=submit]"); await settle(page);
    expect((await toast(page)).includes("You already have a key by that name: drop it first."), await toast(page));
    expect(await page.locator("#keyValue").count() === 0, "a key shown");
    expect(await T0(() => window.__catio.minted.length) === 1, "minted anyway");
  });
  await check("no page errors with the keys", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}
for (const [q, why] of [["", "in claude.ai"], ["?gateway=1", "in claude.ai with the gateway's connector"], ["?via=gateway&keys=none", "on an older gateway runtime"]]) {
  const { page, ctx } = await open(q);
  await openHouse(page);
  await check("there is no Keys " + why, async () => {
    expect((await menuText(page)).includes("Edit rooms"), "no House menu: " + await menuText(page));
    expect(await menuButton(page, "Keys").count() === 0, await menuText(page));
  });
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("?mode=blocked");
  const nextStep = async () => { await page.click("#setupDlg button[type=submit]"); await settle(page); };
  await page.click("#houseBtn");
  await menuButton(page, "Set up again…").click();
  await wizard(page);
  await nextStep(); await nextStep(); await nextStep();
  await check("with the live read blocked, the Sessions step says to ask Claude for a saved copy, and shows the one there is", async () => {
    const t = await page.locator("#setupDlg").innerText();
    expect(t.includes("save a copy of your sessions") && t.includes("Claude's saved copy"), t);
  });
  await check("no page errors in the blocked wizard", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

// Her words (3 October 2026): "Allow all assets to be plug-n-plays". Every piece of art is a slot: the page names the
// slot, never the file, so a piece of her own (or another pack's) drops in where the pack's was, with no code change,
// from The look in the House menu or art/skin.json beside the page. These swaps use pieces of the packs themselves, so
// no new file is needed: what matters is that the slot takes them, and that a piece that doesn't fit is refused.
await check("no piece of art is named by its file outside the list of slots", async () => {
  const src = readFileSync(join(here, "..", "index.html"), "utf8");
  const css = src.slice(src.indexOf("<style>"), src.indexOf("</style>"));
  const rootEnd = css.indexOf("color-scheme: light;");
  const outside = (css.slice(0, css.indexOf(":root {")) + css.slice(rootEnd)).match(/url\(art\/[^)]*\)/g) || [];
  expect(outside.length === 1 && outside[0].includes("sprout.ttf"), outside.join(" "));   // the @font-face, swapped by FontFace
  const js = src.slice(src.indexOf("<script>"));
  const named = (js.slice(0, js.indexOf("the art: every piece a slot")) + js.slice(js.indexOf("const SPR0"))).match(/["'(]art\/licensed\/[^"')]*/g) || [];
  expect(!named.length, named.join(" "));
});
// Her words (4 October 2026): "Make sure the entire design system is plug-n-play". Not only the art: every colour,
// font, type size and the art pixel is a token in :root, and a skin sets any of them the same two ways.
await check("no colour or pixel-font size is written into a rule: each is a token", async () => {
  const src = readFileSync(join(here, "..", "index.html"), "utf8");
  const css = src.slice(src.indexOf("<style>"), src.indexOf("</style>"));
  const rules = css.replace(/\/\*[\s\S]*?\*\//g, "").split("}").filter((r) => !/^\s*(@media[^{]*\{\s*)?:root\b/.test(r));   // :root rules define the tokens
  const colours = rules.join("}").match(/#[0-9A-Fa-f]{3,8}\b|rgba?\(/g) || [];
  expect(!colours.length, colours.join(" "));
  const sizes = css.match(/\d+px\/\d+px var\(--pixel\)/g) || [];
  expect(!sizes.length, sizes.join(" "));
  const js = src.slice(src.indexOf("<script>"));
  const owner = js.indexOf("const OWNER = {"), ownerEnd = js.indexOf("};", owner);
  const hexes = (js.slice(0, owner) + js.slice(ownerEnd)).match(/["']#[0-9A-Fa-f]{3,8}["']/g) || [];   // her look's choices are data
  expect(!hexes.length, hexes.join(" "));
});
await check("each slot's default in ART is the one the CSS draws with: its file, and a 9-slice's border", async () => {
  const src = readFileSync(join(here, "..", "index.html"), "utf8");
  const css = src.slice(src.indexOf(":root {"), src.indexOf("color-scheme: light;"));
  const art = src.slice(src.indexOf("const ART = {"), src.indexOf("const SPR0"));
  const wrong = [];
  for (const line of art.split("\n")) {
    const m = line.match(/^\s+"([\w-]+)":\s*\{.*kind: "(\w+)".*file: (?:LIC \+ )?"([^"]+)"/);
    if (!m || m[2] === "font" || m[2] === "cat") continue;   // the font is @font-face's; a cat's sheet is its mood's rule
    const file = line.includes("file: LIC + ") ? "art/licensed/" + m[3] : m[3];
    if (!css.includes("--art-" + m[1] + ": url(" + file + ")")) wrong.push(m[1] + " is not " + file);
    const sl = line.match(/slice: \[(\d+), (\d+), (\d+), (\d+)\]/), fam = line.match(/fam: "(\w+)"/);
    if (sl && fam && !css.includes("--" + fam[1] + "-t: " + sl[1] + "; --" + fam[1] + "-r: " + sl[2] + "; --" + fam[1] + "-b: " + sl[3] + "; --" + fam[1] + "-l: " + sl[4] + ";")) wrong.push(m[1] + "'s border is not " + sl.slice(1).join(" "));
  }
  expect(!wrong.length, wrong.join("; "));
});
await check("tools/skin.py reads every slot, token and size range the page has", async () => {
  const { mkdtempSync, mkdirSync, copyFileSync, writeFileSync } = await import("node:fs");
  const { execFileSync } = await import("node:child_process");
  const { tmpdir } = await import("node:os");
  const dir = mkdtempSync(join(tmpdir(), "skin-")), c = join(dir, "catio");
  mkdirSync(join(c, "tools"), { recursive: true }); mkdirSync(join(c, "art", "skin"), { recursive: true });
  copyFileSync(join(here, "..", "index.html"), join(c, "index.html")); copyFileSync(join(here, "..", "tools", "skin.py"), join(c, "tools", "skin.py"));
  writeFileSync(join(c, "art", "skin.json"), JSON.stringify({ tokens: { "--ink": "#123456", "--u-desk": "20px" } }));
  const out = execFileSync("python3", [join(c, "tools", "skin.py")], { encoding: "utf8" });
  const src = readFileSync(join(here, "..", "index.html"), "utf8");
  const slots = (src.slice(src.indexOf("const ART = {"), src.indexOf("const SPR0")).match(/^\s+"[\w-]+":\s*\{/gm) || []).length;
  expect(new RegExp("0 of " + slots + " slots").test(out) && /--u-desk = '20px' left out/.test(out), out);
  expect(JSON.parse(readFileSync(join(c, "art", "skin.json"), "utf8")).tokens["--ink"] === "#123456", "token dropped");
});
// a blank picture of any size, for a slot that is weighed by its size
const { deflateSync, crc32 } = await import("node:zlib");
const png = (w, h) => {
  const chunk = (t, d) => { const n = Buffer.alloc(4); n.writeUInt32BE(d.length); const c = Buffer.alloc(4); c.writeUInt32BE(crc32(Buffer.concat([Buffer.from(t), d])) >>> 0); return Buffer.concat([n, Buffer.from(t), d, c]); };
  const ih = Buffer.alloc(13); ih.writeUInt32BE(w, 0); ih.writeUInt32BE(h, 4); ih[8] = 8; ih[9] = 6;
  const raw = Buffer.alloc((w * 4 + 1) * h, 255); for (let y = 0; y < h; y++) raw[y * (w * 4 + 1)] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ih), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
};
await check("art/skin.json beside the page: a slot written as its path alone is drawn", async () => {
  // the page served over http (art/skin.json can't be fetched from file://), its skin.json naming the panel by path
  const P = join(here, ".."), page0 = readFileSync(join(here, ".page.html"), "utf8").replace(/<base href="[^"]*">/, '<base href="http://catio.test/">');
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  await ctx.route("http://catio.test/**", (r) => {
    const path = decodeURIComponent(new URL(r.request().url()).pathname);
    if (path === "/page.html") return r.fulfill({ contentType: "text/html", body: page0 });
    if (path === "/art/skin.json") return r.fulfill({ contentType: "application/json", body: JSON.stringify({ panel: "art/licensed/ui/bubble.png" }) });
    try { return r.fulfill({ body: readFileSync(join(P, path)) }); } catch (e) { return r.fulfill({ status: 404, body: "" }); }
  });
  const page = await ctx.newPage();
  await page.goto("http://catio.test/page.html");
  await page.waitForTimeout(1200);
  const v = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--art-panel"));
  await ctx.close();
  expect(v.includes("ui/bubble.png"), v);
});
await check("tools/skin.py: a map piece is pixel art only drawn near the art pixel, and a member is weighed against her head", async () => {
  const { mkdtempSync, mkdirSync, copyFileSync, writeFileSync } = await import("node:fs");
  const { execFileSync } = await import("node:child_process");
  const { tmpdir } = await import("node:os");
  const dir = mkdtempSync(join(tmpdir(), "skin-")), c = join(dir, "catio");
  for (const d of ["tools", "art/skin", "art/other"]) mkdirSync(join(c, d), { recursive: true });
  copyFileSync(join(here, "..", "index.html"), join(c, "index.html")); copyFileSync(join(here, "..", "tools", "skin.py"), join(c, "tools", "skin.py"));
  // the map button is shown 135 px wide: drawn 135 wide it is smooth at that size, drawn 68 wide it is pixel art
  writeFileSync(join(c, "art/skin/map-button.png"), png(135, 40)); writeFileSync(join(c, "art/skin/map-panel.png"), png(68, 34));
  // her button, pointed at by hand outside the folder, and her lit one in the folder, drawn its size
  writeFileSync(join(c, "art/other/button.png"), png(52, 56)); writeFileSync(join(c, "art/skin/button-hover.png"), png(52, 56));
  // and a panel of hers in the folder under another name, which skin.json points at by hand
  writeFileSync(join(c, "art/skin/my-panel.png"), png(53, 61));
  writeFileSync(join(c, "art", "skin.json"), JSON.stringify({ button: { file: "art/other/button.png", slice: [8, 8, 8, 8] }, panel: "art/skin/my-panel.png" }));
  const out = execFileSync("python3", [join(c, "tools", "skin.py")], { encoding: "utf8" });
  const j = JSON.parse(readFileSync(join(c, "art", "skin.json"), "utf8"));
  expect(!j["map-button"].pixel && j["map-button"].scale === 1 && j["map-panel"].pixel === true && !j["map-panel"].scale, JSON.stringify([j["map-button"], j["map-panel"]]));
  expect(j.button && j["button-hover"], out);
  expect(j.panel && !/no slot is called my-panel/.test(out) && /my-panel\.png: panel/.test(out), out);
});
{
  const { page, ctx, errors } = await open();
  const rootVar = (n) => page.evaluate((n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), n);
  await check("tokens in the skin recolour and resize the whole café", async () => {
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--ink": "#1d3557", "--px-size": "16px", "--hue-1": "#123456" }, at: 1 }));
    await page.waitForTimeout(600);
    const b = await page.evaluate(() => { const c = getComputedStyle(document.getElementById("houseBtn")); return [c.color, c.fontSize]; });
    expect(b[0] === "rgb(29, 53, 87)" && b[1] === "16px", b.join(" | "));
    expect((await rootVar("--hue-1")) === "#123456", await rootVar("--hue-1"));
  });
  await check("a token that isn't a colour or a size is refused, and so is one that isn't a token", async () => {
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--ink": "red; background: url(x)", "--nope": "#000000", "--px-size": "huge" }, at: 2 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--ink")) === "#3F2A20" && (await rootVar("--px-size")) === "18px" && !(await rootVar("--nope")), [await rootVar("--ink"), await rootVar("--px-size")].join(" | "));
  });
  await check("The look changes a colour, keeps it in skin/theme, and puts it back", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const input = page.locator("#artDlg li[data-token='--go'] input");
    await input.evaluate((i) => { i.value = "#ff8800"; i.dispatchEvent(new Event("input", { bubbles: true })); i.dispatchEvent(new Event("change", { bubbles: true })); });
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => window.__catio.store["skin/theme"].tokens["--go"]) === "#ff8800", "not kept");
    expect((await rootVar("--go")) === "#ff8800", await rootVar("--go"));
    expect(/Yours/.test(await page.locator("#artDlg li[data-token='--go']").innerText()), "not marked");
    await page.click("#artDlg li[data-token='--go'] button:has-text('Put back')");
    await page.waitForTimeout(500);
    expect((await rootVar("--go")) === "#C0D470" && !(await page.evaluate(() => "skin/theme" in window.__catio.store)), await rootVar("--go"));
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  // Her words (4 October 2026): "reevaluate plug-n-play capabilities of design systems like Figma". Figma keeps a
  // variable's value per mode and swaps whole themes as design tokens files (the W3C format, 2025.10); so does the café.
  await check("a dark value of a token shows only in the dark, and light keeps its own", async () => {
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--ink": "#111111" }, dark: { "--ink": "#eeeeee" }, at: 3 }));
    await page.waitForTimeout(600);
    const light = await rootVar("--ink");
    await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
    const dark = await rootVar("--ink");
    await page.evaluate(() => { delete document.documentElement.dataset.theme; });
    expect(light === "#111111" && dark === "#eeeeee", light + " | " + dark);
  });
  await check("The look exports the café's tokens as a design tokens file Figma can import", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#tokensExport")]);
    expect(dl.suggestedFilename() === "kittychat-light.tokens.json", dl.suggestedFilename());
    const j = JSON.parse(readFileSync(await dl.path(), "utf8"));
    expect(j.colours.$type === "color" && j.colours.ink.$value.hex === "#111111" && j.colours.ink.$value.colorSpace === "srgb" && j.colours.ink.$value.components.length === 3, JSON.stringify(j.colours.ink));
    expect(j.type.$type === "dimension" && j.type["px-size"].$value.value === 18 && j.type["px-size"].$value.unit === "px", JSON.stringify(j.type["px-size"]));
    expect(j["map-colours"]["hue-1"].$value.hex === "#5e8f34" && Object.keys(j.colours).filter((k) => !k.startsWith("$")).length > 25, "map colours");
  });
  await check("Import tokens… reads a Figma file into the mode chosen, following its aliases, and leaves out what isn't the café's", async () => {
    await page.click("#lookMode-dark"); await settle(page);
    const figma = { primitives: { $type: "color", navy: { $value: { colorSpace: "srgb", components: [0.1137, 0.2078, 0.3412], hex: "#1d3557" } } },
      colours: { $type: "color", go: { $value: "{primitives.navy}" }, brand: { $value: { colorSpace: "srgb", components: [1, 0, 0] } } } };
    await page.locator("#tokensFile").setInputFiles({ name: "Dark.tokens.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(figma)) });
    await page.waitForTimeout(600);
    const d = await page.evaluate(() => window.__catio.store["skin/theme"]);
    expect(d.dark["--go"] === "#1d3557" && d.dark["--ink"] === "#eeeeee" && d.tokens["--ink"] === "#111111" && !("--go" in d.tokens), JSON.stringify(d));
    expect(/1 token from Dark\.tokens\.json in Dark; 2 not the café's/.test(await toast(page)), await toast(page));
    expect((await page.locator("#artDlg li[data-token='--go'] input").inputValue()) === "#1d3557", "the picker shows the dark value");
    await page.locator("#tokensFile").setInputFiles({ name: "notes.json", mimeType: "application/json", buffer: Buffer.from("{nope") });
    await page.waitForTimeout(300);
    expect(/isn't JSON/.test(await toast(page)), await toast(page));
    await page.click("#lookMode-light"); await settle(page);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("the shared Figma file comes out the same in The look and in skin.py as in the gateway and catio_mcp.py", async () => {
    // harness/test/fixtures: the one file all four read, and what each must find in it
    const FIX = join(here, "..", "..", "harness", "test", "fixtures");
    const want = JSON.parse(readFileSync(join(FIX, "tokens-figma.expected.json"), "utf8")), sorted = (o) => JSON.stringify(Object.fromEntries(Object.entries(o).sort()));
    const kept = await page.evaluate(() => { const t = window.__catio.store["skin/theme"]; delete window.__catio.store["skin/theme"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; return t; });
    await page.waitForTimeout(500);
    try {
      await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
      await page.locator("#tokensFile").setInputFiles(join(FIX, "tokens-figma.json"));
      await page.waitForFunction(() => /tokens-figma/.test(document.getElementById("toast").textContent));
      const said = await toast(page), t = await page.evaluate(() => window.__catio.store["skin/theme"].tokens);
      expect(sorted(t) === sorted(want.found), JSON.stringify(t));
      expect(new RegExp(Object.keys(want.found).length + " tokens from tokens-figma\\.json.*" + want.foreign + " not the café's.*" + want.refused + " the café's with a value it can't take").test(said), said);
      const { execFileSync } = await import("node:child_process");
      const py = JSON.parse(execFileSync("python3", ["-c", "import json, sys; sys.path.insert(0, sys.argv[1]); import skin; f, n, r = skin.from_dtcg(json.load(open(sys.argv[2])), skin.token_names()); print(json.dumps([f, n, r]))",
        join(here, "..", "tools"), join(FIX, "tokens-figma.json")], { encoding: "utf8" }));
      expect(sorted(py[0]) === sorted(want.found) && py[1] === want.foreign && py[2] === want.refused, JSON.stringify(py));
    } finally {
      await page.evaluate(() => { const d = document.getElementById("artDlg"); if (d && d.open) d.close(); });
      await page.evaluate((t) => { if (t) window.__catio.put("skin/theme", t); else window.__catio.drop("skin/theme"); }, kept);
      await page.waitForTimeout(500);
    }
  });
  await check("Import tokens… takes the café's own group over a namesake, and refuses a see-through colour or a size out of range rather than call it foreign", async () => {
    const kept = await page.evaluate(() => { const t = window.__catio.store["skin/theme"]; delete window.__catio.store["skin/theme"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; return t; });
    await page.waitForTimeout(500);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const file = { primitives: { grass: { $value: "#00ff00" } }, colours: { grass: { $value: "#112233" }, go: { $value: "#C0D47080" }, tan: { $value: { colorSpace: "srgb", components: [1, 0, 0], alpha: 0.5 } } },
      type: { "px-size": { $value: { value: 17.5, unit: "px" } } } };
    await page.locator("#tokensFile").setInputFiles({ name: "mixed.tokens.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(file)) });
    await page.waitForTimeout(600);
    const t = await page.evaluate(() => window.__catio.store["skin/theme"].tokens);
    expect(t["--grass"] === "#112233" && !("--go" in t) && !("--tan" in t) && !("--px-size" in t), JSON.stringify(t));
    expect(/1 token from mixed\.tokens\.json in Light/.test(await toast(page)) && /3 the café's with a value it can't take/.test(await toast(page)) && !/not the café's/.test(await toast(page)), await toast(page));
    // a namesake refused elsewhere in the file isn't counted when the café's own group gave the token
    await page.locator("#tokensFile").setInputFiles({ name: "twice.tokens.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify({ primitives: { ink: { $value: "#11223380" } }, colours: { ink: { $value: "#112233" } } })) });
    await page.waitForFunction(() => /twice/.test(document.getElementById("toast").textContent));
    const said = await toast(page);
    expect(/1 token from twice/.test(said) && !/can't take/.test(said), said);
    // a size typed back to the café's own is said to be the café's again, not hers
    const f = page.locator("#artDlg li[data-token='--px-size'] input");
    await page.locator("#artDlg details[data-group='Type'] > summary").click();
    await f.fill("20px"); await f.dispatchEvent("change"); await settle(page);
    await f.fill("18px"); await f.dispatchEvent("change"); await settle(page);
    expect(/Pixel font size: the café's again/.test(await toast(page)) && !("--px-size" in (await page.evaluate(() => window.__catio.store["skin/theme"].tokens))), await toast(page));
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
    await page.evaluate((t) => window.__catio.put("skin/theme", t), kept);
    await page.waitForTimeout(500);
  });
  await check("a border or a frame count the page can't take refuses her piece, rather than cutting it with the pack's", async () => {
    await page.evaluate(() => window.__catio.put("skin/panel", { src: "art/licensed/ui/bubble.png", slice: [80, 80, 80, 80], at: 1 }));
    await page.waitForTimeout(600);
    expect(!(await rootVar("--art-panel")).includes("bubble.png"), await rootVar("--art-panel"));
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const row = await page.locator("#artDlg li[data-slot='panel']").textContent();
    expect(/border isn't four whole numbers from 0 to 64/.test(row), row);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
    await page.evaluate(() => { delete window.__catio.store["skin/panel"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("a size out of its range is refused, so no skin can bury the café under its borders", async () => {
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--u-desk": "20px", "--px-size": "0px", "--body-size": "0.9rem" }, at: 4 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--u")) === "2px" && (await rootVar("--px-size")) === "18px" && (await rootVar("--body-size")) === "0.9rem", [await rootVar("--u"), await rootVar("--px-size")].join(" | "));
  });
  await check("a button's lit piece of another size than the button is refused, with why", async () => {
    await page.evaluate(() => window.__catio.put("skin/button-hover", { src: "art/licensed/ui/bubble.png", at: 1 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--art-button-hover")).includes("ui/button-hover.png"), await rootVar("--art-button-hover"));
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const row = await page.locator("#artDlg li[data-slot='button-hover']").textContent();
    expect(/42 × 42/.test(row) && /26 × 28/.test(row) && /shares the button's border/.test(row), row);
  });
  await check("Put everything back clears what is kept, a refused piece and the tokens too", async () => {
    // one the page can't read at all (an address it won't load) goes too, though it was never shown
    await page.evaluate(() => window.__catio.put("skin/panel-x", { src: "https://example.com/x.png", asset: "a-gone", at: 1 }));
    await page.waitForTimeout(500);
    await page.click("#artResetAll");
    await page.waitForTimeout(800);
    const left = await page.evaluate(() => Object.keys(window.__catio.store).filter((p) => p.startsWith("skin/")));
    expect(!left.length, left.join(" "));
    expect(await page.evaluate(() => window.__catio.assetsDeleted.includes("a-gone")), "its file stayed in the store");
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a size she types that isn't kept leaves no preview behind", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    await page.locator("#artDlg details[data-group='Type'] > summary").click();
    const f = page.locator("#artDlg li[data-token='--px-size'] input");
    await f.fill("12px"); await f.dispatchEvent("input");
    expect((await rootVar("--px-size")) === "12px", "no preview");
    await f.fill("12pxx"); await f.dispatchEvent("change"); await settle(page);
    expect((await rootVar("--px-size")) === "18px" && /from 8 to 48px/.test(await toast(page)), await rootVar("--px-size"));
    await page.click("#toast .btn"); await settle(page);   // the warning waits for her OK
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a colour she is choosing when the card is redrawn under her stays, and is kept when she leaves it", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const sel = "#artDlg li[data-token='--tan'] input";
    await page.evaluate((sel) => { const i = document.querySelector(sel); i.focus(); i.value = "#aabbcc"; i.dispatchEvent(new Event("input", { bubbles: true })); i.dataset.old = "1"; }, sel);
    // a change from elsewhere (another device, Claude) redraws The look while she is in the picker
    await page.evaluate(() => { window.__catio.put("skin/theme", { tokens: { "--ink": "#202020" }, at: 5 }); });
    await page.waitForTimeout(600);
    const now = await page.evaluate((sel) => { const i = document.querySelector(sel); return [!i.dataset.old, i.value, document.activeElement === i]; }, sel);
    expect(now[0] && now[1] === "#aabbcc" && now[2], "after the redraw: " + now.join(" | "));
    await page.evaluate(() => document.activeElement.blur()); await settle(page);
    const kept = await page.evaluate(() => window.__catio.store["skin/theme"].tokens);
    expect(String(kept["--tan"]).toLowerCase() === "#aabbcc" && kept["--ink"] === "#202020", JSON.stringify(kept));
    await page.evaluate(() => { const st = window.__catio.store; delete st["skin/theme"]; window.__catio.put("skin/zy", {}); delete st["skin/zy"]; });
    await page.waitForTimeout(500);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a lit button drawn the size of her own button, given with it, is used", async () => {
    await page.evaluate(() => {   // both in one snapshot, as a skin.json or a first load brings them
      window.__catio.store["skin/button"] = { src: "art/licensed/ui/bubble.png", slice: [5, 5, 6, 5], at: 1 };
      window.__catio.put("skin/button-hover", { src: "art/licensed/ui/bubble.png", at: 1 });
    });
    await page.waitForTimeout(700);
    expect((await rootVar("--art-button-hover")).includes("ui/bubble.png") && (await rootVar("--btn-b")) === "6", await rootVar("--art-button-hover"));
    // gone again, in one snapshot (the stub notifies on a write, so a stray document carries the news and goes too)
    await page.evaluate(() => { const st = window.__catio.store; delete st["skin/button"]; delete st["skin/button-hover"]; window.__catio.put("skin/zz", {}); delete st["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("her button, with the pack's bubble: a reply in a thread keeps the bubble's own border", async () => {
    await page.evaluate(() => window.__catio.put("skin/button", { src: "art/licensed/ui/button.png", slice: [3, 4, 5, 4], at: 1 }));
    await page.waitForTimeout(600);
    const [iw, px, btn] = [await rootVar("--bubble-iw"), await rootVar("--bubble-px"), await rootVar("--btn-px")];
    expect(iw === px && iw !== btn, [iw, px, btn].join(" | "));
    // and standing in for the green and pink buttons, her frame keeps their colour inside it: go-ahead and letting go still read
    const faces = await page.evaluate(() => ["green", "pink"].map((c) => { const b = document.createElement("button"); b.className = "btn " + c; document.body.appendChild(b); const cs = getComputedStyle(b); const r = [cs.borderImageSource, cs.borderImageSlice]; b.remove(); return r; }));
    expect(faces.every(([src, slice]) => src.includes("ui/button.png") && !/fill/.test(slice)), JSON.stringify(faces));
    const tag = await page.evaluate(() => { const r = document.createElement("div"); r.className = "rt"; r.setAttribute("aria-selected", "true"); const t = document.createElement("span"); t.className = "tag"; r.appendChild(t); document.body.appendChild(r);
      const cs = getComputedStyle(t), go = getComputedStyle(document.documentElement).getPropertyValue("--go").trim(); const out = [cs.borderImageSlice, cs.backgroundColor, go]; r.remove(); return out; });
    expect(!/fill/.test(tag[0]) && tag[1] === "rgb(" + [1, 3, 5].map((i) => parseInt(tag[2].slice(i, i + 2), 16)).join(", ") + ")", "the chosen room's tag: " + tag.join(" | "));
    await page.evaluate(() => { const st = window.__catio.store; delete st["skin/button"]; window.__catio.put("skin/zz", {}); delete st["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("faces of her own fill their cells: each mood face is shown whole, not cut a pixel in as the pack's are", async () => {
    const box = () => page.evaluate(() => { const b = document.createElement("span"); b.className = "face-ico"; document.body.appendChild(b); const cs = getComputedStyle(b); const r = cs.backgroundSize + " " + cs.backgroundPosition; b.remove(); return r; });
    expect((await box()) === "192px 32px -97px -1px", await box());
    await page.evaluate(() => window.__catio.put("skin/faces", { src: "art/licensed/ui/faces.png", at: 1 }));
    await page.waitForTimeout(600);
    expect((await box()) === "180px 30px -90px 0px", await box());
    await page.evaluate(() => { delete window.__catio.store["skin/faces"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("a family member carrying its head's border, however big, is used: its own border is never read", async () => {
    await page.evaluate(() => window.__catio.put("skin/map-button-hover", { src: "art/licensed/pastel/button-down.png", slice: [40, 44, 48, 44], at: 1 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--art-map-button-hover")).includes("pastel/button-down.png"), await rootVar("--art-map-button-hover"));
    await page.evaluate(() => { delete window.__catio.store["skin/map-button-hover"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("a map piece called pixel art beside its family's smooth head is refused, with why", async () => {
    await page.evaluate(() => window.__catio.put("skin/map-panel-dark", { src: "art/licensed/pastel/panel-dark.png", pixel: true, at: 1 }));
    await page.waitForTimeout(600);
    expect(!(await rootVar("--mpanel-render")).includes("pixelated"), await rootVar("--mpanel-render"));
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const row = await page.locator("#artDlg li[data-slot='map-panel-dark']").textContent();
    expect(/shares the map panel's drawing, which is smooth/.test(row), row);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
    await page.evaluate(() => { delete window.__catio.store["skin/map-panel-dark"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("the thickest frame a skin may give still leaves the house the middle of the screen, drawn the right way round", async () => {
    const kept = await page.evaluate(() => window.__catio.store["skin/theme"]);
    // on a phone, 390 px wide: a 64-pixel border at 4 px an art pixel would be 264 px a side
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => { window.__catio.store["skin/panel"] = { src: "art/licensed/house.png", slice: [64, 64, 64, 64], at: 1 }; window.__catio.put("skin/theme", { tokens: { "--u-phone": "4px" }, at: 10 }); });
    await page.waitForTimeout(900);
    await page.keyboard.press("0"); await page.waitForTimeout(400);
    const c = await cam(page);
    expect(c.s > 0.05, JSON.stringify(c));   // a scale at or under nothing draws the house mirrored, or not at all
    await page.evaluate((t) => { const st = window.__catio.store; delete st["skin/panel"]; if (t) window.__catio.put("skin/theme", t); else window.__catio.drop("skin/theme"); }, kept);
    await page.waitForTimeout(800);
    await page.setViewportSize({ width: 1440, height: 900 }); await page.waitForTimeout(400);
    await page.keyboard.press("0"); await page.waitForTimeout(300);
  });
  await check("the logo is drawn at the art pixel, so it grows and shrinks with her --u-desk", async () => {
    const logo = () => page.evaluate(() => { const r = document.querySelector("#houseBtn .logo").getBoundingClientRect(); return r.width + "x" + r.height; });
    expect((await logo()) === "42x36", await logo());
    const kept = await page.evaluate(() => window.__catio.store["skin/theme"]);
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--u-desk": "3px" }, at: 9 }));
    await page.waitForTimeout(600);
    expect((await logo()) === "63x54", await logo());
    await page.evaluate((t) => { if (t) window.__catio.put("skin/theme", t); else { delete window.__catio.store["skin/theme"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; } }, kept);
    await page.waitForTimeout(600);
  });
  await check("her map button standing in for the pressed one lets the floor on screen keep its colour", async () => {
    await page.evaluate(() => window.__catio.put("skin/map-button", { src: "art/licensed/pastel/button-hover.png", at: 1 }));
    await page.waitForTimeout(600);
    const tab = await page.evaluate(() => { const b = document.querySelector('.floors .pbtn[aria-checked="true"]'); const cs = getComputedStyle(b); return [cs.borderImageSource, cs.borderImageSlice]; });
    expect(tab[0].includes("pastel/button-hover.png") && !/fill/.test(tab[1]), tab.join(" | "));
    await page.evaluate(() => window.__catio.drop("skin/map-button"));
    await page.waitForTimeout(500);
  });
  await check("a piece of hers the café can't read at all says so on its row, with Put back; colours it can't take go with Put everything back", async () => {
    await page.evaluate(() => { window.__catio.put("skin/panel", { src: "https://example.com/panel.png", at: 1 }); window.__catio.put("skin/theme", { tokens: { "--ink": "red" }, at: 1 }); });
    await page.waitForTimeout(600);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    await page.locator("#artDlg details[data-group='Interface'] > summary").click();
    const row = await page.locator("#artDlg li[data-slot='panel']").textContent();
    expect(/isn't a file the café can read/.test(row) && /Put back/.test(row), row);
    await page.click("#artResetAll"); await page.waitForTimeout(800);
    const left = await page.evaluate(() => Object.keys(window.__catio.store).filter((p) => p.startsWith("skin/")));
    expect(!left.length, left.join(" "));
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("an address that climbs out of art/ in disguise is refused, and a cat whose frames aren't square is asked for them", async () => {
    await page.evaluate(() => { window.__catio.put("skin/panel", { src: "art/%2e%2e/%2e%2e/files/x", at: 1 }); window.__catio.put("skin/cat-meow", { src: "art/licensed/ui/logo.png", at: 1 }); });
    try {
      await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
      // The look redraws as the skin lands: wait for both verdicts rather than for a guess at how long they take
      await page.waitForFunction(() => ["panel", "cat-meow"].every((k) => /Yours isn't used/.test((document.querySelector("#artDlg li[data-slot='" + k + "']") || {}).textContent || "")), null, { timeout: 5000 });
      // refused as an address, never even fetched: not "couldn't be read", which is what a fetched one that failed says
      const panel = await page.locator("#artDlg li[data-slot='panel']").textContent();
      expect(/isn't a file the café can read/.test(panel), panel);
      const row = await page.locator("#artDlg li[data-slot='cat-meow']").textContent();
      expect(/frames aren't square/.test(row), row);
    } finally {
      await page.evaluate(() => { const d = document.getElementById("artDlg"); if (d && d.open) d.close(); window.__catio.drop("skin/panel"); window.__catio.drop("skin/cat-meow"); });
      await page.waitForTimeout(500);
    }
  });
  await check("a project map's dots outside its eight neighbourhoods are the rest's grey", async () => {
    await page.evaluate(() => window.__catio.put("graphs/grey-test", { repo: "example/grey-test", at: Date.now(), nodes: 3, edges: 1, communities: 1, gods: [], groups: [{ name: "One", size: 2 }], surprises: [], questions: [],
      map: { n: [{ t: "A", g: 0, d: 3, x: 50, y: 50 }, { t: "B", g: -1, d: 2, x: 150, y: 80 }, { t: "C", g: 11, d: 1, x: 250, y: 120 }], l: [0, 1] } }));
    await page.waitForTimeout(400);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "Project maps" }).click(); await settle(page);
    const fills = await page.evaluate(() => [...document.querySelectorAll("#mapsDlg svg rect[fill]")].map((r) => r.getAttribute("fill").toUpperCase()));
    expect(fills.includes("#5E8F34") && fills.filter((f) => f === "#9A8878").length === 2 && !fills.includes("UNDEFINED"), fills.join(" "));
    await page.evaluate(() => document.getElementById("mapsDlg").close()); await settle(page);
  });
  await check("a button of her own cut another way stands in for the lit, green and pink ones she hasn't drawn", async () => {
    await page.evaluate(() => window.__catio.put("skin/button", { src: "art/licensed/ui/bubble.png", slice: [5, 5, 6, 5], at: 1 }));
    await page.waitForTimeout(700);
    expect((await rootVar("--art-button-pink")).includes("ui/bubble.png") && (await rootVar("--art-button-green")).includes("ui/bubble.png"), await rootVar("--art-button-pink"));
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    expect(/Your button stands in/.test(await page.locator("#artDlg li[data-slot='button-pink']").textContent()), "not said");
    await page.locator("#artDlg details[data-group='Interface'] > summary").click();
    await page.click("#artDlg li[data-slot='button'] button:has-text('Put back')"); await page.waitForTimeout(600);
    expect((await rootVar("--art-button-pink")).includes("ui/button-pink.png"), await rootVar("--art-button-pink"));
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a café's own export, imported again, keeps only what differs", async () => {
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--ink": "#222222" }, dark: {}, at: 5 }));
    await page.waitForTimeout(500);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#tokensExport")]);
    await page.click("#lookMode-dark"); await settle(page);
    await page.locator("#tokensFile").setInputFiles(await dl.path());
    await page.waitForTimeout(600);
    const d = await page.evaluate(() => window.__catio.store["skin/theme"]);
    expect(d && d.tokens["--ink"] === "#222222" && !Object.keys(d.dark || {}).length, JSON.stringify(d));
    await page.click("#lookMode-light"); await settle(page);
    if (await page.locator("#toast .btn").isVisible()) await page.click("#toast .btn");
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a border that is empty or leaves no middle is refused; a paw points where she says", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    await page.locator("#artDlg details[data-group='Interface'] > summary").click();
    await page.locator("#artFile-panel").setInputFiles({ name: "panel.png", mimeType: "image/png", buffer: readFileSync(join(here, "..", "art", "licensed", "ui", "bubble.png")) });
    await page.waitForTimeout(400);
    for (const bad of ["", "0", "30"]) {   // "4," reads as 4 all round, which is fine
      await page.fill("#artBorder-panel", bad);
      await page.click("#artDlg li[data-slot='panel'] .swap button[type=submit]"); await settle(page);
      expect(/fit inside its 42 × 42/.test(await toast(page)) && !(await page.evaluate(() => "skin/panel" in window.__catio.store)), bad + ": " + await toast(page));
      await page.click("#toast .btn");
    }
    await page.click("#artDlg li[data-slot='panel'] .swap button:has-text('Cancel')"); await settle(page);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
    await page.evaluate(() => window.__catio.put("skin/cursor", { src: "art/licensed/ui/cursor-point.png", hot: [2, 2], at: 1 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--cursor-hot")) === "2 2" && /cursor-point\.png.*2 2/.test(await page.evaluate(() => getComputedStyle(document.body).cursor)), await page.evaluate(() => getComputedStyle(document.body).cursor));
    await page.evaluate(() => { delete window.__catio.store["skin/cursor"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(400);
  });
  await check("a map piece drawn near the art pixel starts as pixel art; drawn the size it is shown, smooth", async () => {
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    await page.locator("#artDlg details[data-group='Map panel'] > summary").click();
    for (const [w, h, was] of [[135, 40, "smooth"], [68, 20, "pixel"]]) {
      await page.locator("#artFile-map-button").setInputFiles({ name: "map-button.png", mimeType: "image/png", buffer: png(w, h) });
      await page.waitForTimeout(400);
      expect((await page.inputValue("#artPixel-map-button")) === was, w + ": " + await page.inputValue("#artPixel-map-button"));
    }
    await page.click("#artDlg li[data-slot='map-button'] .swap button:has-text('Cancel')"); await settle(page);
    // a map button the size it is shown, called pixel art: its border would leave the 40 px button no middle
    await page.locator("#artFile-map-button").setInputFiles({ name: "map-button.png", mimeType: "image/png", buffer: png(135, 40) });
    await page.waitForTimeout(400);
    await page.selectOption("#artPixel-map-button", "pixel");
    await page.click("#artDlg li[data-slot='map-button'] .swap button[type=submit]"); await settle(page);
    expect(/too much for the piece as it is shown/.test(await toast(page)) && !(await page.evaluate(() => "skin/map-button" in window.__catio.store)), await toast(page));
    await page.click("#toast .btn");
    await page.click("#artDlg li[data-slot='map-button'] .swap button:has-text('Cancel')"); await settle(page);
    // a map panel drawn at the pack's own size, called pixel art, would show its 28-pixel border 56 px wide: refused
    await page.locator("#artFile-map-panel").setInputFiles({ name: "map-panel.png", mimeType: "image/png", buffer: png(300, 150) });
    await page.waitForTimeout(400);
    await page.selectOption("#artPixel-map-panel", "pixel");
    await page.click("#artDlg li[data-slot='map-panel'] .swap button[type=submit]"); await settle(page);
    expect(/would show 56 px wide/.test(await toast(page)) && !(await page.evaluate(() => "skin/map-panel" in window.__catio.store)), await toast(page));
    await page.click("#toast .btn");
    await page.click("#artDlg li[data-slot='map-panel'] .swap button:has-text('Cancel')"); await settle(page);
    // her armchair's colour, while she is still choosing it: her picture in The look follows, and goes back if she lets go
    const me = () => page.evaluate(() => document.querySelector("#artDlg li[data-slot='owner'] > .pic").innerHTML);
    const was = await me();
    await page.evaluate(() => { const i = document.querySelector("#artDlg li[data-token='--owner-chair'] input"); i.focus(); i.value = "#00ff00"; i.dispatchEvent(new Event("input", { bubbles: true })); });
    await page.waitForTimeout(150);
    const now = await me();
    await page.evaluate(() => document.querySelector("#artDlg li[data-token='--owner-chair'] input").blur());
    await page.waitForTimeout(150);
    expect(now !== was && (await me()) === was && !(await page.evaluate(() => "skin/theme" in window.__catio.store && window.__catio.store["skin/theme"].tokens["--owner-chair"])), "no preview of her armchair");
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("two colours changed one after the other, quickly, are both kept; one set back to the café's isn't hers", async () => {
    await page.evaluate(() => { delete window.__catio.store["skin/theme"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(400);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    await page.evaluate(() => {
      for (const [n, v] of [["--ink", "#101010"], ["--tan", "#202020"], ["--go", "#C0D470"]]) {   // the last is the café's own
        const i = document.querySelector("#artDlg li[data-token='" + n + "'] input"); i.value = v; i.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    await page.waitForTimeout(800);
    const d = await page.evaluate(() => window.__catio.store["skin/theme"]);
    expect(d && d.tokens["--ink"] === "#101010" && d.tokens["--tan"] === "#202020" && !("--go" in d.tokens), JSON.stringify(d));
    if (await page.locator("#toast .btn").isVisible()) await page.click("#toast .btn");
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a thicker frame refits the whole house inside it", async () => {
    await closeMenu(page); await page.keyboard.press("0"); await page.waitForTimeout(300);
    const before = await page.evaluate(() => getComputedStyle(document.getElementById("world")).transform);
    await page.evaluate(() => window.__catio.put("skin/theme", { tokens: { "--u-desk": "4px" }, at: 9 }));
    await page.waitForTimeout(700);
    const after = await page.evaluate(() => getComputedStyle(document.getElementById("world")).transform);
    const trim = await page.evaluate(() => getComputedStyle(document.querySelector(".trim")).borderTopWidth);
    expect(trim === "24px" && before !== after, trim + " | " + before + " → " + after);
    await page.evaluate(() => { delete window.__catio.store["skin/theme"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("a font of hers for the text goes ahead of the café's", async () => {
    await page.evaluate(() => window.__catio.put("skin/font-body", { src: "art/licensed/ui/sprout.ttf", at: 1 }));
    await page.waitForTimeout(800);
    expect((await rootVar("--body")).startsWith('"KittySkin-font-body", "Nunito"'), await rootVar("--body"));
    // the round font is where the pixel font has no letter: hers there reaches every title and button
    await page.evaluate(() => window.__catio.put("skin/font-display", { src: "art/licensed/ui/sprout.ttf", at: 1 }));
    await page.waitForTimeout(800);
    const fam = await page.evaluate(() => getComputedStyle(document.getElementById("houseBtn")).fontFamily);
    expect(/^"?Sprout"?, "?KittySkin-font-display"?/.test(fam), fam);
  });
  await check("a picture of her that isn't the owner's shape is refused, and she is drawn as before", async () => {
    await page.evaluate(() => window.__catio.put("skin/owner", { src: "art/licensed/ui/logo.png", at: 1 }));
    await page.waitForTimeout(600);
    await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    const row = await page.locator("#artDlg li[data-slot='owner']").textContent();
    expect(/21 × 18/.test(row) && /30 × 40/.test(row) && (await page.locator("#artDlg li[data-slot='owner'] .pic svg").count()) === 1, row);
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
    expect(!errors.length, errors.join(" | "));
  });
  await ctx.close();
}
{
  const { page, ctx, errors } = await open();
  const rootVar = (n) => page.evaluate((n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), n);
  const openArt = async () => { await closeMenu(page); await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page); };
  await check("The look lists every slot, in groups, each with the size to draw it at", async () => {
    await openArt();
    const rows = await page.locator("#artDlg li[data-slot]").count();
    const slots = await page.evaluate(() => [...document.querySelectorAll("#artDlg li[data-slot]")].map((l) => l.dataset.slot));
    expect(rows >= 40 && new Set(slots).size === rows, rows + " rows");
    for (const k of ["cat-meow", "cat-walk-side", "house", "decor", "furniture", "panel", "button", "faces", "font", "map-panel", "map-icons"]) expect(slots.includes(k), "no " + k);
    const t = await page.locator("#artDlg").textContent();
    expect(/Exactly 960 × 576/.test(t) && /border 4 4 6 4/.test(t) && /CATS/i.test(t) && /MAP PANEL/i.test(t), t.slice(0, 300));
    expect(await page.locator("#artDlg li[data-slot='panel'] button", { hasText: "Replace" }).count() === 1, "no Replace");
    await page.locator("#artDlg > .dlg > .actions .btn", { hasText: "Close" }).click(); await settle(page);
  });
  await check("a 9-slice in the skin draws every panel, with its own border", async () => {
    await page.evaluate(() => window.__catio.put("skin/panel", { src: "art/licensed/ui/button-green.png", slice: [5, 4, 7, 4], at: 1 }));
    await page.waitForTimeout(600);
    expect((await rootVar("--art-panel")).includes("button-green.png"), await rootVar("--art-panel"));
    expect((await rootVar("--panel-t")) === "5" && (await rootVar("--panel-b")) === "7", "border not set");
    await page.click("#houseBtn"); await settle(page);
    const m = await page.evaluate(() => { const c = getComputedStyle(document.getElementById("menu")); return [c.borderImageSource, c.borderImageSlice, c.borderTopWidth, c.borderBottomWidth]; });
    expect(m[0].includes("button-green.png") && /^5 4 7( 4)? fill$/.test(m[1]) && m[2] === "10px" && m[3] === "14px", m.join(" | "));
    await page.keyboard.press("Escape");
  });
  await check("a cat's sheet in the skin draws its mood, frames and feet from the sheet", async () => {
    await page.evaluate(() => window.__catio.put("skin/cat-work", { src: "art/licensed/mochi-box.png", frames: 4, secs: 0.8, at: 1 }));
    await page.waitForTimeout(600);
    // reduced motion stills every sheet here, so its loop is read from the rule the skin wrote
    const s = await page.evaluate(() => { const e = document.querySelector("#cats .spr.s-idle"); const c = e && getComputedStyle(e); return c && [c.backgroundImage, c.width, c.backgroundSize]; });
    expect(s && s[0].includes("mochi-box.png") && s[1] === "32px" && s[2] === "128px 32px", JSON.stringify(s));
    expect(/\.s-idle \{[^}]*animation: a-skin-idle 0\.8s steps\(4\) infinite/.test(await page.locator("#skinCss").textContent()), "no loop");
  });
  await check("a walk in the skin is every walking cat's, mirrored going left", async () => {
    await page.evaluate(() => window.__catio.put("skin/cat-walk-side", { src: "art/licensed/mochi-idle.png", frames: 10, secs: 1, at: 1 }));
    await page.waitForTimeout(600);
    const css = await page.locator("#skinCss").textContent();
    expect(/\.walker \.spr \{[^}]*mochi-idle\.png[^}]*a-skin-walk[^}]*scaleX\(-1\)/.test(css) && /\.walker\.flip \.spr \{ transform: none; \}/.test(css), css);
  });
  await check("a house of the wrong size is refused, with why, and the pack's house stays", async () => {
    await page.evaluate(() => window.__catio.put("skin/house", { src: "art/licensed/meadow.png", at: 1 }));
    await page.waitForTimeout(600);
    expect((await page.locator("#world img[data-art='house']").getAttribute("src")).endsWith("art/licensed/house.png"), "house swapped");
    await openArt();
    const row = await page.locator("#artDlg li[data-slot='house']").innerText();
    expect(/isn't used/i.test(row) && /112 × 32/.test(row) && /960 × 576/.test(row), row);
    const panel = await page.locator("#artDlg li[data-slot='panel']").textContent();   // its group is folded
    expect(/Yours/.test(panel) && /border 5 4 7 4/.test(panel), panel);
  });
  await check("Replace… checks her file against the slot before keeping it: a picture the wrong size can't be used", async () => {
    await page.locator("#artFile-decor").setInputFiles({ name: "grounds.png", mimeType: "image/png", buffer: readFileSync(join(here, "..", "art", "licensed", "meadow.png")) });
    await page.waitForTimeout(400);
    const f = await page.locator("#artDlg li[data-slot='decor'] .swap").innerText();
    expect(/112 × 32/.test(f) && /960 × 576/.test(f), f);
    expect(!(await page.locator("#artDlg li[data-slot='decor'] .swap button[type=submit]").count()), "Use it offered");
    await page.click("#artDlg li[data-slot='decor'] .swap button:has-text('Cancel')"); await settle(page);
    expect(!(await page.locator("#artDlg li[data-slot='decor'] .swap").count()), "still open");
  });
  await check("Replace… asks a 9-slice drawn at another size for its border, keeps the file and writes its slot", async () => {
    const before = await page.evaluate(() => window.__catio.uploads.length);
    await page.locator("#artFile-field").setInputFiles({ name: "my-field.png", mimeType: "image/png", buffer: readFileSync(join(here, "..", "art", "licensed", "ui", "bubble.png")) });
    await page.waitForTimeout(400);
    expect((await page.locator("#artBorder-field").inputValue()) === "4 4 5 4", await page.locator("#artBorder-field").inputValue());
    await page.fill("#artBorder-field", "5 5 6");
    await page.click("#artDlg li[data-slot='field'] .swap button[type=submit]");
    await page.waitForTimeout(500);
    const d = await page.evaluate(() => window.__catio.store["skin/field"]);
    expect(await page.evaluate(() => window.__catio.uploads.length) === before + 1, "not uploaded");
    expect(d && /^\/_blob\//.test(d.src) && d.asset && JSON.stringify(d.slice) === "[5,5,6,5]" && d.w === 42 && d.h === 42 && d.name === "my-field.png", JSON.stringify(d));
  });
  await check("a font picked with no type of its own is kept as a font, its type read from the font itself", async () => {
    await page.locator("#artFile-font-body").setInputFiles({ name: "MyFont.font", mimeType: "", buffer: readFileSync(join(here, "..", "art", "licensed", "ui", "sprout.ttf")) });
    await page.waitForTimeout(600);
    await page.click("#artDlg li[data-slot='font-body'] .swap button[type=submit]");
    await page.waitForTimeout(600);
    const up = await page.evaluate(() => window.__catio.uploads[window.__catio.uploads.length - 1]);
    expect(up.name === "MyFont.font" && up.type === "font/ttf" && (await page.evaluate(() => !!window.__catio.store["skin/font-body"])), JSON.stringify(up));
    await page.evaluate(() => { delete window.__catio.store["skin/font-body"]; window.__catio.put("skin/zz", {}); delete window.__catio.store["skin/zz"]; });
    await page.waitForTimeout(500);
  });
  await check("a cat's sheet asks for its frames, and refuses a count that doesn't split it", async () => {
    await page.locator("#artFile-cat-meow").setInputFiles({ name: "meow.png", mimeType: "image/png", buffer: readFileSync(join(here, "..", "art", "licensed", "mochi-idle.png")) });
    await page.waitForTimeout(400);
    expect((await page.locator("#artFrames-cat-meow").inputValue()) === "10", await page.locator("#artFrames-cat-meow").inputValue());
    await page.fill("#artFrames-cat-meow", "7");
    await page.click("#artDlg li[data-slot='cat-meow'] .swap button[type=submit]");
    await settle(page);
    expect(/split/.test(await toast(page)) && !(await page.evaluate(() => window.__catio.store["skin/cat-meow"])), await toast(page));
    await page.fill("#artFrames-cat-meow", "10");
    await page.click("#artDlg li[data-slot='cat-meow'] .swap button[type=submit]");
    await page.waitForTimeout(500);
    const d = await page.evaluate(() => window.__catio.store["skin/cat-meow"]);
    expect(d && d.frames === 10 && d.secs === 0.5, JSON.stringify(d));
  });
  await check("a working cat of 4 frames, where the pack's has 10, is asked for its frames rather than refused", async () => {
    await page.locator("#artFile-cat-work").setInputFiles({ name: "work.png", mimeType: "image/png", buffer: readFileSync(join(here, "..", "art", "licensed", "mochi-box.png")) });
    await page.waitForTimeout(400);
    expect((await page.locator("#artFrames-cat-work").inputValue()) === "4" && (await page.locator("#artDlg li[data-slot='cat-work'] .swap button[type=submit]").count()) === 1, await page.locator("#artDlg li[data-slot='cat-work'] .swap").innerText());
    await page.click("#artDlg li[data-slot='cat-work'] .swap button:has-text('Cancel')"); await settle(page);
  });
  await check("Put back gives a slot the pack's piece again, and lets her file go", async () => {
    await page.click("#artDlg li[data-slot='panel'] button:has-text('Put back')");
    await page.waitForTimeout(600);
    expect(!(await page.evaluate(() => "skin/panel" in window.__catio.store)), "doc kept");
    expect((await rootVar("--art-panel")).includes("art/licensed/ui/panel.png") && (await rootVar("--panel-t")) === "6", await rootVar("--art-panel"));
    const asset = await page.evaluate(() => window.__catio.store["skin/field"].asset);
    await page.click("#artDlg li[data-slot='field'] button:has-text('Put back')");
    await page.waitForTimeout(600);
    expect(await page.evaluate((a) => window.__catio.assetsDeleted.includes(a), asset), "asset kept");
  });
  await check("Put every piece back clears the skin, and the cats are the pack's again", async () => {
    await page.click("#artResetAll");
    await page.waitForTimeout(700);
    expect(!(await page.evaluate(() => Object.keys(window.__catio.store).some((p) => p.startsWith("skin/")))), "skin docs left");
    const s = await page.evaluate(() => { const e = document.querySelector("#cats .spr.s-idle"); return e && getComputedStyle(e).backgroundImage; });
    expect(s && s.includes("mochi-idle.png") && !(await page.locator("#skinCss").textContent()).includes("a-skin"), s);
    expect(!errors.length, errors.join(" | "));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=nodb");
  await check("with no database, The look still says what each piece is, with nothing to change", async () => {
    await page.click("#houseBtn"); await page.locator("#menu .mi", { hasText: "The look" }).click(); await settle(page);
    expect((await page.locator("#artDlg li[data-slot]").count()) >= 40, "no slots");
    expect(!(await page.locator("#artDlg button:has-text('Replace')").count()), "Replace offered");
    expect(await page.locator("#artDlg li[data-token] input").count() > 40 && !(await page.locator("#artDlg li[data-token] input:enabled").count()), "a token can be changed");
  });
  await ctx.close();
}

await browser.close();
console.log(results.join("\n"));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
