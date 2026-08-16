// Handmatig debug-hulpje voor de correspondentiekaart, geen automatische test
// (geen assertions -- schrijft screenshots weg voor eigen inspectie, draait
// niet mee in `npm test` of CI). Zet 3D aan, sleept een stuk en maakt
// screenshots, zodat de 3D-projectie zonder handmatig klikken te inspecteren is.
//
//   cd frontend && node scripts/shoot_correspondence.mjs [url] [outdir]

import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:4321/onderwerpen/stikstof/";
const outDir = process.argv[3] ?? "/tmp/correspondence-shots";
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
page.on("console", (m) => console.log(`[console:${m.type()}]`, m.text()));
page.on("pageerror", (e) => console.log("[pageerror]", e.message));

await page.goto(url, { waitUntil: "networkidle" });

const wrapper = page.locator(".correspondence-wrapper");
await wrapper.scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
await page.screenshot({ path: `${outDir}/01-2d.png` });

// 3D is een pil-toggle (net als "Rijen: Partijen/Personen"), geen checkbox meer.
const toggle3D = page.locator(".chart-controls .toggle-btn", { hasText: "3D" });
console.log("3D disabled?", await toggle3D.isDisabled());
await toggle3D.click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${outDir}/02-3d.png` });

const box = await wrapper.boundingBox();
const cx = box.x + box.width / 2;
const cy = box.y + box.height / 2;

await page.mouse.move(cx, cy);
await page.mouse.down();
for (let i = 1; i <= 20; i++) {
	await page.mouse.move(cx + i * 8, cy + i * 2);
	await page.waitForTimeout(20);
}
await page.screenshot({ path: `${outDir}/03-tijdens-sleep.png` });
await page.mouse.up();
await page.waitForTimeout(600);
await page.screenshot({ path: `${outDir}/04-na-sleep.png` });

console.log("screenshots in", outDir);
await browser.close();
