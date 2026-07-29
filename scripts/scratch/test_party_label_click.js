const path = require('path');
const { chromium } = require(path.resolve(process.cwd(), 'node_modules', 'playwright'));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 2400 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(String(err)));

  await page.goto('http://localhost:4321/topics/stikstof/', { waitUntil: 'networkidle' });
  await page.waitForSelector('.party-chart svg text', { timeout: 15000 });

  const headersBefore = await page.locator('h2').allTextContents();
  console.log('column headers BEFORE:', headersBefore);

  await page.locator('.party-chart svg text', { hasText: 'BBB' }).first().click();
  await page.waitForTimeout(400);

  const filterBannerText = await page.locator('text=Gefilterd op partij').textContent().catch(() => null);
  console.log('filter banner after label click:', filterBannerText);

  const headersAfterLabelClick = await page.locator('h2').allTextContents();
  console.log('column headers AFTER LABEL CLICK:', headersAfterLabelClick);

  await page.locator('button:has-text("alles tonen")').first().click();
  await page.waitForTimeout(300);
  console.log('column headers AFTER CLEAR:', await page.locator('h2').allTextContents());

  console.log('CONSOLE ERRORS:', JSON.stringify(errors));
  await browser.close();
})();
