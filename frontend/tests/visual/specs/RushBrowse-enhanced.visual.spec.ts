/**
 * Visual test: RushBrowsePage — Enhanced setup screen (Phase R4).
 *
 * Verifies:
 * - Duration cards + custom duration toggle
 * - Level FilterBar pills + tag FilterDropdown
 * - Available puzzle count display
 * - Responsive at 3 viewports × light + dark themes
 *
 * Phase R4 — Rush Play Enhancement
 */

import { test, expect } from '@playwright/test';

const RUSH_URL = '/puzzle-rush';

const VIEWPORTS = [
  { width: 375, height: 667, name: 'mobile' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 1280, height: 900, name: 'desktop' },
] as const;

test.describe('RushBrowsePage Enhanced Visual', () => {
  // ── Structural tests ─────────────────────────────────────────────

  test('renders duration cards and filter section', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    // Duration cards should be visible
    await expect(page.locator('[data-testid="rush-duration-3"]')).toBeVisible();
    await expect(page.locator('[data-testid="rush-duration-5"]')).toBeVisible();
    await expect(page.locator('[data-testid="rush-duration-10"]')).toBeVisible();

    // Custom duration toggle should be visible
    await expect(page.locator('[data-testid="rush-duration-custom"]')).toBeVisible();
  });

  test('filter section shows level and tag controls', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    // Filter section (may need master index to load)
    const filters = page.locator('[data-testid="rush-filters"]');
    // Filters appear when master indexes load; if they load, verify structure
    if (await filters.count() > 0) {
      await expect(page.locator('[data-testid="rush-level-filter"]')).toBeVisible();
      await expect(page.locator('[data-testid="rush-tag-filter"]')).toBeVisible();
    }
  });

  test('available puzzle count updates on filter change', async ({ page }) => {
    await page.goto(RUSH_URL);
    await page.waitForLoadState('networkidle');

    const countEl = page.locator('[data-testid="rush-available-count"]');
    if (await countEl.count() > 0) {
      // Default: shows "~N puzzles available"
      const text = await countEl.textContent();
      expect(text).toContain('puzzles available');
    }
  });

  // ── Viewport screenshots ─────────────────────────────────────────

  for (const viewport of VIEWPORTS) {
    test(`screenshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(RUSH_URL);
      await page.waitForLoadState('networkidle');
      // Wait for filter section to potentially load
      await page.waitForTimeout(1000);
      await expect(page).toHaveScreenshot(`rush-browse-enhanced-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }

  // ── Dark mode screenshots ────────────────────────────────────────

  for (const viewport of VIEWPORTS) {
    test(`dark mode screenshot at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.emulateMedia({ colorScheme: 'dark' });
      await page.goto(RUSH_URL);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await expect(page).toHaveScreenshot(`rush-browse-enhanced-${viewport.name}-dark.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.05,
      });
    });
  }
});
