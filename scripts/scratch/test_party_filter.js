const path = require('path');
// Run from frontend/ (npm install --save-dev playwright lives there): `node ../scripts/scratch/test_party_filter.js`
const { chromium } = require(path.resolve(process.cwd(), 'node_modules', 'playwright'));
const out = (name) => path.join(__dirname, name);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 2400 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(String(err)));

  await page.goto('http://localhost:4321/topics/stikstof/', { waitUntil: 'networkidle' });

  const chart = await page.waitForSelector('.party-chart', { timeout: 15000 });
  await chart.scrollIntoViewIfNeeded();
  const box = await chart.boundingBox();
  console.log('chart box:', box);
  await page.screenshot({ path: out('shot_1_before.png'), fullPage: true });
  const headersBefore = await page.locator('h2').allTextContents();
  console.log('column headers BEFORE:', headersBefore);

  // click near the vertical middle-left of the chart, where a bar is likely
  const x = box.x + box.width * 0.4;
  const y = box.y + box.height * 0.5;
  await page.mouse.click(x, y);
  await page.waitForTimeout(500);

  const filterBannerText = await page.locator('text=Gefilterd op partij').textContent().catch(() => null);
  console.log('filter banner:', filterBannerText);

  const banner = await page.locator('text=Gefilterd op partij').first();
  const bannerBox = await banner.boundingBox();
  await page.screenshot({ path: out('shot_2b_banner.png'), clip: { x: 0, y: Math.max(0, bannerBox.y - 20), width: 1280, height: 200 } });

  const headers = await page.locator('h2').allTextContents();
  console.log('column headers:', headers);

  const firstH2 = await page.locator('h2').first().boundingBox();
  await page.screenshot({ path: out('shot_2c_columns.png'), clip: { x: 0, y: Math.max(0, firstH2.y - 20), width: 1280, height: 600 } });

  await page.locator('button:has-text("alles tonen")').first().click();
  await page.waitForTimeout(300);
  const headersAfterClear = await page.locator('h2').allTextContents();
  console.log('column headers AFTER CLEAR:', headersAfterClear);

  console.log('CONSOLE ERRORS:', JSON.stringify(errors));

  await browser.close();
})();
