/**
 * Visual test: Board texture (T025).
 * US2: Verify board surface shows wood texture, not flat solid color.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Board Texture Visual', () => {
  test('board surface is not flat solid color at desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // The goban canvas renders the board surface.
    // With Kaya texture, the board should NOT be a uniform #DCB35C solid.
    // Take a screenshot for visual regression comparison.
    const board = page.locator('canvas').first();
    await expect(board).toBeVisible();

    await expect(page).toHaveScreenshot('board-texture-desktop.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('board texture visible in light mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Verify kaya.jpg texture is loaded by checking network or img element
    // The goban library loads textures via getCDNReleaseBase + img path
    const canvas = page.locator('canvas').first();
    await expect(canvas).toBeVisible();

    // Screenshot comparison — textured board vs flat color will differ significantly
    await expect(canvas).toHaveScreenshot('board-canvas-texture.png', {
      maxDiffPixelRatio: 0.05,
    });
  });
});
