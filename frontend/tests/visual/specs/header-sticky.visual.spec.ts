/**
 * Visual test: Header Sticky (T151).
 * US16: Verify header is NOT sticky — scrolls out of viewport.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

test.describe('Header Non-Sticky Visual', () => {
  test('header scrolls out of viewport on scroll (not sticky)', async ({ page }) => {
    // Navigate to a page long enough to scroll
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');

    // Get header position before scroll
    const header = page.locator('header').first();
    const headerBox = await header.boundingBox();
    expect(headerBox).not.toBeNull();

    // Scroll 500px down
    await page.evaluate(() => window.scrollBy(0, 500));
    await page.waitForTimeout(300);

    // After scrolling, header should not be in viewport (not sticky)
    const headerBoxAfter = await header.boundingBox();
    if (headerBoxAfter) {
      // If header is visible, its top should be negative (scrolled up)
      expect(headerBoxAfter.y).toBeLessThan(0);
    }
    // Otherwise header is not in DOM viewport at all — which is fine
  });

  test('header is not position: sticky or fixed', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const header = page.locator('header').first();
    const position = await header.evaluate(
      (el) => window.getComputedStyle(el).position,
    );
    expect(position).not.toBe('sticky');
    expect(position).not.toBe('fixed');
  });
});
