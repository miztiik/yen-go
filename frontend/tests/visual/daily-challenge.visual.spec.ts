/**
 * Visual test: Daily Challenge page.
 * @module tests/visual/daily-challenge.visual.spec
 *
 * Spec 125, Task T101
 */

import { test, expect } from '@playwright/test';

test.describe('Visual: Daily Challenge', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/daily');
    await page.waitForTimeout(1000);
  });

  test('daily challenge header layout', async ({ page }) => {
    const header = page.locator('header').first();
    await expect(header).toBeVisible();
    
    await expect(header).toHaveScreenshot('daily-header.png', {
      threshold: 0.3,
    });
  });

  test('daily challenge mode badge', async ({ page }) => {
    // Find mode badge
    const badge = page.getByText(/Standard|Timed/i).first();
    await expect(badge).toBeVisible();
  });

  test('puzzle navigation carousel', async ({ page }) => {
    const carousel = page.locator('.puzzle-carousel, [data-testid="puzzle-carousel"]');
    const carouselCount = await carousel.count();
    
    if (carouselCount > 0) {
      await expect(carousel.first()).toHaveScreenshot('daily-carousel.png', {
        threshold: 0.3,
      });
    }
  });

  test('full page layout', async ({ page }) => {
    await expect(page).toHaveScreenshot('daily-page-full.png', {
      threshold: 0.3,
      fullPage: true,
    });
  });
});
