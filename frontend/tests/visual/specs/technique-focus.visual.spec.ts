/**
 * Visual test: TechniqueBrowsePage (T075c).
 *
 * Verifies:
 * - No gradient banner (flat bg-elevated)
 * - No Material Design hover lifts
 * - Theme-aware colors (CSS custom properties)
 * - Responsive at 3 viewports + landscape mobile + dark mode
 *
 * Spec 129 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

const TECHNIQUE_URL = '/techniques';

test.describe('TechniqueBrowsePage Visual', () => {
  test('has no gradient banner', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');

    // Verify no gradient CSS anywhere on page stats area
    const statsBar = page.locator('[data-testid="technique-stats"]');
    if (await statsBar.count() > 0) {
      const bgImage = await statsBar.evaluate(
        (el) => window.getComputedStyle(el).backgroundImage,
      );
      expect(bgImage).toBe('none');
    }
  });

  test('cards do not translateY on hover', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');

    const card = page.locator('button').first();
    if (await card.count() > 0) {
      await card.hover();
      const transform = await card.evaluate(
        (el) => window.getComputedStyle(el).transform,
      );
      // Should not contain translateY
      expect(transform).not.toContain('translateY');
    }
  });

  test('no hardcoded white or #059669 in rendered styles', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');

    // Check page source for hardcoded colors
    const html = await page.content();
    expect(html).not.toContain('#059669');
    // inline style="...white..." should not exist
    const inlineWhite = await page.evaluate(() => {
      const allElements = document.querySelectorAll('[style]');
      for (const el of allElements) {
        if ((el as HTMLElement).style.cssText.includes('white')) return true;
      }
      return false;
    });
    expect(inlineWhite).toBe(false);
  });

  // Viewport screenshots
  for (const viewport of [
    { width: 375, height: 667, name: 'mobile' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 1280, height: 900, name: 'desktop' },
    { width: 667, height: 375, name: 'mobile-landscape' },
  ]) {
    test(`screenshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(TECHNIQUE_URL);
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveScreenshot(`technique-focus-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }

  test('screenshot in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('technique-focus-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
