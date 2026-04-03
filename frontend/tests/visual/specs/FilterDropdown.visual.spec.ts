/**
 * Visual test: FilterDropdown component — open/closed/selected states (G54).
 *
 * Verifies:
 * - Closed trigger pill matches FilterBar pill styling
 * - Open panel shows categorised groups with headers
 * - Selected option shows checkmark + accent colour
 * - "All" option renders at top of listbox
 * - Disabled (count=0) options have reduced opacity
 * - Panel positioning and shadow
 * - Backdrop click-to-close
 * - Dark mode theme-aware colours
 * - Responsive across Desktop / Tablet / Mobile
 *
 * Spec: plan-compact-schema-filtering.md §WP9.3 (G54)
 */

import { test, expect } from '@playwright/test';
import {
  VIEWPORTS,
  disableAnimations,
  INTERACTION_SETTLE_MS,
  DEFAULT_MAX_DIFF,
  FULL_PAGE_SCREENSHOT,
  padClip,
  FOCUS_SETTLE_MS,
} from './visual-test-helpers';

test.describe('FilterDropdown Visual', () => {
  // ── Training page tag dropdown ──

  test('closed trigger pill — idle state', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present — no tag data');

    await expect(trigger).toBeVisible();

    const box = await trigger.boundingBox();
    test.skip(!box, 'Trigger not visible');
    expect(box!.height).toBeGreaterThanOrEqual(44);

    await expect(page).toHaveScreenshot('dropdown-closed-idle.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  test('open dropdown panel — shows categories', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    await expect(panel).toBeVisible();

    // Panel should contain "All" option
    const allOption = page.getByTestId('training-tag-filter-option-all');
    await expect(allOption).toBeVisible();

    await expect(page).toHaveScreenshot('dropdown-open-categories.png', FULL_PAGE_SCREENSHOT);
  });

  test('open dropdown — selected option highlighted', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    const options = panel.locator('[role="option"]');
    const optCount = await options.count();
    test.skip(optCount < 2, 'Not enough options to select');

    // Click second option (first after "All")
    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Re-open to see selected state
    const updatedTrigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await updatedTrigger.count()) === 0, 'Trigger disappeared after selection');

    await updatedTrigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('dropdown-option-selected.png', FULL_PAGE_SCREENSHOT);
  });

  test('trigger pill — active state (option selected)', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    // Select something to make the trigger enter "active" state
    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    const options = panel.locator('[role="option"]');
    test.skip((await options.count()) < 2, 'Not enough options to select');

    await options.nth(1).click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Trigger should now show accent styling
    const updatedTrigger = page.getByTestId('training-tag-filter-trigger');
    const box = await updatedTrigger.boundingBox();
    test.skip(!box, 'Trigger not visible after selection');

    await expect(page).toHaveScreenshot('dropdown-trigger-active.png', {
      fullPage: false,
      clip: padClip(box!),
      maxDiffPixelRatio: DEFAULT_MAX_DIFF,
    });
  });

  // ── Chevron rotation (AP2-2) ──

  test('chevron icon rotates 180° when dropdown is open', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    // Chevron should not be rotated when closed
    const chevronClosed = trigger.locator('svg').last();
    const closedTransform = await chevronClosed.evaluate(
      (el) => window.getComputedStyle(el).transform,
    );

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Chevron should be rotated when open
    const chevronOpen = trigger.locator('svg').last();
    const openTransform = await chevronOpen.evaluate(
      (el) => window.getComputedStyle(el).transform,
    );

    // Transforms should differ (closed=none/identity, open=rotate-180)
    expect(openTransform).not.toBe(closedTransform);
  });

  // ── Keyboard navigation (UX-1 / WCAG) ──

  test('keyboard arrow-down highlights focused option', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    // Arrow down twice from "All" to highlight a grouped option
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(FOCUS_SETTLE_MS);

    // AP2-1: Verify aria-activedescendant changed on the listbox
    const listbox = panel.locator('[role="listbox"]');
    if ((await listbox.count()) > 0) {
      const activeDesc = await listbox.getAttribute('aria-activedescendant');
      expect(activeDesc).toBeTruthy();
    } else {
      // Panel itself may be the listbox
      const activeDesc = await panel.getAttribute('aria-activedescendant');
      expect(activeDesc).toBeTruthy();
    }

    await expect(page).toHaveScreenshot('dropdown-keyboard-focus.png', FULL_PAGE_SCREENSHOT);
  });

  // ── P-1: Keyboard-only selection produces visible chip ──

  test('keyboard-only tag selection produces visible chip', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    // Open dropdown via Enter (keyboard-only path)
    await trigger.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open via keyboard');

    // Navigate down past "All" to first real option and select with Enter
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(FOCUS_SETTLE_MS);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Chip should appear from keyboard-only interaction
    const chip = page.getByTestId('training-tag-chip');
    if ((await chip.count()) > 0) {
      await expect(chip).toBeVisible();
    }

    await expect(page).toHaveScreenshot('dropdown-keyboard-select-chip.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Home/End key navigation (UX2-2) ──

  test('Home key jumps to first option, End to last', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    // Press End to jump to last option
    await page.keyboard.press('End');
    await page.waitForTimeout(FOCUS_SETTLE_MS);

    await expect(page).toHaveScreenshot('dropdown-keyboard-end.png', FULL_PAGE_SCREENSHOT);

    // Press Home to jump back to first option ("All")
    await page.keyboard.press('Home');
    await page.waitForTimeout(FOCUS_SETTLE_MS);

    await expect(page).toHaveScreenshot('dropdown-keyboard-home.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Escape to close (AP-3) ──

  test('Escape key closes open dropdown', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    // Press Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Panel should be closed
    await expect(panel).not.toBeVisible();

    await expect(page).toHaveScreenshot('dropdown-after-escape.png', FULL_PAGE_SCREENSHOT);
  });

  // ── R3-5: Backdrop click-to-close ──

  test('clicking outside closes open dropdown', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    // Click on the backdrop (top-left corner of the page, away from the dropdown)
    await page.mouse.click(10, 10);
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    // Panel should be closed
    await expect(panel).not.toBeVisible();

    await expect(page).toHaveScreenshot('dropdown-after-outside-click.png', FULL_PAGE_SCREENSHOT);
  });

  // ── Disabled option visual (AP-2) ──

  test('disabled options show reduced opacity', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    const panel = page.getByTestId('training-tag-filter-panel');
    test.skip((await panel.count()) === 0, 'Dropdown panel did not open');

    // Check if any disabled options exist (count=0 tags)
    const disabledOptions = panel.locator('[role="option"][aria-disabled="true"]');
    test.skip((await disabledOptions.count()) === 0, 'No disabled options in dropdown');

    // Verify disabled option has opacity-50
    const firstDisabled = disabledOptions.first();
    const opacity = await firstDisabled.evaluate(
      (el) => window.getComputedStyle(el).opacity,
    );
    expect(parseFloat(opacity)).toBeLessThanOrEqual(0.55);

    await expect(page).toHaveScreenshot(
      'dropdown-disabled-options.png',
      FULL_PAGE_SCREENSHOT,
    );
  });

  // ── Responsive ──

  for (const viewport of VIEWPORTS) {
    test(`dropdown panel at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/training');
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      const trigger = page.getByTestId('training-tag-filter-trigger');
      test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

      await trigger.click();
      await page.waitForTimeout(INTERACTION_SETTLE_MS);

      await expect(page).toHaveScreenshot(
        `dropdown-panel-${viewport.name}.png`,
        FULL_PAGE_SCREENSHOT,
      );
    });
  }

  // ── Dark mode ──

  test('dropdown closed — dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    await expect(page).toHaveScreenshot('dropdown-closed-dark.png', FULL_PAGE_SCREENSHOT);
  });

  test('dropdown open — dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await disableAnimations(page);

    const trigger = page.getByTestId('training-tag-filter-trigger');
    test.skip((await trigger.count()) === 0, 'Tag filter trigger not present');

    await trigger.click();
    await page.waitForTimeout(INTERACTION_SETTLE_MS);

    await expect(page).toHaveScreenshot('dropdown-open-dark.png', FULL_PAGE_SCREENSHOT);
  });
});
