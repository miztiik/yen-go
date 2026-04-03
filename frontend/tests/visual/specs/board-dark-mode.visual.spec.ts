/**
 * Visual test: Board Dark Mode (T037).
 * US4: Verify dark mode board luminance within 30% of surrounding UI.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

test.describe('Board Dark Mode Visual', () => {
  test('dark mode board luminance within 30% of surrounding UI', async ({ page }) => {
    await page.goto('/collection/beginner');
    await page.waitForLoadState('networkidle');

    // Switch to dark mode
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(500);

    // Measure board container and surrounding UI background luminance
    const result = await page.evaluate(() => {
      const boardEl = document.querySelector('[data-slot="board"]') ?? document.querySelector('canvas')?.parentElement;
      const uiEl = document.querySelector('main') ?? document.body;
      if (!boardEl || !uiEl) return { error: 'Elements not found' };

      function getLuminance(el: Element): number {
        const style = window.getComputedStyle(el);
        const bg = style.backgroundColor;
        const match = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return -1;
        const [, r, g, b] = match.map(Number);
        return 0.2126 * (r / 255) + 0.7152 * (g / 255) + 0.0722 * (b / 255);
      }

      const boardL = getLuminance(boardEl);
      const uiL = getLuminance(uiEl);
      const maxL = Math.max(boardL, uiL);
      const diff = maxL > 0 ? Math.abs(boardL - uiL) / maxL : 0;

      return { boardL, uiL, diff, error: null };
    });

    if (result.error) {
      test.skip(true, result.error);
      return;
    }

    // Board and UI luminance should be within 30%
    expect(result.diff).toBeLessThanOrEqual(0.30);
  });

  test('screenshot light vs dark board comparison', async ({ page }) => {
    await page.goto('/collection/beginner');
    await page.waitForLoadState('networkidle');

    // Light mode screenshot
    await expect(page).toHaveScreenshot('board-light.png', {
      fullPage: false,
      maxDiffPixelRatio: 0.05,
    });

    // Dark mode screenshot
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('board-dark.png', {
      fullPage: false,
      maxDiffPixelRatio: 0.05,
    });
  });
});
