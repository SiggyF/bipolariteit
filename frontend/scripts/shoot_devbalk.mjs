// Schiet de ontwikkelbalk in licht en donker, om te controleren of hij in
// beide thema's leesbaar is. Verwacht een draaiende preview-server:
//
//   cd frontend && npx astro preview --port 4399
//   node scripts/shoot_devbalk.mjs
//
// Screenshots komen in /tmp/balk-<thema>.png.
import { chromium } from "playwright";

const URL = process.env.PREVIEW_URL ?? "http://localhost:4399/";
const browser = await chromium.launch();

for (const thema of ["light", "dark"]) {
	const pagina = await browser.newPage({ viewport: { width: 1100, height: 420 } });
	if (thema === "dark") {
		await pagina.addInitScript(() => localStorage.setItem("theme", "dark"));
	}
	await pagina.goto(URL);
	await pagina.waitForTimeout(700);
	await pagina.screenshot({
		path: `/tmp/balk-${thema}.png`,
		clip: { x: 0, y: 0, width: 1100, height: 140 },
	});
	console.log(`geschreven: /tmp/balk-${thema}.png`);
}

await browser.close();
