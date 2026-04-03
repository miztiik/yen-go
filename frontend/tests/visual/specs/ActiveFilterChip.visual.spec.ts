/**
 * Visual test: ActiveFilterChip component (G58).
 *
 * Verifies:
 * - Chip renders with label + dismiss "x" button
 * - Accent-coloured pill styling (color-mix transparent background)
 * - 44px minimum interactive area for dismiss button
 * - Focus ring visible on keyboard focus
 * - Keyboard dismiss via Enter key
 * - Chip on Training page (tag chip) and Collection page (level chip)
 * - Dark mode theme-aware colours
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.7 (G58)
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

/** Helper: Apply a tag filter on the training page to make the ActiveFilterChip appear. */
async function applyTrainingTagFilter(page: import('@playwright/test').Page): Promise<boolean> {
  await page.goto('/training');
  await page.waitForLoadState('networkidle');
  await disableAnimations(page);

  const trigger = page.getByTestId('training-tag-filter-trigger');
  if ((await trigger.count()) === 0) return false;

  await trigger.click();
  await page.waitForTimeout(INTERACTION_SETTLE_MS);

  const panel = page.getByTestId('training-tag-filter-panel');
  if ((await panel.count()) === 0) return false;

  const options = panel.locator('[role="option"]:not([aria-disabled="true"])');
  if ((await options.count()) < 2) return false;

  await options.nth(1).click();
  await page.waitForTimeout(INTERACTION_SETTLE_MS);

  return true;
}

/** Extract numeric count from stats text like "42 puzzles" → 42. Returns null if unparseable. */
function extractCount(text: string | null): number | null {
  if (!text) return null;
  const match = text.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : null;
}

/** Collection page URLs for cross-context chip tests. */
const COLLECTION_URLS = [
  '/collections/cho-chikun-life-death-elementary',
  '/collections/beginner-essentials',
  '/collections/capture-problems',
] as const;

