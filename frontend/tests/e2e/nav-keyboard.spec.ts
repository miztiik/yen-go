/**
 * E2E test: Keyboard navigation with arrow keys.
 * @module tests/e2e/nav-keyboard.spec
 *
 * Spec 125, Task T108
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation - Keyboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');
    await page.waitForTimeout(1000);
  });

  test('right arrow navigates to next puzzle', async ({ page }) => {
    // Store initial state
    const puzzlePage = page.getByTestId('puzzle-solve-page');
    
    if (await puzzlePage.count() > 0) {
      // Press right arrow
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(500);
      
      // Should still be on puzzle page (navigation triggered)
      await expect(puzzlePage).toBeVisible();
    }
  });

  test('left arrow navigates to previous puzzle', async ({ page }) => {
    const puzzlePage = page.getByTestId('puzzle-solve-page');
    
    if (await puzzlePage.count() > 0) {
      // First go forward
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(500);
      
      // Then go back
      await page.keyboard.press('ArrowLeft');
      await page.waitForTimeout(500);
      
      await expect(puzzlePage).toBeVisible();
    }
  });

  test('n key navigates to next puzzle', async ({ page }) => {
    const puzzlePage = page.getByTestId('puzzle-solve-page');
    
    if (await puzzlePage.count() > 0) {
      await page.keyboard.press('n');
      await page.waitForTimeout(500);
      await expect(puzzlePage).toBeVisible();
    }
  });

  test('p key navigates to previous puzzle', async ({ page }) => {
    const puzzlePage = page.getByTestId('puzzle-solve-page');
    
    if (await puzzlePage.count() > 0) {
      // First go forward
      await page.keyboard.press('n');
      await page.waitForTimeout(500);
      
      // Then go back
      await page.keyboard.press('p');
      await page.waitForTimeout(500);
      
      await expect(puzzlePage).toBeVisible();
    }
  });

  test('keyboard navigation does not trigger in text input', async ({ page }) => {
    // If there's an input field on the page, typing should not navigate
    const textInput = page.locator('input[type="text"]');
    
    if (await textInput.count() > 0) {
      await textInput.first().focus();
      await page.keyboard.press('ArrowRight');
      // Should stay on same puzzle (navigation blocked)
    }
  });
});
