/**
 * UI Overhaul Validation E2E Tests
 * @module tests/e2e/ui-overhaul-validation.spec
 *
 * End-to-end tests validating all Phase 1-5 UI overhaul changes.
 * Covers: UI-001 through UI-046 acceptance criteria.
 *
 * UI-043: Phase 6 — final validation suite.
 */

import { test, expect } from '@playwright/test';

const PUZZLE_URL = '/collections/curated-beginner-essentials/1';

test.describe('UI Overhaul — Board Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('1. Board renders without overflow into sidebar', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    // Board container should have overflow:hidden (GobanContainer)
    const overflow = await board.evaluate(el => getComputedStyle(el).overflow);
    expect(overflow).toBe('hidden');

    // Board should have meaningful dimensions
    const boardBox = await board.boundingBox();
    expect(boardBox).toBeTruthy();
    expect(boardBox!.width).toBeGreaterThan(100);
    expect(boardBox!.height).toBeGreaterThan(100);
  });

  test('2. Correct/wrong move feedback system works', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    // Click on the board — will trigger either correct or wrong feedback
    await board.click({ position: { x: 50, y: 50 } });
    await page.waitForTimeout(500);

    // Solver should remain visible (not crash after interaction)
    const solver = page.locator('[data-component="solver-view"]');
    await expect(solver).toBeVisible();
    const status = await solver.getAttribute('data-status');
    expect(status).toBeTruthy();
  });

  test('3. Transform buttons exist and toggle correctly', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const transformBar = page.getByTestId('transform-bar');
    await expect(transformBar).toBeVisible({ timeout: 10_000 });

    // All transform buttons should be present
    await expect(page.getByLabel('Flip horizontal')).toBeVisible();
    await expect(page.getByLabel('Flip vertical')).toBeVisible();
    await expect(page.getByLabel('Rotate clockwise')).toBeVisible();
    await expect(page.getByLabel('Rotate counter-clockwise')).toBeVisible();
    await expect(page.getByLabel('Swap colors')).toBeVisible();

    // Flip horizontal should toggle aria-pressed
    const flipH = page.getByLabel('Flip horizontal');
    await flipH.click();
    await expect(flipH).toHaveAttribute('aria-pressed', 'true');
    await flipH.click();
    await expect(flipH).toHaveAttribute('aria-pressed', 'false');
  });

  test('4. Coordinate toggle shows/hides labels', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const transformBar = page.getByTestId('transform-bar');
    await expect(transformBar).toBeVisible({ timeout: 10_000 });

    const coordsBtn = page.getByLabel(/coordinates/i);
    await expect(coordsBtn).toBeVisible();

    // Default: labels ON (coordinateLabels default = true)
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'true');

    // Toggle off
    await coordsBtn.click();
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'false');

    // Toggle back on
    await coordsBtn.click();
    await expect(coordsBtn).toHaveAttribute('aria-pressed', 'true');
  });
});

test.describe('UI Overhaul — Sidebar & Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('5. ProblemNav or puzzle counter is present', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    // ProblemNav or puzzle counter should exist
    const navSlot = page.getByTestId('puzzle-nav-slot');
    const counter = page.getByTestId('puzzle-counter');
    const hasNav = (await navSlot.count()) > 0 || (await counter.count()) > 0;
    expect(hasNav).toBe(true);
  });

  test('6. Keyboard shortcuts do not crash', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    // Place a move
    await board.click({ position: { x: 50, y: 50 } });
    await page.waitForTimeout(300);

    // Escape should reset without crashing
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const solver = page.locator('[data-component="solver-view"]');
    await expect(solver).toBeVisible();
  });

  test('7. Action bar has undo and reset buttons', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    const actionBar = page.getByTestId('action-bar');
    await expect(actionBar).toBeVisible({ timeout: 10_000 });

    await expect(page.getByLabel(/undo/i)).toBeVisible();
    await expect(page.getByLabel(/reset/i)).toBeVisible();
  });
});

test.describe('UI Overhaul — Dark Mode', () => {
  test('8. Dark mode renders correctly', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.evaluate(() => {
      localStorage.setItem('yengo:settings', JSON.stringify({
        theme: 'dark', soundEnabled: true, coordinateLabels: true,
      }));
    });
    await page.goto(PUZZLE_URL);
    const board = page.getByTestId('goban-container');
    await expect(board).toBeVisible({ timeout: 10_000 });

    const theme = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(theme).toBe('dark');

    // Board should still render
    const boardBox = await board.boundingBox();
    expect(boardBox).toBeTruthy();
  });
});

test.describe('UI Overhaul — All Pages Load', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('9. Home page loads', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });

  test('10. Collections page loads', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Collections' }).first()).toBeVisible();
  });

  test('11. Daily page loads', async ({ page }) => {
    await page.goto('/daily');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });

  test('12. Puzzle Rush page loads', async ({ page }) => {
    await page.goto('/puzzle-rush');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });

  test('13. Training page loads', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });

  test('14. Random page loads', async ({ page }) => {
    await page.goto('/random');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });
});