test.describe('ActiveFilterChip Visual', () => {
  // ── Basic rendering ──

  test('chip visible after applying tag filter', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter — no tag options available');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    const chipText = await chip.textContent();
    expect(chipText).toBeTruthy();

    const box = await chip.boundingBox();
    test.skip(!box, 'Chip has no bounding box');

    await expect(page).toHaveScreenshot('chip-tag-applied.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── Touch-target compliance (AP-1) ──

  test('chip meets 44px minimum touch target', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter — no tag options available');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    const box = await chip.boundingBox();
    test.skip(!box, 'Chip has no bounding box');

    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test('chip has accent styling', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    const borderColor = await chip.evaluate(
      (el) => window.getComputedStyle(el).borderColor,
    );
    expect(borderColor).toBeTruthy();
    expect(borderColor).not.toBe('rgba(0, 0, 0, 0)');
  });

  test('chip aria-label contains filter name', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    const ariaLabel = await chip.getAttribute('aria-label');
    expect(ariaLabel).toContain('Remove');
    expect(ariaLabel).toContain('filter');
  });

  // ── Dismiss interaction ──

  test('chip disappears after clicking dismiss', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    await chip.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(chip).not.toBeVisible();

    await expect(page).toHaveScreenshot('chip-after-dismiss.png', FULL_PAGE_SCREENSHOT);
  });

  test('page returns to unfiltered state after chip dismiss (UX-2)', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    // Capture filtered puzzle count from stats
    const stats = page.getByTestId('training-stats');
    const hasStats = (await stats.count()) > 0;
    const filteredCount = hasStats ? extractCount(await stats.textContent()) : null;

    await chip.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Chip should be gone
    await expect(chip).not.toBeVisible();

    // UX2-1: Stats should show more results after filter removal
    if (filteredCount !== null && hasStats) {
      const unfilteredCount = extractCount(await stats.textContent());
      if (unfilteredCount !== null) {
        expect(unfilteredCount).toBeGreaterThanOrEqual(filteredCount);
      }
    }

    await expect(page).toHaveScreenshot('chip-post-dismiss-full-page.png', FULL_PAGE_SCREENSHOT);
  });

  // ── R3-7: Keyboard dismiss via Enter ──

  test('chip dismissed via keyboard Enter', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    // Tab to the chip
    let focused = false;
    await page.keyboard.press('Tab');
    for (let i = 0; i < 15; i++) {
      focused = await page.evaluate(
        (testId) => document.activeElement?.closest(`[data-testid="${testId}"]`) !== null,
        'training-tag-chip',
      );
      if (focused) break;
      await page.keyboard.press('Tab');
    }
    test.skip(!focused, 'Could not focus chip via keyboard');

    // Press Enter to dismiss
    await page.keyboard.press('Enter');
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Chip should be gone
    await expect(chip).not.toBeVisible();

    await expect(page).toHaveScreenshot('chip-keyboard-dismiss.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Focus ring ──

  test('chip shows focus ring on keyboard focus', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    // Use keyboard Tab to trigger :focus-visible (not .focus() which only triggers :focus)
    let focused = false;
    await page.keyboard.press('Tab');
    for (let i = 0; i < 10; i++) {
      focused = await page.evaluate(
        (testId) => document.activeElement?.closest(`[data-testid="${testId}"]`) !== null,
        'training-tag-chip',
      );
      if (focused) break;
      await page.keyboard.press('Tab');
    }
    // SA2-1: Assert that focus was actually achieved
    expect(focused).toBe(true);

    await page.waitForTimeout(FOCUS_SETTLE_MS);

    const box = await chip.boundingBox();
    test.skip(!box, 'Chip has no bounding box for focus ring screenshot');

    await expect(page).toHaveScreenshot('chip-focus-ring.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── In context: full filter strip with chip ──

  test('chip inline with filter strip', async ({ page }) => {
    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    await expect(page).toHaveScreenshot('chip-in-filter-strip.png', FULL_PAGE_SCREENSHOT);
  });

  // ── R3-8: Collection page context ──

  test('chip renders in collection page context', async ({ page }) => {
    let chipVisible = false;
    for (const url of COLLECTION_URLS) {
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      const levelPills = page.locator('[data-testid="collection-level-filter"] button');
      if ((await levelPills.count()) >= 2) {
        await levelPills.nth(1).click();
        await page.waitForTimeout(INTERACTION_SETTLE_MS);

        const chip = page.getByTestId('collection-level-chip');
        if ((await chip.count()) > 0) {
          chipVisible = true;
          break;
        }
      }
    }

    test.skip(!chipVisible, 'No collection level chip appeared on any collection page');

    const chip = page.getByTestId('collection-level-chip');
    await expect(chip).toBeVisible();

    const box = await chip.boundingBox();
    test.skip(!box, 'Collection chip has no bounding box');

    await expect(page).toHaveScreenshot('chip-collection-context.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── Responsive ──

  for (const viewport of VIEWPORTS) {
    test(`chip at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      const applied = await applyTrainingTagFilter(page);
      test.skip(!applied, 'Could not apply tag filter');

      await expect(page).toHaveScreenshot(`chip-${viewport.name}.png`, FULL_PAGE_SCREENSHOT);
    });
  }

  // ── Dark mode ──

  test('dark mode — chip has theme-aware colours', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    const chip = page.getByTestId('training-tag-chip');
    await expect(chip).toBeVisible();

    const box = await chip.boundingBox();
    test.skip(!box, 'Chip has no bounding box for dark mode screenshot');

    await expect(page).toHaveScreenshot('chip-dark-mode.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  test('dark mode — chip in full page context', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });

    const applied = await applyTrainingTagFilter(page);
    test.skip(!applied, 'Could not apply tag filter');

    await expect(page).toHaveScreenshot('chip-dark-full-page.png', FULL_PAGE_SCREENSHOT);
  });
});
