/**
 * Visual test: Homepage / HomePageGrid (T134).
 *
 * Verifies:
 * - Single header (no double-header regression)
 * - Apple-inspired card layout with theme-aware colors
 * - Responsive at 4 viewports (Desktop, Tablet, Mobile, Landscape Mobile)
 * - Dark mode variant (data-theme="dark")
 *
 * Spec 129 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

const HOME_URL = '/';

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

test.describe('Homepage Visual', () => {
  test('single header — no double-header regression', async ({ page }) => {
    await page.goto(HOME_URL);
    await page.waitForLoadState('networkidle');

    const headers = page.locator('header');
    await expect(headers).toHaveCount(1);
  });

  test('no inline styles on page elements', async ({ page }) => {
    await page.goto(HOME_URL);
    await page.waitForLoadState('networkidle');

    const inlineStyleCount = await page.evaluate(() => {
      const main = document.querySelector('main') ?? document.body;
      return main.querySelectorAll('[style]').length;
    });
    expect(inlineStyleCount).toBe(0);
  });

  test('no hardcoded hex colors in rendered HTML', async ({ page }) => {
    await page.goto(HOME_URL);
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
      await page.goto(HOME_URL);
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      await expect(page).toHaveScreenshot(`homepage-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  // ── Dark mode screenshots ──────────────
  for (const viewport of [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 375, height: 667, name: 'mobile' },
  ]) {
    test(`dark mode screenshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(HOME_URL);
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'dark');
      });
      await disableAnimations(page);

      await expect(page).toHaveScreenshot(`homepage-dark-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  test('Collections tile navigates to /collections (not modal)', async ({ page }) => {
    await page.goto(HOME_URL);
    await page.waitForLoadState('networkidle');

    // Click the Collections tile
    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();

    // Should navigate to /collections route, not open a modal
    await page.waitForURL('**/collections');
    expect(page.url()).toContain('/collections');

    // No modal overlay should be visible
    const modal = page.locator('[role="dialog"]');
    expect(await modal.count()).toBe(0);
  });
});
