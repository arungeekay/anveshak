// Clean screenshots (no caption overlay) of the LIVE app for the deck.
//   node capture.mjs  ->  shots/*.png
// Warm the app and POST /api/intake/reset first.
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
  await sleep(1200);
}

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(90000);
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.locator('nav a').first().waitFor({ state: 'visible', timeout: 60000 });
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });

async function step(name, fn) {
  try { await fn(); console.log('  ok', name); }
  catch (e) { console.log('  skip', name, e.message.split('\n')[0]); }
}

try {
  await step('01 lead feed', async () => {
    await nav(page, 'Lead Feed');
    await page.locator('text=Night Patrol').first().waitFor({ timeout: 60000 });
    await sleep(2500); await shot('01_leadfeed');
  });

  await step('02 chat + evidence', async () => {
    await nav(page, 'Chat');
    await page.locator('button', { hasText: 'How many chain snatching' }).first().click();
    await page.locator('text=/chain snatching cases/i').last().waitFor({ timeout: 60000 });
    await sleep(2500);
    await page.locator('button', { hasText: 'Evidence' }).first().click().catch(() => {});
    await sleep(1500); await shot('02_chat_evidence');
  });

  await step('07 intake', async () => {
    await nav(page, 'New FIR');
    await page.locator('button', { hasText: 'Register FIR' }).first().click();
    await page.locator('text=/joined|matches an existing/i').first()
      .waitFor({ timeout: 90000 }).catch(() => {});
    await sleep(2000); await shot('07_intake');
  });

  await step('03 series', async () => {
    await nav(page, 'Series');
    await page.getByText('SH-07', { exact: true }).first().waitFor({ timeout: 60000 });
    await page.getByText('SH-07', { exact: true }).first().click();
    await sleep(2000); await shot('03_series');
  });

  await step('04 pack', async () => {
    await nav(page, 'Investigation Room');
    await page.getByRole('button', { name: 'Investigate' }).click();
    const h = page.locator('h3', { hasText: 'Investigation Pack' });
    const t0 = Date.now();
    while (Date.now() - t0 < 85000) { if (await h.count() > 0) break; await sleep(1200); }
    await sleep(2000); await shot('04_pack');
  });

  await step('09 person 360', async () => {
    await nav(page, 'Person 360');
    await page.locator('input[placeholder*="Search a person"]').fill('Prakash Rao');
    await page.getByRole('button', { name: 'Search' }).click();
    await sleep(1800);
    await page.locator('button', { hasText: 'Prakash Rao' }).first().click().catch(() => {});
    await sleep(3500); await shot('09_person');
  });

  await step('08 trust center', async () => {
    await nav(page, 'Trust Center');
    await sleep(3000);
    await page.locator('button', { hasText: 'Prompt injection' }).first().click();
    await sleep(2500); await shot('08_trust');
  });

  await step('05 graph', async () => {
    await nav(page, 'CrimeGraph');
    await page.locator('button', { hasText: 'Prakash Rao hub' }).first().click();
    await sleep(3500); await shot('05_graph');
  });

  await step('06 kannada', async () => {
    await nav(page, 'Chat');
    await page.locator('select').last().selectOption('kn').catch(() => {});
    await page.locator('input[placeholder="Ask ANVESHAK…"]')
      .fill('ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?');
    await page.getByRole('button', { name: 'Send' }).click();
    await page.locator('text=ಫಲಿತಾಂಶ').first().waitFor({ timeout: 60000 }).catch(() => {});
    await sleep(1500); await shot('06_kannada');
  });

  console.log('shots:', fs.readdirSync(OUT).join(', '));
} finally { await ctx.close(); await b.close(); }
