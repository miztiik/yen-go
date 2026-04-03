/**
 * Visual regression tests for StreakDisplay component
 * Tests various streak states: new user, active, at-risk, long streaks,
 * compact mode, and milestone celebrations
 */
import { test, expect } from '@playwright/test';

test.describe('StreakDisplay Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the visual test fixtures page
    await page.goto('/visual-tests.html');
    // Wait for the page to be fully rendered
    await page.waitForSelector('h2:text("StreakDisplay Component")');
  });

  test('New User - No Streak', async ({ page }) => {
    const fixture = page.locator('#streak-new-user');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-new-user.png');
  });

  test('Active Streak - 5 Days', async ({ page }) => {
    const fixture = page.locator('#streak-active');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-active.png');
  });

  test('Streak At Risk', async ({ page }) => {
    const fixture = page.locator('#streak-at-risk');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-at-risk.png');
  });

  test('Long Streak - 30+ Days', async ({ page }) => {
    const fixture = page.locator('#streak-long');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-long.png');
  });

  test('Compact Mode', async ({ page }) => {
    const fixture = page.locator('#streak-compact');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-compact.png');
  });

  test('Milestone Just Reached', async ({ page }) => {
    const fixture = page.locator('#streak-milestone');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('streak-milestone.png');
  });
});
