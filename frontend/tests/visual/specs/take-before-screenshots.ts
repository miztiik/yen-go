/**
 * Playwright screenshot script — captures BEFORE state of Training, Technique, Collections pages.
 * Run: npx playwright test --config=playwright.screenshots.config.ts tests/screenshots/take-before-screenshots.ts
 */
import { test } from '@playwright/test';

test.describe('BEFORE screenshots — Training page redesign audit', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('01 — Training page (full)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const trainingTile = page.locator('text=Training').first();
    await trainingTile.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'tests/screenshots/before/01-training-full.png', fullPage: true });
  });

  test('02 — Training page grid mode', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const trainingTile = page.locator('text=Training').first();
    await trainingTile.click();
    await page.waitForTimeout(1000);
    const gridBtn = page.locator('[data-testid="view-grid"], [aria-label*="Grid"], [aria-label*="grid"]');
    if (await gridBtn.count() > 0) {
      await gridBtn.first().click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: 'tests/screenshots/before/02-training-grid.png', fullPage: true });
  });

  test('03 — Training page list mode', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const trainingTile = page.locator('text=Training').first();
    await trainingTile.click();
    await page.waitForTimeout(1000);
    const listBtn = page.locator('[data-testid="view-list"], [aria-label*="List"], [aria-label*="list"]');
    if (await listBtn.count() > 0) {
      await listBtn.first().click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: 'tests/screenshots/before/03-training-list.png', fullPage: true });
  });

  test('04 — Technique page (reference)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    // Home tile text is just "Technique"
    const techniqueTile = page.locator('[data-testid*="technique"], :text("Technique")').first();
    await techniqueTile.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'tests/screenshots/before/04-technique-focus.png', fullPage: true });
  });

  test('05 — Collections page (reference)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'tests/screenshots/before/05-collections.png', fullPage: true });
  });

  test('06 — Settings dropdown overlap', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const avatarBtn = page.locator('nav button, header button, [data-testid*="settings"], [data-testid*="profile"], [aria-label*="Settings"], [aria-label*="Profile"]');
    const count = await avatarBtn.count();
    if (count > 0) {
      await avatarBtn.last().click();
      await page.waitForTimeout(800);
    }
    await page.screenshot({ path: 'tests/screenshots/before/06-settings-dropdown.png' });
  });

  test('07 — Training Random Challenge visibility', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);
    const trainingTile = page.locator('text=Training').first();
    await trainingTile.click();
    await page.waitForTimeout(1000);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'tests/screenshots/before/07-training-random-challenge.png' });
  });
});
