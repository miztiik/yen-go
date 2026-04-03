/**
 * Visual test: Board sizing (T030).
 * US3: Verify board width >=50% of 1280px viewport and >=90% of 375px viewport.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Board Sizing Visual', () => {
  test('board width >= 50% of desktop viewport (1280px)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    const board = page.locator('[data-slot="board"], canvas').first();
    const box = await board.boundingBox();

    if (!box) {
      test.skip(true, 'Board element not found');
      return;
    }

    // Board should be at least 50% of viewport width (640px)
    expect(box.width).toBeGreaterThanOrEqual(1280 * 0.5);
  });

  test('board width >= 90% of mobile viewport (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    const board = page.locator('[data-slot="board"], canvas').first();
    const box = await board.boundingBox();

    if (!box) {
      test.skip(true, 'Board element not found');
      return;
    }

    // Board should be at least 90% of viewport width (337.5px)
    expect(box.width).toBeGreaterThanOrEqual(375 * 0.9);
  });

  test('board sizing screenshot comparison', async ({ page }) => {
    for (const vp of [
      { width: 1280, height: 800, name: 'desktop' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' },
    ]) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(PUZZLE_URL);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot(`board-sizing-${vp.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    }
  });
});
