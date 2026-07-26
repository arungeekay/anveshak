// Records a real screen capture of the LIVE ANVESHAK app doing the full demo, with
// on-screen caption text (no voiceover) that markets each feature. Node Playwright.
//
//   node record.mjs   ->  out/anveshak-demo.webm
//
// The app must be WARM before running (open Series + Lead Feed once, wait ~90s).

import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'https://anveshak-api-50044329134.development.catalystappsail.in/ui/';
const W = 1600, H = 900;
const OUT = 'out';
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function installOverlay(page) {
  await page.addStyleTag({ content: `
    #cap { position:fixed; left:0; right:0; bottom:0; z-index:2147483000;
      pointer-events:none; font-family:Inter,Segoe UI,sans-serif;
      background:linear-gradient(0deg, rgba(2,6,23,.97) 0%, rgba(2,6,23,.85) 68%, rgba(2,6,23,0) 100%);
      padding:26px 44px 24px; }
    #cap .t { color:#fff; font-size:31px; font-weight:700; letter-spacing:.2px;
      text-shadow:0 2px 10px rgba(0,0,0,.6); }
    #cap .s { color:#9fc4ff; font-size:19px; font-weight:500; margin-top:5px; }
    #card { position:fixed; inset:0; z-index:2147483600; pointer-events:none;
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      background:radial-gradient(1200px 600px at 50% 40%, rgba(11,31,58,.98), rgba(2,6,23,.99));
      font-family:Inter,sans-serif; opacity:0; transition:opacity .35s; }
    #card.show { opacity:1; }
    #card .k { color:#5ab0ff; font-size:22px; font-weight:600; letter-spacing:3px; text-transform:uppercase; }
    #card .h { color:#fff; font-size:54px; font-weight:800; margin-top:14px; text-align:center; }
    #card .p { color:#c9d6e8; font-size:24px; font-weight:500; margin-top:16px; text-align:center; max-width:1100px; }
    #card .f { color:#8aa0bd; font-size:18px; margin-top:34px; text-align:center; }
  ` });
  await page.evaluate(() => {
    if (!document.getElementById('cap')) {
      const c = document.createElement('div'); c.id = 'cap';
      c.innerHTML = '<div class="t"></div><div class="s"></div>';
      document.body.appendChild(c);
    }
    if (!document.getElementById('card')) {
      const d = document.createElement('div'); d.id = 'card';
      d.innerHTML = '<div class="k"></div><div class="h"></div><div class="p"></div><div class="f"></div>';
      document.body.appendChild(d);
    }
  });
}
async function cap(page, t, s = '') {
  await page.evaluate(([t, s]) => {
    const c = document.getElementById('cap'); if (!c) return;
    c.querySelector('.t').textContent = t; c.querySelector('.s').textContent = s;
  }, [t, s]);
}
async function card(page, { kicker = '', head = '', para = '', foot = '' }, ms = 4000) {
  await page.evaluate(([k, h, p, f]) => {
    const c = document.getElementById('card'); if (!c) return;
    c.querySelector('.k').textContent = k; c.querySelector('.h').innerHTML = h;
    c.querySelector('.p').textContent = p; c.querySelector('.f').textContent = f;
    c.classList.add('show');
  }, [kicker, head, para, foot]);
  await sleep(ms);
  await page.evaluate(() => document.getElementById('card')?.classList.remove('show'));
  await sleep(450);
}
async function nav(page, label) {
  const link = page.locator('nav a', { hasText: label }).first();
  await link.waitFor({ state: 'visible', timeout: 30000 });
  await link.click();
  await sleep(800);
}
async function scene(name, fn) {
  try { await fn(); }
  catch (e) { console.log(`scene "${name}" issue: ${e.message.split('\n')[0]}`); }
}

