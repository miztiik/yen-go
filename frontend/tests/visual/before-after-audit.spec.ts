/**
 * Before/After UI Audit Screenshots
 * 
 * Takes screenshots of the puzzle solving UI to document issues:
 * 1. Hover stones not working
 * 2. Self-atari warning on board
 * 3. Coordinate display
 * 4. Puzzle navigation (counter, prev/next/skip)
 * 5. Action buttons visibility
 * 6. Board controls layout
 * 7. Canvas artifacts
 */
import { test } from '@playwright/test';
import path from 'path';

const SCREENSHOT_DIR = path.join(__dirname, '..', '..', 'audit-screenshots');

test.describe('UI Audit - Before Fix', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to elementary collection (has puzzles)
    await page.goto('http://localhost:5173/collections/level-elementary');
    // Wait for board to render
    await page.waitForSelector('[data-slot="board"]', { timeout: 15000 });
    await page.waitForTimeout(2000); // Let goban fully render
  });

  test('01 - Full page initial state', async ({ page }) => {
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'before-01-full-page.png'),
      fullPage: true,
    });
  });

  test('02 - Board area close-up', async ({ page }) => {
    const board = page.locator('[data-slot="board"]');
    await board.screenshot({
      path: path.join(SCREENSHOT_DIR, 'before-02-board-closeup.png'),
    });
  });

  test('03 - Sidebar controls', async ({ page }) => {
    const sidebar = page.locator('.solver-sidebar-col');
    if (await sidebar.isVisible()) {
      await sidebar.screenshot({
        path: path.join(SCREENSHOT_DIR, 'before-03-sidebar.png'),
      });
    }
  });

  test('04 - Hover stone test', async ({ page }) => {
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Move mouse over board intersections
      await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.3);
      await page.waitForTimeout(500);
      await board.screenshot({
        path: path.join(SCREENSHOT_DIR, 'before-04-hover-stone.png'),
      });
    }
  });

  test('05 - After wrong move', async ({ page }) => {
    const board = page.locator('[data-slot="board"]');
    const box = await board.boundingBox();
    if (box) {
      // Click on an unlikely-correct position to trigger wrong answer
      await page.mouse.click(box.x + box.width * 0.1, box.y + box.height * 0.1);
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'before-05-wrong-move.png'),
        fullPage: true,
      });
    }
  });

  test('06 - Transform bar state', async ({ page }) => {
    const transformBar = page.locator('[data-testid="transform-bar"]');
    if (await transformBar.isVisible()) {
      await transformBar.screenshot({
        path: path.join(SCREENSHOT_DIR, 'before-06-transform-bar.png'),
      });
    }
  });

  test('07 - Puzzle counter and navigation', async ({ page }) => {
    const counter = page.locator('.solver-puzzle-counter');
    if (await counter.isVisible()) {
      await counter.screenshot({
        path: path.join(SCREENSHOT_DIR, 'before-07-puzzle-counter.png'),
      });
    }
  });
});
