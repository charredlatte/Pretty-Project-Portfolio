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
import { readFile } from "node:fs/promises";

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
// Three times now something floating over the plan — the cat layer, then the furniture, then
// the hover line — has swallowed the events a room needs, and every screenshot still looked
// right. So sweep a grid over every room, at the widths where the overlays are largest, with
// the longest hover line the page can produce showing. The room boxes are read off the drawn
// SVG, not copied here: a copy would go stale and keep passing.
for (const [width, panel] of [[1200, "folded"], [390, "folded"], [360, "folded"],
                              [1200, "open"], [390, "open"]]) {
  await page.setViewportSize({ width, height: 800 });
  await page.waitForTimeout(250);
  await page.locator("#stage").scrollIntoViewIfNeeded();
  const isOpen = (await page.locator("#mapPanel").getAttribute("data-folded")) === "false";
  if ((panel === "open") !== isOpen) { await page.locator("#mapFold").click(); }
  await page.waitForTimeout(200);
  // make the tip as big as it gets, so its footprint is in the sweep
  await page.locator("#cats .cat .spr").nth(1).hover();
  await page.waitForTimeout(150);

  const dead = await page.evaluate(() => {
    const svg = document.getElementById("plan");
    const box = svg.getBoundingClientRect();
    const vb = svg.getAttribute("viewBox").split(" ").map(Number);
    const out = [];
    for (const g of document.querySelectorAll(".room")) {
      const want = g.getAttribute("data-room");
      const r = g.querySelector("rect.room-hit");
      const [rx, ry, rw, rh] = ["x", "y", "width", "height"].map((a) => Number(r.getAttribute(a)));
      for (let i = 1; i <= 5; i++) {
        for (let j = 1; j <= 5; j++) {
          const wx = rx + (rw * i) / 6, wy = ry + (rh * j) / 6;
          const x = box.left + ((wx - vb[0]) / vb[2]) * box.width;
          const y = box.top + ((wy - vb[1]) / vb[3]) * box.height;
          const el = document.elementFromPoint(x, y);
          const hit = el && el.closest("[data-room]");
          // a cat standing on the spot is allowed to take it; nothing else is
          // a cat standing there may take it, and so may a real button; nothing else
          if (!hit && !(el && el.closest(".cat, .queen-pin, button"))) {
            out.push(`${want} at ${Math.round(wx)},${Math.round(wy)} → ${el ? (el.id || el.className.baseVal || el.tagName) : "null"}`);
          } else if (hit && hit.getAttribute("data-room") !== want) {
            out.push(`${want} at ${Math.round(wx)},${Math.round(wy)} → ${hit.getAttribute("data-room")}`);
          }
        }
      }
    }
    return out;
  });
  ok(`${width}px, map ${panel}: every room owns its 25 points`, dead.length === 0,
    dead.slice(0, 4).join("; ") + (dead.length > 4 ? ` (+${dead.length - 4} more)` : ""));
}
if ((await page.locator("#mapPanel").getAttribute("data-folded")) === "false") {
  await page.locator("#mapFold").click();
}
await page.setViewportSize({ width: 1200, height: 900 });
await page.waitForTimeout(250);
await page.locator("#stage").scrollIntoViewIfNeeded();
await page.mouse.move(5, 5);
await page.waitForTimeout(150);

console.log("\nhover names a thing, and stops naming it");
// a room's centre is where a wandering cat can be; its top-left corner never is
const CORNER = { position: { x: 24, y: 24 } };
await page.locator('rect.room-hit[data-room="kitchen"]').hover(CORNER);
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
await page.locator('rect.room-hit[data-room="dining"]').click({ ...CORNER, force: true });
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

