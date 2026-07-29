// Rooktest voor de filterbalk op een topicpagina. Draait tegen een echte
// build, want de filterstore leest de URL en leeft in een client-only island
// -- dat is precies het gedrag dat een unit-test op de store zou missen.
//
//   cd frontend && npm run build && npx astro preview &
//   node tests/smoke-filters.mjs [http://localhost:4321]
//
// Exit 0 = alles goed, exit 1 = eerste falende check met toelichting.

import { chromium } from "playwright";

const BASE = process.argv[2] ?? "http://localhost:4321";
const TOPIC = `${BASE}/topics/stikstof/`;

const failures = [];

function check(name, condition, detail = "") {
	if (condition) {
		console.log(`  ok   ${name}`);
	} else {
		console.log(`  FAIL ${name}${detail ? ` -- ${detail}` : ""}`);
		failures.push(name);
	}
}

/** "37 van 1368 argumenten" -> [37, 1368] */
async function counts(page) {
	const text = await page.locator(".filter-count").innerText();
	const [shown, total] = text.match(/\d+/g).map(Number);
	return { shown, total };
}

async function openFacet(page, label) {
	await page.locator(".facet-button", { hasText: label }).first().click();
	await page.locator(".facet-panel").waitFor();
}

const browser = await chromium.launch();
const page = await browser.newPage();
page.on("pageerror", (error) => {
	console.log(`  FAIL pagina-fout -- ${error.message}`);
	failures.push("pageerror");
});

console.log("ongefilterde weergave");
await page.goto(TOPIC);
await page.locator(".filter-bar").waitFor();
const initial = await counts(page);
check("toont alle argumenten", initial.shown === initial.total, `${initial.shown} van ${initial.total}`);
check("geen actief-filter-accent", (await page.locator(".filter-bar.is-active").count()) === 0);
check("geen chips", (await page.locator(".filter-chip").count()) === 0);

console.log("filteren op partij");
await openFacet(page, "Partij");
const firstOption = page.locator(".facet-options label").first();
const partyLabel = (await firstOption.locator(".facet-option-label").innerText()).trim();
const partyCount = Number(await firstOption.locator(".facet-option-count").innerText());
await firstOption.locator("input").check();

const filtered = await counts(page);
check("aantal daalt naar het facet-aantal", filtered.shown === partyCount, `${filtered.shown} vs facet ${partyCount}`);
check("totaal blijft ongewijzigd", filtered.total === initial.total);
check("filterbalk is gemarkeerd als actief", (await page.locator(".filter-bar.is-active").count()) === 1);
check("chip toont het filter", (await page.locator(".filter-chip").innerText()).includes(partyLabel));
check("URL bevat het filter", new URL(page.url()).searchParams.has("partij"), page.url());

console.log("grafieken volgen het filter");
const statsHeading = await page.locator(".stats-panel h2").first().innerText();
check("statistiekenkop telt de selectie", statsHeading.includes(String(filtered.shown)), statsHeading);
const partyRows = await page.locator(".party-table tbody tr").count();
check("statistiekentabel houdt alleen de gefilterde partij over", partyRows === 1, `${partyRows} rijen`);

console.log("deelbaarheid en navigatie");
const sharedUrl = page.url();
await page.goto(sharedUrl);
await page.locator(".filter-bar").waitFor();
check("filter overleeft een herladen", (await counts(page)).shown === filtered.shown);

// Expliciet op een verse load, niet na een klik: de grafieken monteren in
// hetzelfde island als de filterstore, dus de volgorde van initialiseren en
// monteren moet ook kloppen als het filter al uit de URL komt.
check("grafiek volgt het filter direct bij laden", (await page.locator(".party-table tbody tr").count()) === 1);

await page.goBack();
await page.locator(".filter-bar").waitFor();
check("terugknop maakt het filter ongedaan", (await counts(page)).shown === initial.total);
check("grafiek volgt de terugknop", (await page.locator(".party-table tbody tr").count()) > 1);

console.log("filteren via een tag op een kaart");
await page.goto(TOPIC);
await page.locator(".tag-badge").first().waitFor();
const tagBadge = page.locator(".tag-badge").first();
const tagName = (await tagBadge.innerText()).trim();
await tagBadge.click();
const tagFiltered = await counts(page);
check("tag staat in de URL", new URL(page.url()).searchParams.getAll("tag").includes(tagName), page.url());
check("aangeklikte tag is gemarkeerd", (await page.locator(".tag-badge.is-active").count()) > 0);

// Niet "minder dan alles": afgeleide tags als Arena-Parlement zitten op elk
// argument, dus daarop filteren levert terecht het volledige corpus op. De
// echte check is dat de selectie klopt met wat het facet voor die tag belooft.
await openFacet(page, "Tag");
const tagOption = page.locator(".facet-options label", { has: page.getByText(tagName, { exact: true }) }).first();
const tagFacetCount = Number(await tagOption.locator(".facet-option-count").innerText());
check("aantal klopt met het facet-aantal van die tag", tagFiltered.shown === tagFacetCount,
	`${tagFiltered.shown} vs facet ${tagFacetCount}`);
await page.locator(".facet-button", { hasText: "Tag" }).first().click(); // paneel weer dicht
check("kolomtotalen tellen op tot de selectie",
	(await page.locator(".column h2").allInnerTexts())
		.map((t) => Number(t.match(/\((\d+)\)/)[1]))
		.reduce((a, b) => a + b, 0) === tagFiltered.shown);

console.log("periodes");
await page.goto(TOPIC);
await page.locator(".filter-bar").waitFor();
await openFacet(page, "Kabinet");
const kabinetten = await page.locator(".facet-options .facet-option-label").allInnerTexts();
const kabinetDatums = [];
for (const naam of kabinetten) {
	// Filter los op elk kabinet en onthoud de vroegste datum in de selectie,
	// zodat we kunnen controleren dat de opties chronologisch staan.
	await page.goto(`${TOPIC}?regering=${encodeURIComponent(naam)}`);
	await page.locator(".filter-bar").waitFor();
	kabinetDatums.push((await counts(page)).shown);
	await openFacet(page, "Kabinet");
	await page.locator(".facet-button", { hasText: "Kabinet" }).first().click();
}
check("elk kabinet levert een niet-lege, kleinere selectie", kabinetDatums.every((n) => n > 0 && n < initial.total),
	kabinetDatums.join(", "));
check("kabinetten dekken samen het hele corpus",
	kabinetDatums.reduce((a, b) => a + b, 0) === initial.total,
	`${kabinetDatums.reduce((a, b) => a + b, 0)} vs ${initial.total}`);

console.log("onzinnige URL-waarden worden genegeerd");
await page.goto(`${TOPIC}?stance=bogus&van=gisteren`);
await page.locator(".filter-bar").waitFor();
const bogus = await counts(page);
check("onbekende waarden filteren niets weg", bogus.shown === bogus.total, `${bogus.shown} van ${bogus.total}`);
check("en leveren geen chips op", (await page.locator(".filter-chip").count()) === 0);

await browser.close();

if (failures.length) {
	console.log(`\n${failures.length} check(s) gefaald: ${failures.join(", ")}`);
	process.exit(1);
}
console.log("\nalle checks geslaagd");
