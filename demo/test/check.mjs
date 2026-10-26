// What the demo page has to do, checked in a real browser.
//
// Two rounds of review on this page found the same class of bug: something drawn over the plan
// swallowing the pointer events the rooms need, so hovering and clicking a room silently did
// nothing while every screenshot looked right. A screenshot cannot see that. These can.
//
//   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright node demo/test/check.mjs
//
// PLAYWRIGHT names the one already on the machine, as catio/test/run.sh does; without it the
// import falls back to a local playwright. Nothing else: no server, no build, no network
// beyond the page's fonts.
// It is not wired into .github/workflows/tests.yml, which is a held path.

import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// resolved the way catio/test/e2e.mjs does, so PLAYWRIGHT points at the one on the machine
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT || "playwright");

const PAGE = "file://" + join(dirname(fileURLToPath(import.meta.url)), "..", "index.html");

let failed = 0;
function ok(name, pass, detail) {
  console.log((pass ? "  ok   " : "  FAIL ") + name + (pass || detail === undefined ? "" : "  — " + detail));
  if (!pass) failed++;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e.message)));
page.on("requestfailed", (r) => { if (!r.url().startsWith("https://fonts.")) errors.push("failed: " + r.url()); });
await page.goto(PAGE, { waitUntil: "networkidle" });
await page.locator("#stage").scrollIntoViewIfNeeded();
await page.waitForTimeout(300);

console.log("the document");
ok("standards mode, not quirks", (await page.evaluate(() => document.compatMode)) === "CSS1Compat");
ok("no horizontal scroll", !(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)));

console.log("\nthe plan takes its own pointer events");
// every pixel of a room — its floor, its furniture, its cabinet — must resolve to that room
for (const [room, pick] of [["dining", "floor"], ["dining", "furniture"], ["kitchen", "cabinet"], ["hall", "stair"]]) {
  const inRoom = await page.evaluate(({ room, pick }) => {
    const b = { dining: [96, 48, 181, 165], kitchen: [272, 48, 245, 165], hall: [272, 208, 245, 181] }[room];
    const svg = document.getElementById("plan");
    const box = svg.getBoundingClientRect();
    const vb = svg.getAttribute("viewBox").split(" ").map(Number);
    const at = { floor: [b[0] + b[2] * 0.5, b[1] + b[3] * 0.55],
                 furniture: [b[0] + b[2] / 2, b[1] + 24],
                 cabinet: [b[0] + b[2] - 30, b[1] + b[3] - 30],
                 stair: [394, 250] }[pick];
    const x = box.left + ((at[0] - vb[0]) / vb[2]) * box.width;
    const y = box.top + ((at[1] - vb[1]) / vb[3]) * box.height;
    const el = document.elementFromPoint(x, y);
    const hit = el && el.closest("[data-room]");
    return hit ? hit.getAttribute("data-room") : null;
  }, { room, pick });
  ok(`${room}: its ${pick} belongs to the room`, inRoom === room, `got ${inRoom}`);
}

console.log("\nhover names a thing, and stops naming it");
await page.locator('rect.room-hit[data-room="kitchen"]').hover();
await page.waitForTimeout(150);
ok("a room is named and its cats counted", (await page.locator("#tip").innerText()) === "Kitchen · 1 cat");
ok("one room bracketed", (await page.locator(".room.on").count()) === 1);
await page.locator("#cats .cat .spr").first().hover();
await page.waitForTimeout(150);
ok("a cat is named with its mood", /Mochi · Busy working/.test(await page.locator("#tip").innerText()));
ok("no room bracketed while on a cat", (await page.locator(".room.on").count()) === 0);
await page.mouse.move(10, 10);
await page.waitForTimeout(150);
ok("the line clears when the pointer leaves", (await page.locator("#tip").innerText()) === "");

console.log("\na click opens a menu beside the thing");
await page.locator('rect.room-hit[data-room="dining"]').click({ force: true });
await page.waitForTimeout(200);
ok("a room menu opens", await page.locator("#menu").isVisible());
ok("named for the room", (await page.locator("#menu h4").innerText()) === "Café");
// Sweeping other rooms must not light them while a menu is pinned. The pointer is dispatched
// rather than moved, because the pinned menu covers some of those rooms — which is correct.
for (const r of ["living", "study", "sunroom"]) {
  await page.locator(`rect.room-hit[data-room="${r}"]`).dispatchEvent("pointerover");
}
await page.waitForTimeout(150);
ok("brackets do not pile up under a pinned menu", (await page.locator(".room.on").count()) <= 2,
  `${await page.locator(".room.on").count()} rooms bracketed`);