console.log("\nmenus open clear of the controls, at every width");
// A menu is never clipped and never covers the brand or the map panel. The phone widths are
// here because the stage is only ~240px tall there, which is shorter than the menu itself —
// the case a 1200px check and an eyeballed screenshot both miss.
for (const width of [1200, 760, 390, 360]) {
  await page.setViewportSize({ width, height: 800 });
  await page.waitForTimeout(250);
  await page.locator("#stage").scrollIntoViewIfNeeded();
  await page.locator("#cats .cat .spr").first().click();
  await page.waitForTimeout(250);
  const m = await page.evaluate(() => {
    const r = (id) => document.getElementById(id).getBoundingClientRect();
    const menu = document.getElementById("menu").getBoundingClientRect();
    const stage = r("stage");
    const over = (b) => !(menu.right <= b.left || menu.left >= b.right ||
                          menu.bottom <= b.top || menu.top >= b.bottom);
    return {
      clear: !over(r("hud")) && !over(r("mapPanel")),
      overStage: menu.left >= stage.left - 2 && menu.right <= stage.right + 2,
      whole: menu.height > 40 && menu.width > 40,
      // it must not be inside the stage, which clips: that is what cut it off at phone width
      outsideTheClip: !document.getElementById("stage").contains(document.getElementById("menu"))
    };
  });
  ok(`${width}px: clear of the brand and the map panel`, m.clear);
  ok(`${width}px: horizontally over the stage`, m.overStage);
  ok(`${width}px: drawn whole, not clipped`, m.whole && m.outsideTheClip);
  await page.keyboard.press("Escape");
}
await page.setViewportSize({ width: 1200, height: 900 });
await page.waitForTimeout(200);
await page.locator("#stage").scrollIntoViewIfNeeded();

// back downstairs, where the queen is
await page.locator("#tabGround").click();
await page.waitForTimeout(400);

console.log("\nwhat a screen reader is told");
// A tab stop inside an aria-hidden subtree is announced as nothing. This is the regression the
// previous round shipped: seven focusable rooms that assistive tech could not see.
const named = await page.evaluate(() => {
  const inHidden = (el) => el.closest('[aria-hidden="true"]') !== null;
  const rooms = [...document.querySelectorAll("rect.room-hit")];
  const cats = [...document.querySelectorAll("#cats .spr")];
  return {
    rooms: rooms.length,
    roomsNamed: rooms.filter((e) => e.getAttribute("aria-label") && !inHidden(e)).length,
    catsNamed: cats.filter((e) => e.getAttribute("aria-label") && !inHidden(e)).length,
    queen: document.querySelector(".queen-pin .spr").getAttribute("aria-label")
  };
});
ok("every room is a named button nothing hides", named.rooms === 7 && named.roomsNamed === 7,
  `${named.roomsNamed}/${named.rooms} named and visible to AT`);
ok("every cat is named too", named.catsNamed === 6, String(named.catsNamed));
// the page exists to say she is not one of your sessions, so she must not be announced as one
ok("the queen is not announced as a working session",
  /queen of the house/.test(named.queen) && !/Busy working/.test(named.queen), named.queen);

console.log("\nnothing is drawn on the cats");
ok("a cat's element holds only its sprite", await page.evaluate(() =>
  [...document.querySelectorAll("#cats > div")].every((d) => d.children.length === 1 &&
    d.firstElementChild.classList.contains("spr") && d.textContent.trim() === "")));
ok("no sign anywhere on the plan", (await page.locator("#plan text").count()) === 0);

console.log("\nhovering a cat outlines it, whatever coat it wears");
// the coat used to be an inline filter, which outranks the stylesheet, so no cat was outlined
for (const which of [0, 3]) {
  const spr = page.locator("#cats .cat .spr").nth(which);
  await spr.hover();
  await page.waitForTimeout(150);
  const f = await spr.evaluate((e) => getComputedStyle(e).filter);
  ok(`cat ${which}: outlined on hover, coat kept`, /drop-shadow/.test(f), f);
}
await page.mouse.move(5, 5);
await page.waitForTimeout(150);

console.log("\na menu action says what it did, and the saying sticks");
await page.locator("#cats .cat .spr").first().click();
await page.waitForTimeout(200);
await page.locator("#menu li button").first().click();
await page.waitForTimeout(400);     // long enough for a stray pointerover to have wiped it
ok("the confirmation survives the menu closing",
  /in a real café/.test(await page.locator("#tip").innerText()),
  JSON.stringify(await page.locator("#tip").innerText()));
await page.mouse.move(5, 5);
await page.waitForTimeout(150);

