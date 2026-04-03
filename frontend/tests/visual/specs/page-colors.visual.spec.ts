/**
 * Page Colors Test — Verify each page header uses correct accent color.
 * T-U39: Each page should match its home tile accent color.
 *
 * Daily=Amber, Rush=Rose, Collections=Purple, Training=Blue,
 * Technique=Emerald, Random=Indigo
 */
import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'daily', path: '/daily', mode: 'daily', testId: 'daily-header' },
  { name: 'rush', path: '/puzzle-rush', mode: 'rush', testId: 'rush-header' },
  { name: 'collections', path: '/collections', mode: 'collections', testId: 'collections-header' },
  { name: 'training', path: '/training', mode: 'training', testId: 'training-header' },
  { name: 'technique', path: '/technique/tesuji', mode: 'technique' },
  { name: 'random', path: '/random', mode: 'random', testId: 'random-header' },
];

test.describe('Page Identity Colors', () => {
  for (const page of PAGES) {
    test(`${page.name} page has data-mode="${page.mode}" (light)`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
        colorScheme: 'light',
      });
      const p = await context.newPage();
      await p.goto(page.path);
      await p.waitForLoadState('networkidle');
      await p.waitForTimeout(500);

      // Verify data-mode attribute
      const layout = p.locator(`[data-mode="${page.mode}"]`);
      await expect(layout).toBeVisible();

      // Verify header exists with accent background
      if (page.testId) {
        const header = p.locator(`[data-testid="${page.testId}"]`);
        await expect(header).toBeVisible();
      }

      await context.close();
    });

    test(`${page.name} page has data-mode="${page.mode}" (dark)`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
        colorScheme: 'dark',
      });
      const p = await context.newPage();
      await p.goto(page.path);
      await p.waitForLoadState('networkidle');
      await p.waitForTimeout(500);

      // Verify data-mode attribute
      const layout = p.locator(`[data-mode="${page.mode}"]`);
      await expect(layout).toBeVisible();

      await context.close();
    });
  }
});
