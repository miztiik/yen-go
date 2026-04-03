/**
 * E2E tests for Auto-Advance feature.
 *
 * Tests the settings toggle, delay stepper, countdown UI,
 * and cancellation mechanisms.
 */

import { test, expect } from '@playwright/test';

const SETTINGS_KEY = 'yengo:settings';

/** Navigate to a collection page with puzzles. */
async function goToCollectionPage(page: import('@playwright/test').Page) {
  // Use elementary training context — has puzzles available
  await page.goto('/yen-go/contexts/training/elementary');
  // Wait for the solver to load
  await page.waitForSelector('[data-component="solver-view"]', { timeout: 15000 });
}

/** Enable auto-advance via localStorage before navigation. */
async function enableAutoAdvance(page: import('@playwright/test').Page, delay = 3) {
  await page.addInitScript(({ key, delay }: { key: string; delay: number }) => {
    const existing = localStorage.getItem(key);
    const settings = existing ? JSON.parse(existing) : {};
    settings.autoAdvance = true;
    settings.autoAdvanceDelay = delay;
    localStorage.setItem(key, JSON.stringify(settings));
  }, { key: SETTINGS_KEY, delay });
}

test.describe('Auto-Advance Settings', () => {
  test('settings panel shows Auto-Advance toggle, default OFF', async ({ page }) => {
    await page.goto('/yen-go/');
    // Open settings gear
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();
    // Verify auto-advance toggle exists and is off
    const toggle = page.getByRole('switch', { name: /auto-advance/i });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-checked', 'false');
  });

  test('toggling auto-advance ON reveals delay stepper', async ({ page }) => {
    await page.goto('/yen-go/');
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();

    // Toggle ON
    const toggle = page.getByRole('switch', { name: /auto-advance/i });
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', 'true');

    // Delay stepper should appear
    const decreaseBtn = page.getByRole('button', { name: 'Decrease delay' });
    const increaseBtn = page.getByRole('button', { name: 'Increase delay' });
    await expect(decreaseBtn).toBeVisible();
    await expect(increaseBtn).toBeVisible();

    // Default delay should be 3s
    await expect(page.getByText('3s')).toBeVisible();
  });

  test('delay stepper adjusts within 1–5 range', async ({ page }) => {
    await page.goto('/yen-go/');
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();

    // Toggle ON first
    const toggle = page.getByRole('switch', { name: /auto-advance/i });
    await toggle.click();

    const decreaseBtn = page.getByRole('button', { name: 'Decrease delay' });
    const increaseBtn = page.getByRole('button', { name: 'Increase delay' });

    // Increase to 5
    await increaseBtn.click();
    await expect(page.getByText('4s')).toBeVisible();
    await increaseBtn.click();
    await expect(page.getByText('5s')).toBeVisible();

    // At max, increase should be disabled
    await expect(increaseBtn).toBeDisabled();

    // Decrease to 1
    for (let i = 0; i < 4; i++) await decreaseBtn.click();
    await expect(page.getByText('1s')).toBeVisible();
    await expect(decreaseBtn).toBeDisabled();
  });
});

test.describe('Auto-Advance Settings Panel Visibility', () => {
  test('settings dropdown has opaque background (CSS fix)', async ({ page }) => {
    await page.goto('/yen-go/');
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();

    // The settings dropdown menu should be visible
    const menu = page.getByRole('menu', { name: 'Settings' });
    await expect(menu).toBeVisible();

    // Verify it has a non-transparent computed background
    const bgColor = await menu.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    // Should NOT be transparent (rgba(0,0,0,0)) or empty
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
    expect(bgColor).not.toBe('transparent');
    expect(bgColor).not.toBe('');
  });
});

test.describe('Auto-Advance Keyboard Shortcut', () => {
  test('pressing A toggles auto-advance and shows toast', async ({ page }) => {
    await goToCollectionPage(page);

    // Press 'a' to toggle auto-advance ON
    await page.keyboard.press('a');

    // Toast should appear
    const toast = page.getByTestId('auto-advance-toast');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Auto-Advance: ON');

    // Toast should disappear after ~1.5s
    await expect(toast).not.toBeVisible({ timeout: 3000 });
  });
});
