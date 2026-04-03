/**
 * Hints Visual Tests
 * @module tests/visual/hints.visual.spec
 *
 * Visual regression tests for hint display and solution markers.
 *
 * Covers: US4
 * Spec 125, Task T087
 */

import { test, expect } from '@playwright/test';

test.describe('Hint Visual - Highlight', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should match hint highlight baseline', async ({ page }) => {
    // Request hint with coordinate
    // Verify circle marker appearance
    const goban = page.locator('[data-testid="goban-board"]');
    // await expect(goban).toHaveScreenshot('hint-highlight.png');
  });

  test.skip('should match hint panel baseline', async ({ page }) => {
    const hintPanel = page.locator('[data-testid="hint-panel"]');
    // await expect(hintPanel).toHaveScreenshot('hint-panel.png');
  });
});

test.describe('Solution Visual - Markers', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.skip('should match solution markers baseline', async ({ page }) => {
    // Show solution
    // Verify correct/wrong markers on board
    const goban = page.locator('[data-testid="goban-board"]');
    // await expect(goban).toHaveScreenshot('solution-markers.png');
  });

  test.skip('should match solution revealed state baseline', async ({ page }) => {
    // After solution reveal
    const puzzlePage = page.locator('[data-testid="puzzle-solve-page"]');
    // await expect(puzzlePage).toHaveScreenshot('solution-revealed.png');
  });
});
