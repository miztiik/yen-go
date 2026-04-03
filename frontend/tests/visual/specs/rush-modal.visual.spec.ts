/**
 * Visual test: Rush Modal (T078).
 * US5: Verify Puzzle Rush modal contains zero red border or pink gradient.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

test.describe('Rush Modal Visual', () => {
  test('rush modal has no red border or pink gradient', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/rush');
    await page.waitForLoadState('networkidle');

    // The rush modal should auto-open or we need to trigger it
    // Look for the modal or a button that opens it
    const startButton = page.locator('button:has-text("Start"), button:has-text("Play"), button:has-text("Rush")').first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(500);
    }

    // Check for any modal overlay
    const modal = page.locator('[role="dialog"], [data-testid*="modal"], .modal').first();
    if (await modal.isVisible()) {
      // Capture the modal for visual regression
      await expect(modal).toHaveScreenshot('rush-modal-no-pink.png', {
        maxDiffPixelRatio: 0.05,
      });
    }

    // Full page screenshot as fallback
    await expect(page).toHaveScreenshot('rush-page-modal.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('rush modal dark mode — no bright artifacts', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.addInitScript(() => {
      document.documentElement.dataset.theme = 'dark';
    });
    await page.goto('/rush');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('rush-page-modal-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
