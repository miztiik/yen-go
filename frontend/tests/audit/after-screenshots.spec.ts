/**
 * UI Audit Screenshots - AFTER fixes applied
 * Captures the same views as before-screenshots.spec.ts for comparison.
 *
 * Run with: npx playwright test --config=playwright.audit.config.ts tests/audit/after-screenshots.spec.ts
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('UI Audit Screenshots - AFTER Fix', () => {
  test('01 - Full page initial state', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'audit-screenshots/after-01-full-page.png', fullPage: true });
  });

  test('02 - Board close-up (coordinates left+bottom)', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    await board.screenshot({ path: 'audit-screenshots/after-02-board.png' });
  });

  test('03 - Sidebar redesign', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.screenshot({ path: 'audit-screenshots/after-03-sidebar.png' });
  });

  test('04 - Hover stone test', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Move to center of board where there should be empty intersections
      await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4);
      await page.waitForTimeout(500);
      await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.3);
      await page.waitForTimeout(500);
      await board.screenshot({ path: 'audit-screenshots/after-04-hover.png' });
    }
  });

  test('05 - After wrong move (board message in sidebar)', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Click on corner to trigger wrong answer
      await page.mouse.click(box.x + box.width * 0.05, box.y + box.height * 0.05);
      await page.waitForTimeout(1500);
      await page.screenshot({ path: 'audit-screenshots/after-05-wrong-move.png', fullPage: true });
    }
  });

  test('06 - Always-visible action buttons', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    // Action bar should be visible even before any move is made
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.screenshot({ path: 'audit-screenshots/after-06-action-buttons.png' });
  });

  test('07 - Navigate to puzzle 2 via Next button', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    // The Next button should now be always visible (not hidden behind AnswerBanner)
    const nextBtn = page.locator('button:has-text("Next")');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'audit-screenshots/after-07-puzzle2.png', fullPage: true });
    }
  });

  test('08 - Transform bar with CCW rotation', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.screenshot({ path: 'audit-screenshots/after-08-transforms.png' });
  });
});