console.log("\nthe wizard remembers what you chose");
await page.locator(".wiz").scrollIntoViewIfNeeded();
await page.locator("#wizNext").click();                     // to Rooms
await page.waitForTimeout(120);
const filed = async () => page.locator(".repo select").evaluateAll((s) => s.map((e) => e.value));
await page.locator("#wizNext").click();                     // to GitHub
await page.waitForTimeout(120);
const before2 = await filed();
await page.locator("#wizBack").click();
await page.waitForTimeout(120);
for (let i = 0; i < 3; i++) { await page.locator('[data-step="less"]').click(); await page.waitForTimeout(60); }
for (let i = 0; i < 3; i++) { await page.locator('[data-step="more"]').click(); await page.waitForTimeout(60); }
await page.locator("#wizNext").click();
await page.waitForTimeout(150);
ok("the rooms the repos were filed in survive a dip in the room count",
  JSON.stringify(await filed()) === JSON.stringify(before2),
  `${JSON.stringify(before2)} → ${JSON.stringify(await filed())}`);
await page.reload({ waitUntil: "networkidle" });
await page.locator("#stage").scrollIntoViewIfNeeded();
await page.waitForTimeout(300);

console.log("\nthe pixel art is drawn as pixel art");
const smoothed = await page.evaluate(() =>
  [...document.querySelectorAll("#cats .spr, .mood .pic, .mark, .fig")]
    .filter((e) => getComputedStyle(e).imageRendering !== "pixelated").length);
ok("nothing with a sprite in it is smoothed", smoothed === 0, smoothed + " smoothed");

// the plan and the cats are placed by two different boxes; they have to agree on where a room is
ok("the cats line up with the plan they stand on", await page.evaluate(() => {
  const svg = document.getElementById("plan");
  const box = svg.getBoundingClientRect();
  const vb = svg.getAttribute("viewBox").split(" ").map(Number);
  const layer = document.getElementById("cats").getBoundingClientRect();
  // world (96,48) by the SVG, and by the percentages the cat layer uses
  const bySvg = box.left + ((96 - vb[0]) / vb[2]) * box.width;
  const byLayer = layer.left + ((96 - vb[0]) / vb[2]) * layer.width;
  return Math.abs(bySvg - byLayer) < 0.5;
}));

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

console.log("\nthe page agrees with the sprites it was given");
// sprites.json is what sprites.py recorded; the page hardcodes the same counts. Without this
// the two drift silently and a sheet renders a squashed cycle with a sliver of the next frame.
const sprites = JSON.parse(
  await readFile(join(dirname(fileURLToPath(import.meta.url)), "..", "art", "sprites.json"), "utf8"));
const pageFrames = await page.evaluate(() => {
  const out = {};
  for (const d of document.querySelectorAll("#cats > div")) {
    const spr = d.querySelector(".spr");
    out["cat-" + (d._showing || d._cat.mood)] = Number(getComputedStyle(spr).getPropertyValue("--frames"));
  }
  for (const e of document.querySelectorAll(".mood .pic, .mark, .fig.queen")) {
    const url = /art\/([a-z-]+)\.png/.exec(getComputedStyle(e).backgroundImage);
    if (url) out[url[1]] = Number(getComputedStyle(e).getPropertyValue("--frames"));
  }
  return out;
});
const wrong = Object.entries(pageFrames)
  .filter(([k, n]) => sprites[k] && sprites[k].frames !== n)
  .map(([k, n]) => `${k}: page ${n}, sheet ${sprites[k].frames}`);
ok("every frame count matches its sheet", wrong.length === 0, wrong.join("; "));
const want = ["cat-work", "cat-review", "cat-meow", "cat-cry", "cat-sleep"];
const missing = want.filter((k) => !(k in pageFrames));
ok("and all five mood sheets were among them", missing.length === 0, "not on the page: " + missing.join(", "));

console.log("\nno errors");
ok("no page errors and no failed loads", errors.length === 0, errors.join(" | "));

await browser.close();
console.log(failed ? `\n${failed} failed` : "\nall checks passed");
process.exit(failed ? 1 : 0);
