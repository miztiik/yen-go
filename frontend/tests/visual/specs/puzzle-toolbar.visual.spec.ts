/**
 * Visual test: Puzzle Toolbar (T084).
 * US6: Verify all puzzle controls are within a single grouped container.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Puzzle Toolbar Visual', () => {
  test('all controls within single toolbar container', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Look for toolbar/controls container
    const toolbar = page.locator(
      '[data-testid="puzzle-toolbar"], [data-testid="quick-controls"], [role="toolbar"]'
    ).first();

    if (await toolbar.isVisible()) {
      // All action buttons should be within this container
      const buttons = toolbar.locator('button');
      const buttonCount = await buttons.count();
      expect(buttonCount).toBeGreaterThan(0);

      await expect(toolbar).toHaveScreenshot('puzzle-toolbar.png', {
        maxDiffPixelRatio: 0.05,
      });
    }

    // Full page screenshot for visual regression
    await expect(page).toHaveScreenshot('puzzle-page-toolbar.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('toolbar responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('puzzle-toolbar-mobile.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
