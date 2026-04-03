/**
 * Sidebar Visual Regression Tests
 * @module tests/e2e/sidebar-visual.spec
 *
 * Validates sidebar rendering after UI overhaul Phases 1-5.
 *
 * UI-027: Phase 6 visual regression suite.
 */

import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collections/curated-beginner-essentials/1';

test.describe('Sidebar — Layout & Structure', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('sidebar has action bar with pill-shaped buttons', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const actionBar = page.getByTestId('action-bar');
    await expect(actionBar).toBeVisible({ timeout: 10_000 });

    // Action buttons should use rounded-full (pill shape, border-radius ≥ 16px)
    const buttons = actionBar.locator('button');
    const count = await buttons.count();
    expect(count).toBeGreaterThan(0);

    const firstBtn = buttons.first();
    const borderRadius = await firstBtn.evaluate(el => getComputedStyle(el).borderRadius);
    expect(parseInt(borderRadius)).toBeGreaterThanOrEqual(16);
  });

  test('no section header dividers (BOARD / ACTIONS)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.getByTestId('goban-container').waitFor({ timeout: 10_000 });

    const bodyText = await page.locator('[data-component="solver-view"]').textContent();
    expect(bodyText).not.toMatch(/\bBOARD\b/);
    expect(bodyText).not.toMatch(/\bACTIONS\b/);
  });

  test('transform bar has toolbar role and correct button count', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const transformBar = page.getByTestId('transform-bar');
    await expect(transformBar).toBeVisible({ timeout: 10_000 });

    await expect(transformBar).toHaveAttribute('role', 'toolbar');

    // 5 transform buttons + 1 coordinate toggle = 6
    const buttons = transformBar.locator('button');
    const count = await buttons.count();
    expect(count).toBe(6);
  });

  test('hint button does not use green background', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const solver = page.locator('[data-component="solver-view"]');
    await expect(solver).toBeVisible({ timeout: 10_000 });

    const hintBtn = page.getByLabel(/hint/i);
    if ((await hintBtn.count()) > 0) {
      const bg = await hintBtn.evaluate(el => getComputedStyle(el).backgroundColor);
      // Should not be pure green (#00xx00)
      expect(bg).not.toMatch(/rgb\(0, \d+, 0\)/);
    }
  });
});

test.describe('Sidebar — Color Swap', () => {
  test('swap colors button toggles aria-pressed', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.goto(PUZZLE_URL);
    const swapBtn = page.getByLabel('Swap colors');
    await expect(swapBtn).toBeVisible({ timeout: 10_000 });

    // Initially not swapped
    await expect(swapBtn).toHaveAttribute('aria-pressed', 'false');

    // Toggle on
    await swapBtn.click();
    await expect(swapBtn).toHaveAttribute('aria-pressed', 'true');

    // Toggle off
    await swapBtn.click();
    await expect(swapBtn).toHaveAttribute('aria-pressed', 'false');
  });
});

test.describe('Sidebar — Dark Mode', () => {
  test('sidebar elements render in dark mode', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('yengo:settings', JSON.stringify({
        theme: 'dark', soundEnabled: true, coordinateLabels: true,
      }));
    });
    await page.goto(PUZZLE_URL);
    await page.getByTestId('goban-container').waitFor({ timeout: 10_000 });

    const theme = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(theme).toBe('dark');

    await expect(page.getByTestId('transform-bar')).toBeVisible();
    await expect(page.getByTestId('action-bar')).toBeVisible();
  });
});

test.describe('Sidebar — Mobile', () => {
  test('sidebar content accessible on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    // On mobile, action bar should be present (stacked below board)
    const boardBox = await board.boundingBox();
    const actionBar = page.getByTestId('action-bar');
    if ((await actionBar.count()) > 0) {
      const actionBox = await actionBar.boundingBox();
      if (boardBox && actionBox) {
        expect(actionBox.y).toBeGreaterThanOrEqual(boardBox.y);
      }
    }
  });
});
