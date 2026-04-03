/**
 * E2E test: Puzzle Rush start and duration selection.
 * @module tests/e2e/rush-start.spec
 *
 * Spec 125, Task T091 (part)
 *
 * Flow: /modes/rush loads RushBrowsePage (duration selection).
 * Clicking a duration card triggers PuzzleRushPage with countdown.
 */

import { test, expect } from '@playwright/test';

test.describe('Puzzle Rush - Start', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/yen-go/modes/rush');
  });

  test('shows browse screen with duration options', async ({ page }) => {
    // Browse screen visible with title
    await expect(page.getByRole('heading', { name: /Puzzle Rush/i })).toBeVisible({ timeout: 15_000 });
    
    // Duration cards (3, 5, 10 minutes)
    await expect(page.getByTestId('rush-duration-3')).toBeVisible();
    await expect(page.getByTestId('rush-duration-5')).toBeVisible();
    await expect(page.getByTestId('rush-duration-10')).toBeVisible();
  });

  test('can click different duration cards', async ({ page }) => {
    // All three duration cards should be clickable
    await expect(page.getByTestId('rush-duration-3')).toBeVisible();
    await expect(page.getByTestId('rush-duration-5')).toBeVisible();
    await expect(page.getByTestId('rush-duration-10')).toBeVisible();
  });

  test('starts countdown when duration card clicked', async ({ page }) => {
    await page.getByTestId('rush-duration-3').click();
    
    // Countdown should show
    await expect(page.getByTestId('countdown-value')).toBeVisible();
    await expect(page.getByText(/Get ready/i)).toBeVisible();
  });

  test('countdown decrements from 3 to 1', async ({ page }) => {
    await page.getByTestId('rush-duration-3').click();
    
    // Start at 3
    await expect(page.getByTestId('countdown-value')).toHaveText('3');
    
    // Wait for decrement
    await page.waitForTimeout(1100);
    await expect(page.getByTestId('countdown-value')).toHaveText('2');
    
    // Wait for next decrement
    await page.waitForTimeout(1100);
    await expect(page.getByTestId('countdown-value')).toHaveText('1');
  });

  test('transitions to playing state after countdown', async ({ page }) => {
    await page.getByTestId('rush-duration-3').click();
    
    // Wait for countdown to complete (3 seconds)
    await page.waitForTimeout(3500);
    
    // Rush overlay should be visible
    await expect(page.getByTestId('rush-overlay')).toBeVisible();
    await expect(page.getByTestId('rush-timer')).toBeVisible();
    await expect(page.getByTestId('rush-lives')).toBeVisible();
  });
});
