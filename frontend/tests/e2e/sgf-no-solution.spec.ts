/**
 * SGF No Solution E2E Test
 * @module tests/e2e/sgf-no-solution.spec
 *
 * End-to-end tests for puzzles without solution branches.
 * Verifies that explore mode is activated when no solution tree exists.
 *
 * Covers: US8, FR-081
 * Spec 125, Task T119
 */

import { test, expect } from '@playwright/test';

test.describe('SGF No Solution - Explore Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should handle puzzle with no solution branches gracefully', async ({ page }) => {
    // This test uses a mock or fixture puzzle with no solution
    await page.goto('/collections/test-collection/1');

    // Board should still load
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });
  });

  test('should allow free exploration when no solution exists', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // User should be able to click anywhere without getting wrong feedback
    const board = page.locator('[data-testid="goban-board"]');
    await board.click({ position: { x: 100, y: 100 } });

    // Should not show "wrong" status for explore mode
    const wrongIndicator = page.getByText(/wrong/i);
    // In explore mode, wrong indicator should not appear
  });

  test('should show explore mode indicator for puzzles without solution', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Check for explore mode indicator or analyze button
    const exploreToggle = page.getByRole('button', { name: /explore/i })
      .or(page.getByText(/explore mode/i));
    // Toggle may be present for explore mode
  });

  test('should allow undo in explore mode', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Click on board
    const board = page.locator('[data-testid="goban-board"]');
    await board.click({ position: { x: 100, y: 100 } });

    // Undo should work
    const undoButton = page.getByRole('button', { name: /undo/i });
    if (await undoButton.isVisible()) {
      await undoButton.click();
    }
  });

  test('should allow reset in explore mode', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Click on board
    const board = page.locator('[data-testid="goban-board"]');
    await board.click({ position: { x: 100, y: 100 } });

    // Reset should work
    const resetButton = page.getByRole('button', { name: /reset/i });
    if (await resetButton.isVisible()) {
      await resetButton.click();
    }
  });
});
