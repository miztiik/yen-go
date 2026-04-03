/**
 * No-Modals Test — Verify no modal overlays appear when navigating pages.
 * T-U40: Navigate to each page from home, verify no modal overlay.
 */
import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'Daily', navText: 'Daily Challenge', expectedUrl: '/daily' },
  { name: 'Rush', navText: 'Puzzle Rush', expectedUrl: '/puzzle-rush' },
  { name: 'Collections', navText: 'Collections', expectedUrl: '/collections' },
  { name: 'Training', navText: 'Training', expectedUrl: '/training' },
  { name: 'Technique', navText: 'Technique', expectedUrl: '/technique' },
  { name: 'Random', navText: 'Random', expectedUrl: '/random' },
];

test.describe('No Modals — All pages render as full pages', () => {
  for (const page of PAGES) {
    test(`${page.name} page has no modal overlay`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
      });
      const p = await context.newPage();

      // Navigate to home
      await p.goto('/');
      await p.waitForLoadState('networkidle');

      // Click the tile
      const tile = p.locator(`text=${page.navText}`).first();
      if (await tile.isVisible()) {
        await tile.click();
        await p.waitForTimeout(1000);
      } else {
        // Navigate directly
        await p.goto(page.expectedUrl);
        await p.waitForLoadState('networkidle');
      }

      // Verify no modal overlay exists
      const modalOverlay = p.locator('[data-testid*="modal"], .modal-overlay, [role="dialog"]');
      const overlayCount = await modalOverlay.count();
      expect(overlayCount).toBe(0);

      // Verify page has full layout (not just a stub behind a modal)
      const pageLayout = p.locator('[data-layout="single-column"]');
      await expect(pageLayout).toBeVisible();

      await context.close();
    });
  }
});