await page.keyboard.press("Escape");
ok("Escape closes it", !(await page.locator("#menu").isVisible()));

console.log("\nthe keyboard reaches the stage");
await page.evaluate(() => document.querySelector("#cats .cat .spr").focus());
await page.waitForTimeout(120);
ok("focusing a cat says its line", (await page.locator("#tip").innerText()).length > 0);
await page.keyboard.press("Enter");
await page.waitForTimeout(200);
ok("Enter opens the cat's menu", await page.locator("#menu").isVisible());
await page.keyboard.press("Escape");
await page.evaluate(() => document.querySelector('rect.room-hit[data-room="kitchen"]').focus());
await page.keyboard.press("Enter");
await page.waitForTimeout(200);
ok("Enter opens a room's menu", (await page.locator("#menu h4").innerText()) === "Kitchen");
await page.keyboard.press("Escape");

console.log("\nthe two controls, and nothing else");
ok("the map panel starts folded", (await page.locator("#mapPanel").getAttribute("data-folded")) === "true");
ok("the badge counts every cat that needs you", (await page.locator("#houseBadge").innerText()) === "3");
// The queen stands in the hall but is not one of the cats: she is in no count, and the badge
// of 3 above is the three CATS that need you, not four.
ok("the queen is on the map but is not a cat", await page.evaluate(() =>
  document.querySelectorAll("#cats .queen-pin").length === 1 &&
  document.querySelectorAll("#cats .cat").length === 5));

// the pips are read as a property: while the panel is folded the tabs are display:none, so
// "not visible" would pass whatever the state
const pip = (id) => page.evaluate((i) => document.getElementById(i).hidden, id);
ok("upstairs pip set from the ground floor", (await pip("upPip")) === false);
ok("ground pip unset from the ground floor", (await pip("groundPip")) === true);

await page.locator("#mapFold").click();
await page.waitForTimeout(150);
ok("unfolding shows the floor tabs", await page.locator("#tabUpper").isVisible());
ok("and the upstairs pip with them", await page.locator("#upPip").isVisible());
await page.locator("#tabUpper").click();
await page.waitForTimeout(400);
ok("ground pip set from upstairs", (await pip("groundPip")) === false);
ok("upstairs pip unset while upstairs", (await pip("upPip")) === true);

console.log("\nmenus open clear of the controls");
await page.locator("#cats .cat .spr").last().click();
await page.waitForTimeout(250);
ok("a menu clears the brand and the map panel", await page.evaluate(() => {
  const m = document.getElementById("menu").getBoundingClientRect();
  return ["hud", "mapPanel"].every((id) => {
    const b = document.getElementById(id).getBoundingClientRect();
    return m.right <= b.left || m.left >= b.right || m.bottom <= b.top || m.top >= b.bottom;
  });
}));
ok("and stays inside the stage", await page.evaluate(() => {
  const s = document.getElementById("stage").getBoundingClientRect();
  const m = document.getElementById("menu").getBoundingClientRect();
  return m.left >= s.left - 1 && m.right <= s.right + 1 && m.top >= s.top - 1 && m.bottom <= s.bottom + 1;
}));
await page.keyboard.press("Escape");

console.log("\nnothing is drawn on the cats");
ok("a cat's element holds only its sprite", await page.evaluate(() =>
  [...document.querySelectorAll("#cats > div")].every((d) => d.children.length === 1 &&
    d.firstElementChild.classList.contains("spr") && d.textContent.trim() === "")));
ok("no sign anywhere on the plan", (await page.locator("#plan text").count()) === 0);

console.log("\nthe wizard runs");
await page.locator(".wiz").scrollIntoViewIfNeeded();
const titles = [];
for (let i = 0; i < 7; i++) {
  titles.push(await page.locator("#wizTitle").innerText());
  if (i < 6) await page.locator("#wizNext").click();
  await page.waitForTimeout(100);
}
ok("all seven steps, in order",
  titles.join(",") === "Welcome,Rooms,GitHub,Sessions,Litter box,How it works,Done", titles.join(","));
ok("the last step offers the doors", (await page.locator("#wizNext").innerText()) === "Open the doors");

console.log("\nthe queen answers");
await page.locator(".scene").scrollIntoViewIfNeeded();
const before = await page.locator("#qsay").innerText();
await page.locator("#qreplies button").nth(1).click();
await page.waitForTimeout(120);
ok("a quick reply changes what she says", (await page.locator("#qsay").innerText()) !== before);

console.log("\nno errors");
ok("no page errors and no failed loads", errors.length === 0, errors.join(" | "));

await browser.close();
console.log(failed ? `\n${failed} failed` : "\nall checks passed");
process.exit(failed ? 1 : 0);
