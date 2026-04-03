import { test, expect } from '@playwright/test';

/**
 * Training Page Visual Regression Tests
 * Spec 129 - Frontend Alignment: Visual consistency for training page
 */

// Standard viewports for visual testing
const viewports = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 800 },
];

test.describe('Training Page Visual', () => {
  test.beforeEach(async ({ page }) => {
    // Mock localStorage with some progress
    await page.addInitScript(() => {
      const progress = {
        beginner: { completed: 15, total: 50 },
        elementary: { completed: 8, total: 50 },
        intermediate: { completed: 0, total: 50 },
      };
      localStorage.setItem('yen-go-training-progress', JSON.stringify(progress));
    });
  });

  test('renders without gradient backgrounds', async ({ page }) => {
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');

    // Check that level cards don't use gradient backgrounds
    const cards = await page.locator('[data-testid^="training-level-"]').all();
    expect(cards.length).toBe(9);

    for (const card of cards) {
      const bg = await card.evaluate((el) => getComputedStyle(el).backgroundImage);
      expect(bg).toBe('none');
    }
  });

  test('filter pills have accessible styling', async ({ page }) => {
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-filter"]');

    const filterButtons = await page.locator('[data-testid="training-filter"] button').all();
    expect(filterButtons.length).toBeGreaterThan(0);

    for (const button of filterButtons) {
      const height = await button.evaluate((el) => el.getBoundingClientRect().height);
      // Pills should be reasonably sized for accessibility
      expect(height).toBeGreaterThanOrEqual(32);
    }
  });

  test('level cards have proper touch targets', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');

    // Find unlocked level cards (they should be clickable)
    const unlockedCards = await page.locator('[data-testid^="training-level-"]:not([data-locked="true"])').all();
    
    for (const card of unlockedCards) {
      const box = await card.boundingBox();
      if (box) {
        // Cards should be at least 44x44 for accessibility
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
      }
    }
  });

  test('no translateY hover transforms on cards', async ({ page }) => {
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');

    const cards = await page.locator('[data-testid^="training-level-"]').all();
    
    for (const card of cards) {
      await card.hover();
      const transform = await card.evaluate((el) => getComputedStyle(el).transform);
      // Should not have vertical translation on hover
      if (transform !== 'none') {
        const matrix = transform.match(/matrix\((.*)\)/);
        if (matrix) {
          const values = matrix[1].split(',').map(Number);
          // translateY is the 6th value in the matrix (index 5)
          expect(values[5]).toBe(0);
        }
      }
    }
  });

  // Responsive viewport tests
  for (const viewport of viewports) {
    test(`visual snapshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/training');
      await page.waitForSelector('[data-testid="training-page"]');
      
      // Wait for any animations to settle
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot(`training-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  test('dark mode visual snapshot', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');
    
    await page.waitForTimeout(300);

    await expect(page).toHaveScreenshot('training-dark-mode.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });

  test('progress badges display correctly', async ({ page }) => {
    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');

    // Check that beginner card shows progress
    const beginnerCard = page.locator('[data-testid="training-level-beginner"]');
    await expect(beginnerCard).toContainText(/15|30%/); // 15 completed or 30% progress
  });

  test('locked levels show lock indicator', async ({ page }) => {
    // Clear progress to ensure later levels are locked
    await page.addInitScript(() => {
      localStorage.removeItem('yen-go-training-progress');
    });

    await page.goto('/training');
    await page.waitForSelector('[data-testid="training-page"]');

    // Advanced levels should show locked state
    const expertCard = page.locator('[data-testid="training-level-expert"]');
    const hasLockedStyle = await expertCard.evaluate((el) => {
      return el.classList.contains('opacity-50') || 
             getComputedStyle(el).opacity < '1';
    });
    
    expect(hasLockedStyle).toBe(true);
  });
});
