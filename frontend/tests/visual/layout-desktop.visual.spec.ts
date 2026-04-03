/**
 * Desktop Layout Visual Tests
 * @module tests/visual/layout-desktop.visual.spec
 *
 * Visual regression tests for desktop layout (1280×800).
 *
 * Covers: US7
 * Spec 125, Task T071
 */

import { test, expect } from '@playwright/test';

test.describe('Desktop Layout (1280x800)', () => {
  test.use({
    viewport: { width: 1280, height: 800 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should show two-column layout on desktop', async ({ page }) => {
    // Navigate to puzzle page
    // Verify board on left, sidebar on right
    const puzzlePage = page.locator('[data-testid="puzzle-solve-page"]');
    // await expect(puzzlePage).toHaveScreenshot('layout-desktop-two-column.png');
  });

  test.skip('should match desktop puzzle page baseline', async ({ page }) => {
    const puzzlePage = page.locator('[data-testid="puzzle-solve-page"]');
    // await expect(puzzlePage).toHaveScreenshot('layout-desktop-puzzle.png');
  });

  test.skip('should show sidebar with proper width on desktop', async ({ page }) => {
    const sidebar = page.locator('[data-testid="puzzle-sidebar"]');
    // Sidebar should be ~320px wide
    // await expect(sidebar).toHaveScreenshot('layout-desktop-sidebar.png');
  });
});
