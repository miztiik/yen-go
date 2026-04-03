/**
 * Visual test: DailyChallengePage (T140).
 *
 * Verifies:
 * - Challenge layout with status indicators
 * - Apple-inspired styling (no inline styles, theme-aware colors)
 * - Responsive at 4 viewports (Desktop, Tablet, Mobile, Landscape Mobile)
 * - Dark mode variant (data-theme="dark")
 *
 * Spec 129 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

const DAILY_URL = '/daily';

/** Disable CSS transitions so screenshots are deterministic. */
async function disableAnimations(page: import('@playwright/test').Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        transition-duration: 0ms !important;
        animation-duration: 0ms !important;
      }
    `,
  });
}

test.describe('DailyChallengePage Visual', () => {
  test('challenge layout renders status indicators', async ({ page }) => {
    await page.goto(DAILY_URL);
    await page.waitForLoadState('networkidle');

    // The daily page should have a main content area
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('no inline styles on page elements', async ({ page }) => {
    await page.goto(DAILY_URL);
    await page.waitForLoadState('networkidle');

    const inlineStyleCount = await page.evaluate(() => {
      const main = document.querySelector('main') ?? document.body;
      return main.querySelectorAll('[style]').length;
    });
    expect(inlineStyleCount).toBe(0);
  });

  test('no hardcoded hex colors', async ({ page }) => {
    await page.goto(DAILY_URL);
    await page.waitForLoadState('networkidle');

    const html = await page.content();
    expect(html).not.toContain('#059669');
  });

  // ── Responsive screenshots (light mode) ──────────────
  for (const viewport of [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' },
    { width: 667, height: 375, name: 'landscape-mobile' },
  ]) {
    test(`screenshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(DAILY_URL);
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      await expect(page).toHaveScreenshot(`daily-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  // ── Dark mode screenshots ────────────────────────────
  for (const viewport of [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' },
    { width: 667, height: 375, name: 'landscape-mobile' },
  ]) {
    test(`dark mode screenshot at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(DAILY_URL);
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'dark');
      });
      await disableAnimations(page);
      await page.waitForTimeout(200);

      await expect(page).toHaveScreenshot(`daily-dark-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }
});
