/**
 * UI Audit Screenshots - Before/After Fix Comparison
 * 
 * Run with: npx playwright test --config=playwright.audit.config.ts
 */
import { test } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('UI Audit Screenshots', () => {
  test('01 - Full page initial state', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'audit-screenshots/before-01-full-page.png', fullPage: true });
  });

  test('02 - Board close-up', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    await board.screenshot({ path: 'audit-screenshots/before-02-board.png' });
  });

  test('03 - Sidebar controls', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.screenshot({ path: 'audit-screenshots/before-03-sidebar.png' });
  });

  test('04 - Hover stone attempt', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Hover over various board intersections
      await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4);
      await page.waitForTimeout(500);
      await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
      await page.waitForTimeout(500);
      await board.screenshot({ path: 'audit-screenshots/before-04-hover.png' });
    }
  });

  test('05 - After wrong move with controls', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Click on corner to trigger wrong answer
      await page.mouse.click(box.x + box.width * 0.05, box.y + box.height * 0.05);
      await page.waitForTimeout(1500);
      await page.screenshot({ path: 'audit-screenshots/before-05-wrong-move.png', fullPage: true });
    }
  });

  test('06 - Board artifacts check (mouse movement)', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Rapidly move over intersections to try to trigger artifacts
      for (let i = 0; i < 10; i++) {
        await page.mouse.move(
          box.x + (Math.random() * box.width),
          box.y + (Math.random() * box.height),
        );
        await page.waitForTimeout(50);
      }
      await page.waitForTimeout(300);
      await board.screenshot({ path: 'audit-screenshots/before-06-artifacts.png' });
    }
  });

  test('07 - Puzzle 2 navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/collections/level-elementary`);
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(3000);
    // Try clicking skip to go to puzzle 2
    const skipBtn = page.locator('button:has-text("Skip")');
    if (await skipBtn.isVisible()) {
      await skipBtn.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'audit-screenshots/before-07-puzzle2.png', fullPage: true });
    }
  });
});
