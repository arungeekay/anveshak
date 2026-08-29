// Records a real screen capture of the LIVE ANVESHAK app, with on-screen caption
// text (no voiceover). Covers every feature, including the Stage-2 additions:
// live FIR intake, Trust Center red-team, Person 360, patrol plan, RBAC scoping,
// the counterfactual and the series replay.
//
//   node record.mjs   ->  out/anveshak-demo.webm
//
// Warm the app first (curl $BASE/api/warm until it reports "warm") and reset demo
// state (POST /api/intake/reset), or SH-07 will already read 16 cases.

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
    #card .p { color:#c9d6e8; font-size:24px; font-weight:500; margin-top:16px; text-align:center; max-width:1150px; }
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
  await sleep(900);
  await installOverlay(page);
}
async function scene(name, fn) {
  try { await fn(); }
  catch (e) { console.log(`scene "${name}": ${e.message.split('\n')[0]}`); }
}

const browser = await chromium.launch({ args: ['--disable-blink-features=AutomationControlled'] });
const ctx = await browser.newContext({
  viewport: { width: W, height: H },
  recordVideo: { dir: OUT, size: { width: W, height: H } },
});
const page = await ctx.newPage();
page.setDefaultTimeout(90000);

await page.goto(BASE, { waitUntil: 'networkidle' });
await page.locator('nav a').first().waitFor({ state: 'visible', timeout: 60000 });
await installOverlay(page);

