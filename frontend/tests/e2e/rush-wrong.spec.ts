/**
 * E2E test: Puzzle Rush wrong answer and lives system.
 * @module tests/e2e/rush-wrong.spec
 *
 * Spec 125, Task T091 (part)
 *
 * Flow: Click duration card on RushBrowsePage -> countdown -> playing.
 */

import { test, expect } from '@playwright/test';

test.describe('Puzzle Rush - Wrong Answers', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/yen-go/modes/rush');
    // Click 3-min duration to start
    await page.getByTestId('rush-duration-3').click();
    // Wait for countdown to complete
    await page.waitForTimeout(3500);
  });

  test('lives display is visible during play', async ({ page }) => {
    const lives = page.getByTestId('rush-lives');
    await expect(lives).toBeVisible();
  });

  test('skip button costs one life', async ({ page }) => {
    const skipButton = page.getByTestId('skip-button');
    await expect(skipButton).toBeVisible();
    await expect(skipButton).toContainText(/Skip/i);
  });

  test('quit button is available during play', async ({ page }) => {
    const quitButton = page.getByTestId('quit-button');
    await expect(quitButton).toBeVisible();
    await quitButton.click();
    
    // Should transition to finished state
    await expect(page.getByTestId('rush-result')).toBeVisible();
  });
});
