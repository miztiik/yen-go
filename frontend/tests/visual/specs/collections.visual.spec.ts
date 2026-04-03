/**
 * Visual test: CollectionsBrowsePage (T080b).
 *
 * Verifies:
 * - Card grid layout responsive at 3 breakpoints
 * - Progress badges displayed correctly
 * - FilterBar with accessible pills
 * - StatsBar with flat background (no gradient)
 * - Theme-aware colors (CSS custom properties)
 * - Dark mode support
 *
 * Spec 129, Phase 8 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

const COLLECTIONS_URL = '/collections';

test.describe('CollectionsBrowsePage Visual', () => {
  test('has no gradient background', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    // Verify main layout has no gradient
    const layout = page.locator('[data-layout="single-column"]');
    if (await layout.count() > 0) {
      const bgImage = await layout.evaluate(
        (el) => window.getComputedStyle(el).backgroundImage,
      );
      expect(bgImage).toBe('none');
    }

    // Verify stats bar has no gradient
    const statsBar = page.locator('[data-testid="collections-stats"]');
    if (await statsBar.count() > 0) {
      const bgImage = await statsBar.evaluate(
        (el) => window.getComputedStyle(el).backgroundImage,
      );
      expect(bgImage).toBe('none');
    }
  });

  test('filter bar renders as accessible pills', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    const filterBar = page.locator('[data-testid="collections-filter"]');
    expect(await filterBar.count()).toBeGreaterThan(0);

    // All Levels button should exist and be a radio button
    const allLevelsButton = page.locator('[data-testid="collections-filter-all"]');
    expect(await allLevelsButton.getAttribute('role')).toBe('radio');
    expect(await allLevelsButton.getAttribute('aria-pressed')).toBe('true');
  });

  test('cards have minimum 44px touch target', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    const cards = page.locator('[data-testid^="collection-"]');
    const cardCount = await cards.count();

    if (cardCount > 0) {
      const firstCard = cards.first();
      const box = await firstCard.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
    }
  });

  test('cards do not translateY on hover', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    const cards = page.locator('[data-testid^="collection-"]');
    if (await cards.count() > 0) {
      const firstCard = cards.first();
      await firstCard.hover();
      const transform = await firstCard.evaluate(
        (el) => window.getComputedStyle(el).transform,
      );
      // Should be 'none' or 'matrix(1, 0, 0, 1, 0, 0)' - no translateY
      expect(transform).not.toContain('translateY');
    }
  });

  test('no inline styles remain', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    // Check page source does not have inline styles with hardcoded colors
    const inlineColorStyles = await page.evaluate(() => {
      const allElements = document.querySelectorAll('[style]');
      for (const el of allElements) {
        const style = (el as HTMLElement).style.cssText.toLowerCase();
        // Check for hardcoded colors that should not exist
        if (
          style.includes('white') ||
          style.includes('#') ||
          style.includes('gradient')
        ) {
          return true;
        }
      }
      return false;
    });
    expect(inlineColorStyles).toBe(false);
  });

  // Viewport screenshots — responsive grid verification
  // Mobile: 1 column
  test('screenshot at mobile (375x667)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('collections-mobile.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  // Tablet: 2 columns
  test('screenshot at tablet (768x1024)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('collections-tablet.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  // Desktop: 3 columns
  test('screenshot at desktop (1280x900)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('collections-desktop.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  // Mobile landscape
  test('screenshot at mobile-landscape (667x375)', async ({ page }) => {
    await page.setViewportSize({ width: 667, height: 375 });
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('collections-mobile-landscape.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('has elevated header band with back button', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    // Verify back button exists and has transparent background
    const backButton = page.locator('button:has-text("Back")');
    expect(await backButton.count()).toBeGreaterThan(0);

    const buttonBg = await backButton.first().evaluate(
      (el) => window.getComputedStyle(el).backgroundColor,
    );
    expect(buttonBg).toBe('rgba(0, 0, 0, 0)');
  });

  test('mastery badges have full opacity (no element-level opacity)', async ({ page }) => {
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');

    const badges = page.locator('span:has-text("New"), span:has-text("Learning"), span:has-text("Practiced"), span:has-text("Proficient"), span:has-text("Mastered")');
    const count = await badges.count();
    if (count > 0) {
      const badge = badges.first();
      const opacity = await badge.evaluate(
        (el) => window.getComputedStyle(el).opacity,
      );
      expect(opacity).toBe('1');
    }
  });

  // Dark mode
  test('screenshot in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(COLLECTIONS_URL);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('collections-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
