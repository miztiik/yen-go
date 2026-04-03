/**
 * Visual test: Puzzle Rush game over screen.
 * @module tests/visual/rush-game-over.visual.spec
 *
 * Spec 125, Task T096
 */

import { test, expect } from '@playwright/test';

test.describe('Visual: Rush Game Over', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/rush');
    await page.getByTestId('start-rush-button').click();
    // Wait for countdown
    await page.waitForTimeout(3500);
    // Quit to reach game over screen
    await page.getByTestId('quit-button').click();
  });

  test('game over screen layout', async ({ page }) => {
    const result = page.getByTestId('rush-result');
    await expect(result).toBeVisible();
    
    await expect(result).toHaveScreenshot('rush-game-over.png', {
      threshold: 0.3,
    });
  });

  test('final score display', async ({ page }) => {
    const finalScore = page.getByTestId('final-score');
    await expect(finalScore).toBeVisible();
    
    // Score should be styled prominently
    const fontSize = await finalScore.evaluate(el => 
      window.getComputedStyle(el).fontSize
    );
    expect(parseInt(fontSize)).toBeGreaterThan(40);
  });

  test('navigation buttons visible', async ({ page }) => {
    await expect(page.getByTestId('home-button')).toBeVisible();
    await expect(page.getByTestId('play-again-button')).toBeVisible();
    
    // Screenshot of button area
    const result = page.getByTestId('rush-result');
    await expect(result).toHaveScreenshot('rush-game-over-buttons.png', {
      threshold: 0.3,
    });
  });

  test('statistics grid layout', async ({ page }) => {
    // Verify stats are shown in a grid
    await expect(page.getByText(/Solved/i)).toBeVisible();
    await expect(page.getByText(/Accuracy/i)).toBeVisible();
  });
});
