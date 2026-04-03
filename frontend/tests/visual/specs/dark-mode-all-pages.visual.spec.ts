/**
 * Visual test: Dark Mode All Pages (T110).
 * Verify zero bright/white artifacts on all 6 pages × 3 viewports in dark mode.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'training', url: '/' },
  { name: 'daily', url: '/daily' },
  { name: 'technique', url: '/technique' },
  { name: 'collections', url: '/collections' },
  { name: 'random', url: '/random' },
  { name: 'rush', url: '/rush' },
] as const;

const VIEWPORTS = [
  { width: 1280, height: 800, name: 'desktop' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 375, height: 667, name: 'mobile' },
] as const;

test.describe('Dark Mode All Pages', () => {
  test.beforeEach(async ({ page }) => {
    // Set dark theme before navigation
    await page.addInitScript(() => {
      document.documentElement.dataset.theme = 'dark';
    });
  });

  for (const pg of PAGES) {
    for (const vp of VIEWPORTS) {
      test(`${pg.name} ${vp.name} — no bright artifacts`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(pg.url);
        await page.waitForLoadState('networkidle');

        await expect(page).toHaveScreenshot(
          `dark-${pg.name}-${vp.name}.png`,
          {
            fullPage: true,
            maxDiffPixelRatio: 0.05,
          }
        );
      });
    }
  }
});
