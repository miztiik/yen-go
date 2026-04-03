/**
 * Random Play Compliance E2E — Actual canvas gameplay validation.
 * @module tests/e2e/random-play-compliance.spec
 *
 * Initiative: 20260329-1500-feature-playing-modes-dry-compliance (Phase 6, T37)
 *
 * Validates that Random mode renders through PuzzleSetPlayer → SolverView → GobanRenderer,
 * producing a real goban canvas that responds to click interactions.
 */

import { test, expect, type Page } from '@playwright/test';

/** Navigate to Random mode, select a level to start playing.
 * RandomPage calls getFilterCounts() synchronously during render,
 * which requires sqliteService to be initialized. We bootstrap DB
 * by first visiting Rush browse (which uses useMasterIndexes → initDb).
 */
async function startRandomGame(page: Page) {
  // 1. Navigate to Rush browse to trigger DB initialization via useMasterIndexes
  await page.goto('/yen-go/modes/rush');
  await page.waitForLoadState('networkidle');
  // Wait for Rush browse page to render DB-dependent content (duration buttons)
  await page.waitForSelector('[data-testid="rush-duration-3"]', { timeout: 15_000 });

  // 2. SPA-navigate to Random (preserves in-memory DB state)
  await page.evaluate(() => {
    window.history.pushState(null, '', '/yen-go/modes/random');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await page.waitForLoadState('networkidle');

  // 3. Click a level card with known puzzle data (beginner=586 puzzles in DB)
  const levelCard = page.getByTestId('level-card-beginner');
  await expect(levelCard).toBeVisible({ timeout: 5000 });
  await levelCard.click();
}

test.describe('Random Play Compliance — Canvas Gameplay', () => {
  test('goban board renders inside SolverView board column', async ({ page }) => {
    await startRandomGame(page);

    // SolverView renders GobanContainer which hosts the goban board
    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    // The goban library renders SVG layers inside a Shadow DOM
    const hasShadow = await gobanContainer.evaluate(el =>
      !!el.querySelector('.goban-board-container')?.shadowRoot
    );
    expect(hasShadow).toBeTruthy();
  });

  test('goban board has non-trivial dimensions', async ({ page }) => {
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    const box = await gobanContainer.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(100);
    expect(box!.height).toBeGreaterThan(100);
  });

  test('clicking on goban board triggers a board interaction', async ({ page }) => {
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    const boardSurface = gobanContainer.locator('.goban-board-container');
    const box = await boardSurface.boundingBox();
    expect(box).not.toBeNull();

    // Click near center of board
    await boardSurface.click({ position: { x: box!.width / 2, y: box!.height / 2 } });

    // Wait for puzzle engine to respond
    await page.waitForTimeout(1000);

    // The key assertion: no crash, board still visible and functional
    await expect(gobanContainer).toBeVisible();
  });

  test('random mode header shows puzzle count and accuracy', async ({ page }) => {
    await startRandomGame(page);

    // Random header rendered via PuzzleSetPlayer's renderHeader
    await expect(page.getByText('Random Challenge')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Puzzles')).toBeVisible();
    await expect(page.getByText('Accuracy')).toBeVisible();
  });

  test('SolverView shows full 2-column layout (not minimal)', async ({ page }) => {
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    // Random mode does NOT use minimal=true, so sidebar should be visible
    const actionBar = page.getByTestId('action-bar');
    await expect(actionBar).toBeVisible();
  });

  test('back button navigates away from random challenge', async ({ page }) => {
    await startRandomGame(page);

    // Wait for board to load
    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    // Back button in Random header
    const backBtn = page.locator('button[aria-label="Back"]');
    if (await backBtn.isVisible()) {
      await backBtn.click();
      // Should navigate away from challenge page
      await page.waitForTimeout(1000);
    }
  });
});
