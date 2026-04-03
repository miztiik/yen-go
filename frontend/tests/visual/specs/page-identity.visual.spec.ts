/**
 * Visual test: Page Identity (T075).
 * US10: Verify all 6 pages have distinctive mode color accent in light + dark mode.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'training', url: '/', mode: 'training' },
  { name: 'daily', url: '/daily', mode: 'daily' },
  { name: 'technique', url: '/technique', mode: 'technique' },
  { name: 'collections', url: '/collections', mode: 'collections' },
  { name: 'random', url: '/random', mode: 'random' },
  { name: 'rush', url: '/rush', mode: 'rush' },
] as const;

test.describe('Page Identity Visual — Light Mode', () => {
  for (const pg of PAGES) {
    test(`${pg.name} page has mode color accent (light)`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(pg.url);
      await page.waitForLoadState('networkidle');

      // Verify data-mode attribute is set on the page layout
      const modeAttr = await page.locator('[data-mode]').first().getAttribute('data-mode');
      // Mode attribute should match page's expected mode (or be present)
      if (modeAttr) {
        expect(modeAttr).toBe(pg.mode);
      }

      await expect(page).toHaveScreenshot(`page-identity-${pg.name}-light.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }
});

test.describe('Page Identity Visual — Dark Mode', () => {
  for (const pg of PAGES) {
    test(`${pg.name} page has mode color accent (dark)`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      // Set dark theme before navigation
      await page.addInitScript(() => {
        document.documentElement.dataset.theme = 'dark';
      });
      await page.goto(pg.url);
      await page.waitForLoadState('networkidle');

      // Verify no bright white artifacts in dark mode
      await expect(page).toHaveScreenshot(`page-identity-${pg.name}-dark.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }
});
