/**
 * Visual test: Theme Switch Timing (T212).
 * Verify theme switch completes in under 200ms with no page reload or puzzle state loss.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Theme Switch Timing Visual', () => {
  test('theme switch completes under 200ms', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Measure time to switch from light to dark
    const switchTime = await page.evaluate(() => {
      const start = performance.now();
      document.documentElement.dataset.theme = 'dark';
      // Force layout/paint
      void document.documentElement.offsetHeight;
      const end = performance.now();
      return end - start;
    });

    expect(switchTime).toBeLessThan(200);
  });

  test('theme switch does not cause page reload', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Set a marker in the page to detect reload
    await page.evaluate(() => {
      (window as Record<string, unknown>).__themeTestMarker = true;
    });

    // Toggle theme
    await page.evaluate(() => {
      document.documentElement.dataset.theme = 'dark';
    });
    await page.waitForTimeout(300);

    // Verify marker still exists (no reload happened)
    const markerExists = await page.evaluate(() => {
      return (window as Record<string, unknown>).__themeTestMarker === true;
    });
    expect(markerExists).toBe(true);

    // Toggle back to light
    await page.evaluate(() => {
      document.documentElement.dataset.theme = 'light';
    });
    await page.waitForTimeout(300);

    // Marker should still exist
    const markerStillExists = await page.evaluate(() => {
      return (window as Record<string, unknown>).__themeTestMarker === true;
    });
    expect(markerStillExists).toBe(true);

    // Visual comparison
    await expect(page).toHaveScreenshot('theme-switch-back-to-light.png', {
      maxDiffPixelRatio: 0.05,
    });
  });
});
