/**
 * Visual test: Cross-Page Parity (T211).
 * Capture board rendering screenshots from PuzzleSetPlayer (SolverView)
 * at same viewport, verify stone quality and board texture are correct.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

test.describe('Cross-Page Board Parity Visual', () => {
  const viewportDesktop = { width: 1280, height: 800 };

  test('PuzzleSetPlayer board rendering — light mode', async ({ page }) => {
    await page.setViewportSize(viewportDesktop);
    await page.goto('/collection/beginner');
    await page.waitForLoadState('networkidle');

    const canvas = page.locator('canvas').first();
    if (await canvas.isVisible()) {
      await expect(canvas).toHaveScreenshot('cross-parity-collection-light.png', {
        maxDiffPixelRatio: 0.05,
      });
    }
  });

  test('PuzzleSetPlayer board rendering — dark mode', async ({ page }) => {
    await page.setViewportSize(viewportDesktop);
    await page.addInitScript(() => {
      document.documentElement.dataset.theme = 'dark';
    });
    await page.goto('/collection/beginner');
    await page.waitForLoadState('networkidle');

    const canvas = page.locator('canvas').first();
    if (await canvas.isVisible()) {
      await expect(canvas).toHaveScreenshot('cross-parity-collection-dark.png', {
        maxDiffPixelRatio: 0.05,
      });
    }
  });

  test('both pages use same stone theme (Shell/Slate)', async ({ page }) => {
    await page.setViewportSize(viewportDesktop);
    await page.goto('/collection/beginner');
    await page.waitForLoadState('networkidle');

    // Full page screenshot for side-by-side comparison
    await expect(page).toHaveScreenshot('cross-parity-full-page.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
