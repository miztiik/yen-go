/**
 * Tablet Layout Visual Tests
 * @module tests/visual/layout-tablet.visual.spec
 *
 * Visual regression tests for tablet layout (768×1024).
 *
 * Covers: US7
 * Spec 125, Task T072
 */

import { test, expect } from '@playwright/test';

test.describe('Tablet Layout (768x1024)', () => {
  test.use({
    viewport: { width: 768, height: 1024 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should show intermediate layout on tablet', async ({ page }) => {
    // Navigate to puzzle page
    // Verify layout adapts for tablet
    const puzzlePage = page.locator('[data-testid="puzzle-solve-page"]');
    // await expect(puzzlePage).toHaveScreenshot('layout-tablet-intermediate.png');
  });

  test.skip('should show narrower sidebar on tablet', async ({ page }) => {
    const sidebar = page.locator('[data-testid="puzzle-sidebar"]');
    // Sidebar should be narrower than desktop
    // await expect(sidebar).toHaveScreenshot('layout-tablet-sidebar.png');
  });
});
