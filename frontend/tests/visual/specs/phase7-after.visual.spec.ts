/**
 * Phase 7/8 AFTER Screenshots — Capture the fixed state after all changes.
 * Captures all 6 browse pages + home grid in both desktop and mobile.
 */
import { test } from '@playwright/test';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCREENSHOT_DIR = resolve(__dirname, '../baselines/phase7/after');

test.describe('Phase 7/8: After Screenshots', () => {
  test('Home grid with SVG icons (desktop)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'home-desktop-light.png'), fullPage: true });
  });

  test('Daily browse page (desktop)', async ({ page }) => {
    await page.goto('/daily');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'daily-desktop-light.png'), fullPage: true });
  });

  test('Rush browse page (desktop)', async ({ page }) => {
    await page.goto('/puzzle-rush');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'rush-desktop-light.png'), fullPage: true });
  });

  test('Collections browse page (desktop)', async ({ page }) => {
    await page.goto('/collections');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'collections-desktop-light.png'), fullPage: true });
  });

  test('Training selection page (desktop)', async ({ page }) => {
    await page.goto('/training');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'training-desktop-light.png'), fullPage: true });
  });

  test('Random browse page (desktop)', async ({ page }) => {
    await page.goto('/random');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'random-desktop-light.png'), fullPage: true });
  });

  test('Technique focus page (desktop)', async ({ page }) => {
    await page.goto('/technique/tesuji');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: resolve(SCREENSHOT_DIR, 'technique-desktop-light.png'), fullPage: true });
  });
});
