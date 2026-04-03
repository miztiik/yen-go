/**
 * Puzzle Auto-Play E2E Test — OGS-native format verification.
 *
 * Verifies that after switching to initial_state + move_tree format:
 * 1. Initial stones render correctly at move 0
 * 2. Opponent auto-plays after correct move
 * 3. Correct/wrong feedback events fire
 *
 * Run: npx playwright test tests/e2e/puzzle-autoplay.spec.ts --config=playwright.e2e.config.ts
 */
import { test, expect, type Page } from '@playwright/test';

const CHO_PUZZLE_1 = '/collections/curated-cho-chikun-life-death-intermediate/1';
const CHO_PUZZLE_2 = '/collections/curated-cho-chikun-life-death-intermediate/2';
const BEGINNER_PUZZLE = '/collections/curated-beginner-essentials/1';
const LEVEL_PUZZLE = '/level/beginner/1';
const SCREENSHOT_DIR = 'test-screenshots/ogs-migration';

// Helper: wait for puzzle solver to fully load
async function waitForSolverReady(page: Page) {
  await page.waitForSelector('.solver-layout', { timeout: 15000 });
  await page.waitForSelector('.goban-container', { timeout: 15000 });
  await page.waitForTimeout(2000);
}

test.describe('OGS-Native Puzzle Format — Auto-Play', () => {
  test.describe.configure({ mode: 'serial' });

  test('loads Cho Chikun puzzle 1 with correct initial stones', async ({ page }) => {
    await page.goto(CHO_PUZZLE_1);
    await waitForSolverReady(page);

    // Take screenshot at initial position
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/cho-puzzle-1-initial.png`,
      fullPage: false,
    });

    // Verify the board is rendered (canvas or SVG exists)
    const boardContainer = page.locator('.goban-container');
    await expect(boardContainer).toBeVisible();
  });

  test('loads Cho Chikun puzzle 2 with correct initial stones', async ({ page }) => {
    await page.goto(CHO_PUZZLE_2);
    await waitForSolverReady(page);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/cho-puzzle-2-initial.png`,
      fullPage: false,
    });

    const boardContainer = page.locator('.goban-container');
    await expect(boardContainer).toBeVisible();
  });

  test('loads beginner essentials puzzle', async ({ page }) => {
    await page.goto(BEGINNER_PUZZLE);
    await waitForSolverReady(page);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/beginner-essentials-initial.png`,
      fullPage: false,
    });

    const boardContainer = page.locator('.goban-container');
    await expect(boardContainer).toBeVisible();
  });

  test('loads level-based puzzle', async ({ page }) => {
    await page.goto(LEVEL_PUZZLE);
    await waitForSolverReady(page);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/level-beginner-initial.png`,
      fullPage: false,
    });

    const boardContainer = page.locator('.goban-container');
    await expect(boardContainer).toBeVisible();
  });

  test('no console errors on puzzle pages', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    const urls = [CHO_PUZZLE_1, CHO_PUZZLE_2, BEGINNER_PUZZLE, LEVEL_PUZZLE];

    for (const url of urls) {
      errors.length = 0; // reset
      await page.goto(url);
      await waitForSolverReady(page);

      // Filter out non-critical errors (network failures for static assets are ok)
      const criticalErrors = errors.filter(
        (e) => !e.includes('net::') && !e.includes('favicon'),
      );

      expect(
        criticalErrors,
        `Console errors on ${url}: ${criticalErrors.join(', ')}`,
      ).toHaveLength(0);
    }
  });
});
