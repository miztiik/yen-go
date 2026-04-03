/**
 * Final Unified screenshots — All 6 pages x 2 viewports x 2 themes = 24 screenshots.
 * T-U37, T-U38
 */
import { test } from '@playwright/test';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCREENSHOT_DIR = resolve(__dirname, '../baselines/final-unified');

const PAGES = [
  { name: 'home', path: '/' },
  { name: 'daily', path: '/daily' },
  { name: 'rush', path: '/puzzle-rush' },
  { name: 'collections', path: '/collections' },
  { name: 'training', path: '/training' },
  { name: 'random', path: '/random' },
  { name: 'technique', path: '/technique/tesuji' },
];

for (const page of PAGES) {
  test(`${page.name} — desktop light`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      colorScheme: 'light',
    });
    const p = await context.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    await p.waitForTimeout(800);
    await p.screenshot({ path: resolve(SCREENSHOT_DIR, `${page.name}-desktop-light.png`), fullPage: true });
    await context.close();
  });

  test(`${page.name} — desktop dark`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      colorScheme: 'dark',
    });
    const p = await context.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    await p.waitForTimeout(800);
    await p.screenshot({ path: resolve(SCREENSHOT_DIR, `${page.name}-desktop-dark.png`), fullPage: true });
    await context.close();
  });

  test(`${page.name} — mobile light`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
      colorScheme: 'light',
    });
    const p = await context.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    await p.waitForTimeout(800);
    await p.screenshot({ path: resolve(SCREENSHOT_DIR, `${page.name}-mobile-light.png`), fullPage: true });
    await context.close();
  });

  test(`${page.name} — mobile dark`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
      colorScheme: 'dark',
    });
    const p = await context.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    await p.waitForTimeout(800);
    await p.screenshot({ path: resolve(SCREENSHOT_DIR, `${page.name}-mobile-dark.png`), fullPage: true });
    await context.close();
  });
}
