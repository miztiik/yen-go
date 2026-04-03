/**
 * Visual Tests for QualityBadge Component
 * 
 * Verifies the 5-level puzzle quality system is correctly displayed.
 * This test fulfills T050 from spec 024-puzzle-quality-system.
 * 
 * 5 Puzzle Quality Levels: Unverified (1), Basic (2), Standard (3), High (4), Premium (5)
 */

import { test, expect } from '@playwright/test';

test.describe('QualityBadge Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');
  });

  test.describe('All Puzzle Quality Levels', () => {
    test('all 5 puzzle quality levels displayed together', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-all');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-all.png');
    });

    test('unverified (1) - light gray stars', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-1');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-1.png');
    });

    test('basic (2) - gray stars', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-2');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-2.png');
    });

    test('standard (3) - bronze stars', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-3');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-3.png');
    });

    test('high (4) - silver stars', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-4');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-4.png');
    });

    test('premium (5) - gold stars', async ({ page }) => {
      const fixture = page.locator('#puzzle-quality-5');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('puzzle-quality-5.png');
    });
  });

  test.describe('Badge Variants', () => {
    test('stars variant (default)', async ({ page }) => {
      const fixture = page.locator('#quality-badge-variant-stars');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-variant-stars.png');
    });

    test('compact variant', async ({ page }) => {
      const fixture = page.locator('#quality-badge-variant-compact');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-variant-compact.png');
    });

    test('full variant', async ({ page }) => {
      const fixture = page.locator('#quality-badge-variant-full');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-variant-full.png');
    });
  });

  test.describe('Badge Sizes', () => {
    test('small size', async ({ page }) => {
      const fixture = page.locator('#quality-badge-size-small');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-size-small.png');
    });

    test('medium size (default)', async ({ page }) => {
      const fixture = page.locator('#quality-badge-size-medium');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-size-medium.png');
    });

    test('large size', async ({ page }) => {
      const fixture = page.locator('#quality-badge-size-large');
      await expect(fixture).toBeVisible();
      await expect(fixture).toHaveScreenshot('quality-badge-size-large.png');
    });
  });

  test.describe('Tooltip Interaction', () => {
    test('tooltip appears on hover', async ({ page }) => {
      const badge = page.locator('#quality-badge-tooltip-test .quality-badge');
      await badge.hover();
      
      // Wait for tooltip to appear
      await page.waitForSelector('.quality-badge-tooltip', { timeout: 2000 });
      
      // Screenshot with tooltip visible
      const fixture = page.locator('#quality-badge-tooltip-test');
      await expect(fixture).toHaveScreenshot('quality-badge-tooltip-hover.png');
    });
  });
});
