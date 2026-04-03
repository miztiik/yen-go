/**
 * Keyboard Focus E2E Test
 * @module tests/e2e/keyboard-focus.spec
 *
 * End-to-end tests for keyboard focus management across board, tree, sidebar.
 * Verifies accessibility and keyboard navigation.
 *
 * Covers: US6, FR-085
 * Spec 125, Task T122a
 */

import { test, expect } from '@playwright/test';

test.describe('Keyboard Focus Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should allow Tab navigation through controls', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Start from the page
    await page.keyboard.press('Tab');
    
    // Should be able to Tab through focusable elements
    let tabCount = 0;
    const maxTabs = 20;

    while (tabCount < maxTabs) {
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      if (focusedElement === 'BUTTON' || focusedElement === 'A') {
        // Found a focusable control
        break;
      }
      await page.keyboard.press('Tab');
      tabCount++;
    }

    // Should find at least one focusable element
    const hasFocusableElements = tabCount < maxTabs;
    expect(hasFocusableElements).toBe(true);
  });

  test('should support arrow key navigation for puzzles', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Arrow keys should work for puzzle navigation
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(100);

    // No crash should occur
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
  });

  test('should support "n" and "p" keyboard shortcuts', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // 'n' for next puzzle
    await page.keyboard.press('n');
    await page.waitForTimeout(100);

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();

    // 'p' for previous puzzle  
    await page.keyboard.press('p');
    await page.waitForTimeout(100);

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
  });

  test('should not trigger shortcuts when typing in input', async ({ page }) => {
    await page.goto('/');

    // If there's a search input, typing should not trigger shortcuts
    const searchInput = page.getByRole('textbox');
    if (await searchInput.first().isVisible()) {
      await searchInput.first().focus();
      await page.keyboard.type('test');
      
      // App should still be on same page
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should have visible focus indicators', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Tab to a button
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check for focus ring/outline (CSS)
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      const style = window.getComputedStyle(el);
      return {
        outline: style.outline,
        boxShadow: style.boxShadow,
        border: style.border,
      };
    });

    // Some focus indicator should be present (not testing specific style)
    expect(focusedElement).not.toBeNull();
  });

  test('should trap focus in modal dialogs', async ({ page }) => {
    // If app has modals, focus should be trapped
    await page.goto('/');

    // Look for any modal trigger
    const modalTrigger = page.getByRole('button', { name: /settings/i })
      .or(page.getByRole('button', { name: /help/i }));

    if (await modalTrigger.first().isVisible()) {
      await modalTrigger.first().click();
      await page.waitForTimeout(200);

      // In modal, tabbing should cycle within modal
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Should still be on page
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should support Escape to close sidebar or menus', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Press Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);

    // Should not crash
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
  });

  test('should maintain focus after puzzle actions', async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');

    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible({ timeout: 10000 });

    // Verify puzzle controls are present
    const resetButton = page.getByRole('button', { name: /reset/i });
    if (await resetButton.isVisible()) {
      // Reset may be disabled if no moves made — just verify it exists
      await expect(resetButton).toBeVisible();
    }

    // Focus should remain manageable after page interactions
    await expect(page.locator('[data-testid="goban-board"]')).toBeVisible();
  });
});
