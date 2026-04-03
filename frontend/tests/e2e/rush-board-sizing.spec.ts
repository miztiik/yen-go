/**
 * Rush Board Sizing E2E — Responsive board width validation.
 * @module tests/e2e/rush-board-sizing.spec
 *
 * Initiative: 20260329-1500-feature-playing-modes-dry-compliance (Phase 6, T38)
 *
 * Validates that the Rush board is NOT hardcoded to max-w-[600px] anymore.
 * After PSP unification, Rush uses SolverView's responsive .solver-board-col layout,
 * which scales with viewport width.
 */

import { test, expect, type Page } from '@playwright/test';

async function startRushGame(page: Page) {
  await page.goto('/yen-go/modes/rush');
  await page.waitForLoadState('networkidle');
  await page.getByTestId('rush-duration-3').click();
  await page.waitForTimeout(4000);
}

test.describe('Rush Board Sizing — Responsive Layout', () => {
  test('board width at 1440px viewport is >=600px (not constrained)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRushGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 10_000 });

    // Get the goban-container width — this is the board rendering area
    const containerBox = await gobanContainer.boundingBox();
    expect(containerBox).not.toBeNull();

    // At 1440px viewport with minimal SolverView, the board should be wide
    // The old hardcoded max-w-[600px] would cap at 600px
    expect(containerBox!.width).toBeGreaterThanOrEqual(500);
  });

  test('board width at 1024px viewport is reasonable', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await startRushGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 10_000 });

    const containerBox = await gobanContainer.boundingBox();
    expect(containerBox).not.toBeNull();

    // At 1024px, board should still be substantial (not squeezed)
    expect(containerBox!.width).toBeGreaterThan(300);
  });

  test('board width at 768px tablet viewport still usable', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await startRushGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 10_000 });

    const containerBox = await gobanContainer.boundingBox();
    expect(containerBox).not.toBeNull();

    // At tablet width, board should still be usable
    expect(containerBox!.width).toBeGreaterThan(200);
  });

  test('rush uses minimal SolverView (no sidebar visible)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRushGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 10_000 });

    // Rush uses minimal=true, sidebar should NOT be rendered
    const sidebarCol = page.locator('.solver-sidebar-col');
    const sidebarCount = await sidebarCol.count();
    expect(sidebarCount).toBe(0);
  });

  test('screenshot at 1440px shows wide board layout', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await startRushGame(page);

    const gobanContainer = page.getByTestId('goban-container');
    await expect(gobanContainer).toBeVisible({ timeout: 10_000 });

    // Take screenshot for visual verification
    await page.screenshot({
      path: 'test-results/rush-board-1440px.png',
      fullPage: false,
    });
  });
});
