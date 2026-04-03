/**
 * Renderer E2E Test
 * @module tests/e2e/renderer-svg-default.spec
 *
 * End-to-end tests verifying the board renderer works correctly.
 * Note: The app defaults to Canvas renderer (not SVG). SVG is a fallback.
 *
 * Covers: US1, FR-087
 * Spec 125, Task T122c
 */

import { test, expect } from '@playwright/test';

test.describe('Renderer - Board Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should render the board with default renderer', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Check that the board container has rendered content (Canvas or SVG)
    const board = page.locator('[data-testid="goban-board"]');
    const innerHTML = await board.innerHTML();

    // Board should contain either canvas or svg element
    const hasContent = innerHTML.includes('<canvas') || innerHTML.includes('<svg');
    expect(hasContent).toBe(true);
  });

  test('should render board at different zoom levels', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Zoom browser
    await page.evaluate(() => {
      document.body.style.zoom = '150%';
    });
    await page.waitForTimeout(200);

    // Board should still be visible
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // Reset zoom
    await page.evaluate(() => {
      document.body.style.zoom = '100%';
    });
  });

  test('should render board with interactive content', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const board = page.locator('[data-testid="goban-board"]');
    
    // Board should contain rendered content
    const content = await board.innerHTML();
    expect(content.length).toBeGreaterThan(0);
  });

  test('should support interaction on the board', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board should be interactive (clickable)
    const board = page.locator('[data-testid="goban-board"]');
    await board.click({ position: { x: 100, y: 100 } });
    
    // Should not crash
    await expect(board).toBeVisible();
  });

  test('should have rendered board elements', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board DOM should have content
    const board = page.locator('[data-testid="goban-board"]');
    const innerHTML = await board.innerHTML();

    // Board should have rendered content (goban renders children dynamically)
    expect(innerHTML.length).toBeGreaterThan(0);
  });
});
