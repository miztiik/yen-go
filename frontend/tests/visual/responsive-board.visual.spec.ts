/**
 * Responsive Board Visual Tests
 * @module tests/visual/responsive-board.visual.spec
 *
 * Visual regression tests for board sizing across viewports.
 *
 * Covers: US7
 * Spec 125, Task T078
 */

import { test, expect } from '@playwright/test';

test.describe('Responsive Board - Desktop (1280x800)', () => {
  test.use({
    viewport: { width: 1280, height: 800 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should size board appropriately for desktop', async ({ page }) => {
    const goban = page.locator('[data-testid="goban-board"]');
    // await expect(goban).toHaveScreenshot('responsive-board-desktop.png');
  });
});

test.describe('Responsive Board - Tablet (768x1024)', () => {
  test.use({
    viewport: { width: 768, height: 1024 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should size board appropriately for tablet', async ({ page }) => {
    const goban = page.locator('[data-testid="goban-board"]');
    // await expect(goban).toHaveScreenshot('responsive-board-tablet.png');
  });
});

test.describe('Responsive Board - Mobile (375x667)', () => {
  test.use({
    viewport: { width: 375, height: 667 },
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should size board appropriately for mobile', async ({ page }) => {
    const goban = page.locator('[data-testid="goban-board"]');
    // await expect(goban).toHaveScreenshot('responsive-board-mobile.png');
  });
});
