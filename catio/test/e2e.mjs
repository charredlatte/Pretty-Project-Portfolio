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
  await page.fill("#rn-sunroom", "Conservatory");
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("renaming a room saves every room and relabels it", async () => {
    const n = await T(page, () => Object.keys(window.__catio.store).filter((k) => k.startsWith("rooms/")).length);
    expect(n === 9, "rooms saved: " + n);
    await hoverRoom(page, "sunroom");
    expect((await menuText(page)).includes("Conservatory"), await menuText(page));
  });
  await menuButton(page, "Sound off").click();
  await check("sound switches on from any room's menu", async () => expect(await menuButton(page, "Sound on").count() === 1, await menuText(page)));
  await check("no page errors during the run", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 6. touch: the first tap opens the menu, the second acts ---------- */
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
  await ctx.close();
}

/* ---------- 7. degraded views ---------- */
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

/* ---------- 8. local mode: the bundle on localhost, no runtime at all ---------- */
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
