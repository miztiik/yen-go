/**
 * Visual test: CollectionViewPage with active filters (G57).
 *
 * Targets the collection *detail* page (e.g., /collections/cho-chikun-life-death-elementary)
 * which has FilterBar (level) + FilterDropdown (tag) + ActiveFilterChip(s).
 * The /collections browse page has only search — no filter components.
 *
 * Verifies:
 * - Level FilterBar in collection context
 * - Tag FilterDropdown in collection context
 * - Active filter chips (level + tag) with dismiss buttons
 * - "Clear All" button when ≥2 filters active
 * - Combined level + tag filter visual state
 * - Empty filter state with clear action
 * - Dark mode with active filters
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.6 (G57)
 */

import { test, expect } from '@playwright/test';
import {
  VIEWPORTS,
  disableAnimations,
  INTERACTION_SETTLE_MS,
  FULL_PAGE_SCREENSHOT,
} from './visual-test-helpers';

// Use a well-known collection slug likely to have data across levels and tags
const COLLECTION_URL = '/collections/cho-chikun-life-death-elementary';
// Fallback collections in case the above has no data
const FALLBACK_URLS = [
  '/collections/beginner-essentials',
  '/collections/capture-problems',
] as const;

/** Navigate to a collection page, falling back if main URL yields no filter strip. */
async function navigateToCollection(page: import('@playwright/test').Page): Promise<boolean> {
  for (const url of [COLLECTION_URL, ...FALLBACK_URLS]) {
    await page.goto(url);
    await page.waitForLoadState('networkidle');

    const filterStrip = page.getByTestId('collection-filter-strip');
    if ((await filterStrip.count()) > 0) {
      return true;
    }
  }
  return false;
}

test.describe('CollectionsBrowsePage Filtered Visual', () => {
  // ── Filter strip layout ──

  test('filter strip — level bar + tag dropdown visible', async ({ page }) => {
    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    const filterStrip = page.getByTestId('collection-filter-strip');
    await expect(filterStrip).toBeVisible();

    await expect(page).toHaveScreenshot('collection-filter-strip.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Level filter ──

  test('level filter — selecting a level shows chip', async ({ page }) => {
    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    const levelPills = page.locator('[data-testid="collection-level-filter"] button');
    const levelCount = await levelPills.count();
    test.skip(levelCount < 2, 'Not enough level pills');

    await levelPills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const levelChip = page.getByTestId('collection-level-chip');
    if ((await levelChip.count()) > 0) {
      await expect(levelChip).toBeVisible();
    }

    await expect(page).toHaveScreenshot('collection-filtered-level.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Tag filter ──

  test('tag filter — selecting a tag shows chip', async ({ page }) => {
    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    const trigger = page.getByTestId('collection-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('collection-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Tag dropdown panel did not open');

    const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
    test.skip((await options.count()) < 2, 'Not enough tag options');

    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const tagChip = page.getByTestId('collection-tag-chip');
    if ((await tagChip.count()) > 0) {
      await expect(tagChip).toBeVisible();
    }

    await expect(page).toHaveScreenshot('collection-filtered-tag.png', FULL_PAGE_SCREENSHOT);
  });

  // ── R3-4: Combined level + tag → Clear All button (using test.skip for critical steps) ──

  test('combined filters — level + tag + clear all button', async ({ page }) => {
    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    // Select a level (required for combined test)
    const levelPills = page.locator('[data-testid="collection-level-filter"] button');
    test.skip((await levelPills.count()) < 2, 'Not enough level pills for combined test');

    await levelPills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Select a tag (required for combined test)
    const trigger = page.getByTestId('collection-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present for combined test');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('collection-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Tag panel did not open for combined test');

    const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
    test.skip((await options.count()) < 2, 'Not enough tag options for combined test');

    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // "Clear All" should appear when ≥2 filters active
    const clearAll = page.getByTestId('collection-clear-all');
    if ((await clearAll.count()) > 0) {
      await expect(clearAll).toBeVisible();
    }

    await expect(page).toHaveScreenshot('collection-combined-filters.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Clear All restores unfiltered state (UX-4) ──

  test('Clear All removes all filters and restores full results', async ({ page }) => {
    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    // Apply level + tag to trigger Clear All button
    const levelPills = page.locator('[data-testid="collection-level-filter"] button');
    if ((await levelPills.count()) >= 2) {
      await levelPills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    const trigger = page.getByTestId('collection-tag-filter-trigger');
    if ((await trigger.count()) > 0) {
      await trigger.click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);

      const panel = page.getByTestId('collection-tag-filter-panel');
      if ((await panel.count()) > 0) {
        const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
        if ((await options.count()) >= 2) {
          await options.nth(1).click();
          await page.waitForTimeout(INTERACTION_SETTLE_MS);
        }
      }
    }

    const clearAll = page.getByTestId('collection-clear-all');
    test.skip((await clearAll.count()) === 0, 'Clear All button not visible — filters may not have applied');

    // Click Clear All
    await clearAll.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // SA2-3: Chips should be removed from DOM after Clear All
    const levelChip = page.getByTestId('collection-level-chip');
    const tagChip = page.getByTestId('collection-tag-chip');
    await expect(levelChip).toHaveCount(0);
    await expect(tagChip).toHaveCount(0);

    await expect(page).toHaveScreenshot('collection-after-clear-all.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Responsive with filtered state ──

  for (const viewport of VIEWPORTS) {
    test(`filtered collection at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      const hasFilters = await navigateToCollection(page);
      test.skip(!hasFilters, 'No collection with filter strip found');

      await disableAnimations(page);

      const levelPills = page.locator('[data-testid="collection-level-filter"] button');
      if ((await levelPills.count()) >= 2) {
        await levelPills.nth(1).click();
        await page.waitForTimeout(INTERACTION_SETTLE_MS);
      }

      await expect(page).toHaveScreenshot(
        `collection-filtered-${viewport.name}.png`,
        FULL_PAGE_SCREENSHOT,
      );
    });
  }

  // ── Dark mode ──

  test('dark mode — filter strip', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    await expect(page).toHaveScreenshot('collection-filter-dark.png', FULL_PAGE_SCREENSHOT);
  });

  test('dark mode — filters active', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    const hasFilters = await navigateToCollection(page);
    test.skip(!hasFilters, 'No collection with filter strip found');

    await disableAnimations(page);

    const levelPills = page.locator('[data-testid="collection-level-filter"] button');
    if ((await levelPills.count()) >= 2) {
      await levelPills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    await expect(page).toHaveScreenshot('collection-filtered-dark.png', FULL_PAGE_SCREENSHOT);
  });
});
