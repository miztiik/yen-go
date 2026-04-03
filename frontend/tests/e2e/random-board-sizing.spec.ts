/**
 * Random Board Sizing E2E — Responsive board width validation.
 * @module tests/e2e/random-board-sizing.spec
 *
 * Initiative: 20260329-1500-feature-playing-modes-dry-compliance (Phase 6, T39)
 *
 * Validates that Random mode uses SolverView's responsive layout,
 * with full 2-column layout (board + sidebar) at desktop widths.
 */

import { test, expect, type Page } from '@playwright/test';

async function startRandomGame(page: Page) {
  // 1. Navigate to Rush browse to trigger DB initialization via useMasterIndexes
  await page.goto('/yen-go/modes/rush');
  await page.waitForLoadState('networkidle');
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

test.describe('Random Board Sizing — Responsive Layout', () => {
  test('board renders at responsive width on 1440px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    const containerBox = await gobanContainer.boundingBox();
    expect(containerBox).not.toBeNull();

    // At 1440px the board should be substantial
    expect(containerBox!.width).toBeGreaterThan(300);
  });

  test('sidebar is visible (Random does not use minimal mode)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    // Random mode uses default SolverView (minimal=false), sidebar column should render
    const sidebarCol = page.locator('.solver-sidebar-col');
    await expect(sidebarCol).toBeVisible();
  });

  test('board has non-trivial size at 1024px', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    const containerBox = await gobanContainer.boundingBox();
    expect(containerBox).not.toBeNull();
    expect(containerBox!.width).toBeGreaterThan(200);
  });

  test('screenshot at 1440px shows 2-column layout', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRandomGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 15_000 });

    await page.screenshot({
      path: 'test-results/random-board-1440px.png',
      fullPage: false,
    });
  });
});
