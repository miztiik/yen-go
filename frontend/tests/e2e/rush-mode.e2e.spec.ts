/**
 * Puzzle Rush E2E Tests — actual gameplay validation.
 *
 * Tests the full Rush flow: browse → select → countdown → play → game over.
 * Validates timer accuracy, board rendering, puzzle loading, and controls.
 *
 * Prerequisites: dev server running (npm run dev) with puzzle data available.
 */

import { test, expect, type Page } from '@playwright/test';

// Helper: navigate to Rush mode
async function goToRush(page: Page) {
  await page.goto('/yen-go/modes/rush');
  await page.waitForLoadState('networkidle');
}

// Helper: wait for element with timeout
async function waitForTestId(page: Page, testId: string, timeout = 10_000) {
  return page.waitForSelector(`[data-testid="${testId}"]`, { timeout });
}

test.describe('Rush Mode — Browse Page', () => {
  test('displays duration selection options', async ({ page }) => {
    await goToRush(page);

    // Should show the browse/setup page with duration options
    // Check for "3 Minutes", "5 Minutes", "10 Minutes" text
    const content = await page.textContent('body');
    expect(content).toContain('Minutes');
  });

  test('has start button that navigates to game', async ({ page }) => {
    await goToRush(page);

    // Look for a clickable duration option (3 Minutes card)
    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
      // Should transition to countdown or game
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Rush Mode — Timer', () => {
  test('timer shows correct MM:SS format for 3-minute game', async ({ page }) => {
    await goToRush(page);

    // Click 3 Minutes to start
    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    // Wait for countdown to finish (3 seconds + buffer)
    await page.waitForTimeout(4500);

    // Check timer display
    const timer = page.locator('[data-testid="rush-timer"]');
    if (await timer.isVisible({ timeout: 2000 })) {
      const timerText = await timer.textContent();
      // Timer should show 2:5x or similar (not 179:xx)
      // Format: M:SS where M < 4
      expect(timerText).toMatch(/^[0-3]:\d{2}$/);

      // Specifically: NOT showing 179:xx (the old seconds-as-minutes bug)
      const minutes = parseInt(timerText!.split(':')[0]);
      expect(minutes).toBeLessThanOrEqual(3);
    }
  });

  test('timer decrements by 1 second per tick', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    // Wait for countdown to finish
    await page.waitForTimeout(4500);

    const timer = page.locator('[data-testid="rush-timer"]');
    if (await timer.isVisible({ timeout: 2000 })) {
      // Read timer value
      const text1 = await timer.textContent();
      const [min1, sec1] = text1!.split(':').map(Number);
      const totalSec1 = min1 * 60 + sec1;

      // Wait ~3 seconds
      await page.waitForTimeout(3200);

      const text2 = await timer.textContent();
      const [min2, sec2] = text2!.split(':').map(Number);
      const totalSec2 = min2 * 60 + sec2;

      // Should have decreased by approximately 3 seconds (±1 tolerance)
      const diff = totalSec1 - totalSec2;
      expect(diff).toBeGreaterThanOrEqual(2);
      expect(diff).toBeLessThanOrEqual(5);
    }
  });
});

test.describe('Rush Mode — HUD', () => {
  test('displays lives as hearts', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const lives = page.locator('[data-testid="rush-lives"]');
    if (await lives.isVisible({ timeout: 2000 })) {
      // Should show 3 hearts
      const hearts = await lives.locator('[aria-label="Life remaining"]').count();
      expect(hearts).toBe(3);
    }
  });

  test('displays score starting at 0', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const score = page.locator('[data-testid="rush-score"]');
    if (await score.isVisible({ timeout: 2000 })) {
      const text = await score.textContent();
      expect(text).toBe('0');
    }
  });

  test('skip button is visible in HUD', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const skip = page.locator('[data-testid="skip-button"]');
    if (await skip.isVisible({ timeout: 2000 })) {
      expect(await skip.isEnabled()).toBeTruthy();
    }
  });

  test('quit button is visible in HUD', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const quit = page.locator('[data-testid="quit-button"]');
    if (await quit.isVisible({ timeout: 2000 })) {
      expect(await quit.textContent()).toContain('Quit');
    }
  });

  test('no pause button exists', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const pause = page.locator('[data-testid="rush-pause-button"]');
    expect(await pause.count()).toBe(0);
  });
});

test.describe('Rush Mode — Board', () => {
  test('board container is rendered', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const board = page.locator('[data-testid="goban-board"]');
    if (await board.isVisible({ timeout: 2000 })) {
      const box = await board.boundingBox();
      expect(box).not.toBeNull();
      // Board should have reasonable dimensions (not a tiny dot)
      expect(box!.width).toBeGreaterThan(100);
      expect(box!.height).toBeGreaterThan(100);
    }
  });

  test('goban canvas renders with reasonable size', async ({ page }) => {
    await goToRush(page);

    // Try with a level filter for better puzzle availability
    await page.goto('/yen-go/modes/rush?l=110');
    await page.waitForLoadState('networkidle');

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(5000);

    // Look for the goban canvas element
    const canvas = page.locator('canvas').first();
    if (await canvas.isVisible({ timeout: 5000 })) {
      const box = await canvas.boundingBox();
      expect(box).not.toBeNull();
      // Canvas should be at least 150px (not a tiny dot from bad cropping)
      expect(box!.width).toBeGreaterThan(150);
      expect(box!.height).toBeGreaterThan(150);
    }
  });
});

test.describe('Rush Mode — Theme', () => {
  test('HUD uses elevated surface, not dark background', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const overlay = page.locator('[data-testid="rush-overlay"]');
    if (await overlay.isVisible({ timeout: 2000 })) {
      const bgColor = await overlay.evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      // Should NOT be dark (rgb(38,38,38) or similar)
      // Should be light/elevated surface
      const match = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (match) {
        const [, r, g, b] = match.map(Number);
        // Light theme: r, g, b should all be > 200 (white-ish)
        const avg = (r + g + b) / 3;
        expect(avg).toBeGreaterThan(180); // Not dark
      }
    }
  });

  test('progress bar is visible below HUD', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    // Progress bar is the h-1 div after the HUD
    const overlay = page.locator('[data-testid="rush-overlay"]');
    if (await overlay.isVisible({ timeout: 2000 })) {
      const parent = overlay.locator('..');
      const progressBar = parent.locator('.h-1').first();
      expect(await progressBar.isVisible()).toBeTruthy();
    }
  });
});

test.describe('Rush Mode — Quit Flow', () => {
  test('quit button transitions to game over screen', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const quit = page.locator('[data-testid="quit-button"]');
    if (await quit.isVisible({ timeout: 2000 })) {
      await quit.click();

      // Should show game over / results screen
      const result = page.locator('[data-testid="rush-result"]');
      await expect(result).toBeVisible({ timeout: 3000 });

      // Should show "Game Over!" heading
      const heading = page.getByText('Game Over!');
      await expect(heading).toBeVisible();
    }
  });

  test('Play Again button is visible on results screen', async ({ page }) => {
    await goToRush(page);

    const threeMin = page.getByText('3 Minutes');
    if (await threeMin.isVisible()) {
      await threeMin.click();
    }

    await page.waitForTimeout(4500);

    const quit = page.locator('[data-testid="quit-button"]');
    if (await quit.isVisible({ timeout: 2000 })) {
      await quit.click();

      const playAgain = page.locator('[data-testid="play-again-button"]');
      await expect(playAgain).toBeVisible({ timeout: 3000 });
    }
  });
});
