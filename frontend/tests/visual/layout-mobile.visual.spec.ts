/**
 * Mobile Layout Visual Tests
 * @module tests/visual/layout-mobile.visual.spec
 *
 * Visual regression tests for mobile layout (375×667).
 *
 * Covers: US7
 * Spec 125, Task T073
 */

import { test, expect } from '@playwright/test';

test.describe('Mobile Layout (375x667)', () => {
  test.use({
    viewport: { width: 375, height: 667 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should show stacked layout on mobile', async ({ page }) => {
    // Navigate to puzzle page
    // Verify board stacked above sidebar
    const puzzlePage = page.locator('[data-testid="puzzle-solve-page"]');
    // await expect(puzzlePage).toHaveScreenshot('layout-mobile-stacked.png');
  });

  test.skip('should have full-width sidebar on mobile', async ({ page }) => {
    const sidebar = page.locator('[data-testid="puzzle-sidebar"]');
    // Sidebar should be full width
    // await expect(sidebar).toHaveScreenshot('layout-mobile-sidebar.png');
  });

  test.skip('should have properly sized touch targets on mobile', async ({ page }) => {
    // All interactive elements should be at least 44px
    const buttons = page.locator('button');
    // Verify touch targets meet accessibility requirements
  });
});
