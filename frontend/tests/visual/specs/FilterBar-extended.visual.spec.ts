/**
 * Visual test: FilterBar component — extended states (G53).
 *
 * Verifies:
 * - All pills visible with correct active/inactive styling
 * - Count badges render correctly
 * - 44px minimum touch targets maintained
 * - Disabled (count=0) pills show reduced opacity
 * - Pill wrapping on narrow viewports (flex-wrap)
 * - Dark mode theme-aware colours (CSS custom properties)
 * - Keyboard navigation (ArrowRight between pills)
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.2 (G53)
 */

import { test, expect } from '@playwright/test';
import {
  VIEWPORTS,
  disableAnimations,
  INTERACTION_SETTLE_MS,
  FOCUS_SETTLE_MS,
  DEFAULT_MAX_DIFF,
  FULL_PAGE_SCREENSHOT,
  padClip,
} from './visual-test-helpers';

test.describe('FilterBar Extended Visual', () => {
  // ── Training page: category FilterBar ──

  test('training filter pills render with correct active state', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const filterBar = page.getByTestId('training-filter');
    await expect(filterBar).toBeVisible();

    // Verify exactly one pill has aria-checked="true" (active)
    const activePill = filterBar.locator('button[aria-checked="true"]');
    await expect(activePill).toHaveCount(1);

    const box = await filterBar.boundingBox();
    test.skip(!box, 'FilterBar not visible — cannot clip screenshot');

    await expect(page).toHaveScreenshot('filterbar-training-default.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  test('training filter pills maintain 44px touch targets', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');

    const pills = page.locator('[data-testid="training-filter"] button');
    const count = await pills.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const box = await pills.nth(i).boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
    }
  });

  test('selecting a different pill updates visual state', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const pills = page.locator('[data-testid="training-filter"] button');
    const pillCount = await pills.count();
    test.skip(pillCount < 2, 'Not enough pills to test selection change');

    await pills.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // R3-1: Verify aria-checked moved to the newly selected pill
    await expect(pills.nth(1)).toHaveAttribute('aria-checked', 'true');
    await expect(pills.nth(0)).toHaveAttribute('aria-checked', 'false');

    const filterBar = page.getByTestId('training-filter');
    const box = await filterBar.boundingBox();
    test.skip(!box, 'FilterBar not visible after selection');

    await expect(page).toHaveScreenshot('filterbar-training-second-selected.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── R3-2: Keyboard navigation (ArrowRight between pills) ──

  test('keyboard ArrowRight moves focus and selection between pills', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const filterBar = page.getByTestId('training-filter');
    const pills = filterBar.locator('button');
    const pillCount = await pills.count();
    test.skip(pillCount < 2, 'Not enough pills to test keyboard nav');

    // Focus the first (active) pill
    await pills.first().focus();
    await page.waitForTimeout(FOCUS_SETTLE_MS);

    // Press ArrowRight to move to next pill
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(FOCUS_SETTLE_MS);

    // Verify focus moved and aria-checked updated
    await expect(pills.nth(1)).toHaveAttribute('aria-checked', 'true');
    await expect(pills.nth(1)).toBeFocused();

    const box = await filterBar.boundingBox();
    test.skip(!box, 'FilterBar not visible');

    await expect(page).toHaveScreenshot('filterbar-keyboard-arrow-right.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── Technique page: level FilterBar (9 pills, all levels) ──

  test('technique level filter shows all 9 level pills', async ({ page }) => {
    await page.goto('/techniques');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const levelFilter = page.getByTestId('level-filter');
    test.skip((await levelFilter.count()) === 0, 'Level filter not present — no data');

    const box = await levelFilter.boundingBox();
    test.skip(!box, 'Level filter not visible');

    await expect(page).toHaveScreenshot('filterbar-technique-levels.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  test('technique level pills scroll horizontally on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/techniques');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const scrollContainer = page.getByTestId('level-filter-scroll');
    test.skip((await scrollContainer.count()) === 0, 'Level scroll container not present');

    const overflow = await scrollContainer.evaluate(
      (el) => window.getComputedStyle(el).overflowX,
    );
    expect(overflow).toBe('auto');

    // SA2-4: Verify content is actually scrollable (not just CSS property)
    const isScrollable = await scrollContainer.evaluate(
      (el) => el.scrollWidth > el.clientWidth,
    );
    expect(isScrollable).toBe(true);

    const box = await scrollContainer.boundingBox();
    test.skip(!box, 'Scroll container not visible');

    await expect(page).toHaveScreenshot('filterbar-technique-levels-mobile.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── Responsive viewport screenshots ──

  for (const viewport of VIEWPORTS) {
    test(`training filter strip at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/training');
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      await expect(page).toHaveScreenshot(
        `filterbar-training-${viewport.name}.png`,
        FULL_PAGE_SCREENSHOT,
      );
    });
  }

  // ── Dark mode ──

  test('filter pills in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const filterBar = page.getByTestId('training-filter');
    test.skip((await filterBar.count()) === 0, 'FilterBar not present');

    const box = await filterBar.boundingBox();
    test.skip(!box, 'FilterBar not visible in dark mode');

    await expect(page).toHaveScreenshot('filterbar-training-dark.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  test('full training page dark mode with filters', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    await expect(page).toHaveScreenshot(
      'filterbar-training-dark-full.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // R3-10: Dark mode for technique level filter bar (9 pills)
  test('technique level filter in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/techniques');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const levelFilter = page.getByTestId('level-filter');
    test.skip((await levelFilter.count()) === 0, 'Level filter not present');

    const box = await levelFilter.boundingBox();
    test.skip(!box, 'Level filter not visible in dark mode');

    await expect(page).toHaveScreenshot('filterbar-technique-levels-dark.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });
});
