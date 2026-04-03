/**
 * Visual Tests for LevelCard Component
 * 
 * Tests various states: unlocked, completed, locked, and different difficulty levels
 */

import { test, expect } from '@playwright/test';

test.describe('LevelCard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Card States', () => {
    test('unlocked level card', async ({ page }) => {
      const fixture = page.locator('#level-card-unlocked');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('level-card-unlocked.png');
    });

    test('completed level card', async ({ page }) => {
      const fixture = page.locator('#level-card-completed');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('level-card-completed.png');
    });

    test('locked level card', async ({ page }) => {
      const fixture = page.locator('#level-card-locked');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('level-card-locked.png');
    });

    test('advanced level card', async ({ page }) => {
      const fixture = page.locator('#level-card-advanced');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('level-card-advanced.png');
    });

    test('expert level card', async ({ page }) => {
      const fixture = page.locator('#level-card-expert');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('level-card-expert.png');
    });
  });
});
