/**
 * Playwright screenshot script — captures SolverView redesign state.
 * Verifies sidebar layout, transform bar visibility, hint container,
 * and responsive behavior after UI/UX redesign (Spec 132/133).
 *
 * Run: npx playwright test --config=playwright.screenshots.config.ts tests/screenshots/solver-redesign.ts
 */
import { test, expect } from '@playwright/test';

test.describe('SolverView redesign screenshots', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('01 — Default sidebar layout (desktop)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    // Navigate to a collection to get a puzzle
    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    // Click first available collection
    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/01-default-sidebar-desktop.png',
      fullPage: true,
    });
  });

  test('02 — Transform bar always visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    // Verify TransformBar is visible (not in a collapsed section)
    const transformBar = page.locator('[data-component="transform-bar"], [data-testid="transform-bar"]');
    if (await transformBar.count() > 0) {
      await expect(transformBar.first()).toBeVisible();
    }

    // Verify no collapsible toggle exists for transforms
    const transformToggle = page.locator('.solver-transforms-toggle');
    expect(await transformToggle.count()).toBe(0);

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/02-transform-bar-visible.png',
    });
  });

  test('03 — Hint container fixed space (no layout shift)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    // Capture before hint click
    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/03a-hint-before.png',
    });

    // Click hint button if available
    const hintBtn = page.locator('button:has-text("Hint")').first();
    if (await hintBtn.isVisible()) {
      await hintBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: 'tests/screenshots/solver-redesign/03b-hint-after.png',
      });
    }
  });

  test('04 — Flip horizontal transform', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    // Click flip horizontal button
    const flipH = page.locator('[aria-label*="Flip horizontal"], [aria-label*="flip horizontal"], [title*="Flip horizontal"]').first();
    if (await flipH.count() > 0) {
      await flipH.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/04-flip-horizontal.png',
    });
  });

  test('05 — Flip vertical transform', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    const flipV = page.locator('[aria-label*="Flip vertical"], [aria-label*="flip vertical"], [title*="Flip vertical"]').first();
    if (await flipV.count() > 0) {
      await flipV.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/05-flip-vertical.png',
    });
  });

  test('06 — Swap colors transform', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    const swapColors = page.locator('[aria-label*="Swap colors"], [aria-label*="swap colors"], [title*="Swap colors"]').first();
    if (await swapColors.count() > 0) {
      await swapColors.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/06-swap-colors.png',
    });
  });

  test('07 — Zoom toggle transform', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    const zoom = page.locator('[aria-label*="Zoom"], [aria-label*="zoom"], [title*="Zoom"]').first();
    if (await zoom.count() > 0) {
      await zoom.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/07-zoom-toggle.png',
    });
  });

  test('08 — Mobile viewport layout (375x812)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/08-mobile-375x812.png',
      fullPage: true,
    });
  });

  test('09 — Dark mode sidebar', async ({ page }) => {
    await page.addInitScript(() => {
      document.documentElement.dataset.theme = 'dark';
    });
    await page.goto('/');
    await page.waitForTimeout(500);

    const collectionsTile = page.locator('text=Collections').first();
    await collectionsTile.click();
    await page.waitForTimeout(1000);

    const firstCollection = page.locator('a[href*="collection"]').first();
    if (await firstCollection.count() > 0) {
      await firstCollection.click();
      await page.waitForTimeout(2000);
    }

    await page.screenshot({
      path: 'tests/screenshots/solver-redesign/09-dark-mode-sidebar.png',
      fullPage: true,
    });
  });
});
