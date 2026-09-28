// End-to-end test of the Catio page: adoption to resolution, sessions changing state, renames and
// moves, filing cabinets, rooms, the hotbar and the degraded views. Run it with catio/test/run.sh.
// The page runs inside the same skeleton the Artifact tool publishes, against runtime-stub.js: an
// in-memory db with live snapshots and a Claude Code Remote feed the test changes as it goes.
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT || "playwright");
const url = "file://" + join(here, ".page.html");
const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
let pass = 0, fail = 0;
const results = [];
async function check(name, fn) {
  try { await fn(); pass++; results.push("PASS " + name); }
  catch (e) { fail++; results.push("FAIL " + name + " :: " + String(e.message || e).split("\n")[0]); }
}
const expect = (cond, msg) => { if (!cond) throw new Error(msg); };
async function open(q = "", viewport = { width: 1280, height: 1000 }) {
  const ctx = await browser.newContext({ viewport });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url + q);
  await page.waitForTimeout(400);
  return { page, ctx, errors };
}
const T = (page, f) => page.evaluate(f);
const toast = async (page) => (await page.locator("#toast").textContent()) || "";
const needsText = async (page) => (await page.locator("#needs").innerText());

process.on("uncaughtException", (e) => { console.log(results.join("\n")); console.log("CRASH " + String(e.message).split("\n")[0]); process.exit(2); });
process.on("unhandledRejection", (e) => { console.log(results.join("\n")); console.log("CRASH " + String(e.message).split("\n")[0]); process.exit(2); });
/* ---------- 1. adoption to resolution, for an adopted chat ---------- */
{
  const { page, ctx, errors } = await open();
  await check("page boots with live sessions and no errors", async () => {
    expect(await page.locator("#chips .chip").count() === 10, "expected 10 room chips");
    expect((await page.locator("#status").innerText()).includes("Live"), "status is not live");
    expect(errors.length === 0, "page errors: " + errors.join("; "));
  });
  await check("the blocked session meows in the list and the scene", async () => {
    expect((await needsText(page)).includes("review the French text"), "needs list lacks the ask");
    expect(await page.locator('#cats .cat.m-meow').count() >= 1, "no meowing cat in the scene");
  });
  await check("old sleepers nap upstairs", async () => {
    expect((await page.locator("#upstairs").innerText()).includes("1 old or archived"), await page.locator("#upstairs").innerText());
  });

  await page.click("#adoptBtn");
  await check("Adopt a cat opens the form", async () => expect(await page.locator("#adoptDlg[open] #adTitle").isVisible(), "form not open"));
  await page.fill("#adTitle", "Lease renewal");
  await page.fill("#adLink", "https://claude.ai/chat/abc");
  await page.fill("#adProject", "Flat lease");
  await page.selectOption("#adRoom", "bedroom");
  await page.selectOption("#adMood", "needs");
  await page.fill("#adNote", "Send the signed form");
  await page.fill("#adName", "Mimi");
  await page.click('#adoptDlg button[type="submit"]');
  await page.waitForTimeout(150);
  await check("adopting writes one cats document with every field", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[1].startsWith("cats/")));
    expect(w.length === 1 && w[0][0] === "set", "writes: " + JSON.stringify(w));
    const d = w[0][2];
    for (const [k, v] of Object.entries({ title: "Lease renewal", link: "https://claude.ai/chat/abc", project: "Flat lease", room: "bedroom", mood: "needs", note: "Send the signed form", name: "Mimi" }))
      expect(d[k] === v, k + " = " + d[k]);
    expect(typeof d.adoptedAt === "number", "adoptedAt missing");
  });
  await check("the dialog closes and says Adopted", async () => {
    expect(!(await page.locator("#adoptDlg").evaluate((d) => d.open)), "dialog still open");
    expect((await toast(page)).includes("Adopted"), "toast: " + (await toast(page)));
  });
  await check("the new cat meows for you, in the bedroom, wearing its project", async () => {
    const t = await needsText(page);
    expect(t.includes("Mimi") && t.includes("Send the signed form") && t.includes("Flat lease") && t.includes("Bedroom"), t);
    const cat = page.locator('#cats .cat[aria-label^="Mimi "]');
    expect(await cat.count() === 1, "cat not in scene");
    expect((await cat.getAttribute("aria-label")).includes("Flat lease"), "no project in label");
    expect(await cat.locator(".emb").count() === 1, "no emblem");
    const lease = await cat.locator(".emb").evaluate((e) => getComputedStyle(e).getPropertyValue("--e").trim());
    expect(lease === "2", "lease should carry books, got " + lease);
    const tally = await page.locator("#tally li.need").innerText();
    expect(tally.includes("2 meowing"), tally);
  });

  // resolution, step 1: in progress
  await page.locator("#needs .item", { hasText: "Mimi" }).click();
  await check("opening the adopted cat shows its card with the ask", async () => {
    expect(await page.locator("#catDlg[open]").count() === 1, "card not open");
    expect((await page.locator("#catDlg").innerText()).includes("Send the signed form"), "ask missing");
  });
  await page.selectOption("#catDlg #adMood", "busy");
  await page.click('#catDlg button[type="submit"]');
  await page.waitForTimeout(150);
  await check("marking it in progress stops the meowing and puts it to work", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[0] === "update" && x[1].startsWith("cats/")));
    expect(w.length === 1 && w[0][2].mood === "busy", JSON.stringify(w));
    expect(!(await needsText(page)).includes("Mimi"), "still in the needs list");
    expect((await page.locator("#busy").innerText()).includes("Mimi"), "not in the at-work list");
    expect(await page.locator('#cats .cat.m-idle[aria-label^="Mimi "]').count() === 1, "scene cat is not working");
  });
  // resolution, step 2: done
  await page.click("#chips .chip:has-text('Bedroom')");
  await page.waitForTimeout(700);
  await page.locator('#cats .cat[aria-label^="Mimi "]').click();
  await page.selectOption("#catDlg #adMood", "done");
  await page.click('#catDlg button[type="submit"]');
  await page.waitForTimeout(150);
  await check("marking it done puts the cat to sleep", async () => {
    expect(await page.locator('#cats .cat.m-sleep[aria-label^="Mimi "]').count() === 1, "not asleep");
    expect(!(await page.locator("#busy").innerText()).includes("Mimi"), "still at work");
  });
  // resolution, step 3: let go
  await page.locator('#cats .cat[aria-label^="Mimi "]').click();
  await page.click("#catDlg button:has-text('Let go')");
  await check("letting go asks once more before deleting", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[0] === "delete"));
    expect(w.length === 0, "deleted without confirming");
    expect(await page.locator("#catDlg button:has-text('Yes, let this cat go')").count() === 1, "no confirm");
  });
  await page.click("#catDlg button:has-text('Yes, let this cat go')");
  await page.waitForTimeout(150);
  await check("letting go deletes the document and the cat leaves the house", async () => {
    const w = await T(page, () => window.__catio.writes.filter((x) => x[0] === "delete"));
    expect(w.length === 1 && w[0][1].startsWith("cats/"), JSON.stringify(w));
    expect(await page.locator('#cats .cat[aria-label^="Mimi "]').count() === 0, "cat still in scene");
    expect(!(await page.locator("#catDlg").evaluate((d) => d.open)), "card still open");
  });

  /* ---------- 2. resolution for a live Claude Code session ---------- */
  await page.click("#zoomOut");
  await page.waitForTimeout(700);
  await T(page, () => window.__catio.setBucket("blocked1", "WORKING", "RUNNING", {}));
  await page.waitForTimeout(100);
  await check("when you answer a session it stops meowing and gets to work", async () => {
    expect(!(await needsText(page)).includes("review the French text"), "still meowing");
    expect((await page.locator("#busy").innerText()).includes("Shop about page"), "not at work");
  });
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "IDLE", { status_category: "completed" }));
  await page.waitForTimeout(100);
  await check("when it finishes it falls asleep", async () => {
    expect(await page.locator('#cats .cat.m-sleep[aria-label*="Shop about page"]').count() === 1, "not asleep");
  });
  await T(page, () => window.__catio.setBucket("blocked1", "COMPLETED", "ARCHIVED", {}));
  await page.waitForTimeout(100);
  await check("when it is archived it goes upstairs", async () => {
    expect(await page.locator('#cats .cat[aria-label*="Shop about page"]').count() === 0, "still in the house");
    expect((await page.locator("#upstairs").innerText()).includes("2 old or archived"), await page.locator("#upstairs").innerText());
  });
  await T(page, () => window.__catio.setBucket("blocked1", "FAILED", "IDLE", { status_detail: "tests failed" }));
  await page.waitForTimeout(100);
  await check("a failed session is upset and counts as needing you", async () => {
    expect((await needsText(page)).includes("tests failed"), "not listed");
    expect((await page.locator("#tally").innerText()).includes("1 upset"), await page.locator("#tally").innerText());
  });

  /* ---------- 3. rename and move a session's cat ---------- */
  await page.click("#chips .chip:has-text('Kitchen')");
  await page.waitForTimeout(700);
  await page.locator('#cats .cat[aria-label*="Week tab editing"]').click();
  await page.fill("#catRename", "Biscuit");
  await page.selectOption("#catRoom", "study");
  await page.click("#catDlg button:has-text('Save')");
  await page.waitForTimeout(150);
  await check("renaming and moving a cat saves it and it walks to the study", async () => {
    const d = await T(page, () => window.__catio.store["sessions/session_work1"]);
    expect(d && d.name === "Biscuit" && d.room === "study", JSON.stringify(d));
    expect(await page.locator('#cats .cat[aria-label^="Biscuit "]').count() === 1, "renamed cat missing");
  });

  /* ---------- 4. filing cabinet and a project's look ---------- */
  await page.click("#chips .chip:has-text('Study')");
  await page.waitForTimeout(700);
  await page.click(".tag.files");
  await page.waitForTimeout(200);
  await check("the study's cabinet lists its projects, archived sessions included", async () => {
    const t = await page.locator("#roomsDlg").innerText();
    expect(t.includes("Filing cabinet") && t.includes("montfortoise-shopify") && t.includes("Intermarche-grocery-shopping-app"), t.slice(0, 300));
  });
  await page.selectOption("#em-montfortoise-shopify", "3");
  await page.selectOption("#coat-montfortoise-shopify", "5");
  await page.locator("#roomsDlg .proj", { hasText: "montfortoise-shopify" }).locator("button:has-text('Save look')").click();
  await page.waitForTimeout(150);
  await check("saving a look restyles every cat of that project", async () => {
    const d = await T(page, () => window.__catio.store["projects/montfortoise-shopify"]);
    expect(d && d.emblem === 3 && d.coat === 5, JSON.stringify(d));
    await page.keyboard.press("Escape");
    const e = await page.locator('#cats .cat[aria-label*="Shop about page"] .emb').evaluate((x) => getComputedStyle(x).getPropertyValue("--e").trim());
    expect(e === "3", "emblem " + e);
  });

  /* ---------- 5. rooms ---------- */
  await page.click("#roomsBtn");
  await page.fill("#rn-sunroom", "Conservatory");
  await page.fill("#rr-garden", "Pretty-Project-Portfolio");
  await page.click('#roomsDlg button[type="submit"]');
  await page.waitForTimeout(200);
  await check("renaming a room saves every room and relabels its chip", async () => {
    const n = await T(page, () => Object.keys(window.__catio.store).filter((k) => k.startsWith("rooms/")).length);
    expect(n === 9, "rooms saved: " + n);
    const g = await T(page, () => window.__catio.store["rooms/garden"]);
    expect(g.repos.join() === "Pretty-Project-Portfolio" && g.name === "Catio", JSON.stringify(g));
    expect(await page.locator("#chips .chip:has-text('Conservatory')").count() === 1, "chip not renamed");
  });

  /* ---------- 6. hotbar ---------- */
  await page.click("#soundBtn");
  await check("sound toggles on", async () => {
    expect((await page.locator("#soundBtn").getAttribute("aria-pressed")) === "true", "not pressed");
    expect((await page.locator("#soundLbl").innerText()) === "Sound on", "label");
  });
  await page.click("#chips .chip:has-text('Catio')");
  await page.waitForTimeout(700);
  await check("Whole house zooms back out", async () => {
    expect(!(await page.locator("#zoomOut").isDisabled()), "should be enabled in a room");
    await page.click("#zoomOut");
    await page.waitForTimeout(700);
    expect(await page.locator("#zoomOut").isDisabled(), "should be disabled at whole house");
  });
  await check("no page errors during the run", async () => expect(errors.length === 0, errors.join("; ")));
  await ctx.close();
}

