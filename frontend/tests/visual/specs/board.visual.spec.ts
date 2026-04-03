/**
 * Board Component Visual Tests
 * 
 * Visual regression tests for the Board component using Playwright.
 * Tests various states and configurations across all viewports.
 * 
 * @see specs/016-playwright-visual-testing/spec.md
 */

import { test, expect } from '@playwright/test';

// Navigate to visual tests page before each test
test.beforeEach(async ({ page }) => {
  await page.goto('/visual-tests.html');
  // Wait for the page to fully render
  await page.waitForLoadState('networkidle');
  // Extra wait for canvas rendering
  await page.waitForTimeout(200);
});

test.describe('Board Visual Tests - Empty Boards', () => {
  test('empty 9x9 board', async ({ page }) => {
    const fixture = page.locator('#board-empty-9x9');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-empty-9x9.png');
  });

  test('empty 13x13 board', async ({ page }) => {
    const fixture = page.locator('#board-empty-13x13');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-empty-13x13.png');
  });

  test('empty 19x19 board', async ({ page }) => {
    const fixture = page.locator('#board-empty-19x19');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-empty-19x19.png');
  });
});

test.describe('Board Visual Tests - With Stones', () => {
  test('board with stones', async ({ page }) => {
    const fixture = page.locator('#board-with-stones');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-with-stones.png');
  });

  test('board with last move marker', async ({ page }) => {
    const fixture = page.locator('#board-with-last-move');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-with-last-move.png');
  });

  test('board corner pattern (tsumego)', async ({ page }) => {
    const fixture = page.locator('#board-corner-pattern');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-corner-pattern.png');
  });
});

test.describe('Board Visual Tests - Interactive States', () => {
  test('board with ghost stone preview', async ({ page }) => {
    const fixture = page.locator('#board-with-ghost-stone');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-with-ghost-stone.png');
  });

  test('board with highlighted move (hint)', async ({ page }) => {
    const fixture = page.locator('#board-with-highlight');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-with-highlight.png');
  });

  test('board with solution markers', async ({ page }) => {
    const fixture = page.locator('#board-with-solution-markers');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-with-solution-markers.png');
  });
});

test.describe('Board Visual Tests - Size Variations', () => {
  test('small board (300x300)', async ({ page }) => {
    const fixture = page.locator('#board-small');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-small.png');
  });

  test('large board (600x600)', async ({ page }) => {
    const fixture = page.locator('#board-large');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-large.png');
  });
});

test.describe('Board Visual Tests - Rotation', () => {
  test('board rotated 90 degrees', async ({ page }) => {
    const fixture = page.locator('#board-rotated-90');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('board-rotated-90.png');
  });
});
