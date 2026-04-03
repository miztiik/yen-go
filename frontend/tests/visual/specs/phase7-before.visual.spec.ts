/**
 * Phase 7 BEFORE Screenshots — Capture the broken state before fixes.
 * T-U01b: Rush navigation bug
 * T-U02b: Puzzle renderer stub state
 */
import { test } from '@playwright/test';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCREENSHOT_DIR = resolve(__dirname, '../baselines/phase7/before');

test.describe('Phase 7: Before Screenshots', () => {
  test('T-U01b: Rush page shows modal then stub content (desktop, light)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click the Rush tile
    const rushTile = page.locator('text=Puzzle Rush').first();
    if (await rushTile.isVisible()) {
      await rushTile.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: resolve(SCREENSHOT_DIR, 'rush-desktop-light.png'),
      fullPage: true,
    });
  });

  test('T-U02b: Training page puzzle stub (desktop, light)', async ({ page }) => {
    // Navigate directly to training level
    await page.goto('/training/beginner');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: resolve(SCREENSHOT_DIR, 'training-desktop-light.png'),
      fullPage: true,
    });
  });

  test('T-U02b: Random page puzzle stub (desktop, light)', async ({ page }) => {
    await page.goto('/random');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: resolve(SCREENSHOT_DIR, 'random-desktop-light.png'),
      fullPage: true,
    });
  });
});
