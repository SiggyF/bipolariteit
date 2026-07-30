// Debug-hulpje voor de correspondentiekaart: zet 3D aan, sleept een stuk en
// maakt screenshots, zodat de 3D-projectie zonder handmatig klikken te
// inspecteren is.
//
//   cd frontend && node ../scripts/shoot_correspondence.mjs [url] [outdir]

import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:4322/topics/stikstof/";
const outDir = process.argv[3] ?? "/tmp/correspondence-shots";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
page.on("console", (m) => console.log(`[console:${m.type()}]`, m.text()));
page.on("pageerror", (e) => console.log("[pageerror]", e.message));

await page.goto(url, { waitUntil: "networkidle" });

const wrapper = page.locator(".correspondence-wrapper");
await wrapper.scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
await page.screenshot({ path: `${outDir}/01-2d.png` });

// 3D-checkbox: de enige checkbox in de chart-controls van dit paneel.
const toggle = page.locator(".chart-controls input[type=checkbox]").first();
console.log("3D disabled?", await toggle.isDisabled());
await toggle.check();
await page.waitForTimeout(800);
await page.screenshot({ path: `${outDir}/02-3d.png` });

// Logo's als contour i.p.v. in kleur, om de twee varianten te kunnen vergelijken.
const logoKeuze = page.locator(".chart-controls select").nth(1);
if (await logoKeuze.count()) {
	await logoKeuze.selectOption("inkt");
	await page.waitForTimeout(600);
	await page.screenshot({ path: `${outDir}/02b-3d-contourlogos.png` });
	await logoKeuze.selectOption("kleur");
	await page.waitForTimeout(400);
}

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
