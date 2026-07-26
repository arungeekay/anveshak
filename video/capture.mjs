// Capture clean screenshots (no caption overlay) of the LIVE app for the deck's
// "Snapshots" slide.  node capture.mjs  ->  shots/*.png
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'https://anveshak-api-50044329134.development.catalystappsail.in/ui/';
const OUT = 'shots';
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function nav(page, label) {
  const link = page.locator('nav a', { hasText: label }).first();
  await link.waitFor({ state: 'visible', timeout: 30000 });
  await link.click();
  await sleep(1000);
}

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(90000);
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.locator('nav a').first().waitFor({ state: 'visible', timeout: 60000 });
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });

try {
  // 1. Lead Feed
  await nav(page, 'Lead Feed');
  await page.locator('text=Night Patrol').first().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(2500); await shot('01_leadfeed');

  // 2. Chat + evidence drawer
  await nav(page, 'Chat');
  await page.locator('button', { hasText: 'How many chain snatching' }).first().click();
  await page.locator('text=/chain snatching cases/i').last().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(2500);
  await page.locator('button', { hasText: 'Evidence' }).first().click().catch(() => {});
  await sleep(1500); await shot('02_chat_evidence');

  // 3. Series (SH-07 expanded)
  await nav(page, 'Series');
  await page.getByText('SH-07', { exact: true }).first().waitFor({ timeout: 60000 }).catch(() => {});
  await page.getByText('SH-07', { exact: true }).first().click().catch(() => {});
  await sleep(1800); await shot('03_series');

  // 4. Investigation Pack
  await nav(page, 'Investigation Room');
  await page.getByRole('button', { name: 'Investigate' }).click();
  const packHeading = page.locator('h3', { hasText: 'Investigation Pack' });
  const t0 = Date.now();
  while (Date.now() - t0 < 85000) { if (await packHeading.count() > 0) break; await sleep(1500); }
  await sleep(2000); await shot('04_pack');

  // 5. CrimeGraph
  await nav(page, 'CrimeGraph');
  await page.locator('button', { hasText: 'Prakash Rao hub' }).first().click();
  await sleep(3500); await shot('05_graph');

  // 6. Kannada chat
  await nav(page, 'Chat');
  await page.locator('select').last().selectOption('kn').catch(() => {});
  await page.locator('input[placeholder="Ask ANVESHAK…"]')
    .fill('ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?');
  await page.getByRole('button', { name: 'Send' }).click();
  await page.locator('text=ಫಲಿತಾಂಶ').first().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(1500); await shot('06_kannada');
  console.log('shots done:', fs.readdirSync(OUT).join(', '));
} catch (e) { console.log('capture issue:', e.message.split('\n')[0]); }
finally { await ctx.close(); await b.close(); }
