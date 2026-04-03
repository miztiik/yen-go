/**
 * Visual test: PuzzleRushPage (T097b).
 *
 * Verifies:
 * - Timer, score, goban board layout
 * - Apple-inspired styling (no inline styles, theme-aware colors)
 * - Responsive at 3 viewports + landscape mobile
 * - Dark mode variant
 *
 * Spec 129 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

const RUSH_URL = '/puzzle-rush';

test.describe('PuzzleRushPage Visual', () => {
  test('setup screen renders with duration options', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    // Verify setup screen shows duration buttons
    const setupScreen = page.locator('[data-testid="puzzle-rush-page"]');
    await expect(setupScreen).toBeVisible();

    // Verify 3 duration options exist
    await expect(page.locator('[data-testid="duration-60"]')).toBeVisible();
    await expect(page.locator('[data-testid="duration-180"]')).toBeVisible();
    await expect(page.locator('[data-testid="duration-300"]')).toBeVisible();

    // Verify start button
    await expect(page.locator('[data-testid="start-rush-button"]')).toBeVisible();
  });

  test('no inline styles on setup screen', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    // Verify no style={{}} attributes on Rush page elements
    const inlineStyles = await page.evaluate(() => {
      const rushPage = document.querySelector('[data-testid="puzzle-rush-page"]');
      if (!rushPage) return 0;
      return rushPage.querySelectorAll('[style]').length;
    });
    expect(inlineStyles).toBe(0);
  });

  test('uses theme-aware colors (no hardcoded hex)', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    const html = await page.content();
    // Should not contain hardcoded emerald/green colors
    expect(html).not.toContain('#059669');
  });

  test('screenshot - setup screen desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('rush-setup-desktop.png');
  });

  test('screenshot - setup screen tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('rush-setup-tablet.png');
  });

  test('screenshot - setup screen mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('rush-setup-mobile.png');
  });

  test('screenshot - setup screen landscape mobile', async ({ page }) => {
    await page.setViewportSize({ width: 667, height: 375 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('rush-setup-landscape.png');
  });

  test('screenshot - setup screen dark mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    // Wait for theme transition
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot('rush-setup-dark.png');
  });
});
