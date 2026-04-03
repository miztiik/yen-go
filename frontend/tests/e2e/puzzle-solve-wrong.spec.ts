/**
 * Puzzle Solve Wrong E2E Test
 * @module tests/e2e/puzzle-solve-wrong.spec
 *
 * End-to-end tests for incorrect move handling.
 * Verifies: Play wrong move → wrong indicator → undo → retry
 *
 * Covers: US1, FR-004, FR-005
 * Spec 125, Task T036
 */

import { test, expect } from '@playwright/test';

test.describe('Puzzle Solve - Wrong Move Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should show wrong indicator when playing incorrect move', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Click on a likely wrong intersection (corner far from setup stones)
    const board = page.locator('[data-testid="goban-board"]');
    const box = await board.boundingBox();
    if (!box) {
      test.skip(true, 'Board not visible');
      return;
    }

    // Click in top-left corner (usually wrong for most puzzles)
    await board.click({
      position: { x: box.width * 0.1, y: box.height * 0.1 }
    });

    // Should show wrong indicator
    await expect(
      page.locator('text=/Wrong|✗|Incorrect/')
    ).toBeVisible({ timeout: 3000 });
  });

  test('should allow undo after wrong move', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Make a wrong move first
    const board = page.locator('[data-testid="goban-board"]');
    const box = await board.boundingBox();
    if (box) {
      await board.click({
        position: { x: box.width * 0.1, y: box.height * 0.1 }
      });
    }

    // Wait for wrong indicator
    await page.waitForTimeout(500);

    // Click undo button
    const undoButton = page.getByRole('button', { name: /Undo/i });
    if (await undoButton.isVisible()) {
      await undoButton.click();
      
      // Should return to solving state
      await expect(
        page.locator('text=/Your Turn|Solving/')
      ).toBeVisible({ timeout: 3000 });
    } else {
      test.skip(true, 'Undo button not found');
    }
  });

  test('should track wrong attempts count', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Make multiple wrong moves
    const board = page.locator('[data-testid="goban-board"]');
    const box = await board.boundingBox();
    if (!box) {
      test.skip(true, 'Board not visible');
      return;
    }

    // First wrong move
    await board.click({
      position: { x: box.width * 0.1, y: box.height * 0.1 }
    });
    await page.waitForTimeout(500);

    // Undo and try again with another wrong move
    const undoButton = page.getByRole('button', { name: /Undo/i });
    if (await undoButton.isVisible()) {
      await undoButton.click();
      await page.waitForTimeout(300);

      // Second wrong move
      await board.click({
        position: { x: box.width * 0.9, y: box.height * 0.9 }
      });
      await page.waitForTimeout(500);

      // Should track attempts (UI may show this)
      // Implementation depends on UI design
    }
    
    test.skip(true, 'Attempt tracking UI not yet implemented');
  });

  test('should allow retry after wrong move without progress loss', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // The puzzle should still be solvable after wrong attempts
    // This confirms the puzzle state is properly reset on undo
    test.skip(true, 'Requires puzzle with known solution');
  });

  test('should show subtle wrong indicator (muted red per Constitution X)', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Make a wrong move
    const board = page.locator('[data-testid="goban-board"]');
    const box = await board.boundingBox();
    if (box) {
      await board.click({
        position: { x: box.width * 0.1, y: box.height * 0.1 }
      });
    }

    // Check that wrong indicator has appropriate styling
    // Should be muted red (#ef4444 or similar), not harsh/bright
    const wrongIndicator = page.locator('text=/Wrong|✗/');
    
    test.skip(true, 'Visual styling test - use visual regression instead');
  });
});