/* ---------- 7. degraded views ---------- */
{
  const { page, ctx } = await open("?mode=noconn");
  await check("without the connector the page says what to do", async () => {
    const t = await page.locator("#status").innerText();
    expect(t.includes("isn't connected") && t.includes("Settings"), t);
  });
  await ctx.close();
}
{
  const { page, ctx } = await open("?mode=nodb");
  await page.click("#adoptBtn");
  await page.fill("#adTitle", "Anything");
  await page.click('#adoptDlg button[type="submit"]');
  await page.waitForTimeout(150);
  await check("without storage, adopting says it can't save", async () => expect((await toast(page)).includes("isn't available"), await toast(page)));
  await ctx.close();
}
{
  const { page, ctx } = await open();
  await T(page, () => { window.__catio.readOnly = true; });
  await page.click("#adoptBtn");
  await page.fill("#adTitle", "Anything");
  await page.click('#adoptDlg button[type="submit"]');
  await page.waitForTimeout(150);
  await check("a view-only visitor is told they can look but not change", async () => expect((await toast(page)).includes("look but not change"), await toast(page)));
  await ctx.close();
}
{
  const { page, ctx, errors } = await open("", { width: 390, height: 844 });
  await page.click("#adoptBtn");
  await check("on a phone the adopt form fits the screen", async () => {
    const box = await page.locator("#adoptDlg").boundingBox();
    expect(box.width <= 390 && box.x >= 0, JSON.stringify(box));
    expect(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "horizontal scroll");
    expect(errors.length === 0, errors.join("; "));
  });
  await ctx.close();
}

await browser.close();
console.log(results.join("\n"));
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
