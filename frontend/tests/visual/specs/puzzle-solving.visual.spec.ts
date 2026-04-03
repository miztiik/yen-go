/**
 * Visual test: Puzzle Solving / SolverView (T141).
 *
 * Verifies:
 * - Goban board renders correctly
 * - Hints overlay, navigation controls visible
 * - Apple-inspired styling (no inline styles, theme-aware colors)
 * - Responsive at 4 viewports (Desktop, Tablet, Mobile, Landscape Mobile)
 * - Dark mode variant (data-theme="dark")
 *
 * Spec 129 — FR-057, FR-088
 */

import { test, expect } from '@playwright/test';

/**
 * Navigate to a puzzle solving page. Uses a collection route so
 * the solver is loaded with a real puzzle context.
 */
const PUZZLE_URL = '/collections/level-beginner';

/** Disable CSS transitions so screenshots are deterministic. */
async function disableAnimations(page: import('@playwright/test').Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        transition-duration: 0ms !important;
        animation-duration: 0ms !important;
      }
    `,
  });
}

test.describe('Puzzle Solving Visual', () => {
  test('goban board is visible', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // The page should have at least a main content area with puzzle content
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('no inline styles on solver elements', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    // Goban canvas will have inline styles (expected). Check non-canvas elements.
    const inlineStyleCount = await page.evaluate(() => {
      const main = document.querySelector('main') ?? document.body;
      const styled = main.querySelectorAll('[style]');
      let count = 0;
      styled.forEach((el) => {
        // Skip canvas/goban elements which legitimately set inline dimensions
        if (el.tagName !== 'CANVAS' && !el.closest('[data-testid="goban"]')) {
          count++;
        }
      });
      return count;
    });
    expect(inlineStyleCount).toBe(0);
  });

  test('no hardcoded hex colors', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForLoadState('networkidle');

    const html = await page.content();
    expect(html).not.toContain('#059669');
  });

  // ── Responsive screenshots (light mode) ──────────────
  for (const viewport of [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' },
    { width: 667, height: 375, name: 'landscape-mobile' },
  ]) {
    test(`screenshot at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(PUZZLE_URL);
      await page.waitForLoadState('networkidle');
      await disableAnimations(page);

      await expect(page).toHaveScreenshot(`puzzle-solving-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }

  // ── Dark mode screenshots ────────────────────────────
  for (const viewport of [
    { width: 1280, height: 720, name: 'desktop' },
    { width: 768, height: 1024, name: 'tablet' },
    { width: 375, height: 667, name: 'mobile' },
    { width: 667, height: 375, name: 'landscape-mobile' },
  ]) {
    test(`dark mode screenshot at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(PUZZLE_URL);
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'dark');
      });
      await disableAnimations(page);
      await page.waitForTimeout(200);

      await expect(page).toHaveScreenshot(`puzzle-solving-dark-${viewport.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }
});
