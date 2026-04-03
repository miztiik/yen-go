/**
 * Layout Consistency — Playwright visual regression tests.
 *
 * Screenshot comparisons for key pages at 3 viewport sizes:
 * - Mobile: 375×812
 * - Tablet: 768×1024
 * - Desktop: 1440×900
 *
 * Spec 127: T060, FR-044, FR-045
 */

import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
] as const;

const PAGES = [
  { name: 'home', path: '/' },
  { name: 'collection', path: '/collection/beginner' },
  { name: 'daily', path: '/daily' },
  { name: 'rush', path: '/rush' },
] as const;

for (const viewport of VIEWPORTS) {
  test.describe(`Layout @ ${viewport.name} (${viewport.width}×${viewport.height})`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
    });

    for (const page of PAGES) {
      test(`${page.name} page renders without layout breaks`, async ({ page: pw }) => {
        await pw.goto(page.path, { waitUntil: 'networkidle' });

        // Wait for boot + content
        await pw.waitForTimeout(1000);

        // Visual regression screenshot
        await expect(pw).toHaveScreenshot(
          `${page.name}-${viewport.name}.png`,
          {
            fullPage: true,
            maxDiffPixelRatio: 0.02,
          },
        );
      });

      test(`${page.name} page has no horizontal overflow`, async ({ page: pw }) => {
        await pw.goto(page.path, { waitUntil: 'networkidle' });
        await pw.waitForTimeout(500);

        const hasOverflow = await pw.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });

        expect(hasOverflow).toBe(false);
      });
    }

    test('header stays sticky on scroll', async ({ page: pw }) => {
      await pw.goto('/', { waitUntil: 'networkidle' });
      await pw.waitForTimeout(500);

      // Scroll down
      await pw.evaluate(() => window.scrollBy(0, 500));
      await pw.waitForTimeout(200);

      // Header should still be visible (sticky top-0)
      const header = pw.locator('[data-component="app-header"], header').first();
      if (await header.count() > 0) {
        const box = await header.boundingBox();
        expect(box).not.toBeNull();
        // Header top should be near viewport top (sticky)
        if (box) {
          expect(box.y).toBeLessThanOrEqual(5);
        }
      }
    });

    test('dark mode applies correctly', async ({ page: pw }) => {
      await pw.goto('/', { waitUntil: 'networkidle' });
      await pw.waitForTimeout(500);

      // Set dark theme
      await pw.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'dark');
      });
      await pw.waitForTimeout(300);

      await expect(pw).toHaveScreenshot(
        `dark-mode-${viewport.name}.png`,
        {
          fullPage: true,
          maxDiffPixelRatio: 0.02,
        },
      );
    });
  });
}
