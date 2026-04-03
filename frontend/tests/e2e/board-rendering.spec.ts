/**
 * Board Rendering Visual Regression Tests
 * @module tests/e2e/board-rendering.spec
 *
 * Validates board rendering correctness after UI overhaul Phases 1-5.
 * Uses GobanContainer (data-testid="goban-container").
 *
 * UI-026: Phase 6 visual regression suite.
 */

import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collections/curated-beginner-essentials/1';

test.describe('Board Rendering — Containment & Overflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('board canvas does not overflow container', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    // Container must clip overflow (GobanContainer sets overflow:hidden)
    const overflow = await container.evaluate(el => getComputedStyle(el).overflow);
    expect(overflow).toBe('hidden');

    // Board should contain either canvas or svg element
    const content = await container.innerHTML();
    const hasRenderedContent = content.includes('<canvas') || content.includes('<svg');
    expect(hasRenderedContent).toBe(true);
  });

  test('board and sidebar do not overlap on desktop', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    const boardBox = await container.boundingBox();
    const actionBar = page.getByTestId('action-bar');
    if ((await actionBar.count()) > 0) {
      const sidebarBox = await actionBar.boundingBox();
      if (boardBox && sidebarBox && sidebarBox.x > boardBox.x) {
        // On desktop layout, board right edge must not exceed sidebar left
        expect(boardBox.x + boardBox.width).toBeLessThanOrEqual(sidebarBox.x + 2);
      }
    }
  });
});

test.describe('Board Rendering — Coordinate Labels', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('coordinate toggle aria-pressed tracks label state', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const transformBar = page.getByTestId('transform-bar');
    await expect(transformBar).toBeVisible({ timeout: 10_000 });

    const coordsBtn = page.getByLabel(/coordinates/i);

    // Default: labels ON
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'true');

    // Toggle OFF
    await coordsBtn.click();
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByTestId('goban-container')).toBeVisible();

    // Toggle ON
    await coordsBtn.click();
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'true');
  });
});

test.describe('Board Rendering — Transforms', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('flip horizontal keeps board contained', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Flip horizontal').click();
    await page.waitForTimeout(500);

    const overflow = await container.evaluate(el => getComputedStyle(el).overflow);
    expect(overflow).toBe('hidden');
    await expect(container).toBeVisible();
  });

  test('flip vertical keeps board contained', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Flip vertical').click();
    await page.waitForTimeout(500);
    await expect(container).toBeVisible();
  });

  test('rotate CW keeps board contained', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Rotate clockwise').click();
    await page.waitForTimeout(500);
    await expect(container).toBeVisible();
  });

  test('rotate CCW keeps board contained', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Rotate counter-clockwise').click();
    await page.waitForTimeout(500);
    await expect(container).toBeVisible();
  });

  test('all transforms combined keeps board contained', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Flip horizontal').click();
    await page.getByLabel('Flip vertical').click();
    await page.getByLabel('Rotate clockwise').click();
    await page.getByLabel('Swap colors').click();
    await page.waitForTimeout(500);

    await expect(container).toBeVisible();
    const overflow = await container.evaluate(el => getComputedStyle(el).overflow);
    expect(overflow).toBe('hidden');
  });
});

test.describe('Board Rendering — Dark Mode', () => {
  test('board renders correctly in dark mode', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('yengo:settings', JSON.stringify({
        theme: 'dark', soundEnabled: true, coordinateLabels: true,
      }));
    });
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    const theme = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(theme).toBe('dark');

    const content = await container.innerHTML();
    const hasContent = content.includes('<canvas') || content.includes('<svg');
    expect(hasContent).toBe(true);
  });
});

test.describe('Board Rendering — Mobile', () => {
  test('board renders on small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(PUZZLE_URL);
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 10_000 });

    const box = await container.boundingBox();
    expect(box).toBeTruthy();
    expect(box!.width).toBeLessThanOrEqual(375);
  });
});
