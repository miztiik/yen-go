/**
 * Tailwind v4 Styling Audit — Screenshot key pages after Tailwind migration.
 * Captures solver page (with puzzle), home, training, daily in both themes.
 */
import { test } from '@playwright/test';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCREENSHOT_DIR = resolve(__dirname, '../baselines/tailwind-audit');

const PAGES = [
  { name: 'home', path: '/' },
  { name: 'training', path: '/training' },
  { name: 'daily', path: '/daily' },
  { name: 'collections', path: '/collections' },
  { name: 'random', path: '/random' },
  { name: 'puzzle-rush', path: '/puzzle-rush' },
  { name: 'solver-elementary', path: '/collections/level-elementary' },
];

for (const page of PAGES) {
  test(`${page.name} — light`, async ({ browser }) => {
    const ctx = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      colorScheme: 'light',
    });
    const p = await ctx.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    await p.waitForTimeout(1000);
    await p.screenshot({
      path: resolve(SCREENSHOT_DIR, `${page.name}-light.png`),
      fullPage: true,
    });
    await ctx.close();
  });

  test(`${page.name} — dark`, async ({ browser }) => {
    const ctx = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      colorScheme: 'dark',
    });
    const p = await ctx.newPage();
    await p.goto(page.path);
    await p.waitForLoadState('networkidle');
    // Toggle dark theme if app uses data-theme
    await p.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await p.waitForTimeout(1000);
    await p.screenshot({
      path: resolve(SCREENSHOT_DIR, `${page.name}-dark.png`),
      fullPage: true,
    });
    await ctx.close();
  });
}
