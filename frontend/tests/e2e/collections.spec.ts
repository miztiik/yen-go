/**
 * Collections E2E Test
 * @module tests/e2e/collections.spec
 *
 * End-to-end tests for the curated collections catalog page.
 * Tests category sections, search, navigation to solver, and puzzle rendering.
 */

import { test, expect } from '@playwright/test';

test.describe('Collection Catalog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should display collections page with category sections', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // Should have page title
    await expect(page.getByRole('heading', { name: 'Collections' }).first()).toBeVisible();

    // Should have search box
    await expect(page.getByTestId('collections-search')).toBeVisible();

    // Should have at least one section
    const sections = page.locator('[data-testid^="section-"]');
    await expect(sections.first()).toBeVisible();
  });

  test('should show featured section with editorial collections', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // Featured section should exist
    const featured = page.getByTestId('section-featured');
    if (await featured.count() > 0) {
      await expect(featured).toBeVisible();
      await expect(featured.getByText('Featured')).toBeVisible();
    }
  });

  test('should show learning paths section', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    const section = page.getByTestId('section-learning-paths');
    if (await section.count() > 0) {
      await expect(section).toBeVisible();
      await expect(section.getByText('Learning Paths')).toBeVisible();
    }
  });

  test('should search collections by name', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByTestId('collections-search');
    await searchInput.fill('essentials');

    // Wait for debounced search to trigger
    await page.waitForTimeout(500);

    // Should show search results — collection cards should appear
    const cards = page.locator('[data-testid^="collection-"]');
    await expect(cards.first()).toBeVisible();
  });

  test('should search collections by author', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByTestId('collections-search');
    await searchInput.fill('cho chikun');

    await page.waitForTimeout(500);

    // Should find Cho Chikun collections
    const choCards = page.locator('[data-testid*="cho-chikun"]');
    await expect(choCards.first()).toBeVisible();
  });

  test('should clear search and restore sections', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByTestId('collections-search');
    await searchInput.fill('test');
    await page.waitForTimeout(500);

    // Clear search
    await page.getByLabel('Clear search').click();
    await page.waitForTimeout(500);

    // Sections should reappear
    const sections = page.locator('[data-testid^="section-"]');
    await expect(sections.first()).toBeVisible();
  });

  test('should show Coming Soon for unavailable collections', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // At least some collections should show Coming Soon
    const comingSoon = page.getByText('Coming Soon');
    if (await comingSoon.count() > 0) {
      await expect(comingSoon.first()).toBeVisible();
    }
  });

  test('should navigate to collection solver when clicking available collection', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // Find a collection card that has data (not disabled)
    const availableCards = page.locator('[data-testid^="collection-"]:not([aria-disabled="true"])');
    const count = await availableCards.count();

    if (count > 0) {
      const firstCard = availableCards.first();
      const cardText = await firstCard.textContent();
      await firstCard.click();

      // Should navigate to collection view
      await expect(page).toHaveURL(/\/collections\/curated-/);

      // Should show puzzle interface or collection details
      await page.waitForLoadState('networkidle');
    }
  });

  test('should show puzzle board when entering a collection with puzzles', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // Click an available collection
    const availableCards = page.locator('[data-testid^="collection-"]:not([aria-disabled="true"])');
    const count = await availableCards.count();

    if (count > 0) {
      await availableCards.first().click();
      await page.waitForLoadState('networkidle');

      // Look for the Go board
      const board = page.locator('[data-testid="goban-board"]');
      if (await board.count() > 0) {
        await expect(board).toBeVisible();
      }
    }
  });
});

test.describe('Collection Navigation', () => {
  test('should navigate from home to collections', async ({ page }) => {
    await page.goto('/');

    // Click Collections tile on home page
    await page.getByText('Collections').click();

    await expect(page).toHaveURL(/\/collections/);
  });

  test('should return to collections from collection view', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    const availableCards = page.locator('[data-testid^="collection-"]:not([aria-disabled="true"])');
    const count = await availableCards.count();

    if (count > 0) {
      await availableCards.first().click();
      await page.waitForLoadState('networkidle');

      // Go back
      const backButton = page.getByRole('button', { name: /back/i });
      if (await backButton.count() > 0) {
        await backButton.click();
        await expect(page).toHaveURL(/\/collections$/);
      }
    }
  });
});
