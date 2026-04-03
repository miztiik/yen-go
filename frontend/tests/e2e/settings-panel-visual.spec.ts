/**
 * E2E visual tests for Settings panel.
 *
 * Verifies the dropdown background is opaque after CSS variable fix.
 */

import { test, expect } from '@playwright/test';

test.describe('Settings Panel Visual', () => {
  test('light theme — dropdown has solid background', async ({ page }) => {
    await page.goto('/yen-go/');
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();

    const menu = page.getByRole('menu', { name: 'Settings' });
    await expect(menu).toBeVisible();
    await expect(menu).toHaveScreenshot('settings-dropdown-light.png');
  });

  test('dark theme — dropdown has solid background', async ({ page }) => {
    // Set dark theme via localStorage
    await page.addInitScript(() => {
      localStorage.setItem('yengo:settings', JSON.stringify({
        theme: 'dark', soundEnabled: true, coordinateLabels: true,
        autoAdvance: false, autoAdvanceDelay: 3,
      }));
    });
    await page.goto('/yen-go/');
    const gearButton = page.getByRole('button', { name: 'Settings' });
    await gearButton.click();

    const menu = page.getByRole('menu', { name: 'Settings' });
    await expect(menu).toBeVisible();
    await expect(menu).toHaveScreenshot('settings-dropdown-dark.png');
  });
});
