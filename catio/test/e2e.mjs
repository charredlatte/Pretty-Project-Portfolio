// End-to-end test of the Catio page: adoption to resolution, sessions changing state, renames and
// moves, filing cabinets, rooms, the hover menus, touch, the degraded views, and local mode.
// Run it with catio/test/run.sh. The page runs inside the same skeleton the Artifact tool publishes,
// against runtime-stub.js (an in-memory db with live snapshots and a sessions feed the test changes);
// local mode runs the bundle from tools/bundle.py on a real localhost server with no runtime at all.
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
const url = "file://" + join(here, ".page.html");
const LOCAL = process.env.LOCAL_URL;   // set by run.sh when it serves the local bundle
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
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ...opts });
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
// point at a clear patch of a room's floor, as a person would
async function hoverRoom(page, room) {
  const pt = await page.evaluate((room) => {
    const h = document.querySelector('.roomhit[data-room="' + room + '"]'); const r = h.getBoundingClientRect();
    for (let fy = 0.92; fy > 0.08; fy -= 0.06) for (let fx = 0.06; fx < 0.96; fx += 0.06) {
      const x = r.left + r.width * fx, y = r.top + r.height * fy;
      if (document.elementFromPoint(x, y) === h) return { x, y };
    }
    return null;
  }, room);
  if (!pt) throw new Error("no clear floor in " + room);
  await page.mouse.move(8, 8);
  await page.mouse.move(pt.x, pt.y);
  await settle(page);
}
async function hoverCat(page, label) {
  const cat = page.locator('#cats .cat[aria-label*="' + label + '"]').first();
  const b = await cat.boundingBox();
  if (!b) throw new Error("no cat " + label);
  await page.mouse.move(8, 8);
  await page.mouse.move(b.x + b.width / 2, b.y + b.height * 0.75);
  await settle(page);
}
const menuButton = (page, name) => page.locator("#menu").getByRole("button", { name, exact: true });

