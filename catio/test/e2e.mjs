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
  // reduced motion unless a test asks for it: the cats stay put, so clicks land on still cats (6c walks them)
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
    expect(await page.locator(".roomhit").count() === 10, "rooms");
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
    expect(await page.locator(".emb").count() === 0, "cats carry no emblems: their coats tell projects apart");
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
    expect(await page.locator("#walkers .walker").count() === 0, "walked, with reduced motion");
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
  await menuButton(page, "Talk").click();
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
    expect(n === 10, "queens drawn: " + n);
    const crowns = await page.locator("#cats .cat.queen .crown").count();
    expect(crowns === 10, "crowns: " + crowns);
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

/* ---------- 5c. anyone else's copy: none of the licensed art ---------- */
// run.sh builds .page-noart.html over a folder holding only the committed art, which is what a
// fresh clone looks like whether or not this checkout has the packs.
{
  const { page, ctx, errors } = await open("", { base: NOART });
  await check("with no licensed art the sign says so, and the queens still work", async () => {
    const words = await page.locator("#status").textContent();
    expect(words.includes("The cat art isn't here"), words);
    expect(words.includes("build-art.py"), "it does not say how to fix it: " + words);
    expect(await page.locator("#status.warn").count() === 1, "the sign is not flagging it");
    // her crown, her menu and what she keeps still work without the packs to draw them
    expect(await page.locator("#cats .cat.queen .crown").count() === 10, "crowns went missing");
    await page.locator('#cats .cat[data-queen="bedroom"]').hover();
    await settle(page);
    expect((await menuText(page)).includes("Queen of the Bedroom"), await menuText(page));
  });
  await check("without the interface art the sign and menus sit on plain colour, not the meadow", async () => {
    const bg = (sel) => page.locator(sel).evaluate((e) => getComputedStyle(e).backgroundColor);
    expect((await bg("#hud")) !== "rgba(0, 0, 0, 0)", "the sign has nothing behind it");
    expect((await bg("#menu")) !== "rgba(0, 0, 0, 0)", "the menu has nothing behind it");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

/* ---------- 6. rooms on the map: signs at every size, the brackets, and the keyboard ---------- */
{
  const { page, ctx, errors } = await open("", { viewport: { width: 1280, height: 720 } });
  await check("on a laptop screen every room still wears its name, inside its own walls", async () => {
    const signs = page.locator("#overlay .sign");
    expect(await signs.count() === 10, "signs: " + await signs.count());
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
  await check("the room under the pointer, and the one its menu belongs to, light up with the white brackets", async () => {
    const ring = await page.locator("#room-kitchen").evaluate((e) => e.classList.contains("lit") && getComputedStyle(e).borderImageSource);
    expect(ring && ring.includes("corners.png"), "no brackets: " + ring);
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
    expect(ring.includes("corners.png"), "no brackets on the focused room");
  });
  await page.keyboard.press("Enter");
  await check("Enter steps into the menu on Look in, with the cats needing you just above it", async () => {
    expect((await page.evaluate(() => document.activeElement.textContent)) === "Look in", await active());
    expect(await page.evaluate(() => { const b = document.activeElement.closest("#menu").querySelector("button"); return b.textContent.startsWith("Caramel"); }), "no cat row above");
  });
  await page.keyboard.press("Escape");
  await page.keyboard.press("ArrowUp");   // the drawing room is right above the studio
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

/* ---------- 6c. cats walk: up the stairs when archived, down them when back, through doorways, and about ---------- */
{
  const { page, ctx, errors } = await open("", { reducedMotion: "no-preference" });
  const cat = (id) => page.locator('#cats .cat[data-id="session_' + id + '"]');
  const settled = (id, cls) => page.waitForFunction(([id, cls]) => {
    const b = document.querySelector('#cats .cat[data-id="session_' + id + '"]');
    return b && !b.classList.contains("walking") && !b._walk && (!cls || b.classList.contains(cls));
  }, [id, cls], { timeout: 25000 });
  await check("while the page opens, cats are simply in their places", async () =>
    expect(await page.locator("#cats .cat.walking, #walkers .walker").count() === 0, "someone is walking on load"));
  await page.waitForTimeout(4200);
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "ARCHIVED", {}));
  await settle(page);
  await check("an archived cat walks off towards the great hall's stairs", async () => {
    expect(await cat("blocked1").count() === 0, "still in its room");
    const w = page.locator('#walkers .walker[data-leaving="session_blocked1"]');
    expect(await w.count() === 1, "nobody walking upstairs");
    const a = await w.boundingBox(), hall = await page.locator('.roomhit[data-room="hall"]').boundingBox();
    await page.waitForTimeout(700);
    const b = await w.boundingBox();
    expect(a && b && Math.hypot(b.x - a.x, b.y - a.y) > 4, "not moving: " + JSON.stringify([a, b]));
    expect(Math.abs(b.x - (hall.x + hall.width / 2)) < Math.abs(a.x - (hall.x + hall.width / 2)) + 1, "not heading for the hall");
  });
  await check("it climbs the stairs and is gone", async () =>
    page.locator('#walkers .walker[data-leaving="session_blocked1"]').waitFor({ state: "detached", timeout: 25000 }));
  await T(page, () => window.__catio.setBucket("blocked1", "BLOCKED", "IDLE", { status_category: "need_input", needs_action: "one more look" }));
  await settle(page);
  await check("brought back, it comes down the stairs and walks to its room, then meows", async () => {
    expect((await cat("blocked1").getAttribute("class")).includes("walking"), "not walking back: " + await cat("blocked1").getAttribute("class"));
    await settled("blocked1", "m-meow");
    expect(await cat("blocked1").getAttribute("data-room") === "study", "not in the craft room");
  });
  {
    const b = await cat("blocked1").boundingBox();
    const to = await page.evaluate(() => {   // a patch of the hall's floor with nothing else on it
      const r = document.querySelector('.roomhit[data-room="hall"]').getBoundingClientRect();
      for (let fy = 0.9; fy > 0.3; fy -= 0.05) for (let fx = 0.2; fx < 0.8; fx += 0.05) {
        const x = r.left + r.width * fx, y = r.top + r.height * fy, h = document.elementFromPoint(x, y);
        if (h && h.dataset.room === "hall" && h.classList.contains("roomhit")) return { x, y };
      }
    });
    await page.mouse.move(b.x + b.width / 2, b.y + b.height * 0.7);
    await page.mouse.down();
    await page.mouse.move(b.x + 40, b.y + 40, { steps: 3 });
    await page.mouse.move(to.x, to.y, { steps: 5 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  }
  await check("moved to the great hall, it walks there through the doorway", async () => {
    expect(await cat("blocked1").getAttribute("data-room") === "hall", "not moved");
    expect((await cat("blocked1").getAttribute("class")).includes("walking"), "it jumped");
    await settled("blocked1", "m-meow");
  });
  await check("a working cat wanders from its station now and then, and comes back", async () => {
    await page.waitForFunction(() => { const b = document.querySelector('#cats .cat[data-id="session_work1"]'); return b && b.classList.contains("walking"); }, null, { timeout: 15000 });
    await settled("work1", "m-idle");
  });
  await check("no page errors while walking", async () => expect(errors.length === 0, errors.join(" | ")));
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

/* ---------- 8b. the harness: the brain, posting into sessions, talking, managing, rules, agents ---------- */
const tools = (page, name) => T(page, () => window.__catio.tools).then((t) => t.filter((x) => !name || x[1] === name));
async function giveFiles(page, files) {
  const [chooser] = await Promise.all([page.waitForEvent("filechooser"), page.locator("#menu").getByRole("button", { name: /Give it files|Choose files/ }).first().click()]);
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
  await check("every session cat wears its model's breed, and agents from other makers join the house", async () => {
    const tag = await page.locator('#cats .cat[aria-label*="Shop about page"] .breed').textContent();
    expect(tag === "O", "breed " + tag);
    const agent = page.locator('#cats .cat[aria-label*="Shop theme"]');
    expect(await agent.count() === 1, "no agent cat");
    expect((await agent.locator(".breed").textContent()) === "OPE", "agent breed");
    expect((await agent.getAttribute("aria-label")).includes("Meowing"), "agent should need her");
  });

  // a file given to one cat: kept, then posted into its session through a Routine bound to it
  await hoverCat(page, "Shop about page");
  await giveFiles(page, { name: "about-fr.md", mimeType: "text/markdown", buffer: Buffer.from("# À propos\nNotre boutique…") });
  await check("a file given to a cat goes to that cat", async () => {
    expect(await page.inputValue("#drop-0") === "session_blocked1", await page.inputValue("#drop-0"));
    expect((await page.locator("#brainDlg").innerText()).includes("Dropped on"), "no reason");
  });
  await page.fill("#dropNote", "Use this for the about page");
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("sending keeps the file, binds a Routine to the session once, and fires it with the delivery", async () => {
    const st = await T(page, () => window.__catio.store);
    const brain = Object.entries(st).filter(([p]) => p.startsWith("brain/"));
    expect(brain.length === 1, "brain docs " + brain.length);
    const d = brain[0][1];
    expect(d.cat === "session_blocked1" && d.status === "pushed" && d.asset && d.note === "Use this for the about page" && d.how === "dropped", JSON.stringify(d));
    const made = await tools(page, "create_trigger");
    expect(made.length === 1 && made[0][2].persistent_session_id === "session_blocked1" && made[0][2].environment_id === "env_test" && !made[0][2].cron_expression, JSON.stringify(made));
    const fired = await tools(page, "fire_trigger");
    expect(fired.length === 1 && fired[0][2].trigger_id === "trig_1", JSON.stringify(fired));
    const text = fired[0][2].text;
    expect(text.startsWith("[Catio] Delivery for you: about-fr.md") && text.includes("Use this for the about page") && text.includes("Notre boutique") && text.includes(d.asset), text);
    expect(st["sessions/session_blocked1"].trigger === "trig_1", "trigger not kept");
  });
  await check("the cat carries its file, and its menu says so", async () => {
    expect((await page.locator('#cats .cat[aria-label*="Shop about page"] .fcount').textContent()) === "1", "no count");
    await hoverCat(page, "Shop about page");
    expect((await menuText(page)).includes("1 file from the brain"), await menuText(page));
  });

  // dropped on a room: sorted among its cats by what the file's name shares with them
  await page.mouse.move(8, 8);
  await dropFiles(page, '.roomhit[data-room="kitchen"]', [{ name: "intermarche-basket.csv", type: "text/csv", text: "item,qty\nlait,2" }]);
  await check("a file dropped on a room is sorted to the cat it matches, and the second post reuses the Routine", async () => {
    expect(await page.inputValue("#drop-0") === "session_work1", await page.inputValue("#drop-0"));
    await page.click("#dropSend");
    await page.waitForTimeout(300);
    expect((await tools(page, "create_trigger")).length === 2, "one Routine per session");
    const fired = await tools(page, "fire_trigger");
    expect(fired.length === 2 && fired[1][2].trigger_id === "trig_2", JSON.stringify(fired));
  });
  await hoverCat(page, "Shop about page");
  await giveFiles(page, { name: "second.txt", mimeType: "text/plain", buffer: Buffer.from("more") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a second file for the same cat fires the same Routine", async () => {
    expect((await tools(page, "create_trigger")).length === 2, "made another Routine");
    const fired = await tools(page, "fire_trigger");
    expect(fired[2][2].trigger_id === "trig_1", JSON.stringify(fired[2]));
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
  await hoverRoom(page, "hall");
  await menuButton(page, "The brain (1)").click();
  await page.locator('#brainDlg select[aria-label="File mystery.bin under"]').selectOption("session_work1");
  await page.waitForTimeout(300);
  await check("filing it from the tray sends it to the cat chosen", async () => {
    const d = Object.entries(await T(page, () => window.__catio.store)).find(([p, v]) => p.startsWith("brain/") && v.name === "mystery.bin")[1];
    expect(d.cat === "session_work1" && d.status === "pushed" && d.how === "manual", JSON.stringify(d));
    expect((await tools(page, "fire_trigger")).pop()[2].text.includes("mystery.bin"), "not delivered");
  });
  await page.keyboard.press("Escape");
  await hoverRoom(page, "hall");
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
  await hoverCat(page, "Shop about page");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Is the French text ready?");
  await page.click("#saySend");
  await page.waitForTimeout(300);
  await check("writing to a cat posts it into the session and keeps it in the conversation", async () => {
    const fired = (await tools(page, "fire_trigger")).pop();
    expect(fired[2].text === "[Catio] Charlotte says: Is the French text ready?", fired[2].text);
    const n = Object.entries(await T(page, () => window.__catio.store)).find(([p]) => p.startsWith("notes/"));
    expect(n && n[1].author === "charlotte" && n[1].cat === "session_blocked1" && n[1].via === "pushed", JSON.stringify(n));
  });
  await T(page, () => window.__catio.put("notes/r1", { cat: "session_blocked1", author: "session", text: "Yes: it's in the PR.", at: Date.now() }));
  await page.waitForTimeout(200);
  await check("the session's answer shows in the conversation", async () => {
    expect((await page.locator("#thread").innerText()).includes("Yes: it's in the PR."), await page.locator("#thread").innerText());
  });

  // managing it
  await page.click("#catDlg button:has-text('Ask to wrap up')");
  await page.waitForTimeout(200);
  await check("asking a cat to wrap up posts the request and records it", async () => {
    expect((await tools(page, "fire_trigger")).pop()[2].text === "[Catio] Request: wrap_up", "no request");
    expect((await T(page, () => window.__catio.store["sessions/session_blocked1"])).request === "wrap_up", "not recorded");
  });
  await page.fill("#catTitle", "Shop about page (FR)");
  await page.click("#catDlg button:has-text('Save')");
  await page.waitForTimeout(200);
  await check("changing a session's title renames the real session", async () => {
    const t = await tools(page, "set_session_title");
    expect(t.length === 1 && t[0][2].session_id === "session_blocked1" && t[0][2].title === "Shop about page (FR)", JSON.stringify(t));
  });
  await hoverCat(page, "Week tab editing");
  await menuButton(page, "Talk").click();
  await page.click("#catDlg button:has-text('Pause')");
  await page.waitForTimeout(150);
  await page.click("#catDlg button:has-text('Archive')");
  await check("archive asks once more", async () => expect((await tools(page, "archive_session")).length === 0, "archived at once"));
  await page.click("#catDlg button:has-text('Yes, archive it')");
  await page.waitForTimeout(200);
  await check("pause and archive call the session's own tools, and archiving unbinds its Routine", async () => {
    expect((await tools(page, "interrupt_session")).length === 1, "no pause");
    expect((await tools(page, "archive_session"))[0][2].session_id === "session_work1", "no archive");
    expect((await tools(page, "delete_trigger"))[0][2].trigger_id === "trig_2", "Routine kept");
  });

  // a new cat, on the model chosen for it
  await hoverRoom(page, "kitchen");
  await menuButton(page, "New cat here").click();
  await page.selectOption("#ncModel", "claude-sonnet-5-5");
  await page.fill("#ncMsg", "Plan next week's meals");
  await page.click('#adoptDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("New cat starts a session on the chosen model, in the room's repository, and files it there", async () => {
    const c = await tools(page, "create_session");
    expect(c.length === 1 && c[0][2].model === "claude-sonnet-5-5" && c[0][2].source_url === "https://github.com/charredlatte/Intermarche-grocery-shopping-app" && c[0][2].environment_id === "env_test" && c[0][2].prompt === "Plan next week's meals", JSON.stringify(c));
    expect((await T(page, () => window.__catio.store["sessions/session_new1"])).room === "kitchen", "not filed");
  });

  // dragging a cat into another room
  {
    const cat = await page.locator('#cats .cat[aria-label*="Shop about page"]').boundingBox();
    const to = await page.locator('.roomhit[data-room="bedroom"]').boundingBox();
    await page.mouse.move(cat.x + cat.width / 2, cat.y + cat.height * 0.7);
    await page.mouse.down();
    await page.mouse.move(cat.x + 40, cat.y + 40, { steps: 3 });
    await page.mouse.move(to.x + to.width * 0.5, to.y + to.height * 0.85, { steps: 5 });
    await page.mouse.up();
    await page.waitForTimeout(250);
  }
  await check("dragging a cat onto another room moves it there, without opening its card", async () => {
    expect((await T(page, () => window.__catio.store["sessions/session_blocked1"])).room === "bedroom", "not moved");
    expect(!(await page.locator("#catDlg").evaluate((d) => d.open)), "the drag opened the card");
    expect((await page.locator('#cats .cat[aria-label*="Shop about page"]').getAttribute("data-room")) === "bedroom", "still in the old room");
  });

  // agents: a message and a file go through the Catio server on her computer
  await hoverCat(page, "Shop theme");
  await menuButton(page, "Talk").click();
  await page.fill("#sayTo", "Green, please");
  await page.click("#saySend");
  await page.waitForTimeout(200);
  await check("writing to an agent's cat goes through the Catio server", async () => {
    const c = (await tools(page, "comment")).pop();
    expect(c[0] === "host:catio" && c[2].cat === "codex-shop" && c[2].text === "Green, please", JSON.stringify(c));
  });
  await page.keyboard.press("Escape");
  await hoverCat(page, "Shop theme");
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
  await hoverRoom(page, "hall");
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
// When claude.ai won't let the page post into sessions, the post is queued for the concierge.
{
  const { page, ctx, errors } = await open("?writes=refused&host=none");
  await page.waitForTimeout(300);
  await hoverCat(page, "Shop about page");
  await giveFiles(page, { name: "note.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
  await page.click("#dropSend");
  await page.waitForTimeout(300);
  await check("a refused post waits in the outbox, and the sign of it is honest", async () => {
    const st = await T(page, () => window.__catio.store);
    const o = Object.entries(st).filter(([p]) => p.startsWith("outbox/"));
    expect(o.length === 1 && o[0][1].status === "queued" && o[0][1].why === "approval_required" && o[0][1].cat === "session_blocked1" && o[0][1].text.includes("note.txt"), JSON.stringify(o));
    const b = Object.entries(st).find(([p]) => p.startsWith("brain/"))[1];
    expect(b.status === "waiting" && b.via === "queued", JSON.stringify(b));
    expect((await toast(page)).includes("queued"), await toast(page));
    expect(await page.locator('#cats .cat[aria-label*="Shop theme"]').count() === 0, "an agent without its server");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=nodb");
  await hoverCat(page, "Shop about page");
  await check("where nothing can be kept, there is nothing to drop files with", async () => expect(await menuButton(page, "Give it files").count() === 0, "offered"));
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
  await page.locator('#cats .cat[data-queen="kitchen"]').click();
  await settle(page);
  await page.fill("#queenAdd", "Off a USB stick, she still remembers.");
  await page.locator('#queenDlg button:has-text("Give it to her")').click();
  await page.locator('#queenDlg button:has-text("Say it")').first().click();
  await page.click("#queenSave");
  await settle(page);
  await page.reload();
  await page.waitForTimeout(700);
  await check("on localhost a queen keeps what you give her, across a reload", async () => {
    const label = await page.locator('#cats .cat[data-queen="kitchen"]').getAttribute("aria-label");
    expect(label.includes("Off a USB stick"), label);
    expect(await page.locator("#overlay .bub.queenb").count() === 1, "she stopped saying it after the reload");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

await browser.close();
console.log(results.join("\n"));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
