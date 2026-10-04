// Look at the page before touching a test: screenshots of the floors or rooms named, with the stub's invented cats.
//   sh catio/test/run.sh look [ground|upper|<room key>…]   (default: both floors, whole)
// Writes catio/test/.look/<name>.png and prints each path, for the agent to open and set beside her words.
// LOOK_QUERY passes the stub's options, e.g. LOOK_QUERY="?gateway=1&mode=blocked".
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT || "playwright");
const out = join(here, ".look");
mkdirSync(out, { recursive: true });
const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
const names = process.argv.length > 2 ? process.argv.slice(2) : ["ground", "upper"];
// "setup": the first run's wizard, which opens over a café with no rooms (the stub's ?mode=empty)
const query = process.env.LOOK_QUERY || (names.includes("setup") ? "?mode=empty" : "");
await page.goto("file://" + join(here, ".page.html") + query);
await page.waitForTimeout(800);
const UPPER = new Set(["upper", "brain", "bath", "bedroom"]);
for (const name of names) {
  if (name === "setup") {
    for (const [i, step] of ["welcome", "rooms", "github", "sessions", "litterbox", "how", "done"].entries()) {
      if (i) await page.click("#setupDlg button[type=submit]");
      await page.waitForTimeout(300);
      await page.screenshot({ path: join(out, "setup-" + step + ".png") });
      console.log(join(out, "setup-" + step + ".png"));
    }
    await page.click("#setupDlg button[type=submit]");   // Open the doors: the names after it show the café it made
    await page.waitForTimeout(500);
    continue;
  }
  // "queen": her card, the scene she talks in; "queen-settings": its Settings overlay, open at You
  if (name.startsWith("queen")) {
    if ((await page.locator("#world").getAttribute("data-floor")) !== "ground") await page.click("#floor-ground");
    if (!(await page.locator("#queenDlg").evaluate((d) => d.open))) {
      await page.keyboard.press("0");
      await page.waitForTimeout(300);
      await page.locator("#cats .cat.queen").dispatchEvent("dblclick");
      await page.waitForTimeout(600);
    }
    if (name === "queen-settings") {
      await page.click("#queenSettingsBtn");
      await page.click("#queenYou summary");
      await page.waitForTimeout(300);
    }
    await page.screenshot({ path: join(out, name + ".png") });
    console.log(join(out, name + ".png"));
    continue;
  }
  // "maps": the project maps dashboard, from the House menu, with two invented maps
  if (name === "maps") {
    await page.evaluate(() => {
      const map = (k) => ({ n: [{ t: "Core", g: 0, d: 9, x: 150, y: 80 }, { t: "Edge " + k, g: 1, d: 4, x: 60, y: 40 }, { t: "Leaf", g: 2, d: 1, x: 250, y: 130 }, { t: "Hub", g: 0, d: 7, x: 200, y: 50 }], l: [0, 1, 0, 2, 0, 3, 3, 2] });
      window.__catio.put("graphs/montfortoise-shopify", { repo: "example/montfortoise-shopify", at: Date.now() - 6e5, nodes: 120, edges: 210, communities: 6, gods: [{ label: "CartDrawer", degree: 14, file: "src/cart.js" }], groups: [{ name: "Checkout", size: 40 }, { name: "Theme", size: 30 }, { name: "Admin", size: 12 }], surprises: [{ a: "Shipping notes", rel: "references", b: "CartDrawer", how: "INFERRED", where: "docs/shipping.md → src/cart.js" }], questions: ["Why does CartDrawer connect Checkout to Theme?"], map: map("A") });
      window.__catio.put("graphs/intermarche-grocery-shopping-app", { repo: "example/Intermarche-grocery-shopping-app", at: Date.now() - 36e5, nodes: 64, edges: 98, communities: 4, gods: [{ label: "Basket", degree: 11, file: "src/basket.js" }], groups: [{ name: "Basket", size: 20 }, { name: "Menus", size: 18 }, { name: "Drive", size: 9 }], surprises: [], questions: ["Where does the basket get its prices?"], map: map("B") });
    });
    await page.waitForTimeout(300);
    await page.evaluate(() => { for (const d of document.querySelectorAll("dialog[open]")) d.close(); });   // a look before it may have left one open
    await page.click("#houseBtn");
    await page.locator("#menu .mi", { hasText: "Project maps" }).click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: join(out, "maps.png") });
    console.log(join(out, "maps.png"));
    await page.evaluate(() => document.getElementById("mapsDlg").close());   // the looks after it see the house, not the dialog
    continue;
  }
  // "art": The look, from the House menu; "art-swap": the house drawn with other pieces in some slots (pieces of the
  // packs themselves, so no new file is needed), then the card with them, and one that doesn't fit
  if (name === "art" || name === "art-swap") {
    await page.evaluate(() => { for (const d of document.querySelectorAll("dialog[open]")) d.close(); });
    if (name === "art-swap") {
      await page.evaluate(() => {
        window.__catio.put("skin/panel", { src: "art/licensed/ui/button-green.png", slice: [4, 4, 6, 4], w: 26, h: 28, at: 1 });
        window.__catio.put("skin/button", { src: "art/licensed/ui/button-pink.png", slice: [4, 4, 6, 4], w: 26, h: 28, at: 1 });
        window.__catio.put("skin/cat-work", { src: "art/licensed/mochi-box.png", frames: 4, secs: 0.8, at: 1 });
        window.__catio.put("skin/cat-walk-side", { src: "art/licensed/mochi-idle.png", frames: 10, secs: 1, at: 1 });
        window.__catio.put("skin/house", { src: "art/licensed/meadow.png", at: 1 });
        window.__catio.put("skin/theme", { tokens: { "--ink": "#1d3557", "--tan": "#a8dadc", "--cream": "#f1faee", "--grass": "#457b9d", "--map-btn": "#e9c46a" }, at: 1 });
      });
      await page.waitForTimeout(800);
      await page.keyboard.press("0");
      await page.waitForTimeout(600);
      await page.click("#houseBtn");
      await page.waitForTimeout(300);
      await page.screenshot({ path: join(out, "art-swap-house.png") });
      console.log(join(out, "art-swap-house.png"));
      await page.keyboard.press("Escape");
    }
    await page.click("#houseBtn");
    await page.locator("#menu .mi", { hasText: "The look" }).click();
    await page.waitForTimeout(500);
    if (name === "art-swap") await page.evaluate(() => { for (const d of document.querySelectorAll("#artDlg details")) d.open = true; document.querySelector('#artDlg li[data-slot="house"]').scrollIntoView(); });
    await page.screenshot({ path: join(out, name + ".png") });
    console.log(join(out, name + ".png"));
    await page.evaluate(() => document.getElementById("artDlg").close());
    continue;
  }
  const floor = UPPER.has(name) ? "upper" : "ground";
  if ((await page.locator("#world").getAttribute("data-floor")) !== floor) await page.click("#floor-" + floor);
  await page.keyboard.press("0");   // the whole house, then into the room named
  if (name !== floor) await page.locator('.roomhit[data-room="' + name + '"]').dispatchEvent("dblclick");
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(out, name + ".png") });
  console.log(join(out, name + ".png"));
}
await browser.close();
