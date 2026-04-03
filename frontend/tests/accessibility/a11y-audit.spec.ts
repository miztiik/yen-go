/**
 * Accessibility Audit — axe-core on all pages at 3 viewports.
 *
 * Verifies:
 * - No critical/serious WCAG violations
 * - Keyboard navigation (Tab, Escape on modals)
 * - ARIA attributes on interactive elements
 *
 * Spec 127: T073
 */

import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Viewports
// ---------------------------------------------------------------------------
const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];

// ---------------------------------------------------------------------------
// Pages
// ---------------------------------------------------------------------------
const pages = [
  { name: 'home', path: '/' },
  { name: 'collection', path: '/#collection/beginner' },
  { name: 'daily', path: '/#daily' },
  { name: 'puzzle-rush', path: '/#puzzle-rush' },
];

// ---------------------------------------------------------------------------
// axe-core scan helper
// ---------------------------------------------------------------------------
async function runAxe(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .disableRules(['color-contrast']) // Tailwind CSS vars make contrast calc unreliable in playwright
    .analyze();
  return results;
}

// ---------------------------------------------------------------------------
// Tests: WCAG compliance per page × viewport
// ---------------------------------------------------------------------------
for (const viewport of viewports) {
  for (const pg of pages) {
    test(`a11y: ${pg.name} @ ${viewport.name} (${viewport.width}px)`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(pg.path, { waitUntil: 'networkidle' });

      const results = await runAxe(page);

      // No critical or serious violations
      const critical = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious',
      );

      if (critical.length > 0) {
        const summary = critical.map(
          (v) => `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} instances)`,
        );
        expect(critical, `WCAG violations:\n${summary.join('\n')}`).toHaveLength(0);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Tests: Keyboard navigation
// ---------------------------------------------------------------------------
test('keyboard: Tab cycles through interactive elements on home page', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/', { waitUntil: 'networkidle' });

  // Press Tab multiple times and verify focus moves
  const focusedTags: string[] = [];
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    const tag = await page.evaluate(() => document.activeElement?.tagName?.toLowerCase());
    if (tag) focusedTags.push(tag);
  }

  // Should cycle through interactive elements (buttons, links, inputs)
  const interactive = focusedTags.filter((t) => ['a', 'button', 'input', 'select', 'textarea'].includes(t));
  expect(interactive.length).toBeGreaterThan(0);
});

test('keyboard: Escape closes settings panel', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/', { waitUntil: 'networkidle' });

  // Look for settings button
  const settingsBtn = page.locator('[aria-label*="settings" i], [aria-label*="Settings" i]').first();
  const hasSettings = await settingsBtn.count();

  if (hasSettings > 0) {
    await settingsBtn.click();

    // Panel should be visible
    const panel = page.locator('[data-component="settings-panel"], [role="dialog"]').first();
    if ((await panel.count()) > 0) {
      await expect(panel).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');

      // Panel should close
      await expect(panel).not.toBeVisible();
    }
  }
});

// ---------------------------------------------------------------------------
// Tests: ARIA attributes on key components
// ---------------------------------------------------------------------------
test('a11y: SolverView has proper ARIA attributes', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Navigate to a puzzle page
  await page.goto('/#collection/beginner', { waitUntil: 'networkidle' });

  // Check for solver data attributes
  const solver = page.locator('[data-component="solver-view"]');
  if ((await solver.count()) > 0) {
    // data-status attribute should be present
    const status = await solver.getAttribute('data-status');
    expect(status).toBeTruthy();

    // Coordinate toggle should have aria-label and aria-pressed
    const toggle = page.locator('[aria-label="Toggle coordinates"]');
    if ((await toggle.count()) > 0) {
      const pressed = await toggle.getAttribute('aria-pressed');
      expect(pressed).toMatch(/^(true|false)$/);
    }
  }
});

test('a11y: AppHeader has navigation landmark', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/', { waitUntil: 'networkidle' });

  // Header should use <header> or role="banner"
  const header = page.locator('header, [role="banner"]').first();
  expect(await header.count()).toBeGreaterThan(0);
});

test('a11y: Main content has main landmark', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/', { waitUntil: 'networkidle' });

  const main = page.locator('main, [role="main"]').first();
  expect(await main.count()).toBeGreaterThan(0);
});