let packShown = false;
try {
  // ===== INTRO =====
  await card(page, {
    kicker: 'KSP Datathon 2026 · Challenge 1',
    head: 'ANVESHAK &nbsp;·&nbsp; ಅನ್ವೇಷಕ',
    para: 'An AI that does not just answer questions. It works cases.',
    foot: 'Ask in Kannada or English · every answer backed by evidence · runs 100% on Zoho Catalyst',
  }, 4200);

  // ===== 1. Night Patrol =====
  await scene('leads', async () => {
    await nav(page, 'Lead Feed');
    await cap(page, 'The AI works before you ask',
      'An overnight sweep raises ranked leads: crime spikes, repeat offenders, growing series');
    await page.locator('text=Night Patrol').first().waitFor({ timeout: 60000 }).catch(() => {});
    await sleep(5200);
  });

  // ===== 2. Patrol plan =====
  await scene('patrol plan', async () => {
    await cap(page, 'Analytics that becomes tonight’s deployment',
      'Which station, which hours, which offence, and the tools each recommendation came from');
    await page.locator('button', { hasText: 'Generate' }).first().click();
    await page.locator('text=Whitefield PS').first().waitFor({ timeout: 60000 }).catch(() => {});
    await page.mouse.wheel(0, 600);
    await sleep(5600);
    await page.mouse.wheel(0, -600);
  });

  // ===== 3. Chat + evidence =====
  await scene('chat', async () => {
    await nav(page, 'Chat');
    await cap(page, 'Any officer. Plain language. Instant answer.',
      'No SQL, no analyst queue: ANVESHAK writes the query, runs it, and answers');
    await sleep(1000);
    await page.locator('button', { hasText: 'How many chain snatching' }).first().click();
    await page.locator('text=/chain snatching cases/i').last().waitFor({ timeout: 60000 }).catch(() => {});
    await sleep(2560);
    await cap(page, 'Every answer shows its evidence',
      'The exact SQL, the row count, the case IDs. The AI never invents a number.');
    await page.locator('button', { hasText: 'Evidence' }).first().click().catch(() => {});
    await sleep(5200);
  });

  // ===== 4. Trust Center: let them attack it =====
  await scene('trust', async () => {
    await nav(page, 'Trust Center');
    await cap(page, 'Try to break it',
      'Metrics recomputed on every load, and a console to attack the system yourself');
    await sleep(4000);
    await cap(page, 'Prompt injection, refused',
      'The instruction hidden in the prompt is pulled out and shown being rejected by the sanitizer');
    await page.locator('button', { hasText: 'Prompt injection' }).first().click();
    await sleep(4800);
    await cap(page, 'Profiling by caste, refused',
      'Religion and caste are never model features. The refusal is explained and audit-logged.');
    await page.locator('button', { hasText: 'Profiling by caste' }).first().click();
    await sleep(4800);
    await cap(page, 'History cannot be rewritten',
      'Every audited action hashes the one before it, so tampering breaks the chain');
    await page.locator('button', { hasText: 'Verify chain' }).first().click();
    await sleep(4000);
  });

  // ===== 5. Live FIR intake (the flagship) =====
  await scene('intake', async () => {
    await nav(page, 'New FIR');
    await cap(page, 'File a new FIR in your own words',
      'Typed or dictated in Kannada. ANVESHAK embeds the narrative as it arrives.');
    await sleep(4800);
    await cap(page, 'Registering and linking…', 'Runtime embedding, then the linkage engine re-runs');
    await page.locator('button', { hasText: 'Register FIR' }).first().click();
    await page.locator('text=/joined|matches an existing/i').first().waitFor({ timeout: 90000 }).catch(() => {});
    await sleep(1500);
    await cap(page, 'It just joined a serial-crime series',
      'That FIR was filed seconds ago. It is now case 16 of a ring operating across three districts.');
    await sleep(6400);
  });

  // ===== 6. Series: codename, explanations, counterfactual, replay =====
  await scene('series', async () => {
    await nav(page, 'Series');
    await cap(page, 'Serial crime, across district lines',
      'MO fingerprinting links cases that siloed district records never connect');
    await page.getByText('SH-07', { exact: true }).first().waitFor({ timeout: 60000 }).catch(() => {});
    await sleep(1600);
    await page.getByText('SH-07', { exact: true }).first().click().catch(() => {});
    await cap(page, 'Operation Gold Chain Black Visor',
      'Each link states what the engine matched on, in words an officer can check against the FIRs');
    await sleep(5600);
    await page.mouse.wheel(0, 420);
    await cap(page, 'What it would have changed',
      'Detectable at case 6. Nine further offences across three districts followed over 142 days.');
    await sleep(6000);
    await scene('replay', async () => {
      await page.locator('button', { hasText: 'Replay the series' }).first().click();
      await cap(page, 'Watch it cross the borders',
        'Fifteen offences in date order, hopping between Bengaluru City, Mandya and Tumakuru');
      await sleep(8800);
    });
  });

  // ===== 7. Investigation Cell =====
  await scene('investigation', async () => {
    await nav(page, 'Investigation Room');
    await cap(page, 'Six AI agents work the case, live',
      'Case Officer, Records, Network, History, Legal, Forecast: each streams its reasoning');
    await sleep(1000);
    await page.getByRole('button', { name: 'Investigate' }).click();
    const packHeading = page.locator('h3', { hasText: 'Investigation Pack' });
    const t0 = Date.now();
    while (Date.now() - t0 < 85000) {
      if (await packHeading.count() > 0) { packShown = true; break; }
      await sleep(1200);
    }
    await cap(page, 'A court-ready pack in seconds, not days',
      'Ranked suspects, evidence-cited leads, legal element checks, and a next-strike forecast');
    if (packShown) {
      await sleep(4800);
      await page.mouse.wheel(0, 380); await sleep(4000);
      await page.mouse.wheel(0, 380); await sleep(3600);
    } else { await sleep(4800); }
  });

  // ===== 8. Person 360 =====
  await scene('person', async () => {
    await nav(page, 'Person 360');
    await cap(page, 'One name, the whole footprint',
      'Case history, an explainable risk score, known associates, and the network around them');
    await page.locator('input[placeholder*="Search a person"]').fill('Prakash Rao');
    await page.getByRole('button', { name: 'Search' }).click();
    await sleep(1600);
    await page.locator('button', { hasText: 'Prakash Rao' }).first().click().catch(() => {});
    await sleep(5600);
    await page.mouse.wheel(0, 400);
    await sleep(4000);
  });

  // ===== 9. CrimeGraph =====
  await scene('graph', async () => {
    await nav(page, 'CrimeGraph');
    await cap(page, 'Expose the network behind the crime',
      'Multi-hop questions over a crime knowledge graph reveal hubs, rings and money trails');
    await page.locator('button', { hasText: 'Prakash Rao hub' }).first().click();
    await sleep(6000);
  });

  // ===== 10. Kannada =====
  await scene('kannada', async () => {
    await nav(page, 'Chat');
    await cap(page, 'In the language officers actually speak',
      'Full Kannada and English, by voice or text, built for Karnataka’s force');
    await page.locator('select').last().selectOption('kn').catch(() => {});
    await sleep(600);
    await page.locator('input[placeholder="Ask ANVESHAK…"]')
      .fill('ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?');
    await page.getByRole('button', { name: 'Send' }).click();
    await sleep(5200);
  });

  // ===== 11. RBAC: the governance moment =====
  await scene('rbac', async () => {
    await cap(page, 'Same question, different officer, different answer',
      'Scope is enforced in the query itself, not hidden in the browser');
    await page.locator('header select').first().selectOption('SHO').catch(() => {});
    await sleep(1200);
    await page.locator('select').last().selectOption('en').catch(() => {});
    await page.locator('input[placeholder="Ask ANVESHAK…"]')
      .fill('How many chain snatching cases were registered in Bengaluru City in 2026?');
    await page.getByRole('button', { name: 'Send' }).click();
    await sleep(6000);
  });

  // ===== 12. Audit =====
  await scene('audit', async () => {
    await nav(page, 'Audit');
    await cap(page, 'Everything is on the record',
      'Every question, refusal and investigation logged with its role, in a tamper-evident chain');
    await sleep(4800);
  });

  // ===== OUTRO =====
  await card(page, {
    kicker: 'An AI that does not just answer. It works cases.',
    head: 'ANVESHAK &nbsp;·&nbsp; ಅನ್ವೇಷಕ',
    para: 'Faster answers · serial crime caught across districts · court-ready packs in minutes · proactive leads every morning',
    foot: 'Team Zen: Hiran Vikraman S R · Arun G K   |   github.com/arungeekay/anveshak   |   100% on Zoho Catalyst',
  }, 5200);
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
  console.log('WROTE out/anveshak-demo.webm  (pack shown:', packShown, ')');
}
