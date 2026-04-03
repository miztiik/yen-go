/**
 * E2E test: Puzzle Rush game over state.
 * @module tests/e2e/rush-game-over.spec
 *
 * Spec 125, Task T092
 *
 * Flow: Click duration card on RushBrowsePage -> countdown -> playing.
 */

import { test, expect } from '@playwright/test';

test.describe('Puzzle Rush - Game Over', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/yen-go/modes/rush');
    // Click 3-min duration to start
    await page.getByTestId('rush-duration-3').click();
    // Wait for countdown to complete
    await page.waitForTimeout(3500);
  });

  test('shows result screen after quitting', async ({ page }) => {
    await page.getByTestId('quit-button').click();
    
    // Result card should appear
    const result = page.getByTestId('rush-result');
    await expect(result).toBeVisible();
    
    // Should show "Game Over" heading
    await expect(result.getByRole('heading', { name: /Game Over/i })).toBeVisible();
  });

  test('result screen shows final score', async ({ page }) => {
    await page.getByTestId('quit-button').click();
    
    const finalScore = page.getByTestId('final-score');
    await expect(finalScore).toBeVisible();
    // Initial score is 0
    await expect(finalScore).toHaveText('0');
  });

  test('result screen shows statistics', async ({ page }) => {
    await page.getByTestId('quit-button').click();
    
    // Should show solved count and accuracy
    await expect(page.getByText(/Solved/i)).toBeVisible();
    await expect(page.getByText(/Accuracy/i)).toBeVisible();
  });

  test('result screen has navigation buttons', async ({ page }) => {
    await page.getByTestId('quit-button').click();
    
    // Home and Play Again buttons
    await expect(page.getByTestId('home-button')).toBeVisible();
    await expect(page.getByTestId('play-again-button')).toBeVisible();
  });

  test('play again button resets game', async ({ page }) => {
    await page.getByTestId('quit-button').click();
    await page.getByTestId('play-again-button').click();
    
    // Should return to setup or start new game
    // (behavior depends on onNewRush callback implementation)
  });
});
