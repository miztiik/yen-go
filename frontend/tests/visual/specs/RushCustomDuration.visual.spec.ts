/**
 * Visual test: Rush Custom Duration slider (Phase R4).
 *
 * Verifies:
 * - Custom duration toggle opens slider
 * - Slider displays duration value
 * - "Start Rush" button shows selected duration
 * - Responsive at mobile + desktop + dark mode
 *
 * Phase R4 — Rush Play Enhancement
 */

import { test, expect } from '@playwright/test';

const RUSH_URL = '/puzzle-rush';

test.describe('RushCustomDuration Visual', () => {
  test('custom toggle opens slider panel', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    // Click custom button
    const customBtn = page.locator('[data-testid="rush-duration-custom"]');
    await customBtn.click();

    // Slider should appear
    await expect(page.locator('[data-testid="rush-custom-slider"]')).toBeVisible();
    await expect(page.locator('[data-testid="rush-custom-value"]')).toBeVisible();
    await expect(page.locator('[data-testid="rush-custom-start"]')).toBeVisible();
  });

  test('slider shows duration value', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('[data-testid="rush-duration-custom"]').click();

    // Default value should be 7:00
    const valueEl = page.locator('[data-testid="rush-custom-value"]');
    const value = await valueEl.textContent();
    expect(value).toMatch(/^\d+:\d{2}$/); // matches "M:SS" format
  });

  test('start button includes duration text', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('[data-testid="rush-duration-custom"]').click();

    const startBtn = page.locator('[data-testid="rush-custom-start"]');
    const text = await startBtn.textContent();
    expect(text).toContain('Start Rush');
    expect(text).toMatch(/\d+:\d{2}/); // includes duration
  });

  // ── Screenshots with slider open ─────────────────────────────────

  test('screenshot: slider open on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="rush-duration-custom"]').click();
    await page.waitForTimeout(300); // animation settle
    await expect(page).toHaveScreenshot('rush-custom-slider-mobile.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('screenshot: slider open on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="rush-duration-custom"]').click();
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot('rush-custom-slider-desktop.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('screenshot: slider open in dark mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="rush-duration-custom"]').click();
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot('rush-custom-slider-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  // ── Slider toggle behavior ───────────────────────────────────────

  test('clicking custom twice toggles slider off', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    const customBtn = page.locator('[data-testid="rush-duration-custom"]');
    await customBtn.click();
    await expect(page.locator('[data-testid="rush-custom-slider"]')).toBeVisible();

    // Toggle off
    await customBtn.click();
    await expect(page.locator('[data-testid="rush-custom-slider"]')).not.toBeVisible();
  });
});