async function main() {
  const browser = await chromium.launch({ args: ['--disable-blink-features=AutomationControlled'] });
  const ctx = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: OUT, size: { width: W, height: H } },
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(90000);

  await page.goto(BASE, { waitUntil: 'networkidle' });
  // Ensure the SPA has actually rendered (nav present) before driving it.
  await page.locator('nav a').first().waitFor({ state: 'visible', timeout: 60000 });
  await installOverlay(page);

  let shown = false; // whether the Investigation Pack rendered (scene 5)
  try {
  // ===== INTRO CARD =====
  await card(page, {
    kicker: 'KSP Datathon 2026 · Challenge 1',
    head: 'ANVESHAK &nbsp;·&nbsp; ಅನ್ವೇಷಕ',
    para: 'An autonomous AI investigation bureau for the Karnataka State Police',
    foot: 'Ask in Kannada or English · every answer backed by evidence · runs 100% on Zoho Catalyst',
  }, 5000);

  // ===== Scene 1 — Night Patrol =====
  await nav(page, 'Lead Feed'); await installOverlay(page);
  await cap(page, 'Night Patrol — the AI works before you ask',
    'Overnight detectors raise ranked leads: crime spikes, repeat offenders, growing series — proactive policing, not reactive');
  await page.locator('text=Night Patrol').first().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(7000);

  // ===== Scene 2 — Ask in English + evidence =====
  await nav(page, 'Chat'); await installOverlay(page);
  await cap(page, 'Any officer. Plain language. Instant answer.',
    'No SQL, no analyst queue — ANVESHAK writes the query, runs it, and answers');
  await sleep(1000);
  await page.locator('button', { hasText: 'How many chain snatching' }).first().click();
  await page.locator('text=/chain snatching cases/i').last().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(3500);
  await cap(page, 'Every answer shows its evidence',
    'The exact SQL, the row count, the case IDs — the AI never invents a number. Court-defensible by design.');
  await page.locator('button', { hasText: 'Evidence' }).first().click().catch(() => {});
  await sleep(6500);

  // ===== Scene 3 — charts on demand =====
  await cap(page, 'From a question to insight in seconds',
    'Trends and hotspots that used to need a data team — now on demand');
  await page.locator('button', { hasText: 'Show the monthly trend' }).first().click();
  await sleep(6500);

  // ===== Scene 4 — Serial linkage (Series) =====
  await nav(page, 'Series'); await installOverlay(page);
  await cap(page, 'Catch serial offenders across district lines',
    'MO fingerprinting links cases that siloed district records would never connect');
  await page.getByText('SH-07', { exact: true }).first().waitFor({ timeout: 60000 }).catch(() => {});
  await sleep(2000);
  await page.getByText('SH-07', { exact: true }).first().click().catch(() => {});
  await cap(page, 'SH-07 — one ring, 15 cases, 3 districts',
    'Shared modus operandi, cosine-linked — a serial series discovered cold, with the evidence for each link');
  await sleep(7000);

  // ===== Scene 5 — AI Investigation Cell (centerpiece) =====
  await nav(page, 'Investigation Room'); await installOverlay(page);
  await cap(page, 'Six AI agents work the case — live',
    'Case Officer → Records → Network → History → Legal → Forecast, streaming their reasoning');
  await sleep(1000);
  await page.getByRole('button', { name: 'Investigate' }).click();
  // Poll for the actual pack heading (an <h3> — won't collide with caption text).
  const packHeading = page.locator('h3', { hasText: 'Investigation Pack' });
  const t0 = Date.now();
  while (Date.now() - t0 < 85000) {
    if (await packHeading.count() > 0) { shown = true; break; }
    await sleep(1500);
  }
  await cap(page, 'A court-ready Investigation Pack in ~2 minutes, not 2 days',
    'Ranked suspects · evidence-cited leads · legal element checks · next-strike forecast');
  if (shown) {
    await packHeading.scrollIntoViewIfNeeded().catch(() => {});
    await sleep(6000);
    // scroll down to reveal leads / legal / forecast sections
    await page.mouse.wheel(0, 380); await sleep(5000);
    await page.mouse.wheel(0, 380); await sleep(4500);
  } else {
    await sleep(6000);
  }

  // ===== Scene 6 — CrimeGraph =====
  await nav(page, 'CrimeGraph'); await installOverlay(page);
  await cap(page, 'Expose the network behind the crime',
    'Multi-hop questions over a crime knowledge graph reveal hubs, rings and money trails');
  await page.locator('button', { hasText: 'Prakash Rao hub' }).first().click();
  await sleep(8000);

  // ===== Scene 7 — Bilingual (Kannada) =====
  await nav(page, 'Chat'); await installOverlay(page);
  await cap(page, 'In the language officers actually speak',
    'Full Kannada + English, by voice or text — built for Karnataka’s force');
  await page.locator('select').last().selectOption('kn').catch(() => {});
  await sleep(600);
  await page.locator('input[placeholder="Ask ANVESHAK…"]')
    .fill('ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?');
  await page.getByRole('button', { name: 'Send' }).click();
  await sleep(6500);

  // ===== Scene 8 — Governance =====
  await nav(page, 'Audit'); await installOverlay(page);
  await cap(page, 'Trustworthy, accountable, court-defensible',
    'Every action audit-logged · role-based access (SHO/SP/SCRB) · no protected attributes in any model');
  await sleep(6000);

  // ===== OUTRO CARD =====
  await card(page, {
    kicker: 'An AI that doesn’t just answer — it works cases',
    head: 'ANVESHAK &nbsp;·&nbsp; ಅನ್ವೇಷಕ',
    para: 'Faster answers · serial crime caught across districts · court-ready packs in minutes · proactive leads every morning',
    foot: 'Team Zen — Hiran Vikraman S R · Arun G K   |   github.com/arungeekay/anveshak   |   100% on Zoho Catalyst',
  }, 6500);
  } catch (e) {
    console.log('scene error (finalizing anyway):', e.message.split('\n')[0]);
  } finally {
    await page.close().catch(() => {});
    await ctx.close().catch(() => {});
    await browser.close().catch(() => {});
  }
  const files = fs.readdirSync(OUT).filter((f) => f.endsWith('.webm'));
  if (files.length) {
    const newest = files.map((f) => ({ f, t: fs.statSync(`${OUT}/${f}`).mtimeMs }))
      .sort((a, b) => b.t - a.t)[0].f;
    if (fs.existsSync(`${OUT}/anveshak-demo.webm`)) fs.rmSync(`${OUT}/anveshak-demo.webm`);
    fs.renameSync(`${OUT}/${newest}`, `${OUT}/anveshak-demo.webm`);
    console.log('WROTE out/anveshak-demo.webm  (pack shown:', shown, ')');
  }
}
main().catch((e) => { console.error('FATAL', e); process.exit(1); });
