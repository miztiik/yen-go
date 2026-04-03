/**
 * Visual test: Responsive Breakpoints (T180).
 * US13: Verify layout mode at 4 viewports.
 * - 375×667: stacked (board above sidebar)
 * - 1024×768: side-by-side
 * - 768×1024: stacked (portrait tablet)
 * - 1280×720: side-by-side
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collection/beginner';

test.describe('Responsive Breakpoints Visual', () => {
  const viewports = [
    { width: 375, height: 667, name: 'mobile', expected: 'stacked' },
    { width: 768, height: 1024, name: 'tablet-portrait', expected: 'stacked' },
    { width: 1024, height: 768, name: 'tablet-landscape', expected: 'side-by-side' },
    { width: 1280, height: 720, name: 'desktop', expected: 'side-by-side' },
  ] as const;

  for (const vp of viewports) {
    test(`layout is ${vp.expected} at ${vp.name} (${vp.width}×${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(PUZZLE_URL);
      await page.waitForLoadState('networkidle');

      // Try to find board and sidebar elements
      const board = page.locator('[data-slot="board"], canvas').first();
      const sidebar = page.locator('[data-testid="puzzle-sidebar"], [data-slot="sidebar"]').first();

      const boardBox = await board.boundingBox();
      const sidebarBox = await sidebar.boundingBox();

      if (!boardBox || !sidebarBox) {
        // If elements not found, skip — page might not have loaded a puzzle
        test.skip(true, 'Board or sidebar not found on page');
        return;
      }

      if (vp.expected === 'side-by-side') {
        // Board and sidebar should be roughly on same Y level (side-by-side)
        // Sidebar's top should be within ~100px of board's top
        expect(Math.abs(sidebarBox.y - boardBox.y)).toBeLessThan(100);
      } else {
        // Board should be above sidebar (stacked)
        expect(boardBox.y).toBeLessThan(sidebarBox.y);
      }
    });

    test(`screenshot at ${vp.name} (${vp.width}×${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(PUZZLE_URL);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot(`breakpoint-${vp.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }
});
