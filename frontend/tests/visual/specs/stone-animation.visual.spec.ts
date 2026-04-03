/**
 * Visual test: Stone Animation (T188).
 * US14: Verify stone placement triggers a visible animation effect.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Stone Animation Visual', () => {
  test('stone placement triggers animation effect', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Find the board canvas
    const canvas = page.locator('canvas').first();
    await expect(canvas).toBeVisible();

    // Take a "before" screenshot
    const beforeScreenshot = await canvas.screenshot();

    // Click on the canvas to place a stone (approximate center intersection)
    const box = await canvas.boundingBox();
    if (box) {
      // Click somewhere on the board to trigger a move
      await canvas.click({ position: { x: box.width * 0.3, y: box.height * 0.3 } });
      // Brief wait for animation to start (< 200ms animation)
      await page.waitForTimeout(100);

      // Take "during animation" screenshot
      const duringScreenshot = await canvas.screenshot();

      // The screenshots should differ if an animation played
      // (stone appeared, or scale/opacity animation triggered)
      expect(Buffer.compare(beforeScreenshot, duringScreenshot)).not.toBe(0);
    }
  });

  test('board has stone-place animation keyframe defined', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Check that the stone-place animation keyframe is defined in CSS
    const hasAnimation = await page.evaluate(() => {
      const sheets = Array.from(document.styleSheets);
      for (const sheet of sheets) {
        try {
          const rules = Array.from(sheet.cssRules);
          for (const rule of rules) {
            if (rule instanceof CSSKeyframesRule && rule.name === 'stone-place') {
              return true;
            }
          }
        } catch {
          // Cross-origin sheets throw
        }
      }
      return false;
    });

    expect(hasAnimation).toBe(true);
  });
});
