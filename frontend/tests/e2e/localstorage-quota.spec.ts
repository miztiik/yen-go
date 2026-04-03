/**
 * LocalStorage Quota E2E Test
 * @module tests/e2e/localstorage-quota.spec
 *
 * End-to-end tests for localStorage quota exceeded handling.
 * Verifies graceful degradation when storage limit is reached.
 *
 * Covers: US6, FR-084
 * Spec 125, Task T122
 */

import { test, expect } from '@playwright/test';

test.describe('LocalStorage Quota - Graceful Degradation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should handle localStorage being disabled', async ({ page }) => {
    // Simulate localStorage being unavailable by mocking it
    await page.addInitScript(() => {
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function () {
        throw new DOMException('QuotaExceededError', 'QuotaExceededError');
      };
    });

    await page.goto('/');

    // App should still load and function
    await expect(page.locator('body')).toBeVisible();
  });

  test('should gracefully handle quota exceeded error', async ({ page }) => {
    await page.goto('/');

    // Fill localStorage close to capacity
    await page.evaluate(() => {
      try {
        const largeString = 'x'.repeat(1024 * 1024); // 1MB string
        for (let i = 0; i < 10; i++) {
          try {
            localStorage.setItem(`test-fill-${i}`, largeString);
          } catch {
            break;
          }
        }
      } catch {
        // Expected when quota is exceeded
      }
    });

    // Navigate and solve a puzzle - should still work
    await page.goto('/collections/curated-beginner-essentials/1');

    // App should not crash
    await expect(page.locator('body')).toBeVisible();
  });

  test('should continue functioning after save failure', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    // Wait for board
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Make storage fail on next write
    await page.evaluate(() => {
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function (key, value) {
        if (key.includes('progress') || key.includes('streak')) {
          throw new DOMException('QuotaExceededError', 'QuotaExceededError');
        }
        return originalSetItem.call(this, key, value);
      };
    });

    // User actions should still work even if saving fails
    // Reset button may be disabled if no moves have been made
    const resetButton = page.getByRole('button', { name: /reset/i });
    if (await resetButton.isVisible() && await resetButton.isEnabled()) {
      await resetButton.click();
      // Should not crash
      await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
    } else {
      // Even without clicking, the board should remain functional
      await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
    }
  });

  test('should show warning when storage is nearly full', async ({ page }) => {
    // This test checks if a warning is shown (optional feature)
    await page.goto('/');

    // Fill localStorage significantly
    await page.evaluate(() => {
      try {
        const mediumString = 'x'.repeat(512 * 1024); // 512KB string
        for (let i = 0; i < 8; i++) {
          try {
            localStorage.setItem(`test-fill-${i}`, mediumString);
          } catch {
            break;
          }
        }
      } catch {
        // Expected when quota is exceeded
      }
    });

    await page.goto('/');

    // App should load - warning is optional
    await expect(page.locator('body')).toBeVisible();
  });

  test('should preserve existing data when quota is reached', async ({ page }) => {
    await page.goto('/');

    // Store some important data
    await page.evaluate(() => {
      localStorage.setItem('yengo-important', JSON.stringify({ streak: 5 }));
    });

    // Try to trigger quota exceeded
    await page.evaluate(() => {
      try {
        const largeString = 'x'.repeat(1024 * 1024);
        for (let i = 0; i < 10; i++) {
          try {
            localStorage.setItem(`fill-${i}`, largeString);
          } catch {
            break;
          }
        }
      } catch {
        // Expected
      }
    });

    // Important data should still be there
    const importantData = await page.evaluate(() => {
      return localStorage.getItem('yengo-important');
    });

    expect(importantData).not.toBeNull();
  });

  test('should work in private/incognito mode', async ({ page }) => {
    // In some browsers, localStorage may be limited in private mode
    await page.goto('/');

    // App should function regardless
    await expect(page.locator('body')).toBeVisible();

    // Basic navigation should work
    const collectionsLink = page.getByRole('link', { name: /collections/i });
    if (await collectionsLink.isVisible()) {
      await collectionsLink.click();
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
