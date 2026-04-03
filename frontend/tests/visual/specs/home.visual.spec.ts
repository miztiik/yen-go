/**
 * Visual Tests for Home Screen Tiles
 * 
 * Tests home screen layout with activity tiles for:
 * - Collections
 * - Daily Challenge
 * - Training
 * - Puzzle Rush
 * - Random Challenge
 * - Technique Focus
 */

import { test, expect } from '@playwright/test';

test.describe('Home Screen Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Desktop Layout', () => {
    test.use({ viewport: { width: 1280, height: 800 } });

    test('home screen with all tiles', async ({ page }) => {
      await expect(page.locator('[data-testid="home-screen"]')).toBeVisible();
      await expect(page).toHaveScreenshot('home-desktop.png');
    });

    test('collections tile', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-collections"]');
      await expect(tile).toBeVisible();
      await expect(tile).toHaveScreenshot('tile-collections-desktop.png');
    });

    test('daily challenge tile', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-daily"]');
      await expect(tile).toBeVisible();
      await expect(tile).toHaveScreenshot('tile-daily-desktop.png');
    });

    test('puzzle rush tile', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-rush"]');
      await expect(tile).toBeVisible();
      await expect(tile).toHaveScreenshot('tile-rush-desktop.png');
    });
  });

  test.describe('Tablet Layout', () => {
    test.use({ viewport: { width: 768, height: 1024 } });

    test('home screen tablet', async ({ page }) => {
      await expect(page.locator('[data-testid="home-screen"]')).toBeVisible();
      await expect(page).toHaveScreenshot('home-tablet.png');
    });
  });

  test.describe('Mobile Layout', () => {
    test.use({ viewport: { width: 375, height: 667 } });

    test('home screen mobile', async ({ page }) => {
      await expect(page.locator('[data-testid="home-screen"]')).toBeVisible();
      await expect(page).toHaveScreenshot('home-mobile.png');
    });

    test('tiles stack vertically on mobile', async ({ page }) => {
      const tiles = page.locator('[data-testid^="tile-"]');
      await expect(tiles.first()).toBeVisible();
      
      // Check that tiles are displayed in a single column
      const firstTile = await tiles.first().boundingBox();
      const secondTile = await tiles.nth(1).boundingBox();
      
      if (firstTile && secondTile) {
        // On mobile, tiles should stack (same x position)
        expect(Math.abs((firstTile.x || 0) - (secondTile.x || 0))).toBeLessThan(50);
      }
    });
  });

  test.describe('Tile Hover States', () => {
    test.use({ viewport: { width: 1280, height: 800 } });

    test('collections tile hover', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-collections"]');
      await tile.hover();
      await expect(tile).toHaveScreenshot('tile-collections-hover.png');
    });

    test('daily tile hover', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-daily"]');
      await tile.hover();
      await expect(tile).toHaveScreenshot('tile-daily-hover.png');
    });
  });

  test.describe('Tile with Progress', () => {
    test.beforeEach(async ({ page }) => {
      // Set up progress data
      await page.evaluate(() => {
        localStorage.setItem('yen-go-progress', JSON.stringify({
          collections: {
            'level-elementary': {
              completedPuzzles: Array.from({ length: 50 }, (_, i) => `p${i}`),
            }
          }
        }));
        localStorage.setItem('yen-go-daily-streak', JSON.stringify({
          current: 7,
          best: 14,
          lastCompletedDate: new Date().toISOString().split('T')[0],
        }));
      });
      await page.reload();
      await page.waitForLoadState('networkidle');
    });

    test('collections tile shows progress', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-collections"]');
      await expect(tile).toBeVisible();
      // Should show some progress indicator
      await expect(tile).toHaveScreenshot('tile-collections-with-progress.png');
    });

    test('daily tile shows streak', async ({ page }) => {
      const tile = page.locator('[data-testid="tile-daily"]');
      await expect(tile).toBeVisible();
      // Should show streak count
      await expect(tile.getByText(/7|streak/i)).toBeVisible();
      await expect(tile).toHaveScreenshot('tile-daily-with-streak.png');
    });
  });
});
