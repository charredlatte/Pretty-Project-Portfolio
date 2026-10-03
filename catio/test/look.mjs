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
  const floor = UPPER.has(name) ? "upper" : "ground";
  if ((await page.locator("#world").getAttribute("data-floor")) !== floor) await page.click("#floor-" + floor);
  await page.keyboard.press("0");   // the whole house, then into the room named
  if (name !== floor) await page.locator('.roomhit[data-room="' + name + '"]').dispatchEvent("dblclick");
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(out, name + ".png") });
  console.log(join(out, name + ".png"));
}
await browser.close();
