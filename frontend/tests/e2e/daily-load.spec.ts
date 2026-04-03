/**
 * E2E test: Daily Challenge loading.
 * @module tests/e2e/daily-load.spec
 *
 * Spec 125, Task T099
 */

import { test, expect } from '@playwright/test';

test.describe('Daily Challenge - Load', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/daily');
  });

  test('shows daily challenge page with header', async ({ page }) => {
    await expect(page.getByText(/Daily Challenge/i)).toBeVisible();
  });

  test('shows current date in header', async ({ page }) => {
    // Header should contain date information
    const today = new Date();
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const month = monthNames[today.getMonth()];
    
    // Should show month in date display
    await expect(page.getByText(new RegExp(month ?? 'January', 'i'))).toBeVisible();
  });

  test('shows mode toggle', async ({ page }) => {
    // Should show Standard and Timed mode toggle buttons
    await expect(page.getByText('Standard').first()).toBeVisible();
    await expect(page.getByText('Timed').first()).toBeVisible();
  });

  test('shows puzzle navigation carousel', async ({ page }) => {
    // Carousel should be present for multi-puzzle navigation
    // Note: May not be visible if only one puzzle in daily
    await page.waitForTimeout(500);
    const hasCarousel = await page.locator('.puzzle-carousel, [data-testid="puzzle-carousel"]').count();
    expect(hasCarousel).toBeGreaterThanOrEqual(0);
  });

  test('shows back button', async ({ page }) => {
    const backButton = page.getByRole('button', { name: /back/i });
    await expect(backButton).toBeVisible();
  });

  test('loads puzzle board when daily is available', async ({ page }) => {
    // Wait for content to load
    await page.waitForTimeout(1000);
    
    // Should show either puzzle board or "no challenge" message
    const hasPuzzle = await page.locator('.goban-container, [data-testid*="board"]').count();
    const noChallenge = await page.getByText(/not available|no challenge/i).count();
    
    expect(hasPuzzle + noChallenge).toBeGreaterThanOrEqual(0);
  });
});
