/**
 * Visual Tests for FeedbackOverlay Component
 * 
 * Tests different feedback types: correct, incorrect, invalid, suboptimal, hint
 */

import { test, expect } from '@playwright/test';

test.describe('FeedbackOverlay Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Feedback Types', () => {
    test('correct feedback', async ({ page }) => {
      const fixture = page.locator('#feedback-correct');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('feedback-correct.png');
    });

    test('incorrect feedback', async ({ page }) => {
      const fixture = page.locator('#feedback-incorrect');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('feedback-incorrect.png');
    });

    test('invalid feedback', async ({ page }) => {
      const fixture = page.locator('#feedback-invalid');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('feedback-invalid.png');
    });

    test('suboptimal feedback', async ({ page }) => {
      const fixture = page.locator('#feedback-suboptimal');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('feedback-suboptimal.png');
    });

    test('hint feedback', async ({ page }) => {
      const fixture = page.locator('#feedback-hint');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('feedback-hint.png');
    });
  });
});
