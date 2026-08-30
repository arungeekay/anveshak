import { chromium } from 'playwright';
import { pathToFileURL } from 'url';
import path from 'path';

const htmlUrl = pathToFileURL(path.resolve('title/title.html')).href;
const b = await chromium.launch();
const pg = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
await pg.goto(htmlUrl);
await pg.waitForTimeout(900);
await pg.screenshot({ path: 'title/title.png' });
await b.close();
console.log('rendered title/title.png');
