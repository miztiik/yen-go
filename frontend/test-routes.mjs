import { chromium } from 'playwright';

const browser = await chromium.launch();
const context = await browser.newContext();

const errors = [];
const logs = [];

const urls = [
  'http://localhost:5173/yen-go/contexts/training/beginner',
  'http://localhost:5173/yen-go/contexts/technique/ko',
  'http://localhost:5173/yen-go/contexts/collection/curated-yamada-tsumego-collection',
];

for (const url of urls) {
  const page = await context.newPage();
  page.on('console', msg => logs.push({ url, type: msg.type(), text: msg.text() }));
  page.on('pageerror', error => errors.push({ url, error: error.message }));

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    const title = await page.title();
    const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 500) || '');
    console.log('=== ' + url + ' ===');
    console.log('Title:', title);
    console.log('Body preview:', bodyText.substring(0, 300));

    // Check for error states
    const errorElem = await page.locator('[data-testid*="error"]').first();
    const hasError = await errorElem.count() > 0;
    if (hasError) {
      const text = await errorElem.textContent();
      console.log('ERROR STATE FOUND:', text);
    }

    // Check for skeleton loading (still loading)
    const skeleton = await page.locator('.animate-pulse').first();
    const hasSkeleton = (await skeleton.count()) > 0;
    if (hasSkeleton) {
      console.log('SKELETON LOADING STATE (still loading)');
    }

    // Check what data-testid elements exist
    const testIds = await page.evaluate(() => {
      const elements = document.querySelectorAll('[data-testid]');
      return Array.from(elements).map(el => el.getAttribute('data-testid'));
    });
    console.log('Test IDs found:', testIds.slice(0, 15));
    console.log();
  } catch (e) {
    console.log('Navigation error for', url, ':', e.message);
  }
  await page.close();
}

if (errors.length > 0) {
  console.log('\nPage errors:');
  errors.forEach(e => console.log('  ', e.url.split('/').pop(), '->', e.error));
}

const warnLogs = logs.filter(l => l.type === 'error' || l.type === 'warning');
if (warnLogs.length > 0) {
  console.log('\nConsole errors/warnings:');
  warnLogs.forEach(l => console.log('  ', l.url.split('/').pop(), '[' + l.type + ']', l.text));
}

await browser.close();
