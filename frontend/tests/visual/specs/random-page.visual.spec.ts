/**
 * Visual test: Random Challenge Page (T096).
 * US8: Verify Random Challenge CTA meets WCAG AA 4.5:1 contrast ratio.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

test.describe('Random Challenge Page Visual', () => {
  test('CTA button meets WCAG AA contrast ratio', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/random');
    await page.waitForLoadState('networkidle');

    // Find the primary CTA button
    const cta = page.locator(
      'button:has-text("Start"), button:has-text("Random"), button:has-text("Challenge"), [data-testid="start-challenge"]'
    ).first();

    if (await cta.isVisible()) {
      // Extract computed colors for contrast calculation
      const colors = await cta.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return {
          color: style.color,
          backgroundColor: style.backgroundColor,
        };
      });

      // Parse RGB values
      const parseRGB = (rgb: string) => {
        const match = rgb.match(/(\d+)/g);
        if (!match) return null;
        return match.map(Number);
      };

      const fg = parseRGB(colors.color);
      const bg = parseRGB(colors.backgroundColor);

      if (fg && bg) {
        // WCAG relative luminance formula
        const luminance = (r: number, g: number, b: number) => {
          const [rs, gs, bs] = [r, g, b].map((c) => {
            const s = c / 255;
            return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
        };

        const l1 = luminance(fg[0], fg[1], fg[2]);
        const l2 = luminance(bg[0], bg[1], bg[2]);
        const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

        // WCAG AA requires 4.5:1 for normal text
        expect(ratio).toBeGreaterThanOrEqual(4.5);
      }
    }

    await expect(page).toHaveScreenshot('random-page-cta.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('random page dark mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.addInitScript(() => {
      document.documentElement.dataset.theme = 'dark';
    });
    await page.goto('/random');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('random-page-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.05,
    });
  });
});
