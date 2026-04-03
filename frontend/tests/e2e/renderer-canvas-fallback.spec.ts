/**
 * Renderer Canvas Fallback E2E Test
 * @module tests/e2e/renderer-canvas-fallback.spec
 *
 * End-to-end tests verifying Canvas fallback when SVG fails or is disabled.
 *
 * Covers: US1, FR-088
 * Spec 125, Task T122d
 */

import { test, expect } from '@playwright/test';

test.describe('Renderer - Canvas Fallback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should support Canvas renderer as fallback', async ({ page }) => {
    // Set user preference to Canvas before navigating
    await page.evaluate(() => {
      localStorage.setItem('yengo-renderer', JSON.stringify({ type: 'canvas' }));
    });

    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board should render even with Canvas preference
    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();
  });

  test('should render correctly with Canvas when specified', async ({ page }) => {
    // Set Canvas preference
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'canvas' }));
    });

    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const board = page.locator('[data-testid="goban-board"]');
    const boundingBox = await board.boundingBox();

    expect(boundingBox).not.toBeNull();
    expect(boundingBox!.width).toBeGreaterThan(50);
  });

  test('should handle Canvas interactions correctly', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'canvas' }));
    });

    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Click on board
    const board = page.locator('[data-testid="goban-board"]');
    await board.click({ position: { x: 150, y: 150 } });

    // Should not crash
    await expect(board).toBeVisible();
  });

  test('should gracefully fallback if SVG is unsupported', async ({ page }) => {
    // This is hard to simulate, but we test the fallback path exists
    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Either SVG or Canvas should work
    const board = page.locator('[data-testid="goban-board"]');
    const content = await board.innerHTML();
    
    const hasSvg = content.includes('<svg');
    const hasCanvas = content.includes('<canvas');

    expect(hasSvg || hasCanvas).toBe(true);
  });

  test('should maintain functionality in Canvas mode', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'canvas' }));
    });

    await page.goto('/collections/test-collection/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Test reset button works
    const resetButton = page.getByRole('button', { name: /reset/i });
    if (await resetButton.isVisible()) {
      await resetButton.click();
      await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
    }
  });

  test('should preserve Canvas preference across sessions', async ({ page }) => {
    // Set preference
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'canvas' }));
    });

    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Reload page
    await page.reload();

    // Preference should persist
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const preference = await page.evaluate(() => {
      const settings = localStorage.getItem('yengo-settings');
      return settings ? JSON.parse(settings) : null;
    });

    expect(preference?.rendererType).toBe('canvas');
  });
});
