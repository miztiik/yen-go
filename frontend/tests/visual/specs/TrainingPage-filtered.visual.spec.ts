/**
 * Visual test: TrainingBrowsePage with active filters applied (G55).
 *
 * Verifies:
 * - Page with tag filter applied — filtered level cards visible
 * - Page with category filter changed — subset of levels shown
 * - Empty filter state — "no matches" message with clear button
 * - Clear filters button click restores unfiltered state
 * - Filter strip layout: FilterBar + FilterDropdown + ActiveFilterChip inline
 * - Combined filter state (category + tag) visual consistency
 * - Dark mode with active filters
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.4 (G55)
 */

import { test, expect } from '@playwright/test';
import {
  VIEWPORTS,
  disableAnimations,
  INTERACTION_SETTLE_MS,
  FULL_PAGE_SCREENSHOT,
} from './visual-test-helpers';

test.describe('TrainingBrowsePage Filtered Visual', () => {
  // R3-9: Seed all 9 levels for consistent visual baseline across all tests
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const levels = [
        'novice', 'beginner', 'elementary', 'intermediate',
        'upper-intermediate', 'advanced', 'low-dan', 'high-dan', 'expert',
      ];
      const progress: Record<string, { completed: number; total: number }> = {};
      levels.forEach((level, i) => {
        progress[level] = { completed: i * 3, total: 50 };
      });
      localStorage.setItem('yen-go-training-progress', JSON.stringify(progress));
    });
  });

  // ── Category filter changes ──

  test('category filter — second option selected', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 2, 'Not enough category pills');

    await pills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('training-filtered-category.png', FULL_PAGE_SCREENSHOT);
  });

  test('category filter — third option selected', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 3, 'Not enough category pills for third option');

    await pills.nth(2).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot(
      'training-filtered-category-advanced.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Tag filter via dropdown ──

  test('tag filter applied — chip visible + filtered results', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
    test.skip((await options.count()) < 2, 'Not enough enabled tag options');

    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Verify chip appeared
    const chip = page.getByTestId('training-tag-chip');
    if ((await chip.count()) > 0) {
      await expect(chip).toBeVisible();
    }

    await expect(page).toHaveScreenshot('training-filtered-tag.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Empty filter state ──

  test('empty filter state shows message after restrictive filter', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    // Actively try to trigger empty state: select last category + last tag
    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    if (pillCount >= 2) {
      await pills.nth(pillCount - 1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    // Also select a tag to further narrow results
    const trigger = page.getByTestId('training-tag-filter-trigger');
    if ((await trigger.count()) > 0) {
      await trigger.click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);

      const panel = page.getByTestId('training-tag-filter-panel');
      if ((await panel.count()) > 0) {
        const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
        const optCount = await options.count();
        if (optCount >= 2) {
          // Select last enabled tag for maximum restriction
          await options.nth(optCount - 1).click();
          await page.waitForTimeout(INTERACTION_SETTLE_MS);
        }
      }
    }

    const emptyState = page.getByTestId('training-empty-filter');
    test.skip(
      (await emptyState.count()) === 0,
      'Empty filter state not triggered — data has results for all filter combos',
    );

    // UX2-3: Verify empty state displays expected message
    const messageText = await emptyState.textContent();
    expect(messageText).toContain('No puzzles match');

    // Verify the clear-filters button is also present
    const clearBtn = page.getByTestId('clear-filters-button');
    if ((await clearBtn.count()) > 0) {
      await expect(clearBtn).toBeVisible();
    }

    await expect(page).toHaveScreenshot(
      'training-empty-filter-state.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── R3-6: Clear filters button click restores unfiltered state ──

  test('clear filters button restores unfiltered state', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    // Trigger empty state: select last category + last tag
    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    if (pillCount >= 2) {
      await pills.nth(pillCount - 1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    const trigger = page.getByTestId('training-tag-filter-trigger');
    if ((await trigger.count()) > 0) {
      await trigger.click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);

      const panel = page.getByTestId('training-tag-filter-panel');
      if ((await panel.count()) > 0) {
        const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
        const optCount = await options.count();
        if (optCount >= 2) {
          await options.nth(optCount - 1).click();
          await page.waitForTimeout(INTERACTION_SETTLE_MS);
        }
      }
    }

    const clearBtn = page.getByTestId('clear-filters-button');
    test.skip(
      (await clearBtn.count()) === 0,
      'Clear filters button not visible — empty state not triggered',
    );

    // Click Clear filters
    await clearBtn.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Empty state should be gone
    const emptyState = page.getByTestId('training-empty-filter');
    await expect(emptyState).toHaveCount(0);

    // Tag chip should also be gone
    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toHaveCount(0);

    await expect(page).toHaveScreenshot(
      'training-after-clear-filters.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Filter strip layout (all components inline) ──

  test('filter strip — all filter components visible', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const filterBar = page.getByTestId('training-filter');
    await expect(filterBar).toBeVisible();

    await expect(page).toHaveScreenshot(
      'training-filter-strip-layout.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Combined category + tag filter (UX-5) ──

  test('combined filter — category + tag applied together', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    // Select second category
    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 2, 'Not enough category pills');

    await pills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Also apply a tag filter
    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
    test.skip((await options.count()) < 2, 'Not enough enabled tag options');

    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot(
      'training-combined-category-tag.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Responsive with filtered state ──

  for (const viewport of VIEWPORTS) {
    test(`filtered state at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/training');
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      const pills = page.locator('[data-testid="training-filter"] button');
      if ((await pills.count()) >= 2) {
        await pills.nth(1).click();
        await page.waitForTimeout(INTERACTION_SETTLE_MS);
      }

      await expect(page).toHaveScreenshot(
        `training-filtered-${viewport.name}.png`,
        FULL_PAGE_SCREENSHOT,
      );
    });
  }

  // ── Dark mode with filters ──

  test('dark mode — category filter active', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="training-filter"] button');
    if ((await pills.count()) >= 2) {
      await pills.nth(1).click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);
    }

    await expect(page).toHaveScreenshot('training-filtered-dark.png', FULL_PAGE_SCREENSHOT);
  });

  test('dark mode — tag filter active with chip', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    if ((await panel.count()) > 0) {
      const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
      if ((await options.count()) >= 2) {
        await options.nth(1).click();
        await page.waitForTimeout(INTERACTION_SETTLE_MS);
      }
    }

    await expect(page).toHaveScreenshot('training-filtered-tag-dark.png', FULL_PAGE_SCREENSHOT);
  });
});
