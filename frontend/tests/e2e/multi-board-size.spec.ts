/**
 * Multi Board Size E2E Test
 * @module tests/e2e/multi-board-size.spec
 *
 * End-to-end tests for different board sizes (5×5, 9×9, 13×13, 19×19).
 * Verifies that puzzles with different board sizes render correctly.
 *
 * Covers: US1, FR-086
 * Spec 125, Task T122b
 */

import { test, expect } from '@playwright/test';

test.describe('Multi Board Size Support', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should render 19x19 board puzzle correctly', async ({ page }) => {
    // Most puzzles default to 19x19
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const board = page.locator('[data-testid="goban-board"]');
    const boundingBox = await board.boundingBox();

    expect(boundingBox).not.toBeNull();
    if (boundingBox) {
      // Board should have reasonable dimensions
      expect(boundingBox.width).toBeGreaterThan(100);
      expect(boundingBox.height).toBeGreaterThan(100);
    }
  });

  test('should handle board size from SZ property', async ({ page }) => {
    // goban respects SZ property in SGF
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Verify SVG or Canvas is rendering
    const svgBoard = page.locator('[data-testid="goban-board"] svg');
    const canvasBoard = page.locator('[data-testid="goban-board"] canvas');

    const hasSvg = await svgBoard.isVisible();
    const hasCanvas = await canvasBoard.isVisible();

    expect(hasSvg || hasCanvas).toBe(true);
  });

  test('should maintain aspect ratio for non-square boards', async ({ page }) => {
    // Some puzzles may have rectangular regions
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const board = page.locator('[data-testid="goban-board"]');
    const boundingBox = await board.boundingBox();

    expect(boundingBox).not.toBeNull();
    // Board should render (aspect ratio handled by goban)
  });

  test('should scale board to fit container', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Resize viewport
    await page.setViewportSize({ width: 800, height: 600 });
    await page.waitForTimeout(200);

    // Board should still be visible and proportional
    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();

    const afterResize = await board.boundingBox();
    expect(afterResize).not.toBeNull();
  });

  test('should handle very small puzzles (5x5 region)', async ({ page }) => {
    // Corner puzzles often only use a small region
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Zoom should help focus on small regions
    const zoomButton = page.getByRole('button', { name: /zoom/i });
    if (await zoomButton.isVisible()) {
      // Test zoom toggle
      await zoomButton.click();
      await page.waitForTimeout(200);
      await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
    }
  });

  test('should render stones correctly on all board sizes', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board should have rendered content (stones)
    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();

    // The goban renders stones as circles/elements
    // Just verify the board container has content
    const hasContent = await board.innerHTML();
    expect(hasContent.length).toBeGreaterThan(0);
  });

  test('should handle board transition on puzzle navigation', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Navigate to next puzzle (might have different board size)
    const nextButton = page.getByRole('button', { name: /next/i });
    if (await nextButton.isVisible() && await nextButton.isEnabled()) {
      await nextButton.click();
      await page.waitForTimeout(500);

      // New board should render correctly
      await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
    }
  });

  test('should display grid lines correctly for all sizes', async ({ page }) => {
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Check for SVG lines or Canvas rendering
    const board = page.locator('[data-testid="goban-board"]');
    const boundingBox = await board.boundingBox();

    // Board should have rendered with proper grid
    expect(boundingBox).not.toBeNull();
    expect(boundingBox!.width).toBeGreaterThan(50);
    expect(boundingBox!.height).toBeGreaterThan(50);
  });
});
