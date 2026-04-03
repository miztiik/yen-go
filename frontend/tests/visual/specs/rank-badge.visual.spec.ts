/**
 * Visual Tests for RankBadge Component (9-Level System)
 * 
 * Verifies the 9-level skill system from config/levels.json is correctly displayed.
 * This test fulfills T019 from spec 020-config-hardcode-removal.
 * 
 * 9 Levels: novice, beginner, elementary, intermediate, upper-intermediate,
 *           advanced, low-dan, high-dan, expert
 */

import { test, expect } from '@playwright/test';

test.describe('RankBadge Visual Tests (9-Level System)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');
  });

  test.describe('All Skill Levels', () => {
    test('all 9 skill levels displayed together', async ({ page }) => {
      const fixture = page.locator('#rank-badge-all-levels');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-all-levels.png');
    });

    test('novice level (DDK 30-25)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-novice');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-novice.png');
    });

    test('beginner level (DDK 24-20)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-beginner');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-beginner.png');
    });

    test('elementary level (DDK 19-15)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-elementary');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-elementary.png');
    });

    test('intermediate level (DDK 14-10)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-intermediate');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-intermediate.png');
    });

    test('upper-intermediate level (DDK 9-5)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-upper-intermediate');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-upper-intermediate.png');
    });

    test('advanced level (DDK 4-1)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-advanced');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-advanced.png');
    });

    test('low-dan level (1d-3d)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-low-dan');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-low-dan.png');
    });

    test('high-dan level (4d-6d)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-high-dan');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-high-dan.png');
    });

    test('expert level (7d+/Pro)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-expert');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-expert.png');
    });
  });

  test.describe('Size Variants', () => {
    test('size comparison (small, medium, large)', async ({ page }) => {
      const fixture = page.locator('#rank-badge-sizes');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('rank-badge-sizes.png');
    });
  });
});
