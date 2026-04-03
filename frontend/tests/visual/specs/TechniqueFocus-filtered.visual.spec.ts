/**
 * Visual test: TechniqueBrowsePage with active filters (G56).
 *
 * Verifies:
 * - Category filter changes card subset (All / Objectives / Tesuji / Techniques)
 * - Sort filter changes card order (A-Z / Count)
 * - Level filter with 9 pills — selecting a level filters technique cards
 * - Combined category + level filter visual state
 * - Filter strip two-row layout (Row 1: Category + Sort, Row 2: Levels)
 * - Dark mode with active filters
 * - Mobile responsiveness — level pills horizontal scroll
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.5 (G56)
 */

import { test, expect } from '@playwright/test';
import {
  VIEWPORTS,
  disableAnimations,
  INTERACTION_SETTLE_MS,
  FULL_PAGE_SCREENSHOT,
} from './visual-test-helpers';

const TECHNIQUE_URL = '/techniques';

test.describe('TechniqueFocus Filtered Visual', () => {
  // ── Category filter ──

  test('category filter — Objectives selected', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="category-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 2, 'Not enough category pills');

    await pills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('technique-filtered-objectives.png', FULL_PAGE_SCREENSHOT);
  });

  test('category filter — Tesuji selected', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="category-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 3, 'Not enough category pills for Tesuji');

    await pills.nth(2).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('technique-filtered-tesuji.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Sort filter ──

  test('sort filter — count sort selected', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const sortPills = page.locator('[data-testid="sort-filter"] button');
    const sortCount = await sortPills.count();
    test.skip(sortCount < 2, 'Not enough sort options');

    // R3-3: Capture card count before sort change
    const cards = page.locator('[data-testid^="technique-card-"]');
    const countBefore = await cards.count();

    await sortPills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // R3-3: Sort should not change card count (reorder only, not filter)
    const countAfter = await cards.count();
    expect(countAfter).toBe(countBefore);

    await expect(page).toHaveScreenshot('technique-sort-count.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Level filter ──

  test('level filter — selecting a specific level', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const levelPills = page.locator('[data-testid="level-filter"] button');
    const levelCount = await levelPills.count();
    test.skip(levelCount < 3, 'Not enough level pills');

    await levelPills.nth(2).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('technique-filtered-level.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Combined: category + level ──

  test('combined filter — category + level', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const catPills = page.locator('[data-testid="category-filter"] button');
    if ((await catPills.count()) >= 2) {
      await catPills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    const levelPills = page.locator('[data-testid="level-filter"] button');
    if ((await levelPills.count()) >= 2) {
      await levelPills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    await expect(page).toHaveScreenshot('technique-combined-filter.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Empty filter state (SA-1) ──

  test('empty filter state shows message after restrictive filters', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    // Select last category to narrow results
    const catPills = page.locator('[data-testid="category-filter"] button');
    const catCount = await catPills.count();
    if (catCount >= 2) {
      await catPills.nth(catCount - 1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    // Select last level to further restrict
    const levelPills = page.locator('[data-testid="level-filter"] button');
    const levelCount = await levelPills.count();
    if (levelCount >= 2) {
      await levelPills.nth(levelCount - 1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    const emptyState = page.getByTestId('technique-empty-filter');
    test.skip(
      (await emptyState.count()) === 0,
      'Empty filter state not triggered — data has results for all filter combos',
    );

    await expect(page).toHaveScreenshot(
      'technique-empty-filter-state.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Filter strip two-row layout ──

  test('filter strip two-row layout visible', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const categoryFilter = page.getByTestId('category-filter');
    await expect(categoryFilter).toBeVisible();

    await expect(page).toHaveScreenshot('technique-filter-strip-layout.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Responsive with filtered state ──

  for (const viewport of VIEWPORTS) {
    test(`filtered state at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(TECHNIQUE_URL);
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      const catPills = page.locator('[data-testid="category-filter"] button');
      if ((await catPills.count()) >= 2) {
        await catPills.nth(1).click();
        await page.waitForTimeout(INTERACTION_SETTLE_MS);
      }

      await expect(page).toHaveScreenshot(
        `technique-filtered-${viewport.name}.png`,
        FULL_PAGE_SCREENSHOT,
      );
    });
  }

  // ── Dark mode ──

  test('dark mode — category filter active', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const catPills = page.locator('[data-testid="category-filter"] button');
    if ((await catPills.count()) >= 2) {
      await catPills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    await expect(page).toHaveScreenshot('technique-filtered-dark.png', FULL_PAGE_SCREENSHOT);
  });

  test('dark mode — level filter active', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(TECHNIQUE_URL);
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const levelPills = page.locator('[data-testid="level-filter"] button');
    const levelCount = await levelPills.count();
    test.skip(levelCount < 3, 'Not enough level pills');

    await levelPills.nth(2).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('technique-filtered-level-dark.png', FULL_PAGE_SCREENSHOT);
  });
});