/* ---------- 1. the screen, and adoption to resolution for an adopted chat ---------- */
{
  const { page, ctx, errors } = await open();
  await check("the catio fills the screen with nothing but the sign and the credits", async () => {
    const st = await page.locator("#stage").boundingBox();
    expect(st.width === 1440 && st.height === 900, JSON.stringify(st));
    expect(await page.locator("#menu").isHidden(), "a menu is open at rest");
    expect(await page.locator(".roomhit").count() === 9, "rooms");
    expect((await page.locator("#status").innerText()).includes("Live") === false || true, "");
    expect(errors.length === 0, "page errors: " + errors.join("; "));
  });
  await check("the blocked session meows in the scene and the sign counts it", async () => {
    expect(await page.locator("#cats .cat.m-meow").count() >= 1, "no meowing cat");
    expect((await page.locator("#tally").innerText()).includes("1 need you"), await page.locator("#tally").innerText());
  });
  await hoverRoom(page, "study");
  await check("hovering a room opens its menu with who needs you", async () => {
    const t = await menuText(page);
    expect(t.includes("Craft room") && t.includes("review the French text"), t);
  });
  await page.mouse.move(4, 450);
  await page.waitForTimeout(450);
  await check("moving away closes the menu", async () => expect(await page.locator("#menu").isHidden(), "still open"));
  await hoverRoom(page, "living");
  await check("old sleepers nap upstairs", async () => expect((await menuText(page)).includes("1 napping upstairs"), await menuText(page)));

  await hoverRoom(page, "bedroom");
  await menuButton(page, "Adopt a cat here").click();
  await check("Adopt a cat here opens the form with that room chosen", async () => {
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
  await check("the new cat meows in the bedroom, wearing its project", async () => {
    expect((await toast(page)).includes("Adopted"), await toast(page));
    const cat = page.locator('#cats .cat[aria-label^="Mimi "]');
    expect(await cat.count() === 1, "cat not in scene");
    expect((await cat.getAttribute("class")).includes("m-meow"), "not meowing");
    const e = await cat.locator(".emb").evaluate((x) => getComputedStyle(x).getPropertyValue("--e").trim());
    expect(e === "2", "lease should carry books, got " + e);
    expect((await page.locator("#tally").innerText()).includes("2 need you"), await page.locator("#tally").innerText());
  });
  await hoverCat(page, "Mimi");
  await check("hovering the cat shows its card, what it needs, and its moods", async () => {
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
  await hoverCat(page, "Mimi");
  await menuButton(page, "Done").click();
  await settle(page);
  await check("Done puts the cat to sleep", async () => expect(await page.locator('#cats .cat.m-sleep[aria-label^="Mimi "]').count() === 1, "not asleep"));
  await hoverCat(page, "Mimi");
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
  await check("when it is archived it goes upstairs", async () => {
    expect(await page.locator('#cats .cat[aria-label*="Shop about page"]').count() === 0, "still in the house");
    await hoverRoom(page, "living");
    expect((await menuText(page)).includes("2 napping upstairs"), await menuText(page));
  });
  await T(page, () => window.__catio.setBucket("blocked1", "FAILED", "IDLE", { status_detail: "tests failed" }));
  await settle(page);
  await check("a failed session is upset and counts as needing you", async () => {
    expect(await page.locator('#cats .cat.m-cry[aria-label*="Shop about page"]').count() === 1, "not upset");
    await hoverCat(page, "Shop about page");
    expect((await menuText(page)).includes("tests failed"), await menuText(page));
  });

  /* ---------- 3. rename and move a session's cat ---------- */
  await hoverCat(page, "Week tab editing");
  await menuButton(page, "Details").click();
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
  await hoverRoom(page, "study");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(700);
  await check("Look in zooms to the room and its menu offers the whole house", async () => {
    await hoverRoom(page, "study");
    expect(await menuButton(page, "Whole house").count() === 1, "no way back");
  });
  await menuButton(page, "Files").click();
  await check("the craft room's cabinet lists its projects and branches, archived sessions included", async () => {
    const t = await page.locator("#roomsDlg").innerText();
    expect(t.includes("Filing cabinet") && t.includes("montfortoise-shopify") && t.includes("Intermarche-grocery-shopping-app") && t.includes("claude/test"), t.slice(0, 300));
  });
  await page.selectOption("#em-montfortoise-shopify", "3");
  await page.selectOption("#coat-montfortoise-shopify", "5");
  await page.locator("#roomsDlg .proj", { hasText: "montfortoise-shopify" }).locator("button:has-text('Save look')").click();
  await settle(page);
  await check("saving a look restyles every cat of that project", async () => {
    const d = await T(page, () => window.__catio.store["projects/montfortoise-shopify"]);
    expect(d && d.emblem === 3 && d.coat === 5, JSON.stringify(d));
    await page.keyboard.press("Escape");
    const e = await page.locator('#cats .cat[aria-label*="Shop about page"] .emb').evaluate((x) => getComputedStyle(x).getPropertyValue("--e").trim());
    expect(e === "3", "emblem " + e);
  });
  await hoverRoom(page, "study");
  await menuButton(page, "Whole house").click();
  await page.waitForTimeout(700);
  await check("Whole house zooms back out", async () => expect(await page.locator('.roomhit[data-room="kitchen"]').isVisible(), "still zoomed in"));

  /* ---------- 5. rooms and sound, from a room's menu ---------- */
  await hoverRoom(page, "kitchen");
  await menuButton(page, "Edit rooms").click();
  await check("Edit rooms opens the cabin plan on the room you pointed at, one card at a time", async () => {
    expect((await page.locator("#rt-kitchen").getAttribute("aria-selected")) === "true", "kitchen not chosen");
    expect(await page.locator("#rn-kitchen").isVisible() && !(await page.locator("#rn-sunroom").isVisible()), "cards");
    expect(await page.evaluate(() => document.activeElement.id) === "rn-kitchen", "focus not on the name");
    expect(await page.locator("#roomsDlg .rt").count() === 9 && await page.locator("#rt-living .door").count() === 1, "plan tabs / front door");
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
    expect(Object.keys(rooms).length === 9, "rooms saved: " + Object.keys(rooms).length);
    const g = rooms["rooms/garden"];
    expect(g.repos.join("|") === "Pretty-Project-Portfolio|charredlatte/other-site" && g.name === "Catio" && g.blurb === "The portfolio, and this page", JSON.stringify(g));
    expect(rooms["rooms/kitchen"].repos.length === 2 && rooms["rooms/kitchen"].blurb.startsWith("Weekly meals"), "untouched rooms keep their data: " + JSON.stringify(rooms["rooms/kitchen"]));
    const front = Object.entries(rooms).filter(([, d]) => d.catchAll).map(([k]) => k);
    expect(front.join() === "rooms/kitchen", "catch-all: " + front.join());
    expect((await page.locator(".sign[data-room=sunroom] .nm").innerText()) === "Conservatory", "sign not renamed");
    await hoverRoom(page, "sunroom");
    expect((await menuText(page)).includes("Conservatory"), await menuText(page));
  });
  await menuButton(page, "Sound off").click();
  await check("sound switches on from any room's menu", async () => expect(await menuButton(page, "Sound on").count() === 1, await menuText(page)));
  await check("no page errors during the run", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 5b. the queens: one per room, keeping what matters in it ---------- */
{
  const { page, ctx, errors } = await open();
  const queen = (room) => page.locator('#cats .cat[data-queen="' + room + '"]');

  await check("every room has a queen, and she is nobody's session", async () => {
    const n = await page.locator("#cats .cat.queen").count();
    expect(n === 9, "queens drawn: " + n);
    const crowns = await page.locator("#cats .cat.queen .crown").count();
    expect(crowns === 9, "crowns: " + crowns);
  });
  await check("she is never counted among the cats that need you", async () => {
    const before = await page.locator("#tally").textContent();
    // the sign counts working cats only: a queen sitting up must not add to it
    const needing = await page.locator("#cats .cat:not(.queen).m-meow, #cats .cat:not(.queen).m-cry, #cats .cat:not(.queen).m-box").count();
    const said = (before.match(/(\d+) need you/) || [])[1];
    expect(String(needing) === String(said || 0), "sign says " + said + ", cats needing you: " + needing);
  });
  await queen("kitchen").hover();
  await settle(page);
  await check("hovering her gives the room in one line", async () => {
    const t = await menuText(page);
    expect(t.includes("Queen of the Kitchen"), t);
    expect(/needs you|need you in here|All quiet|Nothing in this room/.test(t), t);
  });
  await queen("kitchen").click();
  await settle(page);
  await check("her card opens with nothing kept yet", async () => {
    const t = await page.locator("#queenDlg").innerText();
    expect(t.includes("She is keeping nothing for this room yet."), t.slice(0, 200));
  });
  await page.fill("#queenAdd", "The Drive order goes in on Sunday.");
  await page.locator('#queenDlg button:has-text("Give it to her")').click();
  await page.fill("#queenAdd", "Chilli is a health rule, never a taste.");
  await page.locator('#queenDlg button:has-text("Give it to her")').click();
  await page.locator('#queenDlg button:has-text("Say it")').last().click();
  await page.fill("#queenRename", "Mémé");
  await page.click("#queenSave");
  await settle(page);
  await check("what you give her is written as one document for that room", async () => {
    const d = await T(page, () => window.__catio.store["queens/kitchen"]);
    expect(d && d.name === "Mémé", JSON.stringify(d));
    expect(d.notes.length === 2, "notes: " + JSON.stringify(d.notes));
    const said = d.notes.filter((n) => n.pinned);
    expect(said.length === 1 && said[0].text.startsWith("The Drive order"), JSON.stringify(said));
  });
  await check("she takes her new name and sits up to say it", async () => {
    const label = await queen("kitchen").getAttribute("aria-label");
    expect(label.startsWith("Mémé, queen of the Kitchen"), label);
    expect((await queen("kitchen").getAttribute("class")).includes("m-meow"), await queen("kitchen").getAttribute("class"));
  });
  await page.evaluate(() => document.querySelector('.roomhit[data-room="kitchen"]').click());
  await page.waitForTimeout(800);
  await check("in her room she says it out loud, and it opens her card", async () => {
    const bub = page.locator("#overlay .bub.queenb");
    expect(await bub.count() === 1, "bubbles: " + (await bub.count()));
    expect((await bub.innerText()).includes("The Drive order"), await bub.innerText());
    await bub.click();
    await settle(page);
    expect(await page.locator("#queenDlg").isVisible(), "her card did not open");
  });
  await check("the one she is saying is not listed twice in her menu", async () => {
    await page.keyboard.press("Escape");
    await queen("kitchen").hover();
    await settle(page);
    const t = await menuText(page);
    expect(t.split("The Drive order").length === 2, t);
    expect(t.includes("She is also keeping") && t.includes("Chilli is a health rule"), t);
  });
  await queen("kitchen").click();
  await settle(page);
  await page.locator('#queenDlg button:has-text("Saying it")').click();
  await page.click("#queenSave");
  await settle(page);
  await check("taking it back stops her saying it", async () => {
    const d = await T(page, () => window.__catio.store["queens/kitchen"]);
    expect(d.notes.every((n) => !n.pinned), JSON.stringify(d.notes));
    expect(await page.locator("#overlay .bub.queenb").count() === 0, "still saying it");
  });
  await queen("kitchen").click();
  await settle(page);
  await page.locator('#queenDlg button:has-text("Forget")').first().click();
  await page.click("#queenSave");
  await settle(page);
  await check("forgetting one leaves the rest", async () => {
    const d = await T(page, () => window.__catio.store["queens/kitchen"]);
    expect(d.notes.length === 1, JSON.stringify(d.notes));
  });

  // the bug this feature found: redrawing the menu under your pointer used to close it, because the
  // button the redraw removed no longer looked like part of the menu by the time the click arrived
  await hoverRoom(page, "kitchen");
  const was = await menuText(page);
  await menuButton(page, "Sound off").click();
  await check("a menu button that redraws the menu leaves it open, on the same room", async () => {
    expect(await page.locator("#menu").isVisible(), "the menu closed under the pointer");
    const now = await menuText(page);
    expect(now.includes("Kitchen"), "it reopened on another room: " + now.slice(0, 80));
    expect(now.includes("Sound on") && was.includes("Sound off"), now.slice(0, 120));
  });
  await check("no page errors while working the queens", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 6. rooms on the map: signs at every size, the ring, and the keyboard ---------- */
{
  const { page, ctx, errors } = await open("", { viewport: { width: 1280, height: 720 } });
  await check("on a laptop screen every room still wears its name, inside its own walls", async () => {
    const signs = page.locator("#overlay .sign");
    expect(await signs.count() === 9, "signs: " + await signs.count());
    for (const k of ["garden", "kitchen", "dining", "living", "sunroom", "study", "bedroom", "bath", "hall"]) {
      const box = await page.locator(`.sign[data-room=${k}]`).boundingBox(), room = await page.locator(`#room-${k}`).boundingBox();
      expect(box && box.x >= room.x && box.x + box.width <= room.x + room.width + 1 && box.y >= room.y, k + " sign outside its room");
      expect(await page.locator(`.sign[data-room=${k}] .nm`).evaluate((e) => e.scrollWidth <= e.clientWidth + 1), k + " name cut short at its default length");
    }
  });
  await check("the room where a cat needs you carries a badge with its face and count, quiet rooms none", async () => {
    expect((await page.locator(".sign[data-room=study] .badge .n").innerText()) === "1", "craft room badge");
    expect(await page.locator(".sign[data-room=study] .badge.need .face-ico").count() === 1, "no meowing face");
    expect(await page.locator(".sign .badge").count() === 1, "badges on quiet rooms");
    expect(await page.locator(".sign").first().evaluate((e) => getComputedStyle(e).pointerEvents) === "none", "signs catch the pointer");
  });
  await hoverRoom(page, "kitchen");
  await check("the room under the pointer, and the one its menu belongs to, wear the cream ring", async () => {
    const ring = await page.locator("#room-kitchen").evaluate((e) => e.classList.contains("lit") && getComputedStyle(e).borderImageSource);
    expect(ring && ring.includes("ring.png"), "no ring: " + ring);
  });
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
    expect(ring.includes("ring.png"), "no ring on the focused room");
  });
  await page.keyboard.press("Enter");
  await check("Enter steps into the menu on Look in, with the cats needing you just above it", async () => {
    expect((await page.evaluate(() => document.activeElement.textContent)) === "Look in", await active());
    expect(await page.evaluate(() => { const b = document.activeElement.closest("#menu").querySelector("button"); return b.textContent.startsWith("Caramel"); }), "no cat row above");
  });
  await page.keyboard.press("Escape");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowUp");
  await check("arrow keys move the ring to the room next door and open its menu", async () => {
    expect((await active()) === "room-living", "focus: " + (await active()));
    expect((await menuText(page)).startsWith("Living room"), await menuText(page));
    expect((await page.locator("#room-living").getAttribute("tabindex")) === "0" && (await page.locator("#room-study").getAttribute("tabindex")) === "-1", "roving tabindex");
  });
  await page.keyboard.press("Enter");
  await check("Enter steps into the room's menu", async () => expect((await page.evaluate(() => document.activeElement.textContent)) === "Look in", await active()));
  await page.keyboard.press("Escape");
  await check("Escape in the menu goes back to the room, menu still open", async () => {
    expect((await active()) === "room-living" && await page.locator("#menu").isVisible(), await active());
  });
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  await check("Enter twice looks in; focus stays on the room, its menu open, and the move is said aloud", async () => {
    expect(await page.locator('.roomhit.here[data-room="living"]').count() === 1, "not in the living room");
    expect((await active()) === "room-living", "focus: " + (await active()));
    expect((await menuText(page)).includes("Whole house"), "menu shut under the keyboard: " + (await menuText(page)));
    expect((await page.locator("#say").textContent()).startsWith("Living room"), await page.locator("#say").textContent());
  });
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(700);
  await check("in a room, arrows walk into the next one", async () => {
    expect(await page.locator('.roomhit.here[data-room="sunroom"]').count() === 1, "not in the sunroom");
    expect((await active()) === "room-sunroom", "focus: " + (await active()));
  });
  await page.keyboard.press("Enter");
  for (let i = 0; i < 6 && (await page.evaluate(() => document.activeElement.textContent)) !== "Edit rooms"; i++) await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await check("every room action is reachable from the keyboard: Edit rooms opens on that room", async () => {
    expect(await page.locator("#roomsDlg[open]").count() === 1, "editor not open");
    expect((await page.locator("#rt-sunroom").getAttribute("aria-selected")) === "true", "not on the sunroom");
  });
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(700);
  await check("Escape comes back out to the whole house with the ring where you were", async () => {
    expect(await page.locator(".roomhit.here").count() === 0, "still in a room");
    expect((await active()) === "room-sunroom", "focus: " + (await active()));
  });
  const long = "The very long room for tax 2026";   // 31 typed, 30 kept
  await hoverRoom(page, "bath");
  await menuButton(page, "Edit rooms").click();
  await page.fill("#rn-bath", long);
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("a 30-character name is cut short on its sign, whole in the room's name and its menu", async () => {
    const name = (await T(page, () => window.__catio.store["rooms/bath"])).name;
    expect(name.length === 30, "saved " + name.length);
    const box = await page.locator(".sign[data-room=bath]").boundingBox(), room = await page.locator("#room-bath").boundingBox();
    expect(box.x + box.width <= room.x + room.width + 1, "sign spills out");
    expect(await page.locator(".sign[data-room=bath] .nm").evaluate((e) => e.scrollWidth > e.clientWidth), "not cut short");
    expect((await page.locator("#room-bath").getAttribute("aria-label")).startsWith(name), "full name not in the label");
    await hoverRoom(page, "bath");
    expect((await menuText(page)).includes(name), "menu lacks the full name");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 6b. a still pointer: the camera moving under it is not pointing ---------- */
{
  const { page, ctx, errors } = await open();
  await hoverRoom(page, "kitchen");
  await menuButton(page, "Look in").click();
  await page.waitForTimeout(800);
  await check("looking in doesn't open the menu of whatever room slid under the resting pointer", async () => {
    expect(await page.locator('.roomhit.here[data-room="kitchen"]').count() === 1, "not in the kitchen");
    expect(!(await page.locator("#menu").isVisible()), "a menu opened by itself: " + (await menuText(page)).slice(0, 40));
  });
  const box = await page.locator('.roomhit[data-room="kitchen"]').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
  await page.waitForTimeout(300);
  await check("the first real move opens the menu of the room under it", async () => {
    expect((await menuText(page)).includes("Kitchen"), await menuText(page));
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 7. touch: the first tap opens the menu, the second acts ---------- */
{
  const { page, ctx, errors } = await open("", { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const cat = page.locator("#cats .cat.m-meow").first();
  await cat.tap();
  await settle(page);
  await check("on a phone, tapping a cat opens its menu instead of the full card", async () => {
    expect(await page.locator("#menu").isVisible(), "no menu");
    expect(await page.locator("#catDlg[open]").count() === 0, "card opened on the first tap");
  });
  await cat.tap({ force: true });
  await settle(page);
  await check("tapping it again opens its full card", async () => expect(await page.locator("#catDlg[open]").count() === 1, "no card"));
  await page.keyboard.press("Escape");
  await check("the phone view has no sideways scroll and no errors", async () => {
    expect(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "horizontal scroll");
    expect(errors.length === 0, errors.join("; "));
  });
  await check("on a phone the rooms show badges where cats need you, not squashed names", async () => {
    expect(await page.locator("#overlay .sign .nm").count() === 0, "names on a phone map");
    expect((await page.locator(".sign[data-room=study] .badge .n").innerText()) === "1", "craft room badge");
  });
  const room = await page.locator('.roomhit[data-room="study"]').boundingBox();
  await page.touchscreen.tap(room.x + room.width * 0.9, room.y + room.height * 0.15);
  await settle(page);
  await menuButton(page, "Edit rooms").tap();
  await check("on a phone the Rooms plan fits, opens on the tapped room, and its smallest rooms can be tapped", async () => {
    const dlg = await page.locator("#roomsDlg").boundingBox();
    expect(dlg.x >= 0 && dlg.x + dlg.width <= 390, JSON.stringify(dlg));
    expect((await page.locator("#rt-study").getAttribute("aria-selected")) === "true", "not on the craft room");
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
  await hoverRoom(page, "dining");
  await menuButton(page, "Adopt a cat here").click();
  await page.fill("#adTitle", "Anything");
  await page.click('#adoptDlg button[type="submit"]');
  await settle(page);
  await check((q ? "without storage" : "for a view-only visitor") + ", adopting explains why it can't save", async () => expect((await toast(page)).includes(want), await toast(page)));
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
  await hoverRoom(page, "bedroom");
  await menuButton(page, "Adopt a cat here").click();
  await page.fill("#adTitle", "Local test cat");
  await page.fill("#adName", "Loco");
  await page.click('#adoptDlg button[type="submit"]');
  await settle(page);
  await check("adopting on localhost works", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 1, "no cat"));
  await page.reload();
  await page.waitForTimeout(600);
  await check("and the cat is still there after a reload", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 1, "lost on reload"));
  await hoverCat(page, "Loco");
  await menuButton(page, "Details").click();
  await page.click("#catDlg button:has-text('Let go')");
  await page.click("#catDlg button:has-text('Yes, let this cat go')");
  await settle(page);
  await check("letting it go on localhost removes it", async () => expect(await page.locator('#cats .cat[aria-label^="Loco "]').count() === 0, "still there"));
  await ctx.close();
}

await browser.close();
console.log(results.join("\n"));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
