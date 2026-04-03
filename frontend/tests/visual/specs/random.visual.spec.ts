import { test, expect } from '@playwright/test';

/**
 * Random Page Visual Regression Tests
 * Spec 129 - Frontend Alignment: Visual consistency for random page
 */

// Standard viewports for visual testing
const viewports = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 800 },
];

test.describe('Random Page Visual', () => {
  test.beforeEach(async ({ page }) => {
    // Mock localStorage with some session stats
    await page.addInitScript(() => {
      const stats = { puzzles: 5, correct: 3 };
      localStorage.setItem('yen-go-random-session', JSON.stringify(stats));
    });
  });

  test('renders without gradient backgrounds', async ({ page }) => {
    await page.goto('/random');
    await page.waitForSelector('[data-testid="random-page"]');

    // Check that main sections don't use gradient backgrounds
    const actionSection = await page.locator('[data-testid="action-section"]');
    const bg = await actionSection.evaluate((el) => getComputedStyle(el).backgroundImage);
    expect(bg).toBe('none');
  });

  test('filter pills have accessible styling', async ({ page }) => {
    await page.goto('/random');
    await page.waitForSelector('[data-testid="category-filter"]');

    const filterButtons = await page.locator('[data-testid="category-filter"] button').all();
    expect(filterButtons.length).toBe(4); // all, beginner, intermediate, advanced

    for (const button of filterButtons) {
      const height = await button.evaluate((el) => el.getBoundingClientRect().height);
      // Pills should be at least 44px for accessibility
      expect(height).toBeGreaterThanOrEqual(44);
    }
  });

  test('random button has proper touch targets', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/random');
    await page.waitForSelector('[data-testid="random-button"]');

    const button = page.locator('[data-testid="random-button"]');
    const box = await button.boundingBox();
    
    if (box) {
      // Button should be at least 56px tall (as styled)
      expect(box.height).toBeGreaterThanOrEqual(56);
      expect(box.width).toBeGreaterThanOrEqual(200);
    }
  });

  test('level cards have proper styling', async ({ page }) => {
    await page.goto('/random');
    await page.waitForSelector('[data-testid="random-page"]');

    const cards = await page.locator('[data-testid^="level-card-"]').all();
    expect(cards.length).toBe(9); // 9 skill levels

    for (const card of cards) {
      const bg = await card.evaluate((el) => getComputedStyle(el).backgroundImage);
      expect(bg).toBe('none'); // No gradient backgrounds
    }
  });

  // Responsive viewport tests
  for (const viewport of viewports) {
    test(`visual snapshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/random');
      await page.waitForSelector('[data-testid="random-page"]');
      
      // Wait for any animations to settle
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot(`random-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  test('dark mode visual snapshot', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/random');
    await page.waitForSelector('[data-testid="random-page"]');
    
    await page.waitForTimeout(300);

    await expect(page).toHaveScreenshot('random-dark-mode.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });

  test('category filter changes available levels', async ({ page }) => {
    await page.goto('/random');
    await page.waitForSelector('[data-testid="random-page"]');

    // Click on Beginner category
    await page.click('[data-testid="category-filter-beginner"]');
    
    // Should show only 3 beginner levels
    const cards = await page.locator('[data-testid^="level-card-"]').all();
    expect(cards.length).toBe(3);

    // Verify specific levels are shown
    await expect(page.locator('[data-testid="level-card-novice"]')).toBeVisible();
    await expect(page.locator('[data-testid="level-card-beginner"]')).toBeVisible();
    await expect(page.locator('[data-testid="level-card-elementary"]')).toBeVisible();
  });

  test('stats bar displays correctly', async ({ page }) => {
    await page.goto('/random');
    await page.waitForSelector('[data-testid="stats-bar"]');

    const statsBar = page.locator('[data-testid="stats-bar"]');
    await expect(statsBar).toContainText('Puzzles');
    await expect(statsBar).toContainText('Correct');
    await expect(statsBar).toContainText('Accuracy');
  });
});
