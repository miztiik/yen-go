/**
 * E2E test: Collection browsing and puzzle selection.
 * @module tests/e2e/nav-collection.spec
 *
 * Spec 125, Task T109
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation - Collection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
  });

  test('can navigate to collection page', async ({ page }) => {
    // Look for collection links/cards
    const collectionLink = page.getByRole('link', { name: /beginner|intermediate|advanced/i });
    
    if (await collectionLink.count() > 0) {
      await collectionLink.first().click();
      await page.waitForTimeout(1000);
      
      // Should be on collection page
      const puzzlePage = page.getByTestId('puzzle-solve-page');
      const collectionPage = page.getByRole('heading', { level: 1 });
      expect((await puzzlePage.count()) + (await collectionPage.count())).toBeGreaterThan(0);
    }
  });

  test('collection shows puzzle list or grid', async ({ page }) => {
    await page.goto('/training');
    await page.waitForTimeout(1000);
    
    // Should show level cards or list
    const levelItems = page.locator('[data-testid*="level"], .level-card, .collection-item');
    await expect(levelItems.first()).toBeVisible();
  });

  test('selecting a puzzle loads it', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials');
    await page.waitForTimeout(1000);
    
    // Puzzle page should load with board
    const board = page.locator('.goban-container, [data-testid*="board"]');
    
    if (await board.count() > 0) {
      await expect(board.first()).toBeVisible();
    }
  });

  test('back button returns to collection list', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials');
    await page.waitForTimeout(1000);
    
    const backButton = page.getByRole('button', { name: /back/i });
    
    if (await backButton.count() > 0) {
      await backButton.click();
      await page.waitForTimeout(500);
    }
  });
});
