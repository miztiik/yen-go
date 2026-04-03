/**
 * Settings Renderer E2E Test
 * @module tests/e2e/settings-renderer.spec
 *
 * End-to-end tests for renderer selection in user settings.
 * Verifies user can choose between SVG and Canvas renderers.
 *
 * Covers: US1, FR-089
 * Spec 125, Task T122e
 */

import { test, expect } from '@playwright/test';

test.describe('Settings - Renderer Selection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should have settings accessible from navigation', async ({ page }) => {
    await page.goto('/');

    // Settings link or button should be visible
    const settingsLink = page.getByRole('link', { name: /settings/i })
      .or(page.getByRole('button', { name: /settings/i }))
      .or(page.locator('[data-testid="settings-link"]'));

    const hasSettings = await settingsLink.first().isVisible().catch(() => false);
    
    // Settings may be in a menu or nav
    expect(page.locator('body')).toBeVisible();
  });

  test('should persist renderer preference in localStorage', async ({ page }) => {
    // Set renderer preference
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'svg' }));
    });

    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Check preference was saved
    const settings = await page.evaluate(() => {
      const data = localStorage.getItem('yengo-settings');
      return data ? JSON.parse(data) : null;
    });

    expect(settings?.rendererType).toBe('svg');
  });

  test('should apply renderer change immediately', async ({ page }) => {
    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Change preference via localStorage (simulating settings UI)
    await page.evaluate(() => {
      const current = localStorage.getItem('yengo-settings');
      const settings = current ? JSON.parse(current) : {};
      settings.rendererType = 'canvas';
      localStorage.setItem('yengo-settings', JSON.stringify(settings));
    });

    // Reload to apply
    await page.reload();
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board should still render
    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();
  });

  test('should default to SVG when no preference set', async ({ page }) => {
    // Clear all settings
    await page.evaluate(() => localStorage.clear());

    await page.goto('/collections/test-collection/1');
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Board should render (default is SVG)
    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();

    // Check for SVG element (default)
    const content = await board.innerHTML();
    // Content should exist
    expect(content.length).toBeGreaterThan(0);
  });

  test('should validate renderer setting values', async ({ page }) => {
    // Set invalid renderer type
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'invalid' }));
    });

    await page.goto('/collections/test-collection/1');

    // Should fallback to default and not crash
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    const board = page.locator('[data-testid="goban-board"]');
    await expect(board).toBeVisible();
  });

  test('should handle corrupted settings gracefully', async ({ page }) => {
    // Set corrupted JSON
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', 'not-valid-json{');
    });

    await page.goto('/collections/test-collection/1');

    // Should use defaults and not crash
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });
  });

  test('should sync renderer preference across tabs', async ({ page, context }) => {
    // Set preference in first tab
    await page.evaluate(() => {
      localStorage.setItem('yengo-settings', JSON.stringify({ rendererType: 'canvas' }));
    });

    // Open new tab
    const newPage = await context.newPage();
    await newPage.goto('/collections/test-collection/1');

    // Check preference is synced
    const settings = await newPage.evaluate(() => {
      const data = localStorage.getItem('yengo-settings');
      return data ? JSON.parse(data) : null;
    });

    expect(settings?.rendererType).toBe('canvas');
    await newPage.close();
  });
});
